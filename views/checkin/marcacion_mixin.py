"""Pestaña de marcación biométrica por huella.

El flujo es totalmente automático: el postulante apoya el dedo en el
lector y el sistema descubre quién es, le muestra su nombre, aula y
asiento, y registra el ingreso. No hay que buscar a nadie ni elegir dedo.

El reconocimiento facial vive en su propia pestaña
(:mod:`desktop.views.checkin.reconocimiento_mixin`), así que aquí no hay
cámara ni búsqueda por nombre.
"""

import logging
import time
from contextlib import contextmanager

from PySide6.QtCore import QPointF, QRectF, QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from desktop.config.app_config import AppConfig
from desktop.views.checkin.workers import (
    IdentificacionHuellaController,
    liberar_lector_compartido,
)
from desktop.biometria import (
    detectar_lectores, libfprint_disponible, sdk_zk_disponible,
)

log = logging.getLogger(__name__)

# Cuánto tiempo permanece la tarjeta de resultado en pantalla antes de
# volver al panel de espera. Antes era 3,5 s, demasiado corto para leer
# nombre, aula y asiento de un vistazo.
TIEMPO_MOSTRAR_RESULTADO_MS = 30000
TIEMPO_REINICIO_LECTOR_MS = 900

# ── Ajustes de rendimiento ──
ANIMAR_ESPERA = True             # False = huella estática (menos CPU en equipos lentos)
EDAD_MAX_ESTADO_LECTOR_S = 20    # cada cuánto se vuelve a escanear el bus USB
UMBRAL_OPERACION_LENTA_S = 0.15  # avisa en consola si algo tarda más que esto
UMBRAL_BLOQUEO_UI_MS = 400       # avisa si la ventana se congela más que esto

# Colores suaves para el avatar (fondo, texto)
_COLORES_AVATAR = (
    ("#DBEAFE", "#1E40AF"),
    ("#DCFCE7", "#166534"),
    ("#FEF3C7", "#92400E"),
    ("#EDE9FE", "#5B21B6"),
    ("#FCE7F3", "#9D174D"),
    ("#E0F2FE", "#075985"),
)
_COLOR_TONO = {"exito": "#16A34A", "error": "#DC2626", "aviso": "#D97706"}


# ======================================================================
# Utilidades
# ======================================================================
@contextmanager
def _medir(nombre):
    """Registra en consola las operaciones lentas del hilo de la interfaz."""
    inicio = time.perf_counter()
    try:
        yield
    finally:
        duracion = time.perf_counter() - inicio
        if duracion >= UMBRAL_OPERACION_LENTA_S:
            log.warning(
                "Operación lenta en el hilo de la interfaz: %s tardó %.0f ms",
                nombre, duracion * 1000,
            )


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _fuente_etiqueta(px, espaciado):
    """QSS no soporta letter-spacing; se define por código."""
    fuente = QFont()
    fuente.setPixelSize(px)
    fuente.setWeight(QFont.Bold)
    fuente.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return fuente


def _iniciales(nombre):
    partes = str(nombre).split()
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def _formatear_hora(valor):
    """Deja solo HH:MM:SS aunque el servidor mande fecha completa."""
    texto = str(valor)
    if "T" in texto:
        texto = texto.split("T", 1)[1]
    elif " " in texto:
        texto = texto.split(" ")[-1]
    return texto.split(".")[0][:8]


def _pixmap_resultado(tono, lado=64):
    """Insignia circular con check, cruz o signo de exclamación."""
    pm = QPixmap(lado * 2, lado * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawEllipse(QRectF(2, 2, lado - 4, lado - 4))

    s = float(lado)
    p.setPen(QPen(QColor(_COLOR_TONO[tono]), s * 0.09, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    if tono == "exito":
        ruta = QPainterPath()
        ruta.moveTo(s * 0.29, s * 0.52)
        ruta.lineTo(s * 0.44, s * 0.67)
        ruta.lineTo(s * 0.72, s * 0.36)
        p.drawPath(ruta)
    elif tono == "error":
        p.drawLine(QPointF(s * 0.35, s * 0.35), QPointF(s * 0.65, s * 0.65))
        p.drawLine(QPointF(s * 0.65, s * 0.35), QPointF(s * 0.35, s * 0.65))
    else:
        p.drawLine(QPointF(s * 0.5, s * 0.28), QPointF(s * 0.5, s * 0.55))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(_COLOR_TONO[tono]))
        p.drawEllipse(QPointF(s * 0.5, s * 0.71), s * 0.055, s * 0.055)
    p.end()
    return pm


# ======================================================================
# Widgets propios
# ======================================================================
class IconoHuella(QWidget):
    """Huella dibujada con anillos que laten mientras se espera el dedo."""

    def __init__(self, lado=210, parent=None):
        super().__init__(parent)
        self.setFixedSize(lado, lado)
        self._fase = 0.35
        # ~30 cuadros por segundo bastan y gastan mucho menos que 60.
        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._avanzar)

    def _avanzar(self):
        self._fase = (self._fase + 33 / 2600) % 1.0
        self.update()

    def showEvent(self, evento):
        if ANIMAR_ESPERA:
            self._timer.start()
        super().showEvent(evento)

    def hideEvent(self, evento):
        self._timer.stop()
        super().hideEvent(evento)

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        centro = QPointF(self.width() / 2, self.height() / 2)

        # Anillos que se expanden y se desvanecen
        p.setBrush(Qt.NoBrush)
        for i in range(3):
            f = (self._fase + i / 3) % 1.0
            radio = 54 + f * 48
            p.setPen(QPen(QColor(47, 111, 237, int(100 * (1 - f))), 2))
            p.drawEllipse(centro, radio, radio)

        # Disco central
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#E8F0FD"))
        p.drawEllipse(centro, 54, 54)

        # Surcos de la huella
        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor("#2F6FED"), 2.6, Qt.SolidLine, Qt.RoundCap))
        for radio, inicio, tramo in (
            (8, 0, 360), (16, 50, 270), (24, 140, 300), (32, 215, 285), (40, 300, 250)
        ):
            rect = QRectF(centro.x() - radio, centro.y() - radio, radio * 2, radio * 2)
            p.drawArc(rect, int(inicio * 16), int(tramo * 16))
        p.end()


class BarraTiempo(QWidget):
    """Barra fina que se vacía mientras la tarjeta de resultado está visible."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._fraccion = 1.0
        self._color = QColor("#16A34A")

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def set_fraccion(self, valor):
        self._fraccion = max(0.0, min(1.0, valor))
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEF2F7"))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        if self._fraccion > 0:
            p.setBrush(self._color)
            p.drawRoundedRect(QRectF(0, 0, self.width() * self._fraccion, self.height()), 3, 3)
        p.end()


class PanelEspera(QFrame):
    """Pantalla de espera: huella animada e indicaciones grandes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("panelEspera")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(32, 28, 32, 28)
        lay.setSpacing(6)
        lay.addStretch(1)
        lay.addWidget(IconoHuella(), 0, Qt.AlignHCenter)
        lay.addSpacing(8)

        self.lbl_titulo = QLabel("Listo para marcar")
        self.lbl_titulo.setObjectName("esperaTitulo")
        self.lbl_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_sub = QLabel("Apoya el dedo en el lector")
        self.lbl_sub.setObjectName("esperaSub")
        self.lbl_sub.setAlignment(Qt.AlignCenter)
        self.lbl_nota = QLabel("El sistema identificará al postulante automáticamente")
        self.lbl_nota.setObjectName("esperaNota")
        self.lbl_nota.setAlignment(Qt.AlignCenter)

        lay.addWidget(self.lbl_titulo)
        lay.addWidget(self.lbl_sub)
        lay.addSpacing(4)
        lay.addWidget(self.lbl_nota)
        lay.addStretch(1)


class EstadoLector(QLabel):
    """Etiqueta de estado con un punto de color a la izquierda."""

    COLORES = {
        "ok": "#22C55E",
        "aviso": "#F59E0B",
        "error": "#EF4444",
        "activo": "#2F6FED",
        "neutro": "#94A3B8",
    }

    def __init__(self, texto="", parent=None):
        super().__init__(texto, parent)
        self._tono = "neutro"
        self.setContentsMargins(20, 0, 0, 0)

    def set_tono(self, tono):
        self._tono = tono
        self.update()

    def paintEvent(self, evento):
        super().paintEvent(evento)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(self.COLORES.get(self._tono, self.COLORES["neutro"])))
        p.drawEllipse(QPointF(7, self.height() / 2), 4.5, 4.5)
        p.end()


# ======================================================================
# Estilos
# ======================================================================
ESTILOS_MARCACION = """
    QWidget#tabMarcacion { background: #F1F5F9; }
    /* Las etiquetas no heredan fondos ni bordes de reglas generales */
    QLabel { background: transparent; border: none; }

    QLabel#banner {
        color: #0E4F63; background: #E6F6FA;
        border: 1px solid #B5E3EE; border-radius: 12px;
        padding: 10px 16px; font-size: 13px;
    }

    /* ---------- Espera ---------- */
    QFrame#panelEspera {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px;
    }
    QLabel#esperaTitulo { color: #0F2C59; font-size: 32px; font-weight: 800; }
    QLabel#esperaSub    { color: #334155; font-size: 20px; font-weight: 500; }
    QLabel#esperaNota   { color: #94A3B8; font-size: 13px; }

    /* ---------- Resultado ---------- */
    QFrame#resultCard {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px;
    }
    QFrame#resHeader {
        border: none;
        border-top-left-radius: 19px; border-top-right-radius: 19px;
        border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
    }
    QFrame#resHeader[tono="exito"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15803D, stop:1 #22A455);
    }
    QFrame#resHeader[tono="error"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B91C1C, stop:1 #DC3C3C);
    }
    QFrame#resHeader[tono="aviso"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D98A12);
    }
    QLabel#resTitulo    { color: #FFFFFF; font-size: 30px; font-weight: 800; }
    QLabel#resSubtitulo { color: rgba(255, 255, 255, 0.90); font-size: 15px; font-weight: 500; }

    QLabel#resNombre  { color: #0F172A; font-size: 30px; font-weight: 800; }
    QLabel#resMateria { color: #475569; font-size: 15px; font-weight: 600; }
    QLabel#resChip {
        background: #EEF3FB; color: #1E4E96;
        border-radius: 11px; padding: 4px 12px;
        font-size: 13px; font-weight: 700;
    }
    QLabel#resDetalle { color: #334155; font-size: 20px; }
    QLabel#resPie     { color: #0F172A; font-size: 22px; font-weight: 700; }

    QFrame#tile {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px;
    }
    QFrame#tileDestacado {
        background: #E8F0FD; border: 1px solid #BFD3F7; border-radius: 14px;
    }
    QLabel#tileEtiqueta { color: #64748B; }
    QLabel#tileValor    { color: #0F172A; font-size: 26px; font-weight: 800; }
    QLabel#tileValorGrande { color: #1E54B7; font-size: 40px; font-weight: 800; }

    QFrame#motivo {
        background: #FEF2F2; border: 1px solid #FECACA; border-radius: 14px;
    }
    QLabel#motivoEtiqueta { color: #B91C1C; }
    QLabel#motivoTexto    { color: #7F1D1D; font-size: 19px; font-weight: 600; }

    /* ---------- Barra de estado ---------- */
    QFrame#barraEstado {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
    }
    QLabel#lectorTexto { color: #334155; font-size: 12px; font-weight: 600; }
    QLabel#resumenChip {
        background: #EEF3FB; color: #1E4E96;
        border-radius: 11px; padding: 4px 12px;
        font-size: 12px; font-weight: 700;
    }
    QPushButton#btnDetener {
        background: #FFFFFF; color: #B91C1C;
        border: 1px solid #FCA5A5; border-radius: 9px;
        padding: 0 14px; font-size: 12px; font-weight: 700;
    }
    QPushButton#btnDetener:hover { background: #FEF2F2; }
    QPushButton#btnReanudar {
        background: #1E54B7; color: #FFFFFF; border: none;
        border-radius: 9px; padding: 0 14px;
        font-size: 12px; font-weight: 700;
    }
    QPushButton#btnReanudar:hover { background: #17449A; }
    QPushButton#btnReanudar:disabled { background: #A9BEE3; }
"""


class MarcacionMixin:
    # ══════════════════════ CICLO DE VIDA ══════════════════════
    def set_examen(self, data_examen: dict):
        examen_anterior = self.info_examen.get("id_examen")
        examen_nuevo = data_examen.get("id_examen")
        mismo_examen = examen_anterior == examen_nuevo and examen_nuevo is not None
        if getattr(self, "_estacion_activa", False) and not mismo_examen:
            self.detener_estacion()
        self.info_examen = data_examen
        self.lbl_materia.setText(f"Materia: {data_examen.get('materia', '--')}")
        self.lbl_aula.setText(f"Aula: {data_examen.get('nombre_aula', '--')}")
        self.lbl_cierre.setText(f"Cierre: {data_examen.get('cierra_a_las', '--')}")
        if not mismo_examen:
            # Solo se invalida la caché cuando cambia realmente el examen.
            self._resumen_huellas(0, 0)
            self._huellas_examen_cache = None

    def iniciar_estacion(self):
        """Entra a la pantalla de registro e inicia la lectura automática."""
        if getattr(self, "_estacion_activa", False):
            return
        self._estacion_activa = True
        self.btn_huella.setVisible(False)
        self.counter_timer.start(5000)
        # Se difiere para que la pantalla se pinte antes de consultar al servidor.
        QTimer.singleShot(250, self.actualizar_contador)
        self.lbl_estado_lector.setText("Iniciando lector de huella…")
        self.lbl_estado_lector.set_tono("aviso")
        self._inicio_lector_timer.start(1000)
        self._iniciar_vigilancia_fluidez()

    def detener_estacion(self):
        """Sale de la pantalla de registro: corta todo lo que esté corriendo."""
        self._estacion_activa = False
        self._arrancando_identificacion = False
        self._inicio_lector_timer.stop()
        self.counter_timer.stop()
        self.hide_result_timer.stop()
        self._detener_vigilancia_fluidez()
        self.detener_auto_deteccion()
        if self._identificacion and self._identificacion.activo:
            self._identificacion.detener()
            self._restablecer_identificacion()
        # El lector se deja abierto entre identificaciones para ir más rápido;
        # al salir de la estación se libera (el panel admin lo necesita).
        liberar_lector_compartido(self)
        self.limpiar_resultado()

    # ══════════════════════ IDENTIFICACIÓN ══════════════════════
    def identificar_huella(self):
        """Arranca la identificación automática: sólo hay que apoyar el dedo.

        No hace falta buscar al postulante ni elegir dedo: el controlador
        prueba las huellas habilitadas del examen y devuelve quién es.
        """
        if not getattr(self, "_estacion_activa", False):
            return
        if self._identificacion and self._identificacion.activo:
            return
        if getattr(self, "_arrancando_identificacion", False):
            return

        app_key = AppConfig.get_app_key()
        id_examen = self.info_examen.get("id_examen")
        if not app_key:
            self.mostrar_resultado(
                False, "CLIENTE NO CONFIGURADO",
                "No existe una clave APP_CLIENT_KEY válida.", "")
            return
        if not id_examen:
            self.mostrar_resultado(
                False, "SIN EXAMEN ACTIVO",
                "Esta estación no tiene un examen asignado.", "", tono="aviso")
            return

        self.btn_huella.setVisible(False)
        self.btn_cancelar_huella.setVisible(True)
        self.lbl_estado_lector.setText("Preparando lector de huella…")
        self.lbl_estado_lector.set_tono("activo")

        # Abrir el lector puede tardar. Se difiere un instante para que la
        # pantalla alcance a pintar «Preparando lector…» antes de bloquearse.
        self._arrancando_identificacion = True
        QTimer.singleShot(40, lambda: self._arrancar_identificacion(app_key, id_examen))

    def _arrancar_identificacion(self, app_key, id_examen):
        if not getattr(self, "_arrancando_identificacion", False):
            return  # se canceló o se salió de la estación mientras esperaba
        self._arrancando_identificacion = False
        if not getattr(self, "_estacion_activa", False):
            return
        with _medir("abrir el lector e iniciar la identificación"):
            self._identificacion = IdentificacionHuellaController(
                self, app_key, id_examen, self._huellas_examen_cache)
            self._identificacion.iniciar()

    def _guardar_huellas_examen_cache(self, datos):
        self._huellas_examen_cache = datos

    def cancelar_identificacion(self):
        estaba_activa = bool(
            (self._identificacion and self._identificacion.activo)
            or getattr(self, "_arrancando_identificacion", False)
        )
        if self._identificacion and self._identificacion.activo:
            self._identificacion.detener()
        self._restablecer_identificacion()
        if estaba_activa:
            # Va después del reset, que refresca el estado del lector.
            self.lbl_estado_lector.setText("Identificación cancelada")
            self.lbl_estado_lector.set_tono("aviso")
            # Permite volver a activar el lector sin salir de la pantalla.
            self.btn_huella.setText("Reanudar lector")
            self.btn_huella.setVisible(True)

    # ══════════════════════ CALLBACKS ══════════════════════
    def _estado_identificacion(self, mensaje):
        """Progreso de la identificación automática."""
        self.lbl_estado_lector.setText(mensaje)
        self.lbl_estado_lector.set_tono("activo")

    def _resumen_huellas(self, habilitadas, sin_habilitar):
        """Cuántos postulantes del examen pueden marcar con huella."""
        if not habilitadas and not sin_habilitar:
            self.lbl_resumen_huellas.setText("Examen: —")
            return
        partes = []
        partes.append(f"{habilitadas} huella(s) habilitada(s)" if habilitadas
                      else "ninguna huella habilitada")
        if sin_habilitar:
            partes.append(f"{sin_habilitar} sin habilitar")
        self.lbl_resumen_huellas.setText("Examen: " + " · ".join(partes))

    def _identificacion_error(self, mensaje):
        # Tras un error conviene volver a mirar el USB (¿se desconectó?), pero
        # sin hacerlo en cada reintento: se limita a una vez cada 5 s.
        self._restablecer_identificacion(max_edad_s=5)
        self.mostrar_resultado(False, "NO IDENTIFICADO", mensaje, "", tono="aviso")
        if getattr(self, "_estacion_activa", False):
            QTimer.singleShot(2000, self.identificar_huella)

    def _identificacion_lista(self, data, candidato):
        """Muestra a quién pertenece la huella y el resultado del ingreso."""
        self._restablecer_identificacion()
        self.mostrar_resultado_acceso(data, candidato)
        self.actualizar_contador()
        if getattr(self, "_estacion_activa", False):
            QTimer.singleShot(TIEMPO_REINICIO_LECTOR_MS, self.identificar_huella)

    def _restablecer_identificacion(self, max_edad_s=None):
        self.btn_huella.setEnabled(True)
        self.btn_huella.setText("Reanudar lector")
        self.btn_cancelar_huella.setVisible(False)
        self._identificacion = None
        self._arrancando_identificacion = False
        self.actualizar_estado_lector(max_edad_s)

    # ══════════════════════ RESULTADO EN PANTALLA ══════════════════════
    def mostrar_resultado_acceso(self, data, candidato):
        """Tarjeta con los datos del postulante identificado."""
        candidato = candidato or {}
        nombre = data.get("nombre_completo") or candidato.get("nombre_completo", "") or "Postulante"
        ci = data.get("ci") or candidato.get("ci", "")
        aceptado = data.get("resultado") == "ACEPTADO"
        mensaje = data.get("mensaje") or ""

        if aceptado:
            tono = "exito"
            titulo = "ACCESO CONCEDIDO"
            subtitulo = mensaje or "Puede ingresar al aula asignada."
        else:
            tono = "error"
            titulo = "ACCESO RECHAZADO"
            subtitulo = "No se registró el ingreso."

        self.lbl_res_titulo.setText(titulo)
        self.lbl_res_subtitulo.setText(subtitulo)

        # Identidad
        indice = sum(ord(c) for c in str(ci or nombre)) % len(_COLORES_AVATAR)
        fondo, texto = _COLORES_AVATAR[indice]
        self.lbl_res_avatar.setText(_iniciales(nombre))
        self.lbl_res_avatar.setStyleSheet(
            f"background: {fondo}; color: {texto}; border-radius: 48px;"
            "font-size: 34px; font-weight: 800;"
        )
        self.lbl_res_nombre.setText(nombre)

        self.lbl_res_ci.setVisible(bool(ci))
        self.lbl_res_ci.setText(f"CI {ci}")
        carrera = str(data.get("carrera") or "")
        self.lbl_res_carrera.setVisible(bool(carrera))
        self.lbl_res_carrera.setText(carrera)
        materia = str(data.get("materia") or "")
        self.lbl_res_materia.setVisible(bool(materia))
        self.lbl_res_materia.setText(materia)

        # Datos del ingreso
        self.bloque_tiles.setVisible(aceptado)
        self.bloque_motivo.setVisible(not aceptado)
        self.lbl_res_motivo.setText(mensaje or "No se pudo registrar el ingreso.")
        self.lbl_res_aula.setText(str(data.get("aula") or "—"))
        asiento = data.get("numero_asiento")
        self.lbl_res_asiento.setText(str(asiento) if asiento else "—")
        hora = data.get("hora_ingreso")
        self.lbl_res_hora.setText(_formatear_hora(hora) if hora else "—")

        self.pila_cuerpo.setCurrentIndex(1)
        self._mostrar_tarjeta(tono)

    def mostrar_resultado(self, exito: bool, titulo: str, detalle: str, asiento: str,
                          tono: str = None):
        """Resultado simple (errores y avisos): título y mensaje."""
        tono = tono or ("exito" if exito else "error")
        self.lbl_res_titulo.setText(titulo)
        self.lbl_res_subtitulo.setText("")
        self.lbl_res_detalle.setText(detalle)
        self.lbl_res_pie.setText(asiento)
        self.lbl_res_pie.setVisible(bool(asiento))
        self.pila_cuerpo.setCurrentIndex(0)
        self._mostrar_tarjeta(tono)

    def _mostrar_tarjeta(self, tono):
        self.res_header.setProperty("tono", tono)
        _repolish(self.res_header)
        self.lbl_res_icono.setPixmap(_pixmap_resultado(tono))
        self.lbl_res_subtitulo.setVisible(bool(self.lbl_res_subtitulo.text()))
        self.barra_tiempo.set_color(_COLOR_TONO[tono])

        self._timer_cuenta.stop()
        self.barra_tiempo.set_fraccion(1.0)
        self._inicio_cuenta = time.monotonic()
        self._timer_cuenta.start()

        self.panel_espera.setVisible(False)
        self.tarjeta_resultado.setVisible(True)
        self.hide_result_timer.start(TIEMPO_MOSTRAR_RESULTADO_MS)

    def limpiar_resultado(self):
        """Quita la tarjeta de resultado y vuelve al panel de espera."""
        self.hide_result_timer.stop()
        self._timer_cuenta.stop()
        self.tarjeta_resultado.setVisible(False)
        self.lbl_res_titulo.setText("RESULTADO")
        self.lbl_res_subtitulo.setText("")
        self.lbl_res_detalle.setText("")
        self.lbl_res_pie.setText("")
        self.lbl_res_asiento.setText("")
        self.panel_espera.setVisible(True)

    def restaurar_panel_espera(self):
        """Vuelve al panel de espera (lo dispara el temporizador)."""
        self._timer_cuenta.stop()
        self.tarjeta_resultado.setVisible(False)
        self.panel_espera.setVisible(True)
        if getattr(self, "_estacion_activa", False):
            QTimer.singleShot(500, self.identificar_huella)

    def _avanzar_cuenta(self):
        transcurrido_ms = (time.monotonic() - self._inicio_cuenta) * 1000
        self.barra_tiempo.set_fraccion(1.0 - transcurrido_ms / TIEMPO_MOSTRAR_RESULTADO_MS)

    # ══════════════════════ LECTOR ══════════════════════
    def actualizar_estado_lector(self, max_edad_s=None):
        """Muestra en la etiqueta qué lectores de huella están conectados.

        Escanear el bus USB es lento, así que el resultado se guarda y solo se
        repite cuando tiene más de ``max_edad_s`` segundos.
        """
        max_edad = EDAD_MAX_ESTADO_LECTOR_S if max_edad_s is None else max_edad_s
        ahora = time.monotonic()
        cache = getattr(self, "_estado_lector_cache", None)
        if cache is not None and ahora - cache[0] < max_edad:
            estado = cache[1]
        else:
            with _medir("detectar lectores USB"):
                try:
                    lectores, usb_ok = detectar_lectores()
                    fprint_ok = libfprint_disponible()
                    sdk_zk = sdk_zk_disponible()
                    estado = (lectores, usb_ok, fprint_ok, sdk_zk)
                except Exception:
                    estado = ([], False, False, False)
            self._estado_lector_cache = (ahora, estado)
        self._pintar_estado_lector(*estado)

    def _pintar_estado_lector(self, lectores, usb_ok, fprint_ok, sdk_zk):
        if not usb_ok:
            self.lbl_estado_lector.setText("Lector de huella: bus USB no disponible")
            self.lbl_estado_lector.set_tono("error")
        elif not lectores:
            self.lbl_estado_lector.setText("Lector de huella: no conectado")
            self.lbl_estado_lector.set_tono("aviso")
        else:
            utilizable = any(
                (l.tipo == "libfprint" and fprint_ok)
                or (l.tipo == "zk" and sdk_zk)
                for l in lectores
            )
            modelos = ", ".join(l.modelo for l in lectores)
            if utilizable:
                self.lbl_estado_lector.setText(f"Lector {modelos}: listo")
                self.lbl_estado_lector.set_tono("ok")
            else:
                falta = []
                if any(l.tipo == "zk" for l in lectores) and not sdk_zk:
                    falta.append("SDK ZKTeco")
                self.lbl_estado_lector.setText(
                    f"Lector {modelos} detectado — falta "
                    f"{', '.join(falta) or 'configuración'} (setup_lectores_huella.sh)"
                )
                self.lbl_estado_lector.set_tono("aviso")

    # ══════════════════════ DIAGNÓSTICO DE FLUIDEZ ══════════════════════
    def _iniciar_vigilancia_fluidez(self):
        """Avisa en consola cuando la ventana se congela, para ubicar la causa."""
        if getattr(self, "_timer_vigilancia", None) is None:
            self._timer_vigilancia = QTimer(self)
            self._timer_vigilancia.setInterval(100)
            self._timer_vigilancia.timeout.connect(self._latido_vigilancia)
        self._ultimo_latido = time.perf_counter()
        self._timer_vigilancia.start()

    def _detener_vigilancia_fluidez(self):
        timer = getattr(self, "_timer_vigilancia", None)
        if timer is not None:
            timer.stop()

    def _latido_vigilancia(self):
        ahora = time.perf_counter()
        atraso_ms = (ahora - self._ultimo_latido) * 1000 - 100
        self._ultimo_latido = ahora
        if atraso_ms >= UMBRAL_BLOQUEO_UI_MS:
            log.warning(
                "La interfaz estuvo bloqueada unos %.0f ms "
                "(mira el aviso «Operación lenta» justo antes)", atraso_ms,
            )

    # ══════════════════════ INTERFAZ ══════════════════════
    def _crear_tile(self, etiqueta, destacado=False):
        marco = QFrame()
        marco.setObjectName("tileDestacado" if destacado else "tile")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(2)
        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setObjectName("tileEtiqueta")
        lbl_etiqueta.setFont(_fuente_etiqueta(11, 1.6))
        valor = QLabel("—")
        valor.setObjectName("tileValorGrande" if destacado else "tileValor")
        lay.addWidget(lbl_etiqueta)
        lay.addWidget(valor)
        return marco, valor

    def _crear_tarjeta_resultado(self):
        tarjeta = QFrame()
        tarjeta.setObjectName("resultCard")
        tarjeta.setMinimumSize(720, 400)
        tarjeta.setMaximumSize(920, 520)
        raiz = QVBoxLayout(tarjeta)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # ── Cabecera de color ──
        self.res_header = QFrame()
        self.res_header.setObjectName("resHeader")
        self.res_header.setProperty("tono", "exito")
        self.res_header.setFixedHeight(100)
        cab = QHBoxLayout(self.res_header)
        cab.setContentsMargins(30, 0, 30, 0)
        cab.setSpacing(18)

        self.lbl_res_icono = QLabel()
        self.lbl_res_icono.setFixedSize(64, 64)
        cab.addWidget(self.lbl_res_icono)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addStretch()
        self.lbl_res_titulo = QLabel("RESULTADO")
        self.lbl_res_titulo.setObjectName("resTitulo")
        self.lbl_res_titulo.setWordWrap(True)
        self.lbl_res_subtitulo = QLabel("")
        self.lbl_res_subtitulo.setObjectName("resSubtitulo")
        self.lbl_res_subtitulo.setWordWrap(True)
        textos.addWidget(self.lbl_res_titulo)
        textos.addWidget(self.lbl_res_subtitulo)
        textos.addStretch()
        cab.addLayout(textos, 1)
        raiz.addWidget(self.res_header)

        # ── Cuerpo con dos páginas: simple y con datos del postulante ──
        self.pila_cuerpo = QStackedWidget()

        # Página 0: mensaje simple
        simple = QWidget()
        lay_simple = QVBoxLayout(simple)
        lay_simple.setContentsMargins(40, 30, 40, 30)
        lay_simple.setSpacing(10)
        lay_simple.addStretch()
        self.lbl_res_detalle = QLabel("")
        self.lbl_res_detalle.setObjectName("resDetalle")
        self.lbl_res_detalle.setAlignment(Qt.AlignCenter)
        self.lbl_res_detalle.setTextFormat(Qt.RichText)
        self.lbl_res_detalle.setWordWrap(True)
        self.lbl_res_pie = QLabel("")
        self.lbl_res_pie.setObjectName("resPie")
        self.lbl_res_pie.setAlignment(Qt.AlignCenter)
        self.lbl_res_pie.setWordWrap(True)
        lay_simple.addWidget(self.lbl_res_detalle)
        lay_simple.addWidget(self.lbl_res_pie)
        lay_simple.addStretch()
        self.pila_cuerpo.addWidget(simple)

        # Página 1: datos del postulante
        acceso = QWidget()
        lay_acceso = QVBoxLayout(acceso)
        lay_acceso.setContentsMargins(34, 26, 34, 18)
        lay_acceso.setSpacing(20)

        identidad = QHBoxLayout()
        identidad.setSpacing(24)
        self.lbl_res_avatar = QLabel("?")
        self.lbl_res_avatar.setFixedSize(96, 96)
        self.lbl_res_avatar.setAlignment(Qt.AlignCenter)
        identidad.addWidget(self.lbl_res_avatar, 0, Qt.AlignTop)

        datos = QVBoxLayout()
        datos.setSpacing(8)
        self.lbl_res_nombre = QLabel("")
        self.lbl_res_nombre.setObjectName("resNombre")
        self.lbl_res_nombre.setWordWrap(True)
        datos.addWidget(self.lbl_res_nombre)

        fila_chips = QHBoxLayout()
        fila_chips.setSpacing(8)
        self.lbl_res_ci = QLabel("")
        self.lbl_res_ci.setObjectName("resChip")
        self.lbl_res_carrera = QLabel("")
        self.lbl_res_carrera.setObjectName("resChip")
        fila_chips.addWidget(self.lbl_res_ci)
        fila_chips.addWidget(self.lbl_res_carrera)
        fila_chips.addStretch()
        datos.addLayout(fila_chips)

        self.lbl_res_materia = QLabel("")
        self.lbl_res_materia.setObjectName("resMateria")
        self.lbl_res_materia.setWordWrap(True)
        datos.addWidget(self.lbl_res_materia)
        identidad.addLayout(datos, 1)
        lay_acceso.addStretch(1)
        lay_acceso.addLayout(identidad)

        self.bloque_tiles = QWidget()
        tiles = QHBoxLayout(self.bloque_tiles)
        tiles.setContentsMargins(0, 0, 0, 0)
        tiles.setSpacing(14)
        tile_aula, self.lbl_res_aula = self._crear_tile("AULA")
        tile_asiento, self.lbl_res_asiento = self._crear_tile("ASIENTO", destacado=True)
        tile_hora, self.lbl_res_hora = self._crear_tile("INGRESO")
        tiles.addWidget(tile_aula, 1)
        tiles.addWidget(tile_asiento, 1)
        tiles.addWidget(tile_hora, 1)
        lay_acceso.addWidget(self.bloque_tiles)

        self.bloque_motivo = QFrame()
        self.bloque_motivo.setObjectName("motivo")
        lay_motivo = QVBoxLayout(self.bloque_motivo)
        lay_motivo.setContentsMargins(22, 16, 22, 16)
        lay_motivo.setSpacing(4)
        etiqueta_motivo = QLabel("MOTIVO")
        etiqueta_motivo.setObjectName("motivoEtiqueta")
        etiqueta_motivo.setFont(_fuente_etiqueta(11, 1.6))
        self.lbl_res_motivo = QLabel("")
        self.lbl_res_motivo.setObjectName("motivoTexto")
        self.lbl_res_motivo.setWordWrap(True)
        lay_motivo.addWidget(etiqueta_motivo)
        lay_motivo.addWidget(self.lbl_res_motivo)
        self.bloque_motivo.setVisible(False)
        lay_acceso.addWidget(self.bloque_motivo)
        lay_acceso.addStretch(1)
        self.pila_cuerpo.addWidget(acceso)

        raiz.addWidget(self.pila_cuerpo, 1)

        # ── Cuenta regresiva ──
        pie = QWidget()
        lay_pie = QVBoxLayout(pie)
        lay_pie.setContentsMargins(34, 0, 34, 20)
        self.barra_tiempo = BarraTiempo()
        lay_pie.addWidget(self.barra_tiempo)
        raiz.addWidget(pie)

        # La barra se actualiza 10 veces por segundo (basta y consume poco).
        self._inicio_cuenta = 0.0
        self._timer_cuenta = QTimer(tarjeta)
        self._timer_cuenta.setInterval(100)
        self._timer_cuenta.timeout.connect(self._avanzar_cuenta)
        return tarjeta

    def _construir_tab_marcacion(self):
        # ═══ TAB 1: MARCACIÓN BIOMÉTRICA ═══
        tab_marcacion = QWidget()
        tab_marcacion.setObjectName("tabMarcacion")
        tab_marcacion.setAttribute(Qt.WA_StyledBackground, True)
        tab_marcacion.setStyleSheet(ESTILOS_MARCACION)
        layout_marc = QVBoxLayout(tab_marcacion)
        layout_marc.setContentsMargins(24, 20, 24, 18)
        layout_marc.setSpacing(14)

        # Controlador de identificación automática (lo crea el mixin, no la vista)
        self._identificacion = None

        # Aviso de que la identificación por huella es automática
        self.banner_huella = QLabel(
            "<b>Marcación automática</b>  ·  Apoya el dedo en el lector: el sistema "
            "identifica al postulante y registra su ingreso."
        )
        self.banner_huella.setObjectName("banner")
        self.banner_huella.setWordWrap(True)
        layout_marc.addWidget(self.banner_huella)

        # Zona central: espera o resultado (se alternan)
        centro = QHBoxLayout()
        centro.setSpacing(0)
        self.panel_espera = PanelEspera()
        self.panel_espera.setMinimumSize(720, 400)
        self.panel_espera.setMaximumSize(920, 520)
        self.tarjeta_resultado = self._crear_tarjeta_resultado()
        self.tarjeta_resultado.setVisible(False)
        centro.addStretch(1)
        centro.addWidget(self.panel_espera, 10)
        centro.addWidget(self.tarjeta_resultado, 10)
        centro.addStretch(1)
        layout_marc.addLayout(centro, 1)

        # Barra de estado del lector
        barra = QFrame()
        barra.setObjectName("barraEstado")
        fila = QHBoxLayout(barra)
        fila.setContentsMargins(18, 10, 12, 10)
        fila.setSpacing(12)

        self.lbl_estado_lector = EstadoLector("Lector de huella: detectando…")
        self.lbl_estado_lector.setObjectName("lectorTexto")
        fila.addWidget(self.lbl_estado_lector, 1)

        self.lbl_resumen_huellas = QLabel("Examen: comprobando huellas habilitadas…")
        self.lbl_resumen_huellas.setObjectName("resumenChip")
        fila.addWidget(self.lbl_resumen_huellas)

        # El lector se inicia automáticamente al entrar a esta pantalla.
        # Estos botones solo aparecen para detenerlo o reanudarlo a mano.
        self.btn_cancelar_huella = QPushButton("Detener lector")
        self.btn_cancelar_huella.setObjectName("btnDetener")
        self.btn_cancelar_huella.setMinimumHeight(34)
        self.btn_cancelar_huella.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar_huella.setFocusPolicy(Qt.NoFocus)
        self.btn_cancelar_huella.setVisible(False)
        self.btn_cancelar_huella.clicked.connect(self.cancelar_identificacion)
        fila.addWidget(self.btn_cancelar_huella)

        self.btn_huella = QPushButton("Reanudar lector")
        self.btn_huella.setObjectName("btnReanudar")
        self.btn_huella.setMinimumHeight(34)
        self.btn_huella.setCursor(Qt.PointingHandCursor)
        self.btn_huella.setFocusPolicy(Qt.NoFocus)
        self.btn_huella.setToolTip(
            "Apoya el dedo en el lector: el sistema identifica al postulante "
            "y registra su ingreso. No necesitas buscar tu nombre."
        )
        self.btn_huella.setVisible(False)
        self.btn_huella.clicked.connect(self.identificar_huella)
        fila.addWidget(self.btn_huella)

        layout_marc.addWidget(barra)
        # Se difiere: escanear el USB al construir la ventana la haría abrir más lento.
        QTimer.singleShot(300, self.actualizar_estado_lector)

        self.tabs.addTab(tab_marcacion, "Marcación Biométrica")
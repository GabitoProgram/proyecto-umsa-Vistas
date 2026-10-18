import cv2
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from desktop.config.app_config import AppConfig
from desktop.views.checkin.workers import IdentifyWorker

TIEMPO_PAUSA_MS = 6000  # pausa tras identificar a alguien
_COLORES_AVATAR = (
    ("#DBEAFE", "#1E40AF"),
    ("#DCFCE7", "#166534"),
    ("#FEF3C7", "#92400E"),
    ("#EDE9FE", "#5B21B6"),
    ("#FCE7F3", "#9D174D"),
    ("#E0F2FE", "#075985"),
)
_COLOR_TONO = {"exito": "#16A34A", "error": "#DC2626", "aviso": "#D97706", "neutro": "#64748B"}


# ======================================================================
# Utilidades
# ======================================================================
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


def _dibujar_persona(p, cx, cy, escala, color, grosor):
    """Silueta de cabeza y hombros."""
    p.setPen(QPen(QColor(color), grosor, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(QPointF(cx, cy - 0.16 * escala), 0.15 * escala, 0.15 * escala)
    ruta = QPainterPath()
    ruta.moveTo(cx - 0.30 * escala, cy + 0.34 * escala)
    ruta.cubicTo(cx - 0.27 * escala, cy + 0.04 * escala,
                 cx + 0.27 * escala, cy + 0.04 * escala,
                 cx + 0.30 * escala, cy + 0.34 * escala)
    p.drawPath(ruta)


def _pixmap_estado(tono, lado=56):
    """Insignia circular: check, cruz, exclamación o silueta (estado neutro)."""
    pm = QPixmap(lado * 2, lado * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 240))
    p.drawEllipse(QRectF(2, 2, lado - 4, lado - 4))

    s = float(lado)
    color = _COLOR_TONO[tono]
    p.setPen(QPen(QColor(color), s * 0.09, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
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
    elif tono == "aviso":
        p.drawLine(QPointF(s * 0.5, s * 0.28), QPointF(s * 0.5, s * 0.55))
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        p.drawEllipse(QPointF(s * 0.5, s * 0.71), s * 0.055, s * 0.055)
    else:
        _dibujar_persona(p, s * 0.5, s * 0.5, s * 0.8, color, s * 0.07)
    p.end()
    return pm


def _pixmap_espera(lado=116):
    """Ilustración para la ficha vacía: silueta dentro de un disco suave."""
    pm = QPixmap(lado * 2, lado * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#E8F0FD"))
    p.drawEllipse(QRectF(0, 0, lado, lado))
    _dibujar_persona(p, lado / 2, lado / 2, lado * 0.72, "#2F6FED", 3)
    p.end()
    return pm


# ======================================================================
# Widgets propios
# ======================================================================
class VisorCamara(QWidget):
    """Visor con esquinas redondeadas, óvalo guía y estado en vivo."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(560, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._imagen = None
        self._mensaje = "Cámara detenida.\nPulsa «Iniciar detección» para comenzar."
        self._error = False
        self._analizando = False

    def mostrar_frame(self, imagen):
        self._imagen = imagen
        self._mensaje = ""
        self._error = False
        self.update()

    def mostrar_mensaje(self, texto, error=False):
        self._imagen = None
        self._mensaje = texto
        self._error = error
        self._analizando = False
        self.update()

    def setText(self, texto):
        """Compatibilidad con el QLabel anterior."""
        self.mostrar_mensaje(texto)

    def set_analizando(self, valor):
        self._analizando = bool(valor)
        self.update()

    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        forma = QPainterPath()
        forma.addRoundedRect(QRectF(self.rect()), 16, 16)
        p.setClipPath(forma)
        p.fillRect(self.rect(), QColor("#0B1220"))

        if self._imagen is None:
            self._pintar_mensaje(p)
            p.end()
            return

        escalada = self._imagen.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = (self.width() - escalada.width()) // 2
        y = (self.height() - escalada.height()) // 2
        p.drawImage(x, y, escalada)
        self._pintar_guia(p, QRectF(x, y, escalada.width(), escalada.height()))
        self._pintar_indicador(p)
        p.end()

    def _pintar_guia(self, p, area):
        ancho = area.width() * 0.44
        alto = area.height() * 0.82
        oval = QRectF(area.center().x() - ancho / 2, area.center().y() - alto / 2, ancho, alto)

        mascara = QPainterPath()
        mascara.addRect(area)
        mascara.addEllipse(oval)
        mascara.setFillRule(Qt.OddEvenFill)
        p.fillPath(mascara, QColor(11, 18, 32, 130))

        p.setBrush(Qt.NoBrush)
        color_guia = QColor(251, 191, 36) if self._analizando else QColor(255, 255, 255)
        halo = QColor(color_guia)
        halo.setAlpha(60)
        p.setPen(QPen(halo, 8))
        p.drawEllipse(oval)
        linea = QColor(color_guia)
        linea.setAlpha(230)
        p.setPen(QPen(linea, 2.4))
        p.drawEllipse(oval)

    def _pintar_indicador(self, p):
        texto = "ANALIZANDO" if self._analizando else "EN VIVO"
        color = QColor("#FBBF24") if self._analizando else QColor("#EF4444")
        fuente = QFont()
        fuente.setPixelSize(11)
        fuente.setWeight(QFont.Bold)
        fuente.setLetterSpacing(QFont.AbsoluteSpacing, 1.2)
        p.setFont(fuente)
        ancho = p.fontMetrics().horizontalAdvance(texto) + 36
        caja = QRectF(16, 16, ancho, 26)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(11, 18, 32, 170))
        p.drawRoundedRect(caja, 13, 13)
        p.setBrush(color)
        p.drawEllipse(QPointF(caja.left() + 15, caja.center().y()), 4.5, 4.5)
        p.setPen(QColor("#F8FAFC"))
        p.drawText(QRectF(caja.left() + 26, caja.top(), ancho - 28, caja.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, texto)

    def _pintar_mensaje(self, p):
        cx = self.width() / 2
        cy = self.height() / 2 - 34
        color_icono = QColor("#F87171") if self._error else QColor("#475569")
        p.setPen(QPen(color_icono, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(cx - 28, cy - 18, 56, 40), 8, 8)
        p.drawEllipse(QPointF(cx, cy + 2), 11, 11)
        tapa = QPainterPath()
        tapa.moveTo(cx - 12, cy - 18)
        tapa.lineTo(cx - 7, cy - 26)
        tapa.lineTo(cx + 7, cy - 26)
        tapa.lineTo(cx + 12, cy - 18)
        p.drawPath(tapa)
        if self._error:
            p.drawLine(QPointF(cx - 34, cy + 30), QPointF(cx + 34, cy - 38))

        p.setPen(QColor("#FCA5A5") if self._error else QColor("#94A3B8"))
        fuente = p.font()
        fuente.setPointSizeF(10.5)
        p.setFont(fuente)
        p.drawText(
            QRectF(40, cy + 46, self.width() - 80, 100),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            self._mensaje,
        )


class BarraTiempo(QWidget):
    """Barra fina que se vacía durante la pausa entre identificaciones."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(6)
        self._fraccion = 0.0
        self._color = QColor("#16A34A")

    def set_color(self, color):
        self._color = QColor(color)
        self.update()

    def set_fraccion(self, valor):
        self._fraccion = max(0.0, min(1.0, valor))
        self.update()

    def paintEvent(self, _evento):
        if self._fraccion <= 0:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#EEF2F7"))
        p.drawRoundedRect(QRectF(self.rect()), 3, 3)
        p.setBrush(self._color)
        p.drawRoundedRect(QRectF(0, 0, self.width() * self._fraccion, self.height()), 3, 3)
        p.end()


class EstadoDeteccion(QLabel):
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
ESTILOS_RECONOCIMIENTO = """
    QWidget#tabReconocimiento { background: #F1F5F9; }
    /* Las etiquetas no heredan fondos ni bordes de reglas generales */
    QLabel { background: transparent; border: none; }

    QFrame#card {
        background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 20px;
    }
    QLabel#cardTitulo { color: #0F2C59; font-size: 20px; font-weight: 800; }
    QLabel#cardNota   { color: #64748B; font-size: 13px; }
    QLabel#estadoTexto { color: #334155; font-size: 13px; font-weight: 600; }

    QPushButton#btnToggle {
        background: #1E54B7; color: #FFFFFF; border: none;
        border-radius: 10px; padding: 0 22px;
        font-size: 14px; font-weight: 700;
    }
    QPushButton#btnToggle:hover { background: #17449A; }
    QPushButton#btnToggle[activo="true"] {
        background: #FFFFFF; color: #B91C1C; border: 1px solid #FCA5A5;
    }
    QPushButton#btnToggle[activo="true"]:hover { background: #FEF2F2; }

    /* ---------- Ficha de resultado ---------- */
    QFrame#fichaHeader {
        border: none;
        border-top-left-radius: 19px; border-top-right-radius: 19px;
        border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
    }
    QFrame#fichaHeader[tono="neutro"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #334155, stop:1 #64748B);
    }
    QFrame#fichaHeader[tono="exito"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #15803D, stop:1 #22A455);
    }
    QFrame#fichaHeader[tono="error"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B91C1C, stop:1 #DC3C3C);
    }
    QFrame#fichaHeader[tono="aviso"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #B45309, stop:1 #D98A12);
    }
    QLabel#fichaTitulo    { color: #FFFFFF; font-size: 22px; font-weight: 800; }
    QLabel#fichaSubtitulo { color: rgba(255, 255, 255, 0.90); font-size: 13px; font-weight: 500; }

    QLabel#esperaTitulo { color: #0F2C59; font-size: 22px; font-weight: 800; }
    QLabel#esperaSub    { color: #64748B; font-size: 14px; }

    QLabel#fichaNombre  { color: #0F172A; font-size: 24px; font-weight: 800; }
    QLabel#fichaMateria { color: #475569; font-size: 14px; font-weight: 600; }
    QLabel#fichaChip {
        background: #EEF3FB; color: #1E4E96;
        border-radius: 11px; padding: 4px 12px;
        font-size: 12px; font-weight: 700;
    }

    QFrame#tile {
        background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 14px;
    }
    QFrame#tileDestacado {
        background: #E8F0FD; border: 1px solid #BFD3F7; border-radius: 14px;
    }
    QLabel#tileEtiqueta { color: #64748B; }
    QLabel#tileValor    { color: #0F172A; font-size: 20px; font-weight: 800; }
    QLabel#tileValorGrande { color: #1E54B7; font-size: 30px; font-weight: 800; }

    QFrame#motivo {
        background: #FEF2F2; border: 1px solid #FECACA; border-radius: 14px;
    }
    QLabel#motivoEtiqueta { color: #B91C1C; }
    QLabel#motivoTexto    { color: #7F1D1D; font-size: 16px; font-weight: 600; }
"""


class ReconocimientoMixin:
    # ══════════════════════ CONTROL DE LA DETECCIÓN ══════════════════════
    def _on_tab_changed(self, index):
        # La detección automática solo corre cuando su pestaña está visible.
        if index != self.tabs.indexOf(self.tab_reconocimiento):
            self.detener_auto_deteccion()

    def toggle_auto_deteccion(self):
        if self.auto_activo:
            self.detener_auto_deteccion()
        else:
            self.iniciar_auto_deteccion()

    def _pintar_toggle(self):
        self.btn_auto_toggle.setText(
            "Detener detección" if self.auto_activo else "Iniciar detección"
        )
        self.btn_auto_toggle.setProperty("activo", bool(self.auto_activo))
        _repolish(self.btn_auto_toggle)

    def iniciar_auto_deteccion(self):
        if self.auto_activo:
            return
        self.auto_cap = cv2.VideoCapture(0)
        if self.auto_cap is None or not self.auto_cap.isOpened():
            self.auto_visor.mostrar_mensaje(
                "No se pudo acceder a la cámara.\n"
                "Verifique que no esté en uso por otra aplicación.",
                error=True,
            )
            self.auto_estado.setText("Cámara no disponible.")
            self.auto_estado.set_tono("error")
            if self.auto_cap:
                self.auto_cap.release()
            self.auto_cap = None
            return
        self.auto_activo = True
        self.auto_ultimo_id = None
        self._auto_reset_ficha()
        self._pintar_toggle()
        self.auto_estado.setText("Detección activa. Mire a la cámara.")
        self.auto_estado.set_tono("ok")
        self.auto_frame_timer.start(30)
        self._auto_fin_cooldown()

    def detener_auto_deteccion(self):
        if not self.auto_activo and self.auto_cap is None:
            return
        self.auto_activo = False
        self.auto_frame_timer.stop()
        self.auto_detect_timer.stop()
        self.auto_cooldown_timer.stop()
        self._auto_anim_pausa.stop()
        self.barra_pausa.set_fraccion(0.0)
        if self.auto_cap is not None:
            self.auto_cap.release()
            self.auto_cap = None
        self._pintar_toggle()
        self.auto_visor.mostrar_mensaje(
            "Detección detenida.\nPulsa «Iniciar detección» para continuar."
        )
        self.auto_estado.setText("Detección detenida.")
        self.auto_estado.set_tono("neutro")

    # ══════════════════════ CÁMARA E IDENTIFICACIÓN ══════════════════════
    def _auto_actualizar_frame(self):
        if self.auto_cap and self.auto_cap.isOpened():
            ret, frame = self.auto_cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = rgb.shape
                # .copy() para no depender del buffer de numpy
                imagen = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                self.auto_visor.mostrar_frame(imagen)

    def _auto_detectar(self):
        if not self.auto_activo or self.auto_worker is not None:
            return
        if not self.auto_cap or not self.auto_cap.isOpened():
            return
        ret, frame = self.auto_cap.read()
        if not ret:
            return
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return

        app_key = AppConfig.get_app_key()
        if not app_key:
            self.auto_estado.setText("No existe una clave APP_CLIENT_KEY válida.")
            self.auto_estado.set_tono("error")
            return

        id_examen = self.info_examen.get("id_examen")
        self.auto_worker = IdentifyWorker(
            url=f"{self.api_base_url}/marcaciones/identificar-rostro",
            headers={"X-App-Key": app_key},
            id_examen=id_examen,
            image_bytes=encoded.tobytes(),
            parent=self,
        )
        self.auto_worker.resultado.connect(self._auto_mostrar_respuesta)
        self.auto_worker.finished.connect(self._auto_worker_finalizado)
        self.auto_visor.set_analizando(True)
        self.auto_worker.start()

    def _auto_worker_finalizado(self):
        worker, self.auto_worker = self.auto_worker, None
        self.auto_visor.set_analizando(False)
        if worker is not None:
            worker.deleteLater()

    def _auto_mostrar_respuesta(self, data, status_code, error):
        if error:
            self.auto_estado.setText(f"Sin conexión: {error}")
            self.auto_estado.set_tono("error")
            return
        if status_code != 200:
            self.auto_estado.setText(data.get("detail", "Error del servidor"))
            self.auto_estado.set_tono("error")
            return
        if not data.get("coincidencia"):
            self.auto_estado.setText(data.get("mensaje", "Rostro no reconocido."))
            self.auto_estado.set_tono("aviso")
            return

        id_post = data.get("id_postulante")
        # Evitar reenviar repetidamente al mismo postulante.
        if id_post == self.auto_ultimo_id and self.auto_cooldown_timer.isActive():
            return
        self.auto_ultimo_id = id_post

        aceptado = data.get("resultado") == "ACEPTADO"
        self._auto_mostrar_ficha(data, aceptado)

        self.auto_estado.setText(
            data.get("mensaje", "Ingreso procesado.") + " | Aleje el rostro para el siguiente."
        )
        self.auto_estado.set_tono("ok" if aceptado else "error")

        # Pausa la detección unos segundos para no duplicar al mismo postulante.
        self.auto_detect_timer.stop()
        self.auto_cooldown_timer.start(TIEMPO_PAUSA_MS)
        self._auto_anim_pausa.stop()
        self.barra_pausa.set_color(_COLOR_TONO["exito" if aceptado else "error"])
        self.barra_pausa.set_fraccion(1.0)
        self._auto_anim_pausa.setStartValue(1.0)
        self._auto_anim_pausa.setEndValue(0.0)
        self._auto_anim_pausa.setDuration(TIEMPO_PAUSA_MS)
        self._auto_anim_pausa.start()
        self.actualizar_contador()

    def _auto_fin_cooldown(self):
        if self.auto_activo:
            self.auto_detect_timer.start(1200)

    # ══════════════════════ FICHA DE RESULTADO ══════════════════════
    def _auto_poner_tono(self, tono):
        self.ficha_header.setProperty("tono", tono)
        _repolish(self.ficha_header)
        self.lbl_ficha_icono.setPixmap(_pixmap_estado(tono))

    def _auto_reset_ficha(self):
        """Vuelve a la ficha vacía (antes de la primera identificación)."""
        self._auto_poner_tono("neutro")
        self.auto_resultado.setText("Sin identificación")
        self.auto_subtitulo.setText("Esperando detección de rostro…")
        self.pila_ficha.setCurrentIndex(0)
        self._auto_anim_pausa.stop()
        self.barra_pausa.set_fraccion(0.0)

    def _auto_mostrar_ficha(self, data, aceptado):
        nombre = data.get("nombre_completo") or "Postulante"
        ci = data.get("ci")
        carrera = str(data.get("carrera") or "")
        materia = str(data.get("materia") or "")
        mensaje = data.get("mensaje") or ""
        resultado = str(data.get("resultado", "RECHAZADO")).replace("_", " ")

        self._auto_poner_tono("exito" if aceptado else "error")
        self.auto_resultado.setText("ACCESO CONCEDIDO" if aceptado else f"ACCESO {resultado}")
        if aceptado:
            self.auto_subtitulo.setText(mensaje or "Puede ingresar al aula asignada.")
        else:
            self.auto_subtitulo.setText("No se registró el ingreso.")

        # Identidad
        indice = sum(ord(c) for c in str(ci or nombre)) % len(_COLORES_AVATAR)
        fondo, texto = _COLORES_AVATAR[indice]
        self.lbl_ficha_avatar.setText(_iniciales(nombre))
        self.lbl_ficha_avatar.setStyleSheet(
            f"background: {fondo}; color: {texto}; border-radius: 40px;"
            "font-size: 28px; font-weight: 800;"
        )
        self.auto_titulo.setText(nombre)
        self.lbl_ficha_ci.setVisible(bool(ci))
        self.lbl_ficha_ci.setText(f"CI {ci}")
        self.lbl_ficha_carrera.setVisible(bool(carrera))
        self.lbl_ficha_carrera.setText(carrera)
        self.lbl_ficha_materia.setVisible(bool(materia))
        self.lbl_ficha_materia.setText(materia)

        # Datos del ingreso
        self.bloque_tiles.setVisible(aceptado)
        self.bloque_motivo.setVisible(not aceptado)
        self.lbl_ficha_motivo.setText(mensaje or "No se pudo registrar el ingreso.")
        self.lbl_ficha_aula.setText(str(data.get("aula") or "—"))
        asiento = data.get("numero_asiento")
        self.lbl_ficha_asiento.setText(str(asiento) if asiento else "—")
        hora = data.get("hora_ingreso") or data.get("fecha_hora")
        self.lbl_ficha_hora.setText(_formatear_hora(hora) if hora else "—")

        self.pila_ficha.setCurrentIndex(1)

    # ══════════════════════ INTERFAZ ══════════════════════
    def _crear_tile(self, etiqueta, destacado=False):
        marco = QFrame()
        marco.setObjectName("tileDestacado" if destacado else "tile")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(14, 10, 14, 10)
        lay.setSpacing(2)
        lbl_etiqueta = QLabel(etiqueta)
        lbl_etiqueta.setObjectName("tileEtiqueta")
        lbl_etiqueta.setFont(_fuente_etiqueta(10, 1.5))
        valor = QLabel("—")
        valor.setObjectName("tileValorGrande" if destacado else "tileValor")
        lay.addWidget(lbl_etiqueta)
        lay.addWidget(valor)
        return marco, valor

    def _crear_tarjeta_camara(self):
        tarjeta = QFrame()
        tarjeta.setObjectName("card")
        lay = QVBoxLayout(tarjeta)
        lay.setContentsMargins(24, 22, 24, 18)
        lay.setSpacing(12)

        titulo = QLabel("Detección automática de rostro")
        titulo.setObjectName("cardTitulo")
        nota = QLabel("Mire a la cámara. El sistema lo identifica y registra su ingreso solo.")
        nota.setObjectName("cardNota")
        lay.addWidget(titulo)
        lay.addWidget(nota)

        self.auto_visor = VisorCamara()
        lay.addWidget(self.auto_visor, 1)

        fila = QHBoxLayout()
        fila.setSpacing(12)
        self.auto_estado = EstadoDeteccion("Acérquese a la cámara. La identificación es automática.")
        self.auto_estado.setObjectName("estadoTexto")
        self.auto_estado.setWordWrap(True)
        fila.addWidget(self.auto_estado, 1)

        self.btn_auto_toggle = QPushButton("Iniciar detección")
        self.btn_auto_toggle.setObjectName("btnToggle")
        self.btn_auto_toggle.setMinimumHeight(44)
        self.btn_auto_toggle.setMinimumWidth(190)
        self.btn_auto_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_auto_toggle.setFocusPolicy(Qt.NoFocus)
        self.btn_auto_toggle.setProperty("activo", False)
        self.btn_auto_toggle.clicked.connect(self.toggle_auto_deteccion)
        fila.addWidget(self.btn_auto_toggle)
        lay.addLayout(fila)
        return tarjeta

    def _crear_ficha(self):
        ficha = QFrame()
        ficha.setObjectName("card")
        ficha.setMinimumWidth(400)
        raiz = QVBoxLayout(ficha)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        # ── Cabecera de color ──
        self.ficha_header = QFrame()
        self.ficha_header.setObjectName("fichaHeader")
        self.ficha_header.setProperty("tono", "neutro")
        self.ficha_header.setFixedHeight(88)
        cab = QHBoxLayout(self.ficha_header)
        cab.setContentsMargins(24, 0, 24, 0)
        cab.setSpacing(16)
        self.lbl_ficha_icono = QLabel()
        self.lbl_ficha_icono.setFixedSize(56, 56)
        self.lbl_ficha_icono.setPixmap(_pixmap_estado("neutro"))
        cab.addWidget(self.lbl_ficha_icono)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        textos.addStretch()
        self.auto_resultado = QLabel("Sin identificación")
        self.auto_resultado.setObjectName("fichaTitulo")
        self.auto_resultado.setWordWrap(True)
        self.auto_subtitulo = QLabel("Esperando detección de rostro…")
        self.auto_subtitulo.setObjectName("fichaSubtitulo")
        self.auto_subtitulo.setWordWrap(True)
        textos.addWidget(self.auto_resultado)
        textos.addWidget(self.auto_subtitulo)
        textos.addStretch()
        cab.addLayout(textos, 1)
        raiz.addWidget(self.ficha_header)

        # ── Cuerpo: página vacía y página con datos ──
        self.pila_ficha = QStackedWidget()

        vacia = QWidget()
        lay_vacia = QVBoxLayout(vacia)
        lay_vacia.setContentsMargins(24, 24, 24, 24)
        lay_vacia.setSpacing(8)
        lay_vacia.addStretch()
        ilustracion = QLabel()
        ilustracion.setPixmap(_pixmap_espera())
        ilustracion.setAlignment(Qt.AlignCenter)
        lbl_espera = QLabel("Esperando rostro")
        lbl_espera.setObjectName("esperaTitulo")
        lbl_espera.setAlignment(Qt.AlignCenter)
        lbl_espera_sub = QLabel("Los datos del postulante aparecerán aquí cuando sea identificado.")
        lbl_espera_sub.setObjectName("esperaSub")
        lbl_espera_sub.setAlignment(Qt.AlignCenter)
        lbl_espera_sub.setWordWrap(True)
        lay_vacia.addWidget(ilustracion)
        lay_vacia.addSpacing(6)
        lay_vacia.addWidget(lbl_espera)
        lay_vacia.addWidget(lbl_espera_sub)
        lay_vacia.addStretch()
        self.pila_ficha.addWidget(vacia)

        datos = QWidget()
        lay_datos = QVBoxLayout(datos)
        lay_datos.setContentsMargins(24, 22, 24, 12)
        lay_datos.setSpacing(16)

        identidad = QHBoxLayout()
        identidad.setSpacing(18)
        self.lbl_ficha_avatar = QLabel("?")
        self.lbl_ficha_avatar.setFixedSize(80, 80)
        self.lbl_ficha_avatar.setAlignment(Qt.AlignCenter)
        identidad.addWidget(self.lbl_ficha_avatar, 0, Qt.AlignTop)

        col = QVBoxLayout()
        col.setSpacing(6)
        self.auto_titulo = QLabel("Sin identificación")
        self.auto_titulo.setObjectName("fichaNombre")
        self.auto_titulo.setWordWrap(True)
        col.addWidget(self.auto_titulo)
        chips = QHBoxLayout()
        chips.setSpacing(8)
        self.lbl_ficha_ci = QLabel("")
        self.lbl_ficha_ci.setObjectName("fichaChip")
        self.lbl_ficha_carrera = QLabel("")
        self.lbl_ficha_carrera.setObjectName("fichaChip")
        chips.addWidget(self.lbl_ficha_ci)
        chips.addWidget(self.lbl_ficha_carrera)
        chips.addStretch()
        col.addLayout(chips)
        self.lbl_ficha_materia = QLabel("")
        self.lbl_ficha_materia.setObjectName("fichaMateria")
        self.lbl_ficha_materia.setWordWrap(True)
        col.addWidget(self.lbl_ficha_materia)
        identidad.addLayout(col, 1)
        lay_datos.addStretch(1)
        lay_datos.addLayout(identidad)

        self.bloque_tiles = QWidget()
        tiles = QHBoxLayout(self.bloque_tiles)
        tiles.setContentsMargins(0, 0, 0, 0)
        tiles.setSpacing(10)
        tile_aula, self.lbl_ficha_aula = self._crear_tile("AULA")
        tile_asiento, self.lbl_ficha_asiento = self._crear_tile("ASIENTO", destacado=True)
        tile_hora, self.lbl_ficha_hora = self._crear_tile("INGRESO")
        tiles.addWidget(tile_aula, 1)
        tiles.addWidget(tile_asiento, 1)
        tiles.addWidget(tile_hora, 1)
        lay_datos.addWidget(self.bloque_tiles)

        self.bloque_motivo = QFrame()
        self.bloque_motivo.setObjectName("motivo")
        lay_motivo = QVBoxLayout(self.bloque_motivo)
        lay_motivo.setContentsMargins(18, 14, 18, 14)
        lay_motivo.setSpacing(4)
        etiqueta_motivo = QLabel("MOTIVO")
        etiqueta_motivo.setObjectName("motivoEtiqueta")
        etiqueta_motivo.setFont(_fuente_etiqueta(10, 1.5))
        self.lbl_ficha_motivo = QLabel("")
        self.lbl_ficha_motivo.setObjectName("motivoTexto")
        self.lbl_ficha_motivo.setWordWrap(True)
        lay_motivo.addWidget(etiqueta_motivo)
        lay_motivo.addWidget(self.lbl_ficha_motivo)
        self.bloque_motivo.setVisible(False)
        lay_datos.addWidget(self.bloque_motivo)
        lay_datos.addStretch(1)
        self.pila_ficha.addWidget(datos)

        raiz.addWidget(self.pila_ficha, 1)

        # ── Barra de pausa entre identificaciones ──
        pie = QWidget()
        lay_pie = QVBoxLayout(pie)
        lay_pie.setContentsMargins(24, 0, 24, 18)
        self.barra_pausa = BarraTiempo()
        lay_pie.addWidget(self.barra_pausa)
        raiz.addWidget(pie)

        self._auto_anim_pausa = QVariantAnimation(ficha)
        self._auto_anim_pausa.valueChanged.connect(
            lambda valor: self.barra_pausa.set_fraccion(float(valor))
        )
        return ficha

    def _construir_tab_reconocimiento(self):
        # ═══ TAB: RECONOCIMIENTO FACIAL AUTOMÁTICO ═══
        tab_auto = QWidget()
        tab_auto.setObjectName("tabReconocimiento")
        tab_auto.setAttribute(Qt.WA_StyledBackground, True)
        tab_auto.setStyleSheet(ESTILOS_RECONOCIMIENTO)
        layout_auto = QHBoxLayout(tab_auto)
        layout_auto.setContentsMargins(24, 20, 24, 18)
        layout_auto.setSpacing(18)

        # Lado izquierdo: cámara
        layout_auto.addWidget(self._crear_tarjeta_camara(), stretch=3)

        # Lado derecho: ficha de datos
        self.auto_card = self._crear_ficha()
        layout_auto.addWidget(self.auto_card, stretch=2)

        self.tabs.addTab(tab_auto, "Reconocimiento Automático")
        self.tab_reconocimiento = tab_auto
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Estado interno del reconocimiento automático
        self.auto_activo = False
        self.auto_cap = None
        self.auto_worker = None
        self.auto_ultimo_id = None
        self.auto_cooldown_timer = QTimer(self)
        self.auto_cooldown_timer.setSingleShot(True)
        self.auto_cooldown_timer.timeout.connect(self._auto_fin_cooldown)
        self.auto_frame_timer = QTimer(self)
        self.auto_frame_timer.timeout.connect(self._auto_actualizar_frame)
        self.auto_detect_timer = QTimer(self)
        self.auto_detect_timer.timeout.connect(self._auto_detectar)
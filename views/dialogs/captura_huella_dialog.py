"""Diálogo de captura/enrolamiento de huella.

Funciona con cualquier lector soportado:
- **DigitalPersona U.are.U** (y otros compatibles con libfprint).
- **ZKTeco ZK4500/ZK9500** (con la ZKFinger SDK instalada).

Muestra un mapa de manos con el estado de cada dedo, vista previa de la
huella, selector de lector (si hay varios) y el flujo de enrolamiento
multi-etapa.
"""

import logging

from PySide6.QtCore import QRectF, QTimer, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from desktop.biometria import (
    detectar_lectores,
    libfprint_disponible,
    sdk_zk_disponible,
    crear_lector,
    DEDO_NOMBRES,
    LectorNoConectadoError,
    SDKNoDisponibleError,
    PermisoUSBError,
    ErrorLector,
    prefijar_plantilla,
)
from desktop.biometria.modelos import UMBRAL_CONSISTENCIA

log = logging.getLogger(__name__)


def _ajustar_tamano_dialogo(dialogo, ancho_deseado, alto_deseado):
    """Adapta el tamaño del diálogo a la pantalla disponible (ideal para laptops)."""
    pantalla = QGuiApplication.primaryScreen()
    if pantalla:
        disponible = pantalla.availableGeometry()
        ancho = min(ancho_deseado, int(disponible.width() * 0.94))
        alto = min(alto_deseado, int(disponible.height() * 0.90))
    else:
        ancho, alto = ancho_deseado, alto_deseado

    dialogo.setMinimumSize(min(720, ancho), min(480, alto))
    dialogo.resize(ancho, alto)


# ======================================================================
# Mapa de manos
# ======================================================================
# Tipos de dedo: 0 pulgar, 1 índice, 2 medio, 3 anular, 4 meñique
_TIPOS_DEDO = (
    ("pulgar", 0),
    ("indice", 1), ("índice", 1),
    ("medio", 2), ("corazon", 2), ("corazón", 2),
    ("anular", 3),
    ("menique", 4), ("meñique", 4),
)


def _clasificar_dedo(numero, nombre):
    """Devuelve (mano, tipo) leyendo el nombre; si no se entiende, por número."""
    texto = str(nombre).lower()
    mano = "izq" if "izq" in texto else ("der" if "der" in texto else None)
    tipo = next((i for clave, i in _TIPOS_DEDO if clave in texto), None)
    if mano is None or tipo is None:
        mano = "der" if numero <= 5 else "izq"
        tipo = (numero - 1) % 5
    return mano, tipo


def _mapa_dedos(nombres):
    posiciones = {n: _clasificar_dedo(n, nombre) for n, nombre in nombres.items()}
    if len(set(posiciones.values())) != len(posiciones):
        # Nombres ambiguos: se asume 1-5 mano derecha y 6-10 izquierda.
        posiciones = {n: ("der" if n <= 5 else "izq", (n - 1) % 5) for n in nombres}
    return posiciones


def _capsula(cx, base_y, largo, ancho, angulo):
    camino = QPainterPath()
    camino.addRoundedRect(
        QRectF(cx - ancho / 2, base_y - largo, ancho, largo + 26), ancho / 2, ancho / 2
    )
    giro = QTransform()
    giro.translate(cx, base_y + 6)
    giro.rotate(angulo)
    giro.translate(-cx, -(base_y + 6))
    return giro.map(camino)


class MapaManos(QFrame):
    """Dos manos dibujadas; cada dedo cambia de color según su estado."""

    dedo_clicked = Signal(int)

    ANCHO = 250.0
    ALTO = 232.0

    # estado -> (relleno, borde)
    COLORES = {
        "habilitado": ("#22C55E", "#15803D"),
        "registrado": ("#FBBF24", "#B45309"),
        "vacio": ("#E8EEF5", "#C3CFDD"),
    }
    TEXTO_ESTADO = {
        "habilitado": "Registrado y habilitado",
        "registrado": "Registrado, sin habilitar",
        "vacio": "Sin registrar",
    }

    def __init__(self, nombres, parent=None):
        super().__init__(parent)
        self.nombres = dict(nombres)
        self._posiciones = _mapa_dedos(self.nombres)
        self._estados = {}
        self._seleccionado = None
        self._hover = None

        # Geometría base de una mano izquierda (la derecha se obtiene espejada)
        self._dedos_unidad = {
            4: _capsula(67, 126, 62, 24, -9),
            3: _capsula(97, 126, 82, 24, -4),
            2: _capsula(127, 126, 92, 24, 0),
            1: _capsula(157, 126, 84, 24, 5),
            0: _capsula(176, 190, 66, 27, 40),
        }
        self._palma_unidad = QPainterPath()
        self._palma_unidad.addRoundedRect(QRectF(50, 118, 130, 96), 30, 30)

        self.setMouseTracking(True)
        # Reducimos ligeramente el mínimo para que escale bien en laptops (1366x768)
        self.setMinimumSize(420, 220)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    # -- API --------------------------------------------------------------
    def set_estados(self, registrados, habilitados):
        self._estados = {}
        for numero in self.nombres:
            if numero in habilitados:
                self._estados[numero] = "habilitado"
            elif numero in registrados:
                self._estados[numero] = "registrado"
            else:
                self._estados[numero] = "vacio"
        self.update()

    def set_seleccionado(self, numero):
        self._seleccionado = numero
        self.update()

    # -- Geometría --------------------------------------------------------
    def _geometria(self):
        ancho, alto = self.width(), self.height()
        margen, hueco, alto_etiqueta = 10.0, 28.0, 24.0
        escala = min(
            (ancho - 2 * margen - hueco) / (2 * self.ANCHO),
            (alto - 2 * margen - alto_etiqueta) / self.ALTO,
        )
        escala = max(0.4, min(escala, 1.5))
        total = 2 * self.ANCHO * escala + hueco
        x0 = (ancho - total) / 2
        y0 = (alto - (self.ALTO * escala + alto_etiqueta)) / 2

        izq = QTransform()
        izq.translate(x0, y0)
        izq.scale(escala, escala)
        der = QTransform()
        der.translate(x0 + 2 * self.ANCHO * escala + hueco, y0)
        der.scale(-escala, escala)
        transformaciones = {"izq": izq, "der": der}

        dedos = {
            numero: transformaciones[mano].map(self._dedos_unidad[tipo])
            for numero, (mano, tipo) in self._posiciones.items()
        }
        palmas = []
        for mano, etiqueta in (("izq", "Mano izquierda"), ("der", "Mano derecha")):
            borde_izq = x0 if mano == "izq" else x0 + self.ANCHO * escala + hueco
            rect = QRectF(borde_izq, y0 + self.ALTO * escala + 2, self.ANCHO * escala, alto_etiqueta)
            palmas.append((transformaciones[mano].map(self._palma_unidad), rect, etiqueta))
        return dedos, palmas

    def _dedo_en(self, pos):
        dedos, _ = self._geometria()
        for numero, camino in dedos.items():
            if camino.contains(pos):
                return numero
        return None

    # -- Pintado ----------------------------------------------------------
    def paintEvent(self, _event):
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.Antialiasing)
        dedos, palmas = self._geometria()

        for numero, camino in dedos.items():
            estado = self._estados.get(numero, "vacio")
            relleno, borde = self.COLORES[estado]
            seleccionado = numero == self._seleccionado
            color = QColor(relleno)
            if seleccionado and estado == "vacio":
                color = QColor("#DCE8FD")
            if numero == self._hover:
                color = color.lighter(106)

            caja = camino.boundingRect()
            degradado = QLinearGradient(caja.topLeft(), caja.bottomLeft())
            degradado.setColorAt(0.0, color.lighter(112))
            degradado.setColorAt(1.0, color)

            if seleccionado:
                pintor.setBrush(Qt.NoBrush)
                pintor.setPen(QPen(QColor(47, 111, 237, 70), 9, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                pintor.drawPath(camino)
            pintor.setBrush(degradado)
            pintor.setPen(QPen(QColor("#2F6FED") if seleccionado else QColor(borde),
                               3 if seleccionado else 1.4))
            pintor.drawPath(camino)

        fuente = QFont()
        fuente.setPointSizeF(9)
        fuente.setBold(True)
        pintor.setFont(fuente)
        for palma, rect, etiqueta in palmas:
            pintor.setBrush(QColor("#F4F7FB"))
            pintor.setPen(QPen(QColor("#D5DEE9"), 1.4))
            pintor.drawPath(palma)
            pintor.setPen(QColor("#64748B"))
            pintor.drawText(rect, Qt.AlignCenter, etiqueta)
        pintor.end()

    # -- Ratón ------------------------------------------------------------
    def _texto_tooltip(self, numero):
        estado = self._estados.get(numero, "vacio")
        return f"{self.nombres.get(numero, numero)}\n{self.TEXTO_ESTADO[estado]}"

    def mouseMoveEvent(self, evento):
        numero = self._dedo_en(evento.position())
        if numero != self._hover:
            self._hover = numero
            self.setCursor(Qt.PointingHandCursor if numero else Qt.ArrowCursor)
            self.setToolTip(self._texto_tooltip(numero) if numero else "")
            self.update()
        super().mouseMoveEvent(evento)

    def leaveEvent(self, evento):
        self._hover = None
        self.setCursor(Qt.ArrowCursor)
        self.update()
        super().leaveEvent(evento)

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            numero = self._dedo_en(evento.position())
            if numero:
                self.dedo_clicked.emit(numero)
        super().mousePressEvent(evento)


# ======================================================================
# Controlador de enrolamiento
# ======================================================================
class EnrolamientoController:
    """Controlador de enrolamiento que ejecuta en el hilo principal.

    libfprint necesita el main context de GLib del hilo principal,
    por lo que no se puede usar QThread. En su lugar, usamos
    QTimer.singleShot para ejecutar pasos asíncronos sin bloquear la UI.
    """

    def __init__(self, dialog, lector, dedo):
        self.dialog = dialog
        self.lector = lector
        self.dedo = dedo
        self._activo = False

    def iniciar(self):
        """Inicia el proceso de enrolamiento en el hilo principal."""
        self._activo = True
        log.debug("EnrolamientoController: iniciando conexión...")
        try:
            self.lector.conectar()
            log.debug("EnrolamientoController: lector conectado OK")
            # Usar QTimer para no bloquear la UI
            QTimer.singleShot(0, self._enrolar_paso)
        except Exception as error:
            log.exception("Error conectando lector")
            self._activo = False
            self.dialog._on_error(str(error))

    def _enrolar_paso(self):
        """Ejecuta un paso del enrolamiento (asíncrono vía QTimer)."""
        if not self._activo:
            return
        if getattr(self.lector, "soporta_sondeo", False):
            # ZKTeco admite consultas sin espera: se sondea con un QTimer en
            # vez de bloquear la interfaz durante los 3 toques.
            self._capturas = []
            self._sondear()
            return
        try:
            log.debug("EnrolamientoController: iniciando enrolar_dedo...")
            plantilla = self.lector.enrolar_dedo(self.dedo, self._on_avance)
            log.debug("EnrolamientoController: enrolamiento completado OK")
            self._activo = False
            self._cerrar_lector()
            self.dialog._on_plantilla_lista(plantilla, self.lector.tipo)
        except Exception as error:
            log.exception("Error en enrolamiento")
            self._fallar(str(error))

    # -- Enrolamiento ZKTeco sin bloquear -------------------------------
    def _sondear(self):
        if not self._activo:
            return
        try:
            datos = self.lector.capturar_para_enrolar_no_bloqueante()
        except Exception as error:
            log.exception("Error sondeando el lector ZKTeco")
            self._fallar(str(error))
            return
        if datos is None:
            if self._activo:
                QTimer.singleShot(120, self._sondear)
            return

        imagen, plantilla, ancho, alto = datos
        if self._capturas:
            score = self.lector.sdk.comparar_plantillas(
                self._capturas[-1], plantilla
            )
            if score < 0:
                self._fallar(f"Error comparando capturas (código {score})")
                return
            if score < UMBRAL_CONSISTENCIA:
                self._fallar(
                    "Parece que cambiaste de dedo. Empieza de nuevo y usa "
                    "siempre el MISMO dedo."
                )
                return
        self._capturas.append(plantilla)
        self.dialog._on_avance(len(self._capturas), 3, imagen, ancho, alto)

        if len(self._capturas) < 3:
            # Pausa para que el usuario levante el dedo entre toques.
            QTimer.singleShot(600, self._sondear)
            return
        try:
            final = self.lector.sdk.combinar_plantillas(*self._capturas)
        except Exception as error:
            log.exception("Error combinando plantillas")
            self._fallar(str(error))
            return
        self._activo = False
        self._cerrar_lector()
        self.dialog._on_plantilla_lista(final, self.lector.tipo)

    def _fallar(self, mensaje):
        self._activo = False
        self._cerrar_lector()
        self.dialog._on_error(mensaje)

    def _cerrar_lector(self):
        if self.lector and self.lector.conectado:
            try:
                self.lector.cerrar()
            except Exception:
                pass

    def _on_avance(self, completadas, total, imagen, ancho=0, alto=0):
        """Callback de progreso llamado por libfprint (hilo principal)."""
        if self._activo:
            self.dialog._on_avance(completadas, total, imagen, ancho, alto)

    def detener(self):
        """Detiene el proceso de enrolamiento y libera el lector."""
        self._activo = False
        self._cerrar_lector()


# ======================================================================
# Diálogo
# ======================================================================
class DialogCapturaHuella(QDialog):
    """Diálogo de enrolamiento de huella. Devuelve ``plantilla_final``."""

    MAX_HABILITADAS = 2  # Máximo de huellas habilitadas permitidas

    ESTILOS = """
        QDialog { background: #F1F5F9; }
        QLabel { background: transparent; border: none; }
        QScrollArea#scrollDialogo, QWidget#contenedorScroll {
            background: transparent;
            border: none;
        }

        QFrame#card {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
        }

        QLabel#dlgTitulo    { color: #0F2C59; font-size: 22px; font-weight: 800; }
        QLabel#dlgSubtitulo { color: #64748B; font-size: 13px; }
        QLabel#cardTitulo   { color: #1E293B; font-size: 15px; font-weight: 800; }
        QLabel#cardNota     { color: #94A3B8; font-size: 12px; }
        QLabel#campoEtiqueta { color: #334155; font-size: 12px; font-weight: 700; }
        QLabel#dedoNombre   { color: #0F172A; font-size: 17px; font-weight: 800; }
        QLabel#leyenda      { color: #64748B; font-size: 11px; }
        QLabel#estadoCaptura { color: #334155; font-size: 13px; font-weight: 600; }
        QLabel#toques       { color: #64748B; font-size: 12px; font-weight: 600; }

        QProgressBar#progresoCaptura {
            background: #E2E8F0; border: none; border-radius: 5px;
            min-height: 10px; max-height: 10px;
        }
        QProgressBar#progresoCaptura::chunk {
            background: #2F6FED; border-radius: 5px;
        }

        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 10px 18px;
            font-size: 14px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover    { background: #17449A; }
        QPushButton#btnPrimario:pressed  { background: #12367D; }
        QPushButton#btnPrimario:disabled { background: #A9BEE3; color: #FFFFFF; }

        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 10px;
            padding: 10px 18px; font-size: 14px; font-weight: 600;
        }
        QPushButton#btnSecundario:hover { background: #F1F5F9; }

        QPushButton#btnExito {
            background: #16A34A; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 10px 18px;
            font-size: 14px; font-weight: 700;
        }
        QPushButton#btnExito:hover    { background: #15803D; }
        QPushButton#btnExito:disabled { background: #CBD5E1; color: #64748B; }
    """

    COLORES_BANNER = {
        "aviso": ("#FEF3C7", "#FCD34D", "#92400E"),
        "ok": ("#DCFCE7", "#86EFAC", "#166534"),
        "error": ("#FEE2E2", "#FCA5A5", "#991B1B"),
    }

    def __init__(self, postulante=None, dedo_inicial=1, dedos_registrados=None,
                 dedos_habilitados=None, huellas_por_dedo=None, parent=None):
        super().__init__(parent)
        self.postulante = postulante or {}
        self.dedos_registrados = set(dedos_registrados or [])
        self.dedos_habilitados = set(dedos_habilitados or [])
        self.dedos_sin_habilitar = self.dedos_registrados - self.dedos_habilitados
        self.huellas_por_dedo = dict(huellas_por_dedo or {})
        self.guardar_habilitaciones_solicitado = False
        self.setWindowTitle("Registro de Huella")
        _ajustar_tamano_dialogo(self, 960, 720)
        self.setStyleSheet(self.ESTILOS)
        self.plantilla_final = None
        self.tipo_lector = ""
        self._worker = None
        self._lector_info = []

        self._crear_ui(dedo_inicial)
        self._actualizar_lectores()

    # ══════════════════════ INTERFAZ ══════════════════════
    def _crear_ui(self, dedo_inicial):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 16, 20, 16)
        raiz.setSpacing(10)

        # Encabezado fijo arriba
        nombre = self.postulante.get("nombre_completo")
        if not nombre and self.postulante.get("nombres"):
            nombre = f"{self.postulante.get('nombres')} {self.postulante.get('apellidos', '')}".strip()
        ci = self.postulante.get("ci", "")
        detalle = nombre or "Postulante"
        if ci:
            detalle += f"   ·   CI {ci}"

        lbl_titulo = QLabel("Registro de huella")
        lbl_titulo.setObjectName("dlgTitulo")
        lbl_sub = QLabel(detalle)
        lbl_sub.setObjectName("dlgSubtitulo")
        raiz.addWidget(lbl_titulo)
        raiz.addWidget(lbl_sub)

        # Área desplazable para el cuerpo (se activa en pantallas pequeñas)
        scroll = QScrollArea()
        scroll.setObjectName("scrollDialogo")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        contenedor_scroll = QWidget()
        contenedor_scroll.setObjectName("contenedorScroll")
        lay_scroll = QVBoxLayout(contenedor_scroll)
        lay_scroll.setContentsMargins(2, 4, 8, 4)
        lay_scroll.setSpacing(12)

        # Banner de estado del lector
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        lay_scroll.addWidget(self.banner)

        # Cuerpo: dedos a la izquierda, captura a la derecha
        cuerpo = QHBoxLayout()
        cuerpo.setSpacing(16)
        cuerpo.addLayout(self._crear_columna_dedos(dedo_inicial), 1)
        cuerpo.addWidget(self._crear_tarjeta_captura(), 0)
        lay_scroll.addLayout(cuerpo, 1)

        scroll.setWidget(contenedor_scroll)
        raiz.addWidget(scroll, 1)

        # Barra inferior fija (siempre visible en laptops)
        barra = QHBoxLayout()
        barra.addStretch()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self._cancelar_o_confirmar)

        self.btn_guardar_habilitaciones = QPushButton("Guardar cambios")
        self.btn_guardar_habilitaciones.setObjectName("btnExito")
        self.btn_guardar_habilitaciones.setMinimumHeight(40)
        self.btn_guardar_habilitaciones.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_habilitaciones.setEnabled(bool(self.huellas_por_dedo))
        self.btn_guardar_habilitaciones.clicked.connect(self._guardar_habilitaciones)

        barra.addWidget(self.btn_cancelar)
        barra.addWidget(self.btn_guardar_habilitaciones)
        raiz.addLayout(barra)

        self._actualizar_estado_dedos()

    def _crear_columna_dedos(self, dedo_inicial):
        columna = QVBoxLayout()
        columna.setSpacing(12)

        # ── Tarjeta con el mapa de manos ──
        tarjeta_manos = QFrame()
        tarjeta_manos.setObjectName("card")
        lay = QVBoxLayout(tarjeta_manos)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(4)

        titulo = QLabel("Selecciona el dedo")
        titulo.setObjectName("cardTitulo")
        nota = QLabel("Haz clic sobre un dedo para elegirlo. El color indica si ya tiene huella.")
        nota.setObjectName("cardNota")
        lay.addWidget(titulo)
        lay.addWidget(nota)

        self.mapa = MapaManos(DEDO_NOMBRES)
        self.mapa.dedo_clicked.connect(self._dedo_seleccionado)
        lay.addWidget(self.mapa, 1)
        lay.addLayout(self._crear_leyenda())
        columna.addWidget(tarjeta_manos, 1)

        # ── Tarjeta del dedo seleccionado ──
        tarjeta_dedo = QFrame()
        tarjeta_dedo.setObjectName("card")
        lay2 = QVBoxLayout(tarjeta_dedo)
        lay2.setContentsMargins(18, 14, 18, 14)
        lay2.setSpacing(8)

        fila = QHBoxLayout()
        self.lbl_dedo_nombre = QLabel("")
        self.lbl_dedo_nombre.setObjectName("dedoNombre")
        self.lbl_dedo_estado = QLabel("")
        fila.addWidget(self.lbl_dedo_nombre)
        fila.addStretch()
        fila.addWidget(self.lbl_dedo_estado)
        lay2.addLayout(fila)

        self.chk_habilitar = QCheckBox("Habilitar este dedo para la verificación")
        self.chk_habilitar.toggled.connect(self._cambiar_habilitar)
        lay2.addWidget(self.chk_habilitar)

        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setObjectName("cardNota")
        lay2.addWidget(self.lbl_resumen)
        columna.addWidget(tarjeta_dedo)

        # Selector interno (oculto) para compatibilidad con el código que lee
        # ``combo_dedo.currentData()`` desde fuera del diálogo.
        self.combo_dedo = QComboBox(self)
        for numero, nombre_dedo in DEDO_NOMBRES.items():
            self.combo_dedo.addItem(f"{numero} — {nombre_dedo}", numero)
        indice = self.combo_dedo.findData(dedo_inicial)
        if indice >= 0:
            self.combo_dedo.setCurrentIndex(indice)
        self.combo_dedo.setVisible(False)
        self.combo_dedo.currentIndexChanged.connect(self._actualizar_estado_dedos)
        return columna

    def _crear_leyenda(self):
        fila = QHBoxLayout()
        fila.setSpacing(14)
        items = (
            ("Habilitado", "#22C55E", "#15803D", 1),
            ("Registrado, sin habilitar", "#FBBF24", "#B45309", 1),
            ("Sin registrar", "#E8EEF5", "#C3CFDD", 1),
            ("Seleccionado", "#FFFFFF", "#2F6FED", 2),
        )
        for texto, fondo, borde, grosor in items:
            punto = QFrame()
            punto.setFixedSize(12, 12)
            punto.setStyleSheet(
                f"background: {fondo}; border: {grosor}px solid {borde}; border-radius: 6px;"
            )
            etiqueta = QLabel(texto)
            etiqueta.setObjectName("leyenda")
            sub = QHBoxLayout()
            sub.setSpacing(6)
            sub.addWidget(punto)
            sub.addWidget(etiqueta)
            fila.addLayout(sub)
        fila.addStretch()
        return fila

    def _crear_tarjeta_captura(self):
        tarjeta = QFrame()
        tarjeta.setObjectName("card")
        tarjeta.setFixedWidth(320)
        lay = QVBoxLayout(tarjeta)
        lay.setContentsMargins(18, 14, 18, 14)
        lay.setSpacing(8)

        titulo = QLabel("Captura de huella")
        titulo.setObjectName("cardTitulo")
        lay.addWidget(titulo)

        etiqueta_lector = QLabel("Lector")
        etiqueta_lector.setObjectName("campoEtiqueta")
        lay.addWidget(etiqueta_lector)
        self.combo_lector = QComboBox()
        self.combo_lector.setMinimumHeight(34)
        self.combo_lector.currentIndexChanged.connect(self._lector_cambiado)
        lay.addWidget(self.combo_lector)

        # Visor de la huella (ligeramente más compacto para encajar en 768p)
        self.visor = QLabel()
        self.visor.setAlignment(Qt.AlignCenter)
        self.visor.setFixedSize(230, 260)
        self._mostrar_placeholder()
        fila_visor = QHBoxLayout()
        fila_visor.addStretch()
        fila_visor.addWidget(self.visor)
        fila_visor.addStretch()
        lay.addLayout(fila_visor)

        self.lbl_estado = QLabel("Pulsa «Iniciar captura» y coloca el dedo en el lector.")
        self.lbl_estado.setObjectName("estadoCaptura")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setMinimumHeight(36)
        lay.addWidget(self.lbl_estado)

        self.lbl_toques = QLabel("Toques: 0")
        self.lbl_toques.setObjectName("toques")
        lay.addWidget(self.lbl_toques)

        self.progreso = QProgressBar()
        self.progreso.setObjectName("progresoCaptura")
        self.progreso.setRange(0, 3)
        self.progreso.setValue(0)
        self.progreso.setTextVisible(False)
        lay.addWidget(self.progreso)

        self.btn_iniciar = QPushButton("Iniciar captura")
        self.btn_iniciar.setObjectName("btnPrimario")
        self.btn_iniciar.setMinimumHeight(40)
        self.btn_iniciar.setCursor(Qt.PointingHandCursor)
        self.btn_iniciar.clicked.connect(self._iniciar_captura)
        lay.addWidget(self.btn_iniciar)
        lay.addStretch()
        return tarjeta

    def _mostrar_placeholder(self):
        self.visor.setText("Vista previa\nde la huella")
        self.visor.setStyleSheet(
            "background-color: #0B1220; border: 2px solid #E2E8F0; border-radius: 12px;"
            "color: #64748B; font-size: 13px; font-weight: 600;"
        )

    def _banner(self, texto, tipo="aviso"):
        fondo, borde, color = self.COLORES_BANNER[tipo]
        self.banner.setText(texto)
        self.banner.setStyleSheet(
            f"background: {fondo}; border: 1px solid {borde}; color: {color};"
            "border-radius: 10px; padding: 10px 14px; font-size: 12px; font-weight: 600;"
        )
        self.banner.setVisible(True)

    def _pintar_estado_dedo(self, texto, fondo, color):
        self.lbl_dedo_estado.setText(texto)
        self.lbl_dedo_estado.setStyleSheet(
            f"background: {fondo}; color: {color}; border-radius: 10px;"
            "padding: 3px 12px; font-size: 11px; font-weight: 700;"
        )

    # ══════════════════════ LECTORES ══════════════════════
    def _actualizar_lectores(self):
        """Detecta los lectores y llena el selector."""
        self._lector_info = []
        self.combo_lector.blockSignals(True)
        self.combo_lector.clear()
        try:
            lectores, usb_ok = detectar_lectores()
        except Exception:
            lectores, usb_ok = [], False

        libfprint_ok = libfprint_disponible()
        sdk_zk = sdk_zk_disponible()

        if not usb_ok:
            self._banner("No se pudo acceder al bus USB. "
                         "Ejecuta: sudo ./setup_lectores_huella.sh", "aviso")
            self.btn_iniciar.setEnabled(False)
            self.combo_lector.blockSignals(False)
            return

        if not lectores:
            self._banner("No se detectó ningún lector de huella. "
                         "Conecta el lector por USB.", "aviso")
            self.btn_iniciar.setEnabled(False)
            self.combo_lector.blockSignals(False)
            return

        # Construir la lista de lectores utilizables
        utilizables = []
        for lector in lectores:
            if lector.tipo == "libfprint":
                if libfprint_ok:
                    utilizables.append(lector)
            elif sdk_zk:
                utilizables.append(lector)

        for lector in utilizables:
            etiqueta = f"{lector.modelo} ({lector.tipo})"
            self.combo_lector.addItem(etiqueta, lector)
            self._lector_info.append(lector)

        if not utilizables:
            # Hay lectores, pero ninguno utilizable: explicar qué falta
            faltante = []
            if any(l.tipo == "zk" for l in lectores) and not sdk_zk:
                faltante.append("ZKFinger SDK de ZKTeco (para ZK4500/ZK9500)")
            if any(l.tipo == "libfprint" for l in lectores) and not libfprint_ok:
                faltante.append("libfprint-2")
            self._banner(
                f"Lector(es) conectado(s): {', '.join(l.modelo for l in lectores)}.\n"
                f"Falta por instalar: {', '.join(faltante)}.\n"
                "Ejecuta:  ./setup_lectores_huella.sh",
                "aviso",
            )
            self.btn_iniciar.setEnabled(False)
        else:
            lista = "\n".join(f"•  {l.descripcion}" for l in lectores)
            self._banner(f"Lector(es) detectado(s):\n{lista}", "ok")
            self.btn_iniciar.setEnabled(True)
        self.combo_lector.blockSignals(False)
        if self.combo_lector.count() > 0:
            self.combo_lector.setCurrentIndex(0)

    def _texto_instruccion(self):
        lector = self.combo_lector.currentData()
        if lector and lector.scan_type == "swipe":
            self.lbl_estado.setText("Pulsa «Iniciar captura» y PASA el dedo por el lector.")
        else:
            self.lbl_estado.setText(
                "Pulsa «Iniciar captura»; luego levanta el dedo "
                "y colócalo en el lector."
            )

    def _lector_cambiado(self, _indice):
        self._texto_instruccion()

    # ══════════════════════ DEDOS ══════════════════════
    def _dedo_actual(self):
        return self.combo_dedo.currentData() or 1

    def _actualizar_estado_dedos(self, *_):
        """Refresca el mapa de manos y el panel del dedo seleccionado."""
        numero = self._dedo_actual()
        self.mapa.set_estados(self.dedos_registrados, self.dedos_habilitados)
        self.mapa.set_seleccionado(numero)

        self.lbl_dedo_nombre.setText(DEDO_NOMBRES.get(numero, f"Dedo {numero}"))
        registrado = numero in self.dedos_registrados
        habilitado = numero in self.dedos_habilitados
        if habilitado:
            self._pintar_estado_dedo("Registrado y habilitado", "#DCFCE7", "#166534")
        elif registrado:
            self._pintar_estado_dedo("Registrado, sin habilitar", "#FEF3C7", "#92400E")
        else:
            self._pintar_estado_dedo("Sin registrar", "#E8EEF5", "#475569")

        self.chk_habilitar.blockSignals(True)
        self.chk_habilitar.setEnabled(registrado)
        self.chk_habilitar.setChecked(habilitado)
        self.chk_habilitar.blockSignals(False)

        self.lbl_resumen.setText(
            f"Huellas habilitadas: {len(self.dedos_habilitados)} de {self.MAX_HABILITADAS}"
            + ("" if registrado else "   ·   Registra este dedo para poder habilitarlo")
        )

    def _dedo_seleccionado(self, numero):
        """Selecciona un dedo desde el mapa de manos."""
        indice = self.combo_dedo.findData(numero)
        if indice >= 0:
            self.combo_dedo.setCurrentIndex(indice)
        self._actualizar_estado_dedos()
        self._texto_instruccion()

    def _cambiar_habilitar(self, marcado):
        """Habilita/deshabilita el dedo actual con límite de MAX_HABILITADAS."""
        numero = self._dedo_actual()
        if marcado:
            otros = [n for n in self.dedos_habilitados if n != numero]
            if len(otros) >= self.MAX_HABILITADAS:
                self.chk_habilitar.blockSignals(True)
                self.chk_habilitar.setChecked(False)
                self.chk_habilitar.blockSignals(False)
                QMessageBox.warning(
                    self, "Límite alcanzado",
                    f"Solo puedes habilitar un máximo de {self.MAX_HABILITADAS} huellas.\n"
                    "Deshabilita otra primero."
                )
                return
            self.dedos_habilitados.add(numero)
            self.dedos_sin_habilitar.discard(numero)
        else:
            self.dedos_habilitados.discard(numero)
            self.dedos_sin_habilitar.add(numero)
        self._actualizar_estado_dedos()

    def obtener_dedos_habilitados(self):
        """Devuelve el conjunto de dedos habilitados."""
        return set(self.dedos_habilitados)

    def _guardar_habilitaciones(self):
        """Solicita al formulario padre persistir los checks actuales."""
        self.guardar_habilitaciones_solicitado = True
        self.accept()

    # ══════════════════════ FLUJO DE ENROLAMIENTO ══════════════════════
    def _iniciar_captura(self):
        lector_info = self.combo_lector.currentData()
        if not lector_info:
            return
        log.info("=== INICIANDO CAPTURA: lector=%s, indice=%s, dedo=%s ===",
                 lector_info.nombre, lector_info.indice_sdk, self._dedo_actual())
        self.btn_iniciar.setEnabled(False)
        etapas = lector_info.etapas_enrolamiento if lector_info.tipo == "libfprint" else 3
        self.progreso.setRange(0, etapas)
        self.progreso.setValue(0)
        self.lbl_toques.setText(f"Toques: 0 de {etapas}")
        tipo = "swipe" if lector_info.scan_type == "swipe" else "press"
        self.lbl_estado.setText(
            "Pasa el dedo por el lector…" if tipo == "swipe"
            else "Levanta el dedo y colócalo en el lector…"
        )
        # Crear el lector en el hilo principal (libfprint necesita el main context de GLib)
        log.debug("Creando lector en hilo principal...")
        try:
            lector = crear_lector(
                lector_info.tipo, lector_info.indice_sdk, info=lector_info
            )
            log.debug("Lector creado OK: %s", lector)
        except Exception as e:
            log.exception("Error creando lector")
            self.lbl_estado.setText(f"Error creando lector: {e}")
            self.btn_iniciar.setEnabled(True)
            return
        # Usar EnrolamientoController (ejecuta en el hilo principal vía QTimer)
        self._controller = EnrolamientoController(self, lector, self._dedo_actual())
        log.debug("Iniciando EnrolamientoController...")
        self._controller.iniciar()

    def _on_avance(self, completadas, total, imagen, ancho, alto):
        self.progreso.setRange(0, total)
        self.progreso.setValue(completadas)
        self.lbl_toques.setText(f"Toques: {completadas} de {total}")
        if imagen:
            self._mostrar_imagen(imagen, ancho, alto)
        if completadas < total:
            self.lbl_estado.setText(
                f"Toque {completadas} de {total} capturado. "
                "Levanta el dedo y toca de nuevo (el mismo dedo)."
            )

    def _on_plantilla_lista(self, plantilla, tipo_lector):
        self.plantilla_final = prefijar_plantilla(plantilla, tipo_lector)
        self.tipo_lector = tipo_lector
        self.progreso.setValue(self.progreso.maximum())
        self.lbl_toques.setText(
            f"Toques: {self.progreso.maximum()} de {self.progreso.maximum()}"
        )
        self.lbl_estado.setText("Huella registrada. La plantilla está lista.")
        self.btn_iniciar.setEnabled(False)
        self.btn_iniciar.setText("Registrada")
        # No cerrar automáticamente: antes el diálogo desaparecía solo y se
        # enviaba la huella sin que el operador pudiera revisar el estado.
        self.btn_cancelar.setText("Guardar huella")
        self.btn_cancelar.setObjectName("btnExito")
        self.btn_cancelar.setEnabled(True)
        self.btn_cancelar.style().unpolish(self.btn_cancelar)
        self.btn_cancelar.style().polish(self.btn_cancelar)

    def _on_error(self, mensaje):
        self.lbl_estado.setText(f"Error: {mensaje}")
        self.btn_iniciar.setEnabled(True)
        self.btn_iniciar.setText("Reintentar")
        self.progreso.setValue(0)
        self.lbl_toques.setText("Toques: 0")

    def _mostrar_imagen(self, imagen_bytes, ancho=0, alto=0):
        """Renderiza una imagen cruda en escala de grises."""
        if not imagen_bytes:
            return
        # Tamaño real del lector; si no viene, probamos los
        # tamaños conocidos (ZK: 256×300, uru4000: variable).
        candidatos = []
        if ancho and alto and len(imagen_bytes) >= ancho * alto:
            candidatos.append((ancho, alto))
        candidatos.extend([(256, 300), (384, 289), (320, 240), (256, 288)])
        for (w, h) in candidatos:
            if len(imagen_bytes) >= w * h:
                datos = bytes(imagen_bytes[: w * h])
                # .copy() para que la imagen no dependa del buffer temporal
                qimg = QImage(datos, w, h, w, QImage.Format_Grayscale8).copy()
                pixmap = QPixmap.fromImage(qimg)
                self.visor.setPixmap(pixmap.scaled(
                    self.visor.width(), self.visor.height(),
                    Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
                self.visor.setStyleSheet(
                    "background-color: #0B1220; border: 2px solid #86EFAC; border-radius: 12px;"
                )
                return

    # ══════════════════════ CIERRE ══════════════════════
    def _cancelar_o_confirmar(self):
        """El botón inferior guarda la huella capturada o cancela el diálogo."""
        if self.plantilla_final is not None:
            self.accept()
        else:
            self.reject()

    def reject(self):
        self._detener_worker()
        super().reject()

    def accept(self):
        self._detener_worker()
        super().accept()

    def _detener_worker(self):
        if hasattr(self, '_controller') and self._controller:
            self._controller.detener()

    def closeEvent(self, event):
        self._detener_worker()
        super().closeEvent(event)
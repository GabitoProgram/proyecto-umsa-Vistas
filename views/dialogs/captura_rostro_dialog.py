import cv2
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QIcon,
    QImage,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


def _ajustar_tamano_dialogo(dialogo, ancho_deseado, alto_deseado):
    """Ajusta el diálogo al espacio disponible en pantallas pequeñas (laptops)."""
    pantalla = QGuiApplication.primaryScreen()
    if pantalla:
        disponible = pantalla.availableGeometry()
        ancho = min(ancho_deseado, int(disponible.width() * 0.92))
        alto = min(alto_deseado, int(disponible.height() * 0.88))
    else:
        ancho, alto = ancho_deseado, alto_deseado

    dialogo.setMinimumSize(min(540, ancho), min(440, alto))
    dialogo.resize(ancho, alto)


def _icono_camara(color, ancho=26, alto=20):
    """Ícono de cámara dibujado en código (sin emojis)."""
    pm = QPixmap(ancho * 2, alto * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(0, (alto - 18) / 2)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(2, 5.5, 14, 10), 2.4, 2.4)
    p.drawEllipse(QPointF(9, 10.5), 2.8, 2.8)
    tapa = QPainterPath()
    tapa.moveTo(6, 5.5)
    tapa.lineTo(7.4, 3.5)
    tapa.lineTo(10.6, 3.5)
    tapa.lineTo(12, 5.5)
    p.drawPath(tapa)
    p.end()
    return QIcon(pm)


def _icono_usb(color, tamano=16):
    """Ícono minimalista de puerto/conector para identificar cámaras externas."""
    pm = QPixmap(tamano * 2, tamano * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(4, 5, 8, 7), 1.5, 1.5)
    p.drawLine(QPointF(6.5, 5), QPointF(6.5, 2.5))
    p.drawLine(QPointF(9.5, 5), QPointF(9.5, 2.5))
    p.drawLine(QPointF(8, 12), QPointF(8, 14.5))
    p.end()
    return QIcon(pm)


def _icono_refrescar(color="#475569", tamano=16):
    """Ícono de recarga dibujado en código."""
    pm = QPixmap(tamano * 2, tamano * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(2.5, 2.5, tamano - 5, tamano - 5), 40 * 16, 280 * 16)
    p.drawLine(QPointF(tamano - 2.5, 2.5), QPointF(tamano - 2.5, 6.5))
    p.drawLine(QPointF(tamano - 2.5, 6.5), QPointF(tamano - 6.5, 6.5))
    p.end()
    return QIcon(pm)


class VisorCamara(QWidget):
    """Visor con esquinas redondeadas y un óvalo guía para centrar el rostro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        self.setMaximumSize(720, 460)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._imagen = None
        self._mensaje = "Iniciando cámara…"
        self._error = False

    def sizeHint(self):
        return QSize(600, 380)

    def mostrar_frame(self, imagen):
        self._imagen = imagen
        self._mensaje = ""
        self._error = False
        self.update()

    def mostrar_mensaje(self, texto, error=False):
        self._imagen = None
        self._mensaje = texto
        self._error = error
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        forma = QPainterPath()
        forma.addRoundedRect(QRectF(self.rect()), 14, 14)
        p.setClipPath(forma)
        p.fillRect(self.rect(), QColor("#0B1220"))

        if self._imagen is None:
            self._pintar_mensaje(p)
            p.end()
            return

        escalada = self._imagen.scaled(
            self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        x = (self.width() - escalada.width()) // 2
        y = (self.height() - escalada.height()) // 2
        p.drawImage(x, y, escalada)
        self._pintar_guia(p, QRectF(x, y, escalada.width(), escalada.height()))
        p.end()

    def _pintar_guia(self, p, area):
        ancho = area.width() * 0.46
        alto = area.height() * 0.82
        oval = QRectF(
            area.center().x() - ancho / 2, area.center().y() - alto / 2, ancho, alto
        )

        mascara = QPainterPath()
        mascara.addRect(area)
        mascara.addEllipse(oval)
        mascara.setFillRule(Qt.OddEvenFill)
        p.fillPath(mascara, QColor(11, 18, 32, 140))

        p.setBrush(Qt.NoBrush)
        p.setPen(QPen(QColor(255, 255, 255, 60), 8))
        p.drawEllipse(oval)
        p.setPen(QPen(QColor(255, 255, 255, 230), 2.4))
        p.drawEllipse(oval)

    def _pintar_mensaje(self, p):
        centro_x = self.width() / 2
        centro_y = self.height() / 2 - 34
        p.setPen(
            QPen(
                QColor("#F87171") if self._error else QColor("#475569"),
                2.2,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(QRectF(centro_x - 28, centro_y - 18, 56, 40), 8, 8)
        p.drawEllipse(QPointF(centro_x, centro_y + 2), 11, 11)
        tapa = QPainterPath()
        tapa.moveTo(centro_x - 12, centro_y - 18)
        tapa.lineTo(centro_x - 7, centro_y - 26)
        tapa.lineTo(centro_x + 7, centro_y - 26)
        tapa.lineTo(centro_x + 12, centro_y - 18)
        p.drawPath(tapa)
        if self._error:
            p.drawLine(
                QPointF(centro_x - 34, centro_y + 30),
                QPointF(centro_x + 34, centro_y - 38),
            )

        p.setPen(QColor("#FCA5A5") if self._error else QColor("#94A3B8"))
        fuente = p.font()
        fuente.setPointSizeF(10.5)
        p.setFont(fuente)
        p.drawText(
            QRectF(40, centro_y + 46, self.width() - 80, 90),
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            self._mensaje,
        )


class DialogCapturaRostro(QDialog):
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
            border-radius: 16px;
        }

        /* Barra contenedora del selector de cámaras */
        QFrame#barraCamaras {
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-radius: 12px;
        }

        QLabel#dlgTitulo    { color: #0F2C59; font-size: 22px; font-weight: 800; }
        QLabel#dlgSubtitulo { color: #64748B; font-size: 13px; }
        QLabel#estadoTexto  { color: #334155; font-size: 13px; font-weight: 600; }
        QLabel#lblFuente    { color: #475569; font-size: 12px; font-weight: 700; }
        QLabel#atajo        { color: #64748B; font-size: 12px; }
        QLabel#consejo {
            background: #EEF3FB; color: #1E4E96;
            border-radius: 10px; padding: 4px 10px;
            font-size: 11px; font-weight: 600;
        }

        /* Botones tipo Píldora (Chips) para elegir cámara en 1 clic */
        QPushButton#chipCamara {
            background: #FFFFFF;
            color: #475569;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 5px 12px;
            font-size: 12px;
            font-weight: 600;
        }
        QPushButton#chipCamara:hover {
            background: #F1F5F9;
            border-color: #94A3B8;
            color: #0F172A;
        }
        QPushButton#chipCamara:checked {
            background: #1E54B7;
            color: #FFFFFF;
            border: 1px solid #1E54B7;
            font-weight: 700;
        }

        /* Botón de recarga rápida en la barra */
        QPushButton#btnRefrescar {
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
        }
        QPushButton#btnRefrescar:hover {
            background: #E8F0FD;
            border-color: #1E54B7;
        }

        /* Botones principales inferiores */
        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 22px;
            font-size: 14px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover    { background: #17449A; }
        QPushButton#btnPrimario:pressed  { background: #12367D; }
        QPushButton#btnPrimario:disabled { background: #A9BEE3; color: #FFFFFF; }

        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 10px; padding: 0 22px;
            font-size: 14px; font-weight: 600;
        }
        QPushButton#btnSecundario:hover { background: #F1F5F9; }

        QPushButton#btnFantasma {
            background: transparent; color: #1E54B7; border: none;
            border-radius: 8px; padding: 0 12px;
            font-size: 12px; font-weight: 700;
        }
        QPushButton#btnFantasma:hover { background: #E8F0FD; }
    """

    COLORES_ESTADO = {
        "ok": "#22C55E",
        "aviso": "#F59E0B",
        "error": "#EF4444",
    }

    def __init__(self, parent=None, postulante=None):
        super().__init__(parent)
        self.setWindowTitle("Captura de Rostro")
        self.setStyleSheet(self.ESTILOS)
        self.postulante = postulante or {}
        self.imagen_capturada = None
        self.cap = None
        self.indice_actual = 0

        _ajustar_tamano_dialogo(self, 690, 620)
        self.init_ui()
        self.iniciar_camara()

    # ------------------------------------------------------------------
    # Interfaz
    # ------------------------------------------------------------------
    def init_ui(self):
        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 18, 22, 18)
        raiz.setSpacing(12)

        # Encabezado fijo
        lbl_titulo = QLabel("Captura de rostro")
        lbl_titulo.setObjectName("dlgTitulo")
        raiz.addWidget(lbl_titulo)

        nombre = self.postulante.get("nombre_completo")
        if not nombre and self.postulante.get("nombres"):
            nombre = f"{self.postulante.get('nombres')} {self.postulante.get('apellidos', '')}".strip()
        detalle = nombre or "Toma de fotografía facial"
        if nombre and self.postulante.get("ci"):
            detalle += f"   ·   CI {self.postulante.get('ci')}"
        lbl_sub = QLabel(detalle)
        lbl_sub.setObjectName("dlgSubtitulo")
        raiz.addWidget(lbl_sub)

        # Área desplazable para la tarjeta de la cámara
        scroll = QScrollArea()
        scroll.setObjectName("scrollDialogo")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        contenedor = QWidget()
        contenedor.setObjectName("contenedorScroll")
        lay_scroll = QVBoxLayout(contenedor)
        lay_scroll.setContentsMargins(2, 2, 6, 2)
        lay_scroll.setSpacing(10)

        # Tarjeta con el visor
        tarjeta = QFrame()
        tarjeta.setObjectName("card")
        lay = QVBoxLayout(tarjeta)
        lay.setContentsMargins(18, 16, 18, 14)
        lay.setSpacing(12)

        # --- BARRA MODERNA DE SELECCIÓN DE CÁMARAS ---
        barra_camaras = QFrame()
        barra_camaras.setObjectName("barraCamaras")
        fila_camara = QHBoxLayout(barra_camaras)
        fila_camara.setContentsMargins(12, 8, 12, 8)
        fila_camara.setSpacing(8)

        icono_lbl = QLabel()
        icono_lbl.setPixmap(_icono_camara("#475569", 20, 16).pixmap(20, 16))
        fila_camara.addWidget(icono_lbl)

        etiqueta_camara = QLabel("Dispositivo:")
        etiqueta_camara.setObjectName("lblFuente")
        fila_camara.addWidget(etiqueta_camara)

        # Grupo de botones exclusivos (Píldoras de 1 clic)
        self.grupo_camaras = QButtonGroup(self)
        self.grupo_camaras.setExclusive(True)

        opciones_camara = [
            (0, "Integrada (0)", False),
            (1, "USB 1", True),
            (2, "USB 2", True),
            (3, "USB 3", True),
        ]

        for idx, texto, es_usb in opciones_camara:
            btn_chip = QPushButton(texto)
            btn_chip.setObjectName("chipCamara")
            btn_chip.setCheckable(True)
            btn_chip.setCursor(Qt.PointingHandCursor)
            btn_chip.setMinimumHeight(30)
            if es_usb:
                btn_chip.setIcon(_icono_usb("#64748B", 14))
                btn_chip.setIconSize(QSize(14, 14))
                btn_chip.setToolTip(f"Conectar a cámara externa USB (Puerto {idx})")
            else:
                btn_chip.setToolTip("Cámara principal integrada en la laptop (Puerto 0)")

            if idx == 0:
                btn_chip.setChecked(True)

            self.grupo_camaras.addButton(btn_chip, idx)
            fila_camara.addWidget(btn_chip)

        self.grupo_camaras.idClicked.connect(self._camara_seleccionada)

        fila_camara.addStretch()

        # Botón de refrescar directo en la barra por si acaban de conectar el USB
        self.btn_refrescar_barra = QPushButton()
        self.btn_refrescar_barra.setObjectName("btnRefrescar")
        self.btn_refrescar_barra.setFixedSize(30, 30)
        self.btn_refrescar_barra.setCursor(Qt.PointingHandCursor)
        self.btn_refrescar_barra.setIcon(_icono_refrescar("#1E54B7", 16))
        self.btn_refrescar_barra.setIconSize(QSize(16, 16))
        self.btn_refrescar_barra.setToolTip("Reconectar / Actualizar cámara actual")
        self.btn_refrescar_barra.clicked.connect(self.iniciar_camara)
        fila_camara.addWidget(self.btn_refrescar_barra)

        lay.addWidget(barra_camaras)
        # ---------------------------------------------

        self.visor = VisorCamara()
        lay.addWidget(self.visor, 1, Qt.AlignHCenter)

        fila_estado = QHBoxLayout()
        fila_estado.setSpacing(8)
        self.punto_estado = QLabel()
        self.punto_estado.setFixedSize(10, 10)
        self.lbl_estado = QLabel("Iniciando cámara…")
        self.lbl_estado.setObjectName("estadoTexto")
        fila_estado.addWidget(self.punto_estado, 0, Qt.AlignVCenter)
        fila_estado.addWidget(self.lbl_estado)
        fila_estado.addStretch()
        for texto in ("Buena iluminación", "Mirar de frente", "Sin lentes oscuros"):
            chip = QLabel(texto)
            chip.setObjectName("consejo")
            fila_estado.addWidget(chip)
        lay.addLayout(fila_estado)

        lay_scroll.addWidget(tarjeta, 1)
        scroll.setWidget(contenedor)
        raiz.addWidget(scroll, 1)

        # Botones inferiores fijos
        fila_botones = QHBoxLayout()
        fila_botones.setSpacing(10)
        atajo = QLabel("Atajo: barra espaciadora")
        atajo.setObjectName("atajo")
        fila_botones.addWidget(atajo)
        fila_botones.addStretch()

        self.btn_reintentar = QPushButton("Reintentar cámara")
        self.btn_reintentar.setObjectName("btnFantasma")
        self.btn_reintentar.setMinimumHeight(40)
        self.btn_reintentar.setCursor(Qt.PointingHandCursor)
        self.btn_reintentar.clicked.connect(self.iniciar_camara)
        self.btn_reintentar.setVisible(False)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setObjectName("btnSecundario")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_capturar = QPushButton("Tomar foto")
        self.btn_capturar.setObjectName("btnPrimario")
        self.btn_capturar.setMinimumHeight(40)
        self.btn_capturar.setCursor(Qt.PointingHandCursor)
        self.btn_capturar.setIcon(_icono_camara("#FFFFFF"))
        self.btn_capturar.setIconSize(QSize(26, 20))
        self.btn_capturar.clicked.connect(self.capturar)

        fila_botones.addWidget(self.btn_reintentar)
        fila_botones.addWidget(self.btn_cancelar)
        fila_botones.addWidget(self.btn_capturar)
        raiz.addLayout(fila_botones)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_frame)

        self._poner_estado("Iniciando cámara…", "aviso")

    def _poner_estado(self, texto, tono):
        self.lbl_estado.setText(texto)
        self.punto_estado.setStyleSheet(
            f"background: {self.COLORES_ESTADO[tono]}; border-radius: 5px;"
        )

    def _actualizar_iconos_chips(self):
        """Actualiza el color del ícono USB a blanco cuando el chip está activo."""
        for btn in self.grupo_camaras.buttons():
            idx = self.grupo_camaras.id(btn)
            if idx > 0:
                color = "#FFFFFF" if btn.isChecked() else "#64748B"
                btn.setIcon(_icono_usb(color, 14))

    # ------------------------------------------------------------------
    # Cámara
    # ------------------------------------------------------------------
    def iniciar_camara(self):
        self.detener_camara()
        self._actualizar_iconos_chips()
        indice = self.indice_actual

        self.visor.mostrar_mensaje(f"Conectando con cámara {indice}…", error=False)
        self._poner_estado(f"Abriendo cámara {indice}…", "aviso")
        QGuiApplication.processEvents()

        self.cap = None
        try:
            cap = cv2.VideoCapture(int(indice), cv2.CAP_DSHOW)
        except (AttributeError, TypeError):
            cap = cv2.VideoCapture(int(indice))
        if cap.isOpened():
            self.cap = cap
        else:
            cap.release()
        if self.cap is None:
            # Algunos controladores no funcionan con DirectShow.
            cap = cv2.VideoCapture(int(indice))
            if cap.isOpened():
                self.cap = cap
            else:
                cap.release()
        if self.cap is None or not self.cap.isOpened():
            self.cap = None
            tipo = "integrada (0)" if indice == 0 else f"USB {indice}"
            self.visor.mostrar_mensaje(
                f"No se detectó la cámara {tipo}.\n"
                "Verifique que esté bien conectada por USB y que no esté en uso por otra aplicación.",
                error=True,
            )
            self._poner_estado(f"Cámara {tipo} no disponible", "error")
            self.btn_capturar.setEnabled(False)
            self.btn_reintentar.setVisible(True)
        else:
            self.btn_capturar.setEnabled(True)
            self.btn_reintentar.setVisible(False)
            self._poner_estado("Cámara activa. Centra el rostro en el óvalo.", "ok")
            self.timer.start(30)

    def _camara_seleccionada(self, indice):
        if indice == self.indice_actual and self.cap is not None:
            return
        self.indice_actual = indice
        self.iniciar_camara()

    def actualizar_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, _ = rgb.shape
                imagen = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
                self.visor.mostrar_frame(imagen)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.capturar()
        else:
            super().keyPressEvent(event)

    def capturar(self):
        if not self.cap or not self.cap.isOpened():
            QMessageBox.warning(
                self,
                "Cámara no disponible",
                "No se pudo acceder a la cámara. Cierre otras aplicaciones que la usen "
                "(o el registro de check-in) y vuelva a intentarlo.",
            )
            return
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(
                self,
                "Captura fallida",
                "No se pudo leer la imagen de la cámara. Intente nuevamente.",
            )
            return
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            QMessageBox.warning(
                self,
                "Captura fallida",
                "No se pudo codificar la imagen capturada. Intente nuevamente.",
            )
            return
        self.imagen_capturada = encoded.tobytes()
        self.accept()

    # ------------------------------------------------------------------
    # Cierre
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        self.detener_camara()
        super().closeEvent(event)

    def reject(self):
        self.detener_camara()
        super().reject()

    def accept(self):
        self.detener_camara()
        super().accept()

    def detener_camara(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None
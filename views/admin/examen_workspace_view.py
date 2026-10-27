import requests
from PySide6.QtWidgets import (
    QAbstractSpinBox, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QLineEdit, QSpinBox, QFileDialog, QInputDialog, QListWidget, QListWidgetItem,
    QScrollArea, QSizePolicy, QDialog, QComboBox
)
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
)
from desktop.config.app_config import AppConfig


# ----------------------------------------------------------------------
# Íconos de línea dibujados en código (sin emojis ni archivos externos)
# ----------------------------------------------------------------------
def _pixmap_icono(nombre, color, ancho=26, alto=20):
    pm = QPixmap(ancho * 2, alto * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(0, (alto - 18) / 2)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)

    if nombre == "mas":
        p.drawLine(QPointF(9, 3.5), QPointF(9, 14.5))
        p.drawLine(QPointF(3.5, 9), QPointF(14.5, 9))

    elif nombre == "menos":
        p.drawLine(QPointF(3.5, 9), QPointF(14.5, 9))

    elif nombre == "atras":
        ruta = QPainterPath()
        ruta.moveTo(11, 3.5)
        ruta.lineTo(5.5, 9)
        ruta.lineTo(11, 14.5)
        p.drawPath(ruta)

    elif nombre == "subir":
        p.drawLine(QPointF(9, 12), QPointF(9, 3.5))
        flecha = QPainterPath()
        flecha.moveTo(5.5, 7)
        flecha.lineTo(9, 3.5)
        flecha.lineTo(12.5, 7)
        p.drawPath(flecha)
        bandeja = QPainterPath()
        bandeja.moveTo(3, 11)
        bandeja.lineTo(3, 14.5)
        bandeja.lineTo(15, 14.5)
        bandeja.lineTo(15, 11)
        p.drawPath(bandeja)

    elif nombre == "lupa":
        p.drawEllipse(QPointF(8, 8), 4.8, 4.8)
        p.drawLine(QPointF(11.6, 11.6), QPointF(15.5, 15.5))

    elif nombre == "reporte":
        hoja = QPainterPath()
        hoja.moveTo(4.5, 2.5)
        hoja.lineTo(10.5, 2.5)
        hoja.lineTo(14, 6)
        hoja.lineTo(14, 15.5)
        hoja.lineTo(4.5, 15.5)
        hoja.closeSubpath()
        p.drawPath(hoja)
        doblez = QPainterPath()
        doblez.moveTo(10.5, 2.5)
        doblez.lineTo(10.5, 6)
        doblez.lineTo(14, 6)
        p.drawPath(doblez)
        p.drawLine(QPointF(7, 9.5), QPointF(11.5, 9.5))
        p.drawLine(QPointF(7, 12.3), QPointF(11.5, 12.3))

    elif nombre == "dado":
        p.drawRoundedRect(QRectF(3, 3, 12, 12), 2.6, 2.6)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(color))
        for x, y in ((6.3, 6.3), (11.7, 6.3), (9, 9), (6.3, 11.7), (11.7, 11.7)):
            p.drawEllipse(QPointF(x, y), 1.05, 1.05)

    elif nombre == "refrescar":
        p.drawArc(QRectF(3.5, 3.5, 11, 11), 60 * 16, 270 * 16)
        punta = QPainterPath()
        punta.moveTo(11.2, 2.6)
        punta.lineTo(14.6, 4.6)
        punta.lineTo(12.2, 7.4)
        p.drawPath(punta)

    elif nombre == "editar":
        lapiz = QPainterPath()
        lapiz.moveTo(11.5, 3.2)
        lapiz.lineTo(14.8, 6.5)
        lapiz.lineTo(6.8, 14.5)
        lapiz.lineTo(3.2, 14.8)
        lapiz.lineTo(3.5, 11.2)
        lapiz.closeSubpath()
        p.drawPath(lapiz)
        p.drawLine(QPointF(9.8, 4.9), QPointF(13.1, 8.2))

    p.end()
    return pm


def _icono(nombre, color, ancho=26):
    return QIcon(_pixmap_icono(nombre, color, ancho))


def _fuente_etiqueta(px, espaciado):
    """QSS no soporta letter-spacing; se define por código."""
    fuente = QFont()
    fuente.setPixelSize(px)
    fuente.setWeight(QFont.Bold)
    fuente.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return fuente


def _repolish(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


# ----------------------------------------------------------------------
# Diálogo estilizado para cambiar Aula y Asiento
# ----------------------------------------------------------------------
class DialogEditarAsignacion(QDialog):
    ESTILOS_DLG = """
        QDialog { background: #F8FAFC; }
        QLabel { background: transparent; border: none; }
        QFrame#cardDlg {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
        }
        QLabel#dlgTitulo { color: #0F2C59; font-size: 18px; font-weight: 800; }
        QLabel#dlgSub    { color: #64748B; font-size: 13px; font-weight: 600; }
        QLabel#lblCampo  { color: #334155; font-size: 12px; font-weight: 700; }

        QComboBox#comboDlg {
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 10px;
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 600;
            color: #0F172A;
        }
        QComboBox#comboDlg:hover { border-color: #94A3B8; }
        QComboBox#comboDlg:focus { border: 2px solid #1E54B7; }

        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover    { background: #17449A; }
        QPushButton#btnPrimario:pressed  { background: #12367D; }
        QPushButton#btnPrimario:disabled { background: #A9BEE3; color: #FFFFFF; }

        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 10px; padding: 0 16px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnSecundario:hover { background: #F1F5F9; }
    """

    def __init__(self, parent, postulante, aulas, api_base_url, headers):
        super().__init__(parent)
        self.setWindowTitle("Editar aula y asiento")
        self.setStyleSheet(self.ESTILOS_DLG)
        self.setFixedSize(420, 310)
        self.postulante = postulante
        self.aulas = aulas
        self.api_base_url = api_base_url
        self.headers = headers

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 18, 20, 18)
        lay.setSpacing(14)

        lbl_t = QLabel("Editar aula y asiento")
        lbl_t.setObjectName("dlgTitulo")
        nombre = postulante.get("nombre_completo") or "Postulante"
        ci = postulante.get("ci") or ""
        lbl_s = QLabel(f"{nombre}   ·   CI {ci}" if ci else nombre)
        lbl_s.setObjectName("dlgSub")
        lbl_s.setWordWrap(True)
        lay.addWidget(lbl_t)
        lay.addWidget(lbl_s)

        card = QFrame()
        card.setObjectName("cardDlg")
        form = QVBoxLayout(card)
        form.setContentsMargins(16, 14, 16, 16)
        form.setSpacing(10)

        lbl_aula = QLabel("AULA ASIGNADA")
        lbl_aula.setObjectName("lblCampo")
        lbl_aula.setFont(_fuente_etiqueta(10, 1.2))
        self.combo_aula = QComboBox()
        self.combo_aula.setObjectName("comboDlg")
        self.combo_aula.setMinimumHeight(38)

        actual_aula = postulante.get("nombre_aula")
        idx_inicial = 0
        for i, a in enumerate(self.aulas):
            self.combo_aula.addItem(str(a.get("nombre", "")), userData=a)
            if a.get("nombre") == actual_aula:
                idx_inicial = i

        lbl_asiento = QLabel("NÚMERO DE ASIENTO")
        lbl_asiento.setObjectName("lblCampo")
        lbl_asiento.setFont(_fuente_etiqueta(10, 1.2))
        self.combo_asiento = QComboBox()
        self.combo_asiento.setObjectName("comboDlg")
        self.combo_asiento.setMinimumHeight(38)

        form.addWidget(lbl_aula)
        form.addWidget(self.combo_aula)
        form.addSpacing(4)
        form.addWidget(lbl_asiento)
        form.addWidget(self.combo_asiento)
        lay.addWidget(card, 1)

        botones = QHBoxLayout()
        botones.addStretch()
        btn_cancelar = QPushButton("Cancelar")
        btn_cancelar.setObjectName("btnSecundario")
        btn_cancelar.setMinimumHeight(38)
        btn_cancelar.setCursor(Qt.PointingHandCursor)
        btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar cambios")
        self.btn_guardar.setObjectName("btnPrimario")
        self.btn_guardar.setMinimumHeight(38)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self.accept)

        botones.addWidget(btn_cancelar)
        botones.addWidget(self.btn_guardar)
        lay.addLayout(botones)

        self.combo_aula.currentIndexChanged.connect(self._cargar_asientos_aula)
        self.combo_aula.setCurrentIndex(idx_inicial)
        self._cargar_asientos_aula()

    def _cargar_asientos_aula(self):
        self.combo_asiento.clear()
        aula = self.combo_aula.currentData()
        if not aula:
            self.btn_guardar.setEnabled(False)
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/aulas/{aula['id_aula']}/asientos",
                headers=self.headers,
                timeout=5,
            )
            if respuesta.status_code != 200:
                self.btn_guardar.setEnabled(False)
                return
            asientos = [a for a in respuesta.json() if a.get("habilitado", True)]
        except (requests.RequestException, ValueError):
            self.btn_guardar.setEnabled(False)
            return

        asientos.sort(key=lambda a: a.get("numero_asiento", 0))
        if not asientos:
            self.combo_asiento.addItem("Sin asientos habilitados", userData=None)
            self.btn_guardar.setEnabled(False)
            return

        actual_asiento = self.postulante.get("numero_asiento")
        idx_asiento = 0
        for i, a in enumerate(asientos):
            num = a.get("numero_asiento")
            self.combo_asiento.addItem(f"Asiento #{num}", userData=a)
            if num == actual_asiento:
                idx_asiento = i
        self.combo_asiento.setCurrentIndex(idx_asiento)
        self.btn_guardar.setEnabled(True)

    def seleccion(self):
        return self.combo_aula.currentData(), self.combo_asiento.currentData()


class ExamenWorkspaceView(QWidget):
    volver = Signal()

    # Los estilos usan nombres de objeto: así no se mezclan con el estilo global
    # de la aplicación (assets/styles.qss) ni se heredan a los cuadros de diálogo.
    ESTILOS = """
        QWidget#workspaceRoot, QWidget#workspaceContenido, QWidget#tabPagina {
            background: #F8FAFC;
        }
        QScrollArea#workspaceScroll { background: transparent; border: none; }
        QLabel { background: transparent; border: none; }

        /* ---------- Encabezado ---------- */
        QLabel#breadcrumb   { color: #64748B; font-size: 12px; font-weight: 600; }
        QLabel#paginaTitulo { color: #0F2C59; font-size: 26px; font-weight: 800; }
        QLabel#paginaSub    { color: #64748B; font-size: 13px; }

        QFrame#panel {
            background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
        }
        QLabel#cardTitulo { color: #1E293B; font-size: 15px; font-weight: 800; }
        QLabel#cardNota   { color: #94A3B8; font-size: 12px; }
        QLabel#chip {
            background: #E8F0FD; color: #1E54B7;
            border-radius: 12px; padding: 5px 14px;
            font-size: 12px; font-weight: 700;
        }

        /* ---------- Datos del examen ---------- */
        QFrame#tile {
            background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 14px;
        }
        QFrame#tileAviso {
            background: #FEF3C7; border: 1px solid #FCD34D; border-radius: 14px;
        }
        QLabel#tileEtiqueta      { color: #64748B; }
        QLabel#tileEtiquetaAviso { color: #A16207; }
        QLabel#tileValor         { color: #0F2C59; font-size: 16px; font-weight: 800; }
        QLabel#tileValorAviso    { color: #92400E; font-size: 16px; font-weight: 800; }

        /* ---------- Botones ---------- */
        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 16px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover    { background: #17449A; }
        QPushButton#btnPrimario:pressed  { background: #12367D; }
        QPushButton#btnPrimario:disabled { background: #CBD5E1; color: #64748B; }

        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 10px; padding: 0 16px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnSecundario:hover   { background: #F1F5F9; border: 1px solid #B6C3D4; }
        QPushButton#btnSecundario:pressed { background: #E2E8F0; }

        QPushButton#btnExito {
            background: #16A34A; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnExito:hover   { background: #15803D; }
        QPushButton#btnExito:pressed { background: #166534; }

        QPushButton#btnPeligro {
            background: #FFFFFF; color: #B91C1C;
            border: 1px solid #FCA5A5; border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnPeligro:hover { background: #FEF2F2; }

        QPushButton#btnFantasma {
            background: transparent; color: #475569; border: none;
            border-radius: 8px; padding: 0 12px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnFantasma:hover { background: #E2E8F0; color: #0F172A; }

        /* ---------- Campos ---------- */
        QLineEdit#buscador {
            background: #FFFFFF; border: 1px solid #D5DEE9;
            border-radius: 10px; padding: 8px 12px;
            font-size: 14px; color: #0F172A;
            selection-background-color: #BFD6F6; selection-color: #0F172A;
        }
        QLineEdit#buscador:hover { border: 1px solid #A9BBD1; }
        QLineEdit#buscador:focus { border: 2px solid #1E54B7; padding: 7px 11px; }

        QSpinBox#spinTolerancia {
            background: #FFFFFF; border: 1px solid #D5DEE9; border-radius: 10px;
            padding: 6px 12px; font-size: 14px; font-weight: 700; color: #0F172A;
        }
        QSpinBox#spinTolerancia:focus { border: 2px solid #1E54B7; padding: 5px 11px; }

        /* ---------- Pestañas ---------- */
        QTabWidget#tabsWorkspace::pane {
            border: none; background: transparent; top: 0px; padding: 0px;
        }
        QTabWidget#tabsWorkspace QTabBar::tab {
            background: transparent; color: #64748B;
            border: none; border-bottom: 3px solid transparent;
            border-radius: 0px; padding: 10px 20px; margin-right: 8px;
            font-size: 13px; font-weight: 700;
        }
        QTabWidget#tabsWorkspace QTabBar::tab:hover { color: #334155; background: transparent; }
        QTabWidget#tabsWorkspace QTabBar::tab:selected {
            color: #1E54B7; background: transparent; border-bottom: 3px solid #1E54B7;
        }

        /* ---------- Tablas y lista ---------- */
        QTableWidget#tablaWs {
            background: #FFFFFF; alternate-background-color: #F8FAFD;
            border: none; outline: none; gridline-color: transparent;
            color: #1E293B; font-size: 13px;
            selection-background-color: #E3EEFC; selection-color: #0F2C59;
        }
        QTableWidget#tablaWs::item { padding: 6px 10px; border: none; }
        QTableWidget#tablaWs QHeaderView::section {
            background: #F8FAFC; color: #64748B;
            border: none; border-bottom: 1px solid #E2E8F0;
            padding: 12px 10px; font-size: 12px; font-weight: 700;
        }
        QTableWidget#tablaWs QTableCornerButton::section { background: #F8FAFC; border: none; }

        QListWidget#listaAulas {
            background: #FFFFFF; border: none; outline: none;
            color: #1E293B; font-size: 14px;
        }
        QListWidget#listaAulas::item {
            padding: 12px 10px; border-bottom: 1px solid #EEF2F7;
        }
        QListWidget#listaAulas::item:hover    { background: #F4F8FD; }
        QListWidget#listaAulas::item:selected { background: #E3EEFC; color: #0F2C59; }

        /* ---------- Disponibilidad de sillas ---------- */
        QFrame#stat {
            background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px;
        }
        QLabel#statEtiqueta { color: #64748B; }
        QLabel#statValor    { color: #0F2C59; font-size: 34px; font-weight: 800; }
        QLabel#statSub      { color: #94A3B8; font-size: 12px; }

        QLabel#estadoSillas {
            border-radius: 10px; padding: 12px 14px;
            font-size: 14px; font-weight: 700;
        }
        QLabel#estadoSillas[tono="neutro"] {
            background: #F1F5F9; color: #475569; border-left: 4px solid #94A3B8;
        }
        QLabel#estadoSillas[tono="ok"] {
            background: #DCFCE7; color: #166534; border-left: 4px solid #16A34A;
        }
        QLabel#estadoSillas[tono="aviso"] {
            background: #FEF3C7; color: #92400E; border-left: 4px solid #D97706;
        }

        /* ---------- Scrollbar ---------- */
        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #C3D2E0; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #9FB6CB; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    def __init__(self, examen_data, token_data=None, api_base_url=None, parent=None):
        super().__init__(parent)
        self.examen = examen_data
        self.token_data = token_data or {}
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self.tolerancia_actual = self.examen.get("tolerancia_minutos", 10)
        self.aulas_disponibles = []
        self.postulantes_examen = []
        self.asignaciones_examen = []
        self.carrera_nombre = ""
        self.init_ui()
        QTimer.singleShot(0, self._cargar_inicial)

    def get_auth_headers(self):
        token = self.token_data.get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    def _cargar_inicial(self):
        self._resolver_carrera()
        self.chip_carrera.lbl_valor.setText(self.carrera_nombre or "—")
        self.lbl_subtitulo.setText(self.carrera_nombre or "Examen")
        self.cargar_postulantes_examen()
        self.cargar_aulas_sorteo()
        self.cargar_asignaciones()

    def _resolver_carrera(self):
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/carreras",
                headers=self.get_auth_headers(),
                timeout=4
            )
            if respuesta.status_code == 200:
                id_carrera = self.examen.get("id_carrera")
                for carrera in respuesta.json():
                    if carrera.get("id_carrera") == id_carrera:
                        self.carrera_nombre = carrera.get("nombre", "")
                        break
        except (requests.RequestException, ValueError):
            self.carrera_nombre = ""

    # ══════════════════ PIEZAS REUTILIZABLES ══════════════════
    @staticmethod
    def _boton(texto, tipo="primario", icono=None, alto=40):
        nombres = {
            "primario": "btnPrimario", "secundario": "btnSecundario",
            "exito": "btnExito", "peligro": "btnPeligro", "fantasma": "btnFantasma",
        }
        boton = QPushButton(texto)
        boton.setObjectName(nombres[tipo])
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFocusPolicy(Qt.NoFocus)
        boton.setMinimumHeight(alto)
        if icono:
            color = "#FFFFFF" if tipo in ("primario", "exito") else (
                "#B91C1C" if tipo == "peligro" else "#334155")
            boton.setIcon(_icono(icono, color))
            boton.setIconSize(QSize(26, 20))
        return boton

    @staticmethod
    def _preparar_tabla(tabla):
        tabla.setObjectName("tablaWs")
        tabla.setFrameShape(QFrame.NoFrame)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        tabla.verticalHeader().setVisible(False)
        tabla.verticalHeader().setDefaultSectionSize(52)
        tabla.horizontalHeader().setHighlightSections(False)
        tabla.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    @staticmethod
    def _en_panel(widget, margen=10):
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(margen, margen, margen, margen)
        lay.addWidget(widget)
        return panel

    def init_ui(self):
        self.setObjectName("workspaceRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(self.ESTILOS)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setObjectName("workspaceScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        contenedor.setObjectName("workspaceContenido")
        contenedor.setAttribute(Qt.WA_StyledBackground, True)
        main_layout = QVBoxLayout(contenedor)
        main_layout.setContentsMargins(32, 26, 32, 24)
        main_layout.setSpacing(18)

        # Barra superior: volver + ruta
        barra_sup = QHBoxLayout()
        barra_sup.setSpacing(8)
        btn_volver = self._boton("Volver", "fantasma", "atras")
        btn_volver.clicked.connect(self.volver.emit)
        lbl_ruta = QLabel("Académico   ›   Gestiones   ›   Carreras   ›   Exámenes   ›   Espacio del examen")
        lbl_ruta.setObjectName("breadcrumb")
        barra_sup.addWidget(btn_volver)
        barra_sup.addWidget(lbl_ruta)
        barra_sup.addStretch()
        main_layout.addLayout(barra_sup)

        main_layout.addLayout(self._crear_header_examen())
        main_layout.addWidget(self._crear_tarjeta_tolerancia())

        # Pestañas del workspace
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tabsWorkspace")
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self._crear_tab_postulantes(), "Postulantes e inscripción")
        self.tabs.addTab(self._crear_tab_aulas_sorteo(), "Aulas y sorteo de asientos")
        main_layout.addWidget(self.tabs, stretch=1)

        scroll.setWidget(contenedor)
        outer.addWidget(scroll)

    # ══════════════════ ENCABEZADO ══════════════════
    def _crear_header_examen(self):
        caja = QVBoxLayout()
        caja.setSpacing(14)

        fila = QHBoxLayout()
        fila.setSpacing(12)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_materia = QLabel(self.examen.get("materia", "Examen"))
        lbl_materia.setObjectName("paginaTitulo")
        lbl_materia.setWordWrap(True)
        self.lbl_subtitulo = QLabel("Examen")
        self.lbl_subtitulo.setObjectName("paginaSub")
        textos.addWidget(lbl_materia)
        textos.addWidget(self.lbl_subtitulo)
        fila.addLayout(textos, 1)

        self.btn_reporte = self._boton("Generar reporte", "primario", "reporte")
        self.btn_reporte.setMinimumWidth(170)
        self.btn_reporte.clicked.connect(self.exportar_reporte)
        fila.addWidget(self.btn_reporte, 0, Qt.AlignBottom)
        caja.addLayout(fila)

        chips = QHBoxLayout()
        chips.setSpacing(14)
        chips.addWidget(self._chip("FECHA", str(self.examen.get("fecha", "—"))), 1)
        chips.addWidget(self._chip(
            "HORARIO",
            f"{self.examen.get('hora_inicio', '—')} – {self.examen.get('hora_fin', '—')}"
        ), 1)
        self.chip_carrera = self._chip("CARRERA", "—", guardar_valor=True)
        chips.addWidget(self.chip_carrera, 1)
        self.chip_tolerancia = self._chip(
            "TOLERANCIA ACTUAL", f"{self.tolerancia_actual} min",
            destacado=True, guardar_valor=True
        )
        chips.addWidget(self.chip_tolerancia, 1)
        caja.addLayout(chips)
        return caja

    def _chip(self, etiqueta, valor, destacado=False, guardar_valor=False):
        chip = QFrame()
        chip.setObjectName("tileAviso" if destacado else "tile")
        lay = QVBoxLayout(chip)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(3)
        lbl_e = QLabel(etiqueta)
        lbl_e.setObjectName("tileEtiquetaAviso" if destacado else "tileEtiqueta")
        lbl_e.setFont(_fuente_etiqueta(10, 1.5))
        lbl_v = QLabel(str(valor))
        lbl_v.setObjectName("tileValorAviso" if destacado else "tileValor")
        lbl_v.setWordWrap(True)
        lay.addWidget(lbl_e)
        lay.addWidget(lbl_v)
        if guardar_valor:
            chip.lbl_valor = lbl_v
        return chip

    def _crear_tarjeta_tolerancia(self):
        panel = QFrame()
        panel.setObjectName("panel")
        fila = QHBoxLayout(panel)
        fila.setContentsMargins(22, 16, 22, 16)
        fila.setSpacing(10)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        lbl_tol = QLabel("Tolerancia de ingreso")
        lbl_tol.setObjectName("cardTitulo")
        lbl_ayuda = QLabel("Permite el ingreso hasta la hora de fin más la tolerancia.")
        lbl_ayuda.setObjectName("cardNota")
        textos.addWidget(lbl_tol)
        textos.addWidget(lbl_ayuda)
        fila.addLayout(textos, 1)

        btn_menos_5 = self._boton("5", "secundario", "menos", alto=40)
        btn_menos_5.setToolTip("Restar 5 minutos")
        btn_menos_5.clicked.connect(
            lambda: self.spin_tol.setValue(max(0, self.spin_tol.value() - 5)))

        self.spin_tol = QSpinBox()
        self.spin_tol.setObjectName("spinTolerancia")
        self.spin_tol.setRange(0, 180)
        self.spin_tol.setValue(self.tolerancia_actual)
        self.spin_tol.setSuffix(" min")
        self.spin_tol.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.spin_tol.setAlignment(Qt.AlignCenter)
        self.spin_tol.setMinimumHeight(40)
        self.spin_tol.setMinimumWidth(110)
        self.spin_tol.setToolTip("Tolerancia adicional después de la hora de cierre")

        btn_mas_5 = self._boton("5", "secundario", "mas", alto=40)
        btn_mas_5.setToolTip("Sumar 5 minutos")
        btn_mas_5.clicked.connect(lambda: self.ajustar_tolerancia(self.tolerancia_actual + 5))
        btn_mas_10 = self._boton("10", "secundario", "mas", alto=40)
        btn_mas_10.setToolTip("Sumar 10 minutos y aplicar")
        btn_mas_10.clicked.connect(lambda: self.ajustar_tolerancia(self.tolerancia_actual + 10))

        btn_aplicar = self._boton("Aplicar", "primario", alto=40)
        btn_aplicar.setMinimumWidth(100)
        btn_aplicar.clicked.connect(lambda: self.ajustar_tolerancia(self.spin_tol.value()))

        for widget in (btn_menos_5, self.spin_tol, btn_mas_5, btn_mas_10, btn_aplicar):
            fila.addWidget(widget)
        return panel

    # ══════════════════ PESTAÑA POSTULANTES ══════════════════
    def _crear_tab_postulantes(self):
        w = QWidget()
        w.setObjectName("tabPagina")
        w.setAttribute(Qt.WA_StyledBackground, True)
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 18, 0, 0)
        l.setSpacing(14)

        bar = QHBoxLayout()
        bar.setSpacing(12)
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setObjectName("buscador")
        self.txt_buscar.setPlaceholderText("Buscar postulante por CI, nombre o apellido…")
        self.txt_buscar.setMinimumHeight(44)
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.addAction(_icono("lupa", "#94A3B8", ancho=20), QLineEdit.LeadingPosition)
        paleta = self.txt_buscar.palette()
        paleta.setColor(QPalette.PlaceholderText, QColor("#94A3B8"))
        self.txt_buscar.setPalette(paleta)
        self.txt_buscar.textChanged.connect(self.filtrar_postulantes)

        self.lbl_contador = QLabel("0 postulantes")
        self.lbl_contador.setObjectName("chip")

        bar.addWidget(self.txt_buscar, stretch=1)
        bar.addWidget(self.lbl_contador)
        l.addLayout(bar)

        self.tabla_postulantes = QTableWidget(0, 8)
        self._preparar_tabla(self.tabla_postulantes)
        self.tabla_postulantes.setHorizontalHeaderLabels([
            "C.I.", "Postulante", "Inscripción", "Aula", "Asiento", "Huellas", "Rostro", "Acción"
        ])
        header = self.tabla_postulantes.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        for col in (0, 2, 4, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        # Ancho fijo amplio para la columna Acción así jamás recorta el botón
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.tabla_postulantes.setColumnWidth(7, 175)
        self.tabla_postulantes.setMinimumHeight(360)
        l.addWidget(self._en_panel(self.tabla_postulantes), stretch=1)
        return w

    def cargar_postulantes_examen(self):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/examenes/{id_examen}/postulantes",
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code == 200:
                self.postulantes_examen = respuesta.json()
                self.filtrar_postulantes(self.txt_buscar.text())
        except requests.RequestException:
            self.postulantes_examen = []

    def inscribir_manual(self):
        datos = {}
        for campo, etiqueta in (
            ("ci", "C.I."),
            ("nombres", "Nombres"),
            ("apellidos", "Apellidos")
        ):
            valor, aceptado = QInputDialog.getText(self, "Inscripción manual", f"{etiqueta}:")
            if not aceptado or not valor.strip():
                return
            datos[campo] = valor.strip()
        datos["genero"] = None
        try:
            postulante = requests.post(
                f"{self.api_base_url}/postulantes/",
                json=datos,
                headers=self.get_auth_headers(),
                timeout=6
            )
            if postulante.status_code not in (200, 201):
                QMessageBox.warning(self, "Inscripción", str(postulante.json().get("detail", "No se pudo registrar el postulante.")))
                return
            id_postulante = postulante.json().get("id_postulante")
            inscripcion = requests.post(
                f"{self.api_base_url}/inscripciones",
                json={
                    "id_postulante": id_postulante,
                    "id_gestion": self.examen.get("id_gestion"),
                    "id_carrera": self.examen.get("id_carrera"),
                    "estado": "HABILITADO"
                },
                headers=self.get_auth_headers(),
                timeout=6
            )
            if inscripcion.status_code in (200, 201):
                self.cargar_postulantes_examen()
                QMessageBox.information(self, "Inscripción", "Postulante inscrito correctamente.")
            else:
                QMessageBox.warning(self, "Inscripción", str(inscripcion.json().get("detail", "No se pudo crear la inscripción.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Inscripción", f"Error de conexión: {error}")

    def importar_postulantes_excel(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel", "", "Excel (*.xlsx *.xls)"
        )
        if not archivo:
            return
        try:
            with open(archivo, "rb") as contenido:
                respuesta = requests.post(
                    f"{self.api_base_url}/postulantes/importar-excel",
                    files={"file": (archivo.split("/")[-1], contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=self.get_auth_headers(),
                    timeout=30
                )
            if respuesta.status_code == 200:
                self.cargar_postulantes_examen()
                QMessageBox.information(self, "Importación", respuesta.json().get("mensaje", "Importación completada."))
            else:
                QMessageBox.warning(self, "Importación", str(respuesta.json().get("detail", "No se pudo importar el archivo.")))
        except (OSError, requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Importación", f"Error al importar: {error}")

    def filtrar_postulantes(self, texto):
        texto = texto.strip().lower()
        filas = [p for p in self.postulantes_examen if not texto or texto in (
            f"{p.get('ci', '')} {p.get('nombre_completo', '')}"
        ).lower()]
        total = len(self.postulantes_examen)
        palabra = "postulante" if total == 1 else "postulantes"
        self.lbl_contador.setText(
            f"{len(filas)} de {total} {palabra}" if texto else f"{total} {palabra}"
        )

        verde = QBrush(QColor("#15803D"))
        gris = QBrush(QColor("#94A3B8"))
        rojo = QBrush(QColor("#B91C1C"))
        self.tabla_postulantes.setRowCount(len(filas))
        for fila, postulante in enumerate(filas):
            id_asignacion = postulante.get("id_asignacion")
            if not id_asignacion:
                id_asignacion = next(
                    (
                        asignacion.get("id_asignacion")
                        for asignacion in self.asignaciones_examen
                        if asignacion.get("id_inscripcion") == postulante.get("id_inscripcion")
                    ),
                    None,
                )
                if id_asignacion:
                    postulante = dict(postulante)
                    postulante["id_asignacion"] = id_asignacion
            huellas = [h for h in postulante.get("huellas", []) if h.get("habilitada")]
            aula = postulante.get("nombre_aula") or "sin asignar"
            asiento = postulante.get("numero_asiento")
            estado = str(postulante.get("estado_inscripcion") or "")

            valores = (
                postulante.get("ci"),
                postulante.get("nombre_completo"),
                estado,
                aula,
                f"#{asiento}" if asiento else "—",
                ", ".join(str(h.get("tipo_dedo")) for h in huellas) or "ninguna",
                "HABILITADO" if postulante.get("rostro_habilitado") else "DESHABILITADO",
            )
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                if columna in (0, 2, 4, 5, 6):
                    item.setTextAlignment(Qt.AlignCenter)
                if columna == 1:
                    fuente = item.font()
                    fuente.setBold(True)
                    item.setFont(fuente)
                if columna == 2:
                    if estado.upper() == "HABILITADO":
                        item.setForeground(verde)
                    elif estado.upper() in ("RETIRADO", "ANULADO"):
                        item.setForeground(rojo)
                if columna == 3:
                    item.setForeground(verde if postulante.get("nombre_aula") else gris)
                if columna == 5 and not huellas:
                    item.setForeground(gris)
                if columna == 6:
                    item.setForeground(verde if postulante.get("rostro_habilitado") else gris)
                self.tabla_postulantes.setItem(fila, columna, item)

            # Botón con el mismo estilo exacto de "Generar reporte" (btnPrimario).
            # La celda y el botón llevan parent para no existir nunca como ventanas sueltas.
            celda = QWidget(self.tabla_postulantes)
            lay_celda = QHBoxLayout(celda)
            lay_celda.setContentsMargins(8, 7, 8, 7)

            boton = self._boton("Editar asiento", "primario", "editar", alto=36)
            boton.setParent(celda)
            boton.setMinimumWidth(150)
            boton.clicked.connect(
                lambda _checked=False, p=postulante: self.editar_asignacion_postulante(p)
            )
            lay_celda.addWidget(boton)
            self.tabla_postulantes.setCellWidget(fila, 7, celda)

    def editar_asignacion_postulante(self, postulante):
        id_asignacion = postulante.get("id_asignacion")
        if not id_asignacion:
            QMessageBox.information(
                self, "Sin asignación",
                "Este postulante todavía no tiene aula ni asiento asignados.",
            )
            return

        if not self.aulas_disponibles:
            self.cargar_aulas_sorteo()
        aulas = self.aulas_disponibles
        if not aulas:
            QMessageBox.warning(self, "Aulas", "No hay aulas activas disponibles.")
            return

        dlg = DialogEditarAsignacion(
            self, postulante, aulas, self.api_base_url, self.get_auth_headers()
        )
        if dlg.exec() != QDialog.Accepted:
            return
        aula, asiento = dlg.seleccion()
        if not aula or not asiento:
            return

        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/asignaciones/{id_asignacion}",
                json={
                    "id_aula": aula["id_aula"],
                    "id_asiento": asiento["id_asiento"],
                },
                headers=self.get_auth_headers(),
                timeout=6,
            )
            if respuesta.status_code == 200:
                self.cargar_postulantes_examen()
                self.cargar_asignaciones()
                QMessageBox.information(
                    self, "Asignación actualizada",
                    "El aula y el asiento se actualizaron correctamente.",
                )
            else:
                detalle = respuesta.json().get("detail", "No se pudo actualizar la asignación.")
                QMessageBox.warning(self, "Asignación", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Error de red", str(error))

    # ══════════════════ PESTAÑA AULAS Y SORTEO ══════════════════
    def _crear_tab_aulas_sorteo(self):
        w = QWidget()
        w.setObjectName("tabPagina")
        w.setAttribute(Qt.WA_StyledBackground, True)
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 18, 0, 0)
        l.setSpacing(18)

        # ── Columna izquierda: selección de aulas ──
        panel_aulas = QFrame()
        panel_aulas.setObjectName("panel")
        izquierda = QVBoxLayout(panel_aulas)
        izquierda.setContentsMargins(20, 18, 20, 16)
        izquierda.setSpacing(6)

        lbl_aulas = QLabel("1. Selecciona las aulas")
        lbl_aulas.setObjectName("cardTitulo")
        izquierda.addWidget(lbl_aulas)
        lbl_help = QLabel("Puedes elegir una o varias aulas marcando la casilla.")
        lbl_help.setObjectName("cardNota")
        izquierda.addWidget(lbl_help)
        izquierda.addSpacing(6)

        self.lista_aulas = QListWidget()
        self.lista_aulas.setObjectName("listaAulas")
        self.lista_aulas.setFrameShape(QFrame.NoFrame)
        self.lista_aulas.setMinimumHeight(300)
        self.lista_aulas.itemChanged.connect(self._on_aulas_seleccionadas)
        izquierda.addWidget(self.lista_aulas, stretch=1)

        btn_refrescar = self._boton("Actualizar aulas", "secundario", "refrescar")
        btn_refrescar.clicked.connect(self.cargar_aulas_sorteo)
        izquierda.addWidget(btn_refrescar)
        l.addWidget(panel_aulas, stretch=2)

        # ── Columna derecha: disponibilidad + acciones + asignaciones ──
        derecha = QVBoxLayout()
        derecha.setSpacing(14)

        self.card_disp = QFrame()
        self.card_disp.setObjectName("panel")
        disp_layout = QVBoxLayout(self.card_disp)
        disp_layout.setContentsMargins(20, 18, 20, 18)
        disp_layout.setSpacing(12)

        lbl_resumen = QLabel("2. Disponibilidad de sillas")
        lbl_resumen.setObjectName("cardTitulo")
        disp_layout.addWidget(lbl_resumen)

        stats = QHBoxLayout()
        stats.setSpacing(12)
        stat_pend, self.lbl_pendientes, self.lbl_pendientes_sub = self._crear_stat("POR ASIGNAR")
        stat_sillas, self.lbl_sillas, self.lbl_sillas_sub = self._crear_stat("SILLAS LIBRES")
        stats.addWidget(stat_pend, 1)
        stats.addWidget(stat_sillas, 1)
        disp_layout.addLayout(stats)

        self.lbl_estado_sillas = QLabel("Selecciona al menos un aula.")
        self.lbl_estado_sillas.setObjectName("estadoSillas")
        self.lbl_estado_sillas.setProperty("tono", "neutro")
        self.lbl_estado_sillas.setWordWrap(True)
        disp_layout.addWidget(self.lbl_estado_sillas)

        acciones = QHBoxLayout()
        acciones.setSpacing(10)
        self.btn_sorteo = self._boton("Ejecutar sorteo de asientos", "primario", "dado", alto=44)
        self.btn_sorteo.clicked.connect(self.ejecutar_sorteo)
        acciones.addWidget(self.btn_sorteo, stretch=2)

        # El botón solo se crea para SUPER_ADMIN. Antes se creaba siempre y se
        # llamaba a setVisible(True) antes de entrar en el layout, lo que lo
        # mostraba un instante como ventana suelta.
        self.btn_limpiar = None
        if self.token_data.get("rol") == "SUPER_ADMIN":
            self.btn_limpiar = self._boton("Limpiar asignaciones", "peligro", alto=44)
            self.btn_limpiar.clicked.connect(self.limpiar_asignaciones)
            acciones.addWidget(self.btn_limpiar, stretch=1)
        disp_layout.addLayout(acciones)
        derecha.addWidget(self.card_disp)

        panel_asig = QFrame()
        panel_asig.setObjectName("panel")
        asig_layout = QVBoxLayout(panel_asig)
        asig_layout.setContentsMargins(20, 18, 20, 12)
        asig_layout.setSpacing(8)
        lbl_asig = QLabel("Asignaciones actuales de este examen")
        lbl_asig.setObjectName("cardTitulo")
        asig_layout.addWidget(lbl_asig)

        self.tabla_asignaciones = QTableWidget(0, 4)
        self._preparar_tabla(self.tabla_asignaciones)
        self.tabla_asignaciones.setHorizontalHeaderLabels([
            "Inscripción", "Aula", "Asiento", "Fecha"
        ])
        self.tabla_asignaciones.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_asignaciones.setMinimumHeight(220)
        asig_layout.addWidget(self.tabla_asignaciones, stretch=1)
        derecha.addWidget(panel_asig, stretch=1)

        l.addLayout(derecha, stretch=3)
        return w

    @staticmethod
    def _crear_stat(etiqueta):
        marco = QFrame()
        marco.setObjectName("stat")
        lay = QVBoxLayout(marco)
        lay.setContentsMargins(18, 12, 18, 12)
        lay.setSpacing(0)
        lbl_e = QLabel(etiqueta)
        lbl_e.setObjectName("statEtiqueta")
        lbl_e.setFont(_fuente_etiqueta(10, 1.5))
        valor = QLabel("—")
        valor.setObjectName("statValor")
        sub = QLabel("")
        sub.setObjectName("statSub")
        lay.addWidget(lbl_e)
        lay.addWidget(valor)
        lay.addWidget(sub)
        return marco, valor, sub

    def cargar_aulas_sorteo(self):
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/aulas",
                headers=self.get_auth_headers(),
                timeout=5
            )
            self.aulas_disponibles = [
                a for a in (respuesta.json() if respuesta.status_code == 200 else [])
                if a.get("activa", True)
            ]
        except (requests.RequestException, ValueError):
            self.aulas_disponibles = []

        self.lista_aulas.blockSignals(True)
        self.lista_aulas.clear()
        if not self.aulas_disponibles:
            item = QListWidgetItem("No hay aulas activas. Créalas en «Aulas y Asientos».")
            item.setFlags(Qt.NoItemFlags)
            self.lista_aulas.addItem(item)
        for aula in self.aulas_disponibles:
            habilitados = aula.get("asientos_habilitados", 0)
            item = QListWidgetItem(
                f"{aula.get('nombre')}   ·   {habilitados} de {aula.get('capacidad', 0)} asientos habilitados"
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, aula)
            self.lista_aulas.addItem(item)
        self.lista_aulas.blockSignals(False)
        self._on_aulas_seleccionadas()

    def aulas_seleccionadas(self):
        seleccionadas = []
        for i in range(self.lista_aulas.count()):
            item = self.lista_aulas.item(i)
            if item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                seleccionadas.append(item.data(Qt.UserRole))
        return seleccionadas

    def _on_aulas_seleccionadas(self, *_):
        aulas = self.aulas_seleccionadas()
        self.btn_sorteo.setEnabled(bool(aulas))
        self._actualizar_disponibilidad(aulas)

    def _poner_estado_sillas(self, texto, tono):
        self.lbl_estado_sillas.setText(texto)
        self.lbl_estado_sillas.setProperty("tono", tono)
        _repolish(self.lbl_estado_sillas)

    def _actualizar_disponibilidad(self, aulas):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        params = [("id_aulas", a["id_aula"]) for a in aulas]
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/asignaciones/examen/{id_examen}/disponibilidad",
                params=params,
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code != 200:
                return
            d = respuesta.json()
        except (requests.RequestException, ValueError):
            return

        self.lbl_pendientes.setText(str(d.get("pendientes", 0)))
        self.lbl_pendientes_sub.setText(
            f"ya asignados: {d.get('ya_asignados', 0)} de {d.get('total_postulantes', 0)}"
        )
        self.lbl_sillas.setText(str(d.get("asientos_libres", 0)))
        self.lbl_sillas_sub.setText(
            f"en {len(aulas)} aula(s) seleccionada(s)" if aulas else "sin aulas seleccionadas"
        )

        diferencia = d.get("diferencia", 0)
        if not aulas:
            self._poner_estado_sillas("Selecciona al menos un aula.", "neutro")
        elif d.get("suficiente"):
            if diferencia == 0:
                texto = "Sillas exactas para los postulantes pendientes."
            else:
                texto = f"Sillas suficientes. Sobran {diferencia} silla(s)."
            self._poner_estado_sillas(texto, "ok")
        else:
            self._poner_estado_sillas(
                f"Faltan {abs(diferencia)} silla(s). Puedes sortear igual; "
                "los que no alcancen quedarán pendientes.", "aviso")

    def cargar_asignaciones(self):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/asignaciones/examen/{id_examen}",
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code != 200:
                return
            asignaciones = respuesta.json()
            self.asignaciones_examen = asignaciones
            self.tabla_asignaciones.setRowCount(len(asignaciones))
            for fila, asignacion in enumerate(asignaciones):
                valores = (
                    asignacion.get("id_inscripcion"),
                    asignacion.get("nombre_aula"),
                    f"#{asignacion.get('numero_asiento')}",
                    asignacion.get("fecha_asignacion")
                )
                for columna, valor in enumerate(valores):
                    item = QTableWidgetItem(str(valor or ""))
                    if columna in (0, 2):
                        item.setTextAlignment(Qt.AlignCenter)
                    self.tabla_asignaciones.setItem(fila, columna, item)
            self.filtrar_postulantes(self.txt_buscar.text())
        except requests.RequestException:
            self.asignaciones_examen = []
            self.tabla_asignaciones.setRowCount(0)

    def ejecutar_sorteo(self):
        aulas = self.aulas_seleccionadas()
        if not aulas:
            QMessageBox.warning(self, "Sin aula", "Seleccione al menos un aula antes de sortear.")
            return
        nombres = ", ".join(a.get("nombre", "") for a in aulas)
        confirm = QMessageBox.question(
            self, "Confirmar Sorteo",
            f"¿Ejecutar el sorteo de asientos en {len(aulas)} aula(s):\n{nombres}?\n\n"
            "Se asignará aleatoriamente una butaca a cada postulante pendiente.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            respuesta = requests.post(
                f"{self.api_base_url}/asignaciones/sortear-examen",
                json={
                    "id_examen": self.examen.get("id_examen"),
                    "id_aulas": [a["id_aula"] for a in aulas],
                },
                headers=self.get_auth_headers(),
                timeout=15
            )
            if respuesta.status_code == 200:
                cantidad = len(respuesta.json())
                QMessageBox.information(
                    self, "Sorteo completado",
                    f"Se asignaron {cantidad} postulantes en {len(aulas)} aula(s)."
                )
                self.cargar_asignaciones()
                self.cargar_postulantes_examen()
                self._on_aulas_seleccionadas()
            else:
                detalle = respuesta.json().get("detail", "No se pudo ejecutar el sorteo.")
                QMessageBox.warning(self, "Sorteo no realizado", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Error de red", f"No se pudo contactar al servidor: {error}")

    def limpiar_asignaciones(self):
        confirm = QMessageBox.question(
            self, "Limpiar asignaciones",
            "¿Eliminar todas las asignaciones de asientos de este examen?\n"
            "Esto permite volver a sortear desde cero.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/asignaciones/examen/{self.examen.get('id_examen')}",
                headers=self.get_auth_headers(),
                timeout=10
            )
            if respuesta.status_code == 200:
                QMessageBox.information(self, "Asignaciones", respuesta.json().get("mensaje", "Asignaciones eliminadas."))
                self.cargar_asignaciones()
                self.cargar_postulantes_examen()
                self._on_aulas_seleccionadas()
            else:
                QMessageBox.warning(self, "Asignaciones", str(respuesta.json().get("detail", "No se pudo limpiar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Error de red", f"No se pudo contactar al servidor: {error}")

    def ajustar_tolerancia(self, nuevos_minutos):
        id_examen = self.examen.get("id_examen")
        try:
            res = requests.patch(
                f"{self.api_base_url}/examenes/{id_examen}/tolerancia",
                json={"tolerancia_minutos": nuevos_minutos},
                headers=self.get_auth_headers(),
                timeout=3
            )
            if res.status_code == 200:
                self.tolerancia_actual = nuevos_minutos
                self.spin_tol.setValue(nuevos_minutos)
                self.chip_tolerancia.lbl_valor.setText(f"{self.tolerancia_actual} min")
                QMessageBox.information(self, "Tolerancia Actualizada", f"La tolerancia se actualizó a {nuevos_minutos} minutos.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar la tolerancia.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error de red: {str(e)}")

    def exportar_reporte(self):
        id_examen = self.examen.get("id_examen")
        destino, filtro = QFileDialog.getSaveFileName(
            self, "Guardar reporte de asistencia", f"reporte_examen_{id_examen}.xlsx",
            "Excel (*.xlsx);;PDF (*.pdf)"
        )
        if not destino:
            return
        es_pdf = "PDF" in filtro
        extension = ".pdf" if es_pdf else ".xlsx"
        if not destino.lower().endswith(extension):
            destino += extension
        try:
            formato = "pdf" if es_pdf else "excel"
            respuesta = requests.get(
                f"{self.api_base_url}/reportes/examen/{id_examen}/{formato}",
                headers=self.get_auth_headers(),
                timeout=15
            )
            if respuesta.status_code != 200:
                QMessageBox.warning(self, "Reporte", "No se pudo generar el reporte.")
                return
            with open(destino, "wb") as archivo:
                archivo.write(respuesta.content)
            QMessageBox.information(self, "Reporte generado", f"Archivo guardado en:\n{destino}")
        except (OSError, requests.RequestException) as error:
            QMessageBox.critical(self, "Reporte", f"No se pudo guardar el archivo: {error}")
import os
import sys

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFrame, QScrollArea, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPixmap
from desktop.config.app_config import AppConfig
from desktop.views.checkin.marcacion_mixin import MarcacionMixin
from desktop.views.checkin.reconocimiento_mixin import ReconocimientoMixin
from desktop.views.checkin.contador_mixin import ContadorMixin


# ---------------------------------------------------------------------------
# Estilos. Todo va con selectores por nombre de objeto: así solo se aplican a
# los widgets de esta pantalla y no se recalculan en las pestañas internas.
# Solo cambian colores, bordes y tipografía: ningún tamaño ni margen.
# ---------------------------------------------------------------------------
ESTILO_HEADER = """
QFrame#checkinHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0B2147, stop:0.55 #0F2C59, stop:1 #14407F);
    border-bottom: 2px solid #1E40AF;
}

QLabel#checkinLogo {
    background: transparent;
}
QLabel#checkinInst {
    font-size: 18px; font-weight: 800; color: #FFFFFF;
    background: transparent;
}
QLabel#checkinCarreras {
    font-size: 10px; font-weight: 600; color: #BFDBFE;
    background: transparent;
}
QLabel#checkinAula {
    font-size: 13px; font-weight: 700; color: #FFFFFF;
    background-color: #1E40AF;
    border: 1px solid #3B63C9;
    border-radius: 10px;
    padding: 4px 14px;
}
QLabel#checkinCierre {
    font-size: 13px; font-weight: 700; color: #FECACA;
    background-color: rgba(248, 113, 113, 0.16);
    border: 1px solid rgba(248, 113, 113, 0.35);
    border-radius: 10px;
    padding: 4px 14px;
}

QPushButton#checkinLogin {
    background-color: rgba(255, 255, 255, 0.06);
    border: 1px solid #4B5F80;
    color: #E2E8F0;
    padding: 6px 16px;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 600;
}
QPushButton#checkinLogin:hover {
    background-color: #1E40AF;
    border-color: #60A5FA;
    color: #FFFFFF;
}
QPushButton#checkinLogin:pressed {
    background-color: #1B3A9A;
    border-color: #93C5FD;
}
"""

ESTILO_BODY = """
QWidget#checkinBody { background-color: #F1F5F9; }

/* Pestañas */
QTabWidget::pane { border: none; background: transparent; }
QTabWidget::tab-bar { left: 0px; }
QTabBar { background: transparent; }
QTabBar::tab {
    background: transparent;
    color: #64748B;
    padding: 6px 18px;
    margin-right: 6px;
    border: none;
    border-bottom: 3px solid transparent;
    font-size: 13px;
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    color: #1E3A8A;
    background-color: #E2E8F0;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}
QTabBar::tab:selected {
    color: #0F2C59;
    border-bottom: 3px solid #2563EB;
}
"""

ESTILO_SCROLL = """
QScrollArea#checkinScroll { background: transparent; border: none; }
QScrollArea#checkinScroll QScrollBar:vertical {
    background: transparent; width: 10px; margin: 2px;
}
QScrollArea#checkinScroll QScrollBar::handle:vertical {
    background: #CBD5E1; border-radius: 4px; min-height: 28px;
}
QScrollArea#checkinScroll QScrollBar::handle:vertical:hover { background: #94A3B8; }
QScrollArea#checkinScroll QScrollBar::add-line:vertical,
QScrollArea#checkinScroll QScrollBar::sub-line:vertical { height: 0; }
QScrollArea#checkinScroll QScrollBar:horizontal {
    background: transparent; height: 10px; margin: 2px;
}
QScrollArea#checkinScroll QScrollBar::handle:horizontal {
    background: #CBD5E1; border-radius: 4px; min-width: 28px;
}
QScrollArea#checkinScroll QScrollBar::handle:horizontal:hover { background: #94A3B8; }
QScrollArea#checkinScroll QScrollBar::add-line:horizontal,
QScrollArea#checkinScroll QScrollBar::sub-line:horizontal { width: 0; }
"""


def _ruta_logo():
    base = getattr(sys, "_MEIPASS", None)
    if not base:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "umsa_logo.jpg")


class CheckInView(MarcacionMixin, ReconocimientoMixin, ContadorMixin, QWidget):
    solicitar_login = Signal()

    def __init__(self, parent=None, api_base_url=None):
        super().__init__(parent)
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self.info_examen = {}
        self._huellas_examen_cache = None
        self._estacion_activa = False
        self._inicio_lector_timer = QTimer(self)
        self._inicio_lector_timer.setSingleShot(True)
        self._inicio_lector_timer.timeout.connect(self.identificar_huella)

        self.init_ui()

        self.hide_result_timer = QTimer(self)
        self.hide_result_timer.setSingleShot(True)
        self.hide_result_timer.timeout.connect(self.restaurar_panel_espera)

        self.counter_timer = QTimer(self)
        self.counter_timer.timeout.connect(self.actualizar_contador)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── HEADER BAR ──
        header = QFrame()
        header.setObjectName("checkinHeader")
        header.setFixedHeight(60)
        # Selectores por nombre: un «QFrame {…}» a secas también alcanza a
        # las etiquetas de la barra (QLabel es un QFrame) y les dibuja borde.
        header.setStyleSheet(ESTILO_HEADER)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        lbl_logo = QLabel()
        lbl_logo.setObjectName("checkinLogo")
        pixmap = QPixmap(_ruta_logo())
        if not pixmap.isNull():
            lbl_logo.setPixmap(
                pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            lbl_logo.setFixedSize(48, 48)
        else:
            lbl_logo.hide()

        lbl_inst = QLabel("UMSA Medicina")
        lbl_inst.setObjectName("checkinInst")

        self.lbl_carreras = QLabel("Carreras: --")
        self.lbl_carreras.setObjectName("checkinCarreras")
        self.lbl_carreras.setWordWrap(True)
        self.lbl_carreras.setMinimumWidth(340)
        self.lbl_carreras.setMaximumWidth(460)
        self.lbl_carreras.setMaximumHeight(46)
        self.lbl_carreras.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.lbl_carreras.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        self.lbl_aula = QLabel("Aula: --")
        self.lbl_aula.setObjectName("checkinAula")

        self.lbl_cierre = QLabel("Cierre: --")
        self.lbl_cierre.setObjectName("checkinCierre")

        self.btn_login = QPushButton("Panel Admin")
        self.btn_login.setObjectName("checkinLogin")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.clicked.connect(self.solicitar_login.emit)

        header_layout.addWidget(lbl_logo)
        header_layout.addSpacing(10)
        header_layout.addWidget(lbl_inst)
        header_layout.addSpacing(18)
        header_layout.addWidget(self.lbl_carreras, stretch=1)
        header_layout.addSpacing(12)
        header_layout.addWidget(self.lbl_aula)
        header_layout.addSpacing(12)
        header_layout.addWidget(self.lbl_cierre)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_login)
        main_layout.addWidget(header)

        # ── BODY ──
        body = QWidget()
        body.setObjectName("checkinBody")
        body.setAttribute(Qt.WA_StyledBackground, True)
        # Una regla de fondo sin selector se aplicaba a TODOS los widgets de las
        # pestañas y obligaba a recalcular estilos en cada cambio de pestaña.
        body.setStyleSheet(ESTILO_BODY)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        self.tabs = QTabWidget()

        self._construir_tab_marcacion()
        self._construir_tab_reconocimiento()
        self._construir_tab_contador()
        self.scroll_tabs = QScrollArea()
        self.scroll_tabs.setObjectName("checkinScroll")
        self.scroll_tabs.setWidgetResizable(True)
        self.scroll_tabs.setFrameShape(QFrame.NoFrame)
        self.scroll_tabs.setStyleSheet(ESTILO_SCROLL)
        self.scroll_tabs.viewport().setAutoFillBackground(False)
        self.scroll_tabs.setWidget(self.tabs)
        body_layout.addWidget(self.scroll_tabs)
        main_layout.addWidget(body, stretch=1)
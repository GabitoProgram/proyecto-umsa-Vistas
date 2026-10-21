from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QFrame,
)
from PySide6.QtCore import Qt, QTimer, Signal
from desktop.config.app_config import AppConfig
from desktop.views.checkin.marcacion_mixin import MarcacionMixin
from desktop.views.checkin.reconocimiento_mixin import ReconocimientoMixin
from desktop.views.checkin.contador_mixin import ContadorMixin


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
        # Con selector por nombre: un «QFrame {…}» a secas también alcanza a
        # las etiquetas de la barra (QLabel es un QFrame) y les dibuja borde.
        header.setStyleSheet("""
            QFrame#checkinHeader {
                background-color: #0F2C59;
                border-bottom: 2px solid #1E3A8A;
            }
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        lbl_inst = QLabel("UMSA Medicina")
        lbl_inst.setStyleSheet("font-size: 18px; font-weight: 800; color: #FFFFFF; background: transparent;")

        self.lbl_materia = QLabel("Materia: --")
        self.lbl_materia.setStyleSheet("font-size: 14px; font-weight: 600; color: #93C5FD; background: transparent;")

        self.lbl_aula = QLabel("Aula: --")
        self.lbl_aula.setStyleSheet(
            "font-size: 13px; background-color: #1E3A8A; color: #FFFFFF; "
            "padding: 4px 14px; border-radius: 10px; font-weight: 700;"
        )

        self.lbl_cierre = QLabel("Cierre: --")
        self.lbl_cierre.setStyleSheet("font-size: 14px; color: #FCA5A5; font-weight: 700; background: transparent;")

        self.btn_login = QPushButton("Panel Admin")
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #475569;
                color: #CBD5E1;
                padding: 6px 16px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #1E3A8A;
                border-color: #60A5FA;
                color: #FFFFFF;
            }
        """)
        self.btn_login.clicked.connect(self.solicitar_login.emit)

        header_layout.addWidget(lbl_inst)
        header_layout.addSpacing(20)
        header_layout.addWidget(self.lbl_materia)
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
        body.setStyleSheet("""
            QWidget#checkinBody { background-color: #F8FAFC; }
            QTabWidget::pane { border: none; background: transparent; }
        """)
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(20, 16, 20, 16)
        body_layout.setSpacing(12)

        self.tabs = QTabWidget()

        self._construir_tab_marcacion()
        self._construir_tab_reconocimiento()
        self._construir_tab_contador()
        body_layout.addWidget(self.tabs)
        main_layout.addWidget(body, stretch=1)
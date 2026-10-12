from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit,
    QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
import requests
import cv2
from datetime import date

from desktop.config.app_config import AppConfig
from desktop.api.client import api
from desktop.ui.postulantes_view import PostulantesView

from desktop.views.admin.common_mixin import CommonMixin
from desktop.views.admin.dashboard_mixin import DashboardMixin
from desktop.views.admin.academico_mixin import AcademicoMixin
from desktop.views.admin.gestiones_mixin import GestionesMixin
from desktop.views.admin.carreras_mixin import CarrerasMixin
from desktop.views.admin.examenes_mixin import ExamenesMixin
from desktop.views.admin.postulantes_mixin import PostulantesMixin
from desktop.views.admin.biometria_mixin import BiometriaMixin
from desktop.views.admin.aulas_mixin import AulasMixin
from desktop.views.admin.usuarios_mixin import UsuariosMixin
from desktop.views.admin.auditoria_mixin import AuditoriaMixin


class MainDashboardWindow(
    CommonMixin,
    DashboardMixin,
    AcademicoMixin,
    GestionesMixin,
    CarrerasMixin,
    ExamenesMixin,
    PostulantesMixin,
    BiometriaMixin,
    AulasMixin,
    UsuariosMixin,
    AuditoriaMixin,
    QMainWindow,
):
    volver_a_checkin = Signal()

    def __init__(self, token_data=None, api_base_url=None, parent=None):
        super().__init__(parent)
        self.token_data = token_data or {}
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self.rol = self.token_data.get("rol", "ADMIN")
        self.setWindowTitle("Sistema Biométrico UMSA - Panel de Administración")
        self.setMinimumSize(1200, 750)
        self.init_ui()
        self.showMaximized()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── SIDEBAR ──
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setStyleSheet("""
            QFrame {
                background-color: #0F2C59;
                border-right: 1px solid #1A3F7A;
            }
            QLabel { background: transparent; }
        """)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 24, 16, 20)
        sb_layout.setSpacing(6)

        lbl_app = QLabel("UMSA MEDICINA")
        lbl_app.setStyleSheet("font-size: 17px; font-weight: 900; color: #FFFFFF; letter-spacing: 1px;")
        lbl_sub = QLabel(f"Rol: {self.rol}")
        lbl_sub.setStyleSheet("font-size: 12px; color: #93C5FD; font-weight: 600;")
        sb_layout.addWidget(lbl_app)
        sb_layout.addWidget(lbl_sub)
        sb_layout.addSpacing(16)

        # Botón regresar al check-in
        self.btn_checkin = QPushButton("Volver a Registro")
        self.btn_checkin.setCursor(Qt.PointingHandCursor)
        self.btn_checkin.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: white;
                text-align: center;
                padding: 10px 14px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
                border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.btn_checkin.clicked.connect(self.solicitar_retorno_checkin)
        sb_layout.addWidget(self.btn_checkin)
        sb_layout.addSpacing(10)

        # Navegación
        self.nav_buttons = []
        nav_items = [
            ("Dashboard", 0),
            ("Postulantes", 1),
            ("Gestiones y Examenes", 2),
            ("Aulas y Asientos", 3),
        ]
        if self.rol == "SUPER_ADMIN":
            nav_items.append(("Usuarios", 4))
            nav_items.append(("Auditoria", 5))

        for texto, idx in nav_items:
            btn = self._crear_btn_nav(texto, idx)
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()

        btn_logout = QPushButton("Cerrar Sesion")
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #334155;
                color: #94A3B8;
                padding: 9px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #7F1D1D;
                color: #FFFFFF;
                border-color: #EF4444;
            }
        """)
        btn_logout.clicked.connect(self.close)
        sb_layout.addWidget(btn_logout)

        layout.addWidget(sidebar)

        # ── CONTENIDO PRINCIPAL ──
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("background-color: #F8FAFC;")

        api.jwt_token = self.token_data.get("access_token")
        api.current_user = self.token_data
        self.content_stack.addWidget(self._crear_dashboard_view())
        self.content_stack.addWidget(PostulantesView())
        self.content_stack.addWidget(self._crear_academico_view())
        self.content_stack.addWidget(self._crear_aulas_view())

        self.content_stack.addWidget(self._crear_usuarios_view())
        self.content_stack.addWidget(self._crear_auditoria_view())

        layout.addWidget(self.content_stack)

        # Seleccionar Dashboard por defecto
        if self.nav_buttons:
            self._activar_nav(0)

    def _crear_btn_nav(self, texto, index):
        btn = QPushButton(texto)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setProperty("nav_index", index)
        btn.setStyleSheet(self._nav_style(False))
        btn.clicked.connect(lambda: self._activar_nav(index))
        return btn

    def _nav_style(self, active):
        if active:
            return """
                QPushButton {
                    background-color: #1E3A8A;
                    color: #FFFFFF;
                    text-align: left;
                    padding: 10px 14px;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 600;
                    border: none;
                }
            """
        return """
            QPushButton {
                background-color: transparent;
                color: #CBD5E1;
                text-align: left;
                padding: 10px 14px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
                border: none;
            }
            QPushButton:hover {
                background-color: #1A3F7A;
                color: #FFFFFF;
            }
        """

    def _activar_nav(self, index):
        self.content_stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            is_active = btn.property("nav_index") == index
            btn.setStyleSheet(self._nav_style(is_active))

    def solicitar_retorno_checkin(self):
        self.volver_a_checkin.emit()
        self.close()

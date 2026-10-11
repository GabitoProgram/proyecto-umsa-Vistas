import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QSpacerItem
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QSize
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QBrush, QPalette


class GradientPanel(QWidget):
    """Panel lateral con gradiente institucional UMSA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(420)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor("#0F2C59"))
        gradient.setColorAt(0.5, QColor("#1A3F7A"))
        gradient.setColorAt(1.0, QColor("#0B1D3A"))
        painter.fillRect(self.rect(), QBrush(gradient))
        painter.end()


class LoginView(QWidget):
    login_exitoso = Signal(dict)

    def __init__(self, parent=None, api_base_url="http://localhost:8000/api/v1"):
        super().__init__(parent)
        self.api_base_url = api_base_url
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #F1F5F9;")

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ═══════════════════════════════════════════════
        # PANEL IZQUIERDO — Branding institucional
        # ═══════════════════════════════════════════════
        left_panel = GradientPanel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(48, 60, 48, 48)
        left_layout.setSpacing(0)

        # Ícono / emblema
        lbl_icon = QLabel("🏛")
        lbl_icon.setStyleSheet("font-size: 56px; background: transparent;")
        lbl_icon.setAlignment(Qt.AlignLeft)
        left_layout.addWidget(lbl_icon)
        left_layout.addSpacing(24)

        # Título principal
        lbl_univ = QLabel("Universidad Mayor\nde San Andrés")
        lbl_univ.setStyleSheet(
            "font-size: 32px; font-weight: 800; color: #FFFFFF; "
            "line-height: 1.2; background: transparent;"
        )
        left_layout.addWidget(lbl_univ)
        left_layout.addSpacing(8)

        # Subtítulo facultad
        lbl_fac = QLabel("FACULTAD DE MEDICINA")
        lbl_fac.setStyleSheet(
            "font-size: 14px; font-weight: 700; color: #60A5FA; "
            "letter-spacing: 3px; background: transparent;"
        )
        left_layout.addWidget(lbl_fac)
        left_layout.addSpacing(32)

        # Línea separadora
        separator = QFrame()
        separator.setFixedHeight(2)
        separator.setStyleSheet("background-color: rgba(255, 255, 255, 0.15); border: none;")
        left_layout.addWidget(separator)
        left_layout.addSpacing(32)

        # Descripción del sistema
        lbl_desc = QLabel(
            "Sistema de Control de Acceso\n"
            "y Verificación Biométrica"
        )
        lbl_desc.setStyleSheet(
            "font-size: 18px; font-weight: 500; color: rgba(255, 255, 255, 0.85); "
            "line-height: 1.5; background: transparent;"
        )
        left_layout.addWidget(lbl_desc)
        left_layout.addSpacing(24)

        # Features del sistema
        features = [
            ("🔒", "Autenticación segura con roles"),
            ("👁", "Verificación facial en tiempo real"),
            ("🖐", "Lectura de huella dactilar"),
            ("📊", "Monitoreo y auditoría completa"),
        ]
        for icon, text in features:
            feat_layout = QHBoxLayout()
            feat_layout.setSpacing(12)
            lbl_feat_icon = QLabel(icon)
            lbl_feat_icon.setStyleSheet("font-size: 18px; background: transparent;")
            lbl_feat_icon.setFixedWidth(28)
            lbl_feat_text = QLabel(text)
            lbl_feat_text.setStyleSheet(
                "font-size: 13px; color: rgba(255, 255, 255, 0.7); background: transparent;"
            )
            feat_layout.addWidget(lbl_feat_icon)
            feat_layout.addWidget(lbl_feat_text)
            feat_layout.addStretch()
            left_layout.addLayout(feat_layout)
            left_layout.addSpacing(6)

        left_layout.addStretch()

        # Pie del panel izquierdo
        lbl_footer = QLabel("© 2026 UMSA — Todos los derechos reservados")
        lbl_footer.setStyleSheet(
            "font-size: 11px; color: rgba(255, 255, 255, 0.35); background: transparent;"
        )
        left_layout.addWidget(lbl_footer)

        main_layout.addWidget(left_panel, 45)

        # ═══════════════════════════════════════════════
        # PANEL DERECHO — Formulario de login
        # ═══════════════════════════════════════════════
        right_panel = QWidget()
        right_panel.setStyleSheet("background-color: #F1F5F9;")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignCenter)

        # Tarjeta de Login centrada con sombra
        self.card = QFrame()
        self.card.setFixedSize(440, 520)
        self.card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 16px;
            }
        """)

        # Sombra elegante
        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(15, 44, 89, 30))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(44, 44, 44, 36)
        card_layout.setSpacing(0)

        # Ícono del formulario
        lbl_form_icon = QLabel("🔐")
        lbl_form_icon.setStyleSheet("font-size: 40px; background: transparent;")
        lbl_form_icon.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_form_icon)
        card_layout.addSpacing(16)

        # Título
        lbl_titulo = QLabel("Iniciar Sesión")
        lbl_titulo.setStyleSheet(
            "font-size: 26px; font-weight: 800; color: #0F172A; background: transparent;"
        )
        lbl_titulo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_titulo)
        card_layout.addSpacing(6)

        # Subtítulo
        lbl_sub = QLabel("Ingrese sus credenciales para acceder al panel")
        lbl_sub.setStyleSheet(
            "font-size: 13px; color: #94A3B8; background: transparent;"
        )
        lbl_sub.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_sub)
        card_layout.addSpacing(28)

        # ——— Campo: Usuario ———
        lbl_user = QLabel("Usuario")
        lbl_user.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #374151; "
            "margin-bottom: 4px; background: transparent;"
        )
        card_layout.addWidget(lbl_user)
        card_layout.addSpacing(4)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Ingrese su nombre de usuario")
        self.txt_user.setMinimumHeight(44)
        self.txt_user.setStyleSheet("""
            QLineEdit {
                padding: 10px 14px;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                font-size: 14px;
                color: #1E293B;
                background-color: #F8FAFC;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #CBD5E1;
            }
        """)
        card_layout.addWidget(self.txt_user)
        card_layout.addSpacing(16)

        # ——— Campo: Contraseña ———
        lbl_pass = QLabel("Contraseña")
        lbl_pass.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #374151; "
            "margin-bottom: 4px; background: transparent;"
        )
        card_layout.addWidget(lbl_pass)
        card_layout.addSpacing(4)

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.Password)
        self.txt_pass.setPlaceholderText("Ingrese su contraseña")
        self.txt_pass.setMinimumHeight(44)
        self.txt_pass.setStyleSheet("""
            QLineEdit {
                padding: 10px 14px;
                border: 1.5px solid #E2E8F0;
                border-radius: 10px;
                font-size: 14px;
                color: #1E293B;
                background-color: #F8FAFC;
            }
            QLineEdit:focus {
                border: 2px solid #2563EB;
                background-color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #CBD5E1;
            }
        """)
        self.txt_pass.returnPressed.connect(self.procesar_login)
        card_layout.addWidget(self.txt_pass)
        card_layout.addSpacing(10)

        # ——— Mensaje de error ———
        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("""
            QLabel {
                color: #DC2626;
                font-size: 12px;
                font-weight: 600;
                background-color: #FEF2F2;
                border: 1px solid #FECACA;
                border-radius: 8px;
                padding: 8px 12px;
            }
        """)
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setVisible(False)
        card_layout.addWidget(self.lbl_error)
        card_layout.addSpacing(10)

        # ——— Botón Ingresar ———
        self.btn_ingresar = QPushButton("  Ingresar")
        self.btn_ingresar.setMinimumHeight(48)
        self.btn_ingresar.setCursor(Qt.PointingHandCursor)
        self.btn_ingresar.setStyleSheet("""
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                padding: 12px 24px;
                font-weight: 700;
                border-radius: 10px;
                font-size: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1D4ED8;
            }
            QPushButton:pressed {
                background-color: #1E40AF;
            }
            QPushButton:disabled {
                background-color: #93C5FD;
                color: rgba(255, 255, 255, 0.8);
            }
        """)
        self.btn_ingresar.clicked.connect(self.procesar_login)
        card_layout.addWidget(self.btn_ingresar)
        card_layout.addSpacing(20)

        # ——— Pie de la tarjeta ———
        lbl_help = QLabel("¿Problemas para acceder? Contacte al administrador.")
        lbl_help.setStyleSheet(
            "font-size: 11px; color: #94A3B8; background: transparent;"
        )
        lbl_help.setAlignment(Qt.AlignCenter)
        lbl_help.setWordWrap(True)
        card_layout.addWidget(lbl_help)

        right_layout.addWidget(self.card)

        main_layout.addWidget(right_panel, 55)

    def procesar_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()

        if not username or not password:
            self.mostrar_error("Por favor, ingrese su usuario y contraseña.")
            return

        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.setText("  Verificando...")
        self.lbl_error.setVisible(False)

        try:
            # Login OAuth2 estándar compatible con FastAPI form-data
            res = requests.post(
                f"{self.api_base_url}/auth/login",
                data={"username": username, "password": password},
                timeout=4
            )
            if res.status_code == 200:
                data = res.json()
                self.login_exitoso.emit(data)
            elif res.status_code == 401:
                self.mostrar_error("Las credenciales ingresadas son incorrectas.")
            else:
                self.mostrar_error(f"Error del servidor ({res.status_code}). Intente más tarde.")
        except requests.exceptions.ConnectionError:
            self.mostrar_error("No se pudo conectar con el servidor. Verifique la conexión.")
        except Exception as e:
            self.mostrar_error(f"Error inesperado: {str(e)}")
        finally:
            self.btn_ingresar.setEnabled(True)
            self.btn_ingresar.setText("  Ingresar")

    def mostrar_error(self, mensaje: str):
        self.lbl_error.setText(f"⚠  {mensaje}")
        self.lbl_error.setVisible(True)

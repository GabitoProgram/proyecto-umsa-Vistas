import os
import time

import requests
from PySide6.QtCore import Qt, Signal, QPointF
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPalette,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from config.app_config import AppConfig
from desktop.views.checkin.workers import _ejecutar_en_hilo


def _fuente(px, peso=QFont.Bold, espaciado=0.0):
    """QSS no soporta letter-spacing, por eso estas etiquetas se fijan por código."""
    fuente = QFont()
    fuente.setPixelSize(px)
    fuente.setWeight(peso)
    if espaciado:
        fuente.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return fuente


class GradientPanel(QWidget):
    """Panel lateral con gradiente institucional UMSA."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(420)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()

        gradient = QLinearGradient(0, 0, w, h)
        gradient.setColorAt(0.0, QColor("#0B2248"))
        gradient.setColorAt(0.55, QColor("#16407F"))
        gradient.setColorAt(1.0, QColor("#0A1B3B"))
        painter.fillRect(self.rect(), QBrush(gradient))

        # Círculos decorativos muy sutiles
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 255, 255, 12))
        painter.drawEllipse(QPointF(w * 0.92, h * 0.10), 190, 190)
        painter.setBrush(QColor(255, 255, 255, 9))
        painter.drawEllipse(QPointF(w * 0.05, h * 0.95), 150, 150)
        painter.end()


class LoginView(QWidget):
    login_exitoso = Signal(dict)

    # Paleta:
    #   Navy institucional : #0B2248 / #16407F
    #   Primario (botón)   : #1E54B7  (hover #17449A, pressed #12367D)
    #   Fondo derecho      : #EEF2F7
    #   Texto principal    : #0F172A / secundario #64748B
    ESTILOS = """
        QWidget#loginRoot, QWidget#rightPanel { background: #EEF2F7; }

        /* Evita que las etiquetas hereden fondos o bordes */
        QLabel { background: transparent; border: none; }

        /* ---------- PANEL IZQUIERDO ---------- */
        QFrame#logoBadge { background: #FFFFFF; border: none; border-radius: 22px; }
        QLabel#logoFallback { color: #0F2C59; font-size: 20px; font-weight: 800; }
        QLabel#brandTitle   { color: #FFFFFF; font-size: 30px; font-weight: 800; }
        QLabel#brandFaculty { color: #8DBDF2; }
        QFrame#separator    { background: rgba(255, 255, 255, 0.14); border: none; }
        QLabel#brandDesc    { color: rgba(255, 255, 255, 0.92); font-size: 18px; font-weight: 500; }
        QLabel#featureCheck {
            color: #7FE0BE; background: rgba(127, 224, 190, 0.16);
            border-radius: 10px; font-size: 11px; font-weight: 800;
        }
        QLabel#featureText  { color: rgba(255, 255, 255, 0.82); font-size: 13px; }
        QLabel#brandFooter  { color: rgba(255, 255, 255, 0.50); font-size: 11px; }

        /* ---------- TARJETA ---------- */
        QFrame#loginCard {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 18px;
        }
        QLabel#formEyebrow {
            color: #1E54B7; background: #E8F0FD;
            border-radius: 11px; padding: 5px 12px;
        }
        QLabel#formTitle { color: #0F172A; font-size: 26px; font-weight: 800; }
        QLabel#formSub   { color: #64748B; font-size: 13px; }
        QLabel#fieldLabel { color: #334155; font-size: 13px; font-weight: 600; }
        QLabel#helpLabel  { color: #64748B; font-size: 11px; }

        QLineEdit#loginInput {
            padding: 10px 14px;
            border: 1px solid #D5DEE9;
            border-radius: 10px;
            font-size: 14px;
            color: #0F172A;
            background: #F8FAFC;
            selection-background-color: #BFD6F6;
            selection-color: #0F172A;
        }
        QLineEdit#loginInput:hover { border: 1px solid #A9BBD1; }
        QLineEdit#loginInput:focus {
            padding: 9px 13px;
            border: 2px solid #1E54B7;
            background: #FFFFFF;
        }

        QLabel#errorLabel {
            color: #B91C1C; background: #FEF2F2;
            border: 1px solid #FECACA; border-radius: 8px;
            font-size: 12px; font-weight: 600; padding: 8px 12px;
        }

        QPushButton#btnLogin {
            background: #1E54B7; color: #FFFFFF;
            border: none; border-radius: 10px;
            padding: 12px 24px; font-size: 15px; font-weight: 700;
        }
        QPushButton#btnLogin:hover    { background: #17449A; }
        QPushButton#btnLogin:pressed  { background: #12367D; }
        QPushButton#btnLogin:disabled { background: #9DB8E3; color: #FFFFFF; }
    """

    def __init__(self, parent=None, api_base_url=None):
        super().__init__(parent)
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self._login_en_curso = False
        self._entrega_login = None
        self._ultima_actividad = time.monotonic()
        self.init_ui()

    # ------------------------------------------------------------------
    # Construcción de la interfaz
    # ------------------------------------------------------------------
    def init_ui(self):
        self.setObjectName("loginRoot")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(self.ESTILOS)

        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        main_layout.addWidget(self._crear_panel_izquierdo(), 45)
        main_layout.addWidget(self._crear_panel_derecho(), 55)

    def registrar_actividad(self, *_):
        self._ultima_actividad = time.monotonic()

    def hay_actividad(self):
        """True si hay un inicio de sesión en curso."""
        return self._login_en_curso

    def inactivo_por(self, segundos):
        return time.monotonic() - self._ultima_actividad >= segundos

    def limpiar_formulario(self):
        self.txt_user.clear()
        self.txt_pass.clear()
        self.lbl_error.clear()
        self.btn_ingresar.setText("Ingresar")
        self.btn_ingresar.setEnabled(True)
        self.txt_user.setFocus()

    def _crear_panel_izquierdo(self):
        left_panel = GradientPanel()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(52, 56, 52, 44)
        left_layout.setSpacing(0)

        # Logo dentro de una insignia blanca (el JPG trae fondo blanco y
        # se veía como un cuadro pegado sobre el gradiente).
        badge = QFrame()
        badge.setObjectName("logoBadge")
        badge.setFixedSize(104, 104)
        badge_layout = QVBoxLayout(badge)
        badge_layout.setContentsMargins(12, 12, 12, 12)

        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignCenter)
        logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "assets", "umsa_logo.jpg"
        )
        logo = QPixmap(logo_path)
        if not logo.isNull():
            lbl_logo.setPixmap(
                logo.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            lbl_logo.setText("UMSA")
            lbl_logo.setObjectName("logoFallback")
        badge_layout.addWidget(lbl_logo)
        left_layout.addWidget(badge, 0, Qt.AlignLeft)
        left_layout.addSpacing(28)

        lbl_univ = QLabel("Universidad Mayor\nde San Andrés")
        lbl_univ.setObjectName("brandTitle")
        left_layout.addWidget(lbl_univ)
        left_layout.addSpacing(10)

        lbl_fac = QLabel("FACULTAD DE MEDICINA")
        lbl_fac.setObjectName("brandFaculty")
        lbl_fac.setFont(_fuente(13, QFont.Bold, 3))
        left_layout.addWidget(lbl_fac)
        left_layout.addSpacing(28)

        separator = QFrame()
        separator.setObjectName("separator")
        separator.setFixedHeight(1)
        left_layout.addWidget(separator)
        left_layout.addSpacing(28)

        lbl_desc = QLabel("Sistema de Control de Acceso\ny Verificación Biométrica")
        lbl_desc.setObjectName("brandDesc")
        left_layout.addWidget(lbl_desc)
        left_layout.addSpacing(22)

        features = [
            "Autenticación segura con roles",
            "Verificación facial en tiempo real",
            "Lectura de huella dactilar",
            "Monitoreo y auditoría completa",
        ]
        for text in features:
            row = QHBoxLayout()
            row.setSpacing(12)
            check = QLabel("✓")
            check.setObjectName("featureCheck")
            check.setFixedSize(20, 20)
            check.setAlignment(Qt.AlignCenter)
            label = QLabel(text)
            label.setObjectName("featureText")
            row.addWidget(check)
            row.addWidget(label)
            row.addStretch()
            left_layout.addLayout(row)
            left_layout.addSpacing(10)

        left_layout.addStretch()

        lbl_footer = QLabel("© 2026 UMSA — Todos los derechos reservados")
        lbl_footer.setObjectName("brandFooter")
        left_layout.addWidget(lbl_footer)
        return left_panel

    def _crear_panel_derecho(self):
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_panel.setAttribute(Qt.WA_StyledBackground, True)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(24, 24, 24, 24)
        right_layout.setAlignment(Qt.AlignCenter)

        # Tarjeta: usa objectName para que su estilo NO se herede a las
        # etiquetas internas (QLabel es subclase de QFrame).
        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(440)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(48)
        shadow.setXOffset(0)
        shadow.setYOffset(10)
        shadow.setColor(QColor(15, 44, 89, 40))
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 32)
        card_layout.setSpacing(0)

        lbl_eyebrow = QLabel("ACCESO ADMINISTRATIVO")
        lbl_eyebrow.setObjectName("formEyebrow")
        lbl_eyebrow.setFont(_fuente(11, QFont.Bold, 1.5))
        card_layout.addWidget(lbl_eyebrow, 0, Qt.AlignHCenter)
        card_layout.addSpacing(18)

        lbl_titulo = QLabel("Iniciar Sesión")
        lbl_titulo.setObjectName("formTitle")
        lbl_titulo.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_titulo)
        card_layout.addSpacing(6)

        lbl_sub = QLabel("Ingrese sus credenciales para acceder al panel")
        lbl_sub.setObjectName("formSub")
        lbl_sub.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(lbl_sub)
        card_layout.addSpacing(28)

        # Usuario
        lbl_user = QLabel("Usuario")
        lbl_user.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_user)
        card_layout.addSpacing(6)
        self.txt_user = self._crear_campo("Ingrese su nombre de usuario")
        card_layout.addWidget(self.txt_user)
        card_layout.addSpacing(16)

        # Contraseña
        lbl_pass = QLabel("Contraseña")
        lbl_pass.setObjectName("fieldLabel")
        card_layout.addWidget(lbl_pass)
        card_layout.addSpacing(6)
        self.txt_pass = self._crear_campo("Ingrese su contraseña", password=True)
        card_layout.addWidget(self.txt_pass)
        card_layout.addSpacing(12)

        self.txt_user.returnPressed.connect(self.txt_pass.setFocus)
        self.txt_pass.returnPressed.connect(self.procesar_login)
        self.txt_user.textChanged.connect(self.registrar_actividad)
        self.txt_pass.textChanged.connect(self.registrar_actividad)

        # Error
        self.lbl_error = QLabel("")
        self.lbl_error.setObjectName("errorLabel")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        self.lbl_error.setWordWrap(True)
        self.lbl_error.setVisible(False)
        card_layout.addWidget(self.lbl_error)
        card_layout.addSpacing(12)

        # Botón
        self.btn_ingresar = QPushButton("Ingresar")
        self.btn_ingresar.setObjectName("btnLogin")
        self.btn_ingresar.setMinimumHeight(48)
        self.btn_ingresar.setCursor(Qt.PointingHandCursor)
        self.btn_ingresar.clicked.connect(self.procesar_login)
        card_layout.addWidget(self.btn_ingresar)
        card_layout.addSpacing(20)

        lbl_help = QLabel("¿Problemas para acceder? Contacte al administrador.")
        lbl_help.setObjectName("helpLabel")
        lbl_help.setAlignment(Qt.AlignCenter)
        lbl_help.setWordWrap(True)
        card_layout.addWidget(lbl_help)

        right_layout.addWidget(self.card)
        return right_panel

    def _crear_campo(self, placeholder, password=False):
        campo = QLineEdit()
        campo.setObjectName("loginInput")
        campo.setPlaceholderText(placeholder)
        campo.setMinimumHeight(46)
        if password:
            campo.setEchoMode(QLineEdit.Password)
        # QSS no soporta ::placeholder; el color se define con la paleta.
        paleta = campo.palette()
        paleta.setColor(QPalette.PlaceholderText, QColor("#94A3B8"))
        campo.setPalette(paleta)
        return campo

    def showEvent(self, event):
        super().showEvent(event)
        self.txt_user.setFocus()

    # ------------------------------------------------------------------
    # Lógica
    # ------------------------------------------------------------------
    def procesar_login(self):
        if self._login_en_curso:
            return
        username = self.txt_user.text().strip()
        password = self.txt_pass.text()

        if not username or not password:
            self.mostrar_error("Por favor, ingrese su usuario y contraseña.")
            return

        self._login_en_curso = True
        self.btn_ingresar.setEnabled(False)
        self.btn_ingresar.setText("Verificando...")
        self.lbl_error.setVisible(False)

        def pedir():
            # Login OAuth2 estándar compatible con FastAPI form-data
            res = requests.post(
                f"{self.api_base_url}/auth/login",
                data={"username": username, "password": password},
                timeout=4,
            )
            try:
                datos = res.json()
            except ValueError:
                datos = {}
            return res.status_code, datos

        # La petición va en un hilo: antes congelaba la interfaz hasta 4 s.
        self._entrega_login = _ejecutar_en_hilo(pedir, self._login_terminado)

    def _login_terminado(self, resultado, error):
        self._login_en_curso = False
        self.btn_ingresar.setEnabled(True)
        self.btn_ingresar.setText("Ingresar")

        if error is not None:
            self.mostrar_error(
                "No se pudo conectar con el servidor. Verifique la conexión."
            )
            return

        status, data = resultado
        if status == 200:
            self.login_exitoso.emit(data)
        elif status == 401:
            self.mostrar_error("Las credenciales ingresadas son incorrectas.")
            self.txt_pass.clear()
            self.txt_pass.setFocus()
        else:
            self.mostrar_error(
                f"Error del servidor ({status}). Intente más tarde."
            )

    def mostrar_error(self, mensaje: str):
        self.lbl_error.setText(mensaje)
        self.lbl_error.setVisible(True)
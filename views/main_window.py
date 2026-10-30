import os

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

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


# ----------------------------------------------------------------------
# Íconos de línea dibujados con QPainter (sin emojis ni archivos externos)
# ----------------------------------------------------------------------
def _pixmap_icono(nombre, color):
    # Lienzo de 28x20 (lógico) a doble resolución; los 8px de la derecha
    # son el espacio entre el ícono y el texto del botón.
    pm = QPixmap(56, 40)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(color), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)

    if nombre == "dashboard":
        for x, y in ((3, 3), (11, 3), (3, 11), (11, 11)):
            p.drawRoundedRect(QRectF(x, y, 6, 6), 1.6, 1.6)

    elif nombre == "postulantes":
        p.drawEllipse(QPointF(10, 6.5), 3.2, 3.2)
        ruta = QPainterPath()
        ruta.moveTo(3.5, 17)
        ruta.cubicTo(4, 11.5, 16, 11.5, 16.5, 17)
        p.drawPath(ruta)

    elif nombre == "calendario":
        p.drawRoundedRect(QRectF(3, 4.5, 14, 12.5), 2, 2)
        p.drawLine(QPointF(3, 8.5), QPointF(17, 8.5))
        p.drawLine(QPointF(7, 3), QPointF(7, 6))
        p.drawLine(QPointF(13, 3), QPointF(13, 6))

    elif nombre == "aulas":
        p.drawRoundedRect(QRectF(4, 3, 12, 14), 1.6, 1.6)
        p.drawLine(QPointF(8.5, 17), QPointF(8.5, 12.5))
        p.drawLine(QPointF(11.5, 17), QPointF(11.5, 12.5))
        p.drawLine(QPointF(8.5, 12.5), QPointF(11.5, 12.5))
        p.drawLine(QPointF(7.5, 7), QPointF(9, 7))
        p.drawLine(QPointF(11, 7), QPointF(12.5, 7))

    elif nombre == "usuarios":
        p.drawEllipse(QPointF(7.5, 6.8), 2.8, 2.8)
        ruta = QPainterPath()
        ruta.moveTo(2.5, 16.5)
        ruta.cubicTo(2.8, 11.6, 12.2, 11.6, 12.5, 16.5)
        p.drawPath(ruta)
        p.drawEllipse(QPointF(13.8, 7.6), 2.3, 2.3)
        ruta2 = QPainterPath()
        ruta2.moveTo(14.4, 11.8)
        ruta2.cubicTo(16.4, 12, 17.2, 14, 17.5, 16.5)
        p.drawPath(ruta2)

    elif nombre == "auditoria":
        p.drawRoundedRect(QRectF(4.5, 3, 11, 14), 1.8, 1.8)
        p.drawLine(QPointF(7.2, 7.5), QPointF(12.8, 7.5))
        p.drawLine(QPointF(7.2, 10.5), QPointF(12.8, 10.5))
        p.drawLine(QPointF(7.2, 13.5), QPointF(10.5, 13.5))

    elif nombre == "salir":
        ruta = QPainterPath()
        ruta.moveTo(8, 3.5)
        ruta.lineTo(4.5, 3.5)
        ruta.lineTo(4.5, 16.5)
        ruta.lineTo(8, 16.5)
        p.drawPath(ruta)
        p.drawLine(QPointF(8.5, 10), QPointF(16, 10))
        flecha = QPainterPath()
        flecha.moveTo(13, 7)
        flecha.lineTo(16, 10)
        flecha.lineTo(13, 13)
        p.drawPath(flecha)

    p.end()
    return pm


def _crear_icono(nombre, reposo="#AFC0D8", activo="#FFFFFF"):
    """Gris azulado en reposo; blanco al pasar el mouse o cuando está activo."""
    icono = QIcon()
    pix_reposo = _pixmap_icono(nombre, reposo)
    pix_activo = _pixmap_icono(nombre, activo)
    icono.addPixmap(pix_reposo, QIcon.Normal, QIcon.Off)
    icono.addPixmap(pix_activo, QIcon.Active, QIcon.Off)
    icono.addPixmap(pix_activo, QIcon.Normal, QIcon.On)
    icono.addPixmap(pix_activo, QIcon.Active, QIcon.On)
    return icono


def _fuente_etiqueta(px, espaciado):
    """QSS no soporta letter-spacing; se define por código."""
    fuente = QFont()
    fuente.setPixelSize(px)
    fuente.setWeight(QFont.Bold)
    fuente.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return fuente


def _buscar_logo():
    base = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        ruta = os.path.join(base, "assets", "umsa_logo.jpg")
        if os.path.exists(ruta):
            return ruta
        base = os.path.dirname(base)
    return None


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
    cerrar_sesion = Signal()

    # Las subclases (panel auxiliar) solo cambian este texto.
    TITULO_VENTANA = "Sistema Biométrico UMSA - Panel de Administración"

    # Los estilos usan objectName: así NO se heredan a las etiquetas internas
    # (QLabel es subclase de QFrame) ni a las páginas del contenido.
    ESTILOS_SIDEBAR = """
        QFrame#sidebar {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #0F2C59, stop:1 #0A1B3B);
            border: none;
        }
        QLabel { background: transparent; border: none; }

        QFrame#brandBadge { background: #FFFFFF; border: none; border-radius: 12px; }
        QLabel#brandFallback { color: #0F2C59; font-size: 11px; font-weight: 800; }
        QLabel#brandName { color: #FFFFFF; font-size: 17px; font-weight: 800; }
        QLabel#brandSub  { color: #8FB0D9; font-size: 11px; }

        QFrame#sbSeparator { background: rgba(255, 255, 255, 0.10); border: none; }
        QLabel#sectionLabel { color: #6F8DB5; }

        QPushButton#navButton {
            background: transparent;
            color: #B8C7DC;
            text-align: left;
            padding: 10px 12px;
            border: 1px solid transparent;
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#navButton:hover {
            background: rgba(255, 255, 255, 0.07);
            color: #FFFFFF;
        }
        QPushButton#navButton:checked {
            background: rgba(255, 255, 255, 0.13);
            border: 1px solid rgba(255, 255, 255, 0.10);
            color: #FFFFFF;
        }

        QFrame#userCard {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 12px;
        }
        QLabel#userAvatar {
            background: #2F6FED; color: #FFFFFF;
            border-radius: 18px; font-size: 14px; font-weight: 800;
        }
        QLabel#userName { color: #FFFFFF; font-size: 13px; font-weight: 700; }
        QLabel#userRole { color: #8FB0D9; font-size: 11px; }

        QPushButton#btnLogout {
            background: transparent;
            color: #F2B8B8;
            text-align: left;
            padding: 10px 12px;
            border: 1px solid rgba(255, 255, 255, 0.14);
            border-radius: 10px;
            font-size: 13px;
            font-weight: 600;
        }
        QPushButton#btnLogout:hover {
            background: rgba(239, 68, 68, 0.18);
            border: 1px solid rgba(248, 113, 113, 0.60);
            color: #FFFFFF;
        }
        QPushButton#btnLogout:pressed { background: rgba(239, 68, 68, 0.28); }
    """

    def __init__(self, token_data=None, api_base_url=None, parent=None):
        super().__init__(parent)
        self.token_data = token_data or {}
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self.rol = self.token_data.get("rol", "ADMIN")
        # La X de esta ventana NO cierra la aplicación: pide cerrar sesión.
        # AppController llama a cerrar_para_sesion() para permitir el cierre.
        self._cierre_autorizado = False
        self.setWindowTitle(self.TITULO_VENTANA)
        self.setMinimumSize(1200, 750)
        self.init_ui()
        # No se llama a showMaximized() aquí: la ventana se muestra una sola
        # vez, desde AppController, cuando ya está completamente construida.
        # Mostrarla dentro del constructor causaba el destello al iniciar sesión.

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        layout.addWidget(self._crear_sidebar())

        # ── CONTENIDO PRINCIPAL ──
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("contentStack")
        self.content_stack.setAttribute(Qt.WA_StyledBackground, True)
        # Solo el contenedor lleva fondo; las páginas internas no lo heredan.
        self.content_stack.setStyleSheet(
            "QStackedWidget#contentStack { background: #F1F5F9; }"
        )

        api.jwt_token = self.token_data.get("access_token")
        api.current_user = self.token_data
        self.content_stack.addWidget(self._crear_dashboard_view())
        self.content_stack.addWidget(PostulantesView())
        self.content_stack.addWidget(self._crear_academico_view())
        self.content_stack.addWidget(self._crear_aulas_view())

        if self.rol == "SUPER_ADMIN":
            self.content_stack.addWidget(self._crear_usuarios_view())
            self.content_stack.addWidget(self._crear_auditoria_view())

        layout.addWidget(self.content_stack, 1)

        # Seleccionar Dashboard por defecto
        if self.nav_buttons:
            self._activar_nav(0)

    def _crear_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(264)
        sidebar.setStyleSheet(self.ESTILOS_SIDEBAR)

        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(16, 22, 16, 18)
        sb_layout.setSpacing(0)

        sb_layout.addLayout(self._crear_marca())
        sb_layout.addSpacing(22)
        sb_layout.addWidget(self._crear_separador())
        sb_layout.addSpacing(18)

        # Navegación
        self.nav_buttons = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        sb_layout.addWidget(self._crear_titulo_seccion("MENÚ PRINCIPAL"))
        sb_layout.addSpacing(8)
        principales = [
            ("Dashboard", 0, "dashboard"),
            ("Postulantes", 1, "postulantes"),
            ("Gestiones y Exámenes", 2, "calendario"),
            ("Aulas y Asientos", 3, "aulas"),
        ]
        sb_layout.addLayout(self._crear_grupo_nav(principales))

        if self.rol == "SUPER_ADMIN":
            sb_layout.addSpacing(20)
            sb_layout.addWidget(self._crear_titulo_seccion("ADMINISTRACIÓN"))
            sb_layout.addSpacing(8)
            sistema = [
                ("Usuarios", 4, "usuarios"),
                ("Auditoría", 5, "auditoria"),
            ]
            sb_layout.addLayout(self._crear_grupo_nav(sistema))

        sb_layout.addStretch()

        sb_layout.addWidget(self._crear_separador())
        sb_layout.addSpacing(14)
        sb_layout.addWidget(self._crear_tarjeta_usuario())
        sb_layout.addSpacing(10)

        btn_logout = QPushButton("Cerrar sesión")
        btn_logout.setObjectName("btnLogout")
        btn_logout.setCursor(Qt.PointingHandCursor)
        btn_logout.setFocusPolicy(Qt.NoFocus)
        btn_logout.setMinimumHeight(42)
        btn_logout.setIcon(_crear_icono("salir", reposo="#F2B8B8", activo="#FFFFFF"))
        btn_logout.setIconSize(QSize(28, 20))
        btn_logout.clicked.connect(self.solicitar_cierre_sesion)
        sb_layout.addWidget(btn_logout)
        return sidebar

    def _crear_marca(self):
        fila = QHBoxLayout()
        fila.setSpacing(12)

        insignia = QFrame()
        insignia.setObjectName("brandBadge")
        insignia.setFixedSize(46, 46)
        insignia_layout = QVBoxLayout(insignia)
        insignia_layout.setContentsMargins(6, 6, 6, 6)

        lbl_logo = QLabel()
        lbl_logo.setAlignment(Qt.AlignCenter)
        logo = QPixmap(_buscar_logo() or "")
        if not logo.isNull():
            lbl_logo.setPixmap(logo.scaled(34, 34, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            lbl_logo.setText("UMSA")
            lbl_logo.setObjectName("brandFallback")
        insignia_layout.addWidget(lbl_logo)
        fila.addWidget(insignia)

        textos = QVBoxLayout()
        textos.setSpacing(1)
        lbl_app = QLabel("UMSA")
        lbl_app.setObjectName("brandName")
        lbl_sub = QLabel("Facultad de Medicina")
        lbl_sub.setObjectName("brandSub")
        textos.addWidget(lbl_app)
        textos.addWidget(lbl_sub)
        fila.addLayout(textos, 1)
        return fila

    def _crear_separador(self):
        separador = QFrame()
        separador.setObjectName("sbSeparator")
        separador.setFixedHeight(1)
        return separador

    def _crear_titulo_seccion(self, texto):
        etiqueta = QLabel(texto)
        etiqueta.setObjectName("sectionLabel")
        etiqueta.setFont(_fuente_etiqueta(10, 1.4))
        etiqueta.setContentsMargins(4, 0, 0, 0)
        return etiqueta

    def _crear_grupo_nav(self, items):
        grupo = QVBoxLayout()
        grupo.setSpacing(4)
        for texto, idx, icono in items:
            btn = self._crear_btn_nav(texto, idx, icono)
            grupo.addWidget(btn)
            self.nav_buttons.append(btn)
        return grupo

    def _crear_tarjeta_usuario(self):
        nombre = (
            self.token_data.get("nombre_completo")
            or self.token_data.get("nombre")
            or self.token_data.get("username")
            or self.token_data.get("usuario")
            or "Usuario"
        )
        nombre = str(nombre).strip() or "Usuario"
        rol_legible = str(self.rol).replace("_", " ").title()

        tarjeta = QFrame()
        tarjeta.setObjectName("userCard")
        fila = QHBoxLayout(tarjeta)
        fila.setContentsMargins(12, 10, 12, 10)
        fila.setSpacing(12)

        avatar = QLabel(nombre[:1].upper())
        avatar.setObjectName("userAvatar")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignCenter)
        fila.addWidget(avatar)

        textos = QVBoxLayout()
        textos.setSpacing(1)
        corto = nombre if len(nombre) <= 18 else f"{nombre[:17]}…"
        lbl_nombre = QLabel(corto)
        lbl_nombre.setObjectName("userName")
        lbl_nombre.setToolTip(nombre)
        lbl_rol = QLabel(rol_legible)
        lbl_rol.setObjectName("userRole")
        textos.addWidget(lbl_nombre)
        textos.addWidget(lbl_rol)
        fila.addLayout(textos, 1)
        return tarjeta

    # ------------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------------
    def _crear_btn_nav(self, texto, index, icono=None):
        btn = QPushButton(texto)
        btn.setObjectName("navButton")
        btn.setCursor(Qt.PointingHandCursor)
        btn.setFocusPolicy(Qt.NoFocus)
        btn.setCheckable(True)
        btn.setMinimumHeight(42)
        btn.setProperty("nav_index", index)
        if icono:
            btn.setIcon(_crear_icono(icono))
            btn.setIconSize(QSize(28, 20))
        btn.clicked.connect(lambda _checked=False, i=index: self._activar_nav(i))
        self.nav_group.addButton(btn)
        return btn

    def _activar_nav(self, index):
        self.content_stack.setCurrentIndex(index)
        for btn in self.nav_buttons:
            btn.setChecked(btn.property("nav_index") == index)

    def solicitar_cierre_sesion(self):
        confirmacion = QMessageBox.question(
            self,
            "Cerrar sesión",
            "¿Está seguro de que desea cerrar la sesión actual?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion == QMessageBox.Yes:
            self.cerrar_sesion.emit()

    def cerrar_para_sesion(self):
        """Cierre programático (logout): autoriza el closeEvent."""
        self._cierre_autorizado = True
        self.close()

    def closeEvent(self, evento):
        # La X del panel administrativo no debe cerrar toda la aplicación.
        # Se interpreta como "cerrar sesión" y se vuelve a marcación/login.
        if self._cierre_autorizado:
            super().closeEvent(evento)
            return
        evento.ignore()
        # Diferido: dejar que Qt termine este closeEvent antes de que el
        # controlador vuelva a cerrar la ventana (evita un cierre anidado).
        QTimer.singleShot(0, self.cerrar_sesion.emit)
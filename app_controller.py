import requests
from PySide6.QtWidgets import QStackedWidget, QMainWindow, QMessageBox
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal

from config.app_config import AppConfig
from api.client import api
from views.checkin_view import CheckInView
from views.login_view import LoginView
from views.main_window import MainDashboardWindow

class _EmisorExamen(QObject):
    listo = Signal(int, object, str)  # código HTTP (0 si falló), datos, error


class _TareaExamen(QRunnable):
    """Consulta el examen activo fuera del hilo de la interfaz."""

    def __init__(self, emisor, url, headers):
        super().__init__()
        self._emisor = emisor
        self._url = url
        self._headers = headers

    def run(self):
        try:
            res = requests.get(self._url, headers=self._headers, timeout=3)
            datos = None
            if res.status_code == 200:
                try:
                    datos = res.json()
                except ValueError:
                    datos = {}
            self._emisor.listo.emit(res.status_code, datos, "")
        except Exception as error:
            self._emisor.listo.emit(0, None, str(error))


class AppController(QMainWindow):
    def __init__(self, api_base_url=None):
        super().__init__()
        self.api_base_url = api_base_url or AppConfig.get_api_base_url()
        self.setWindowTitle("Sistema Biométrico - UMSA Medicina")
        self.setMinimumSize(1100, 720)

        self.stack = QStackedWidget(self)
        self.setCentralWidget(self.stack)

        self.checkin_view = CheckInView(self, api_base_url=self.api_base_url)
        self.login_view = LoginView(self, api_base_url=self.api_base_url)
        self.admin_window = None

        self.stack.addWidget(self.checkin_view)  # 0
        self.stack.addWidget(self.login_view)    # 1

        # Señales de navegación
        self.checkin_view.solicitar_login.connect(self.mostrar_login)
        self.login_view.login_exitoso.connect(self.abrir_panel_administrativo)

        # Timer de sondeo de examen activo (cada 30s). La consulta al servidor
        # se hace en un hilo aparte: antes congelaba la ventana hasta 3 s cada
        # vez que el servidor tardaba en responder.
        self._consultando_examen = False
        self._emisor_examen = _EmisorExamen()
        self._emisor_examen.listo.connect(self._examen_consultado)
        self._pool_examen = QThreadPool()
        self._pool_examen.setMaxThreadCount(1)
        self.check_timer = QTimer(self)
        self.check_timer.timeout.connect(self.evaluar_examen_activo)

    def iniciar(self):
        if not AppConfig.get_app_key():
            QMessageBox.critical(self, "Configuración inválida", "No existe APP_CLIENT_KEY en la configuración del cliente.")
            self.close()
            return
        self.evaluar_examen_activo()
        self.check_timer.start(30000)
        self.show()

    def evaluar_examen_activo(self):
        if self.admin_window and self.admin_window.isVisible():
            return
        if self._consultando_examen:
            return  # ya hay una consulta en camino

        app_key = AppConfig.get_app_key()
        if not app_key:
            return

        self._consultando_examen = True
        self._pool_examen.start(_TareaExamen(
            self._emisor_examen,
            f"{self.api_base_url}/examenes/activos-ahora",
            {"X-App-Key": app_key},
        ))

    def _examen_consultado(self, status, datos, error):
        self._consultando_examen = False
        if self.admin_window and self.admin_window.isVisible():
            return  # el panel se abrió mientras llegaba la respuesta

        if status == 200:
            activos = (datos or {}).get("activos", [])
            if activos:
                self.mostrar_checkin(activos[0])
            else:
                self.mostrar_login()
        elif status == 401:
            QMessageBox.critical(
                self, "Clave Inválida",
                "La clave configurada fue dada de baja o no es válida."
            )
            self.mostrar_login()
        elif status == 0:  # sin conexión con el servidor
            if self.stack.currentWidget() != self.checkin_view:
                self.mostrar_login()

    def mostrar_checkin(self, data_examen):
        self.checkin_view.set_examen(data_examen)
        self.stack.setCurrentWidget(self.checkin_view)
        self.checkin_view.iniciar_estacion()

    def mostrar_login(self):
        self.checkin_view.detener_estacion()
        self.stack.setCurrentWidget(self.login_view)

    def abrir_panel_administrativo(self, token_data):
        self.mostrar_login()
        if not self.admin_window:
            self.admin_window = MainDashboardWindow(
                token_data=token_data,
                api_base_url=self.api_base_url,
            )
            self.admin_window.cerrar_sesion.connect(self.cerrar_sesion)
        self.admin_window.show()
        self.hide()

    def cerrar_sesion(self):
        admin_window = self.admin_window
        self.admin_window = None
        if admin_window:
            admin_window.close()
            admin_window.deleteLater()

        api.jwt_token = None
        api.current_user = None
        self.login_view.limpiar_formulario()
        self.show()
        self.evaluar_examen_activo()
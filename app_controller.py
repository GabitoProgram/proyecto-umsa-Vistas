import requests
from PySide6.QtWidgets import QStackedWidget, QMainWindow, QMessageBox
from PySide6.QtCore import QTimer

from config.app_config import AppConfig
from views.checkin_view import CheckInView
from views.login_view import LoginView
from views.main_window import MainDashboardWindow

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

        # Timer de sondeo de examen activo (cada 30s)
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

        app_key = AppConfig.get_app_key()
        if not app_key:
            return

        headers = {"X-App-Key": app_key}
        try:
            res = requests.get(
                f"{self.api_base_url}/examenes/activos-ahora",
                headers=headers,
                timeout=3
            )
            if res.status_code == 200:
                activos = res.json().get("activos", [])
                if activos:
                    self.mostrar_checkin(activos[0])
                else:
                    self.mostrar_login()
            elif res.status_code == 401:
                QMessageBox.critical(
                    self, "Clave Inválida",
                    "La clave configurada fue dada de baja o no es válida."
                )
                self.mostrar_login()
        except Exception:
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
            self.admin_window.volver_a_checkin.connect(self.retornar_a_checkin_desde_admin)
        self.admin_window.show()
        self.hide()

    def retornar_a_checkin_desde_admin(self):
        self.show()
        self.evaluar_examen_activo()

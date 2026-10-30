import sys
import os
import logging
import threading
import types
import importlib
from logging.handlers import RotatingFileHandler

def get_base_path():
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


# Asegurar que la raíz del proyecto esté en el PYTHONPATH
ROOT_DIR = get_base_path()
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Compatibilidad con imports del paquete usado en el proyecto original.
desktop_package = types.ModuleType("desktop")
desktop_package.__path__ = [ROOT_DIR]
sys.modules.setdefault("desktop", desktop_package)
for _subpaquete in ("biometria", "config", "api", "ui", "views"):
    _alias = types.ModuleType(f"desktop.{_subpaquete}")
    _alias.__path__ = [os.path.join(ROOT_DIR, _subpaquete)]
    sys.modules.setdefault(f"desktop.{_subpaquete}", _alias)
    try:
        sys.modules[f"desktop.{_subpaquete}"] = importlib.import_module(_subpaquete)
    except ModuleNotFoundError:
        pass

from PySide6.QtWidgets import QApplication
from app_controller import AppController
from api.client import api
from config.app_config import AppConfig


def _configurar_logging():
    """Deja un rastro en disco: en el .exe no hay consola (console=False)."""
    formato = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    consola = logging.StreamHandler()
    consola.setFormatter(formato)
    root.addHandler(consola)
    try:
        carpeta = os.path.join(
            os.environ.get("LOCALAPPDATA", ROOT_DIR), "SistemaAdmision", "logs"
        )
        os.makedirs(carpeta, exist_ok=True)
        archivo = RotatingFileHandler(
            os.path.join(carpeta, "app.log"),
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        archivo.setFormatter(formato)
        root.addHandler(archivo)
    except OSError:
        pass


def _instalar_excepthook():
    """Registra errores no controlados en vez de morir en silencio."""
    def _hook(tipo, valor, traza):
        logging.getLogger("excepcion").critical(
            "Error no controlado", exc_info=(tipo, valor, traza)
        )
        try:
            from PySide6.QtWidgets import QApplication, QMessageBox
            # Los cuadros de diálogo solo se crean desde el hilo de la GUI.
            if (QApplication.instance() is not None
                    and threading.current_thread() is threading.main_thread()):
                QMessageBox.critical(
                    None,
                    "Error inesperado",
                    "Ocurrió un error inesperado. El detalle quedó registrado "
                    "en el archivo de logs.\n\n"
                    f"{tipo.__name__}: {valor}",
                )
        except Exception:
            pass
        sys.__excepthook__(tipo, valor, traza)

    sys.excepthook = _hook


def main():
    _configurar_logging()
    _instalar_excepthook()

    app = QApplication(sys.argv)

    # Cargar QSS
    qss_path = os.path.join(ROOT_DIR, "assets", "styles.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    api_base_url = AppConfig.get_api_base_url()
    api.BASE_URL = api_base_url
    controller = AppController(api_base_url=api_base_url)
    controller.iniciar()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

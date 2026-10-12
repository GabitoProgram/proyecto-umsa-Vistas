import sys
import os
import logging
import types

# Asegurar que la raíz del proyecto esté en el PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Compatibilidad con imports del paquete usado en el proyecto original.
desktop_package = types.ModuleType("desktop")
desktop_package.__path__ = [ROOT_DIR]
sys.modules.setdefault("desktop", desktop_package)

from PySide6.QtWidgets import QApplication
from app_controller import AppController
from api.client import api
from config.app_config import AppConfig

def main():
    # Configurar logging para diagnóstico de huella
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app = QApplication(sys.argv)

    # Cargar QSS
    qss_path = os.path.join(os.path.dirname(__file__), "assets", "styles.qss")
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

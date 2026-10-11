import sys
import os
import logging

# Asegurar que la raíz del proyecto esté en el PYTHONPATH
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from PySide6.QtWidgets import QApplication
from desktop.app_controller import AppController
from desktop.api.client import api

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

    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
    api.BASE_URL = api_base_url
    controller = AppController(api_base_url=api_base_url)
    controller.iniciar()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()

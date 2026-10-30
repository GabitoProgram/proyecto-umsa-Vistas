import requests
from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2

from desktop.views.dialogs.postulante_dialog import (
    DialogEditarPostulante,
    DialogNuevoPostulanteGestion,
)
from desktop.views.dialogs.gestion_dialog import DialogGestion
from desktop.views.dialogs.carrera_dialog import DialogCarrera
from desktop.views.dialogs.examen_dialog import DialogExamen
from desktop.views.dialogs.captura_rostro_dialog import DialogCapturaRostro
from desktop.views.admin.examen_workspace_view import ExamenWorkspaceView


class CommonMixin:
    def _obtener_lista(self, endpoint, timeout=8):
        try:
            response = requests.get(
                f"{self.api_base_url}{endpoint}",
                headers=self._auth_headers(),
                timeout=timeout
            )
            if response.status_code == 401:
                self._avisar_sesion_expirada()
                return []
            return response.json() if response.status_code == 200 else []
        except (requests.RequestException, ValueError):
            return []

    def _obtener_objeto(self, endpoint, timeout=8):
        """Igual que _obtener_lista pero para endpoints que devuelven un objeto."""
        try:
            response = requests.get(
                f"{self.api_base_url}{endpoint}",
                headers=self._auth_headers(),
                timeout=timeout
            )
            if response.status_code == 401:
                self._avisar_sesion_expirada()
                return None
            if response.status_code != 200:
                return None
            datos = response.json()
            return datos if isinstance(datos, dict) else None
        except (requests.RequestException, ValueError):
            return None

    def _avisar_sesion_expirada(self):
        """Avisa una sola vez y vuelve al login (el token ya no sirve)."""
        if getattr(self, "_sesion_expirada_avisada", False):
            return
        self._sesion_expirada_avisada = True
        QTimer.singleShot(0, self._mostrar_aviso_sesion_expirada)

    def _mostrar_aviso_sesion_expirada(self):
        QMessageBox.information(
            self,
            "Sesión expirada",
            "Tu sesión expiró o fue cerrada. Vuelve a iniciar sesión.",
        )
        if hasattr(self, "cerrar_sesion"):
            self.cerrar_sesion.emit()

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token_data.get('access_token', '')}"}

    def _cargar_tabla_simple(self, table, endpoint, fields):
        try:
            response = requests.get(
                f"{self.api_base_url}{endpoint}",
                headers=self._auth_headers(),
                timeout=5
            )
            data = response.json() if response.status_code == 200 else []
            table.setRowCount(len(data))
            for row, item in enumerate(data):
                for column, field in enumerate(fields):
                    table.setItem(row, column, QTableWidgetItem(str(item.get(field) or "")))
        except requests.RequestException:
            table.setRowCount(0)

    def _crear_catalogo(self, endpoint, payload, etiqueta):
        try:
            respuesta = requests.post(
                f"{self.api_base_url}{endpoint}",
                json=payload,
                headers=self._auth_headers(),
                timeout=5
            )
            if respuesta.status_code in (200, 201):
                QMessageBox.information(self, etiqueta, f"{etiqueta} creada correctamente.")
            else:
                detalle = respuesta.json().get("detail", f"No se pudo crear la {etiqueta.lower()}.")
                QMessageBox.warning(self, etiqueta, str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, etiqueta, f"Error de conexion: {error}")

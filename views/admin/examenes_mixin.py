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


class ExamenesMixin:
    def abrir_workspace_desde_nav(self, examen):
        workspace = ExamenWorkspaceView(examen, self.token_data, self.api_base_url, self)
        workspace.volver.connect(self.cerrar_workspace)
        index = self.content_stack.addWidget(workspace)
        self.content_stack.setCurrentIndex(index)

    def cerrar_workspace(self):
        # Vuelve a la pestaña de navegación académica (gestiones/carreras/exámenes)
        self.content_stack.setCurrentIndex(2)

    def crear_examen_nav(self):
        dlg = DialogExamen(None, self.gestion_nav_id, self.carrera_nav_id, self)
        if dlg.exec():
            self._crear_catalogo("/admin/examenes", dlg.get_data(), "Examen")
            self.abrir_carrera_nav({"id_carrera": self.carrera_nav_id, "nombre": self.examen_nav_title.text().replace("Exámenes de ", "")})

    def editar_examen_nav(self, examen):
        dlg = DialogExamen(examen, self.gestion_nav_id, self.carrera_nav_id, self)
        if dlg.exec():
            try:
                respuesta = requests.patch(
                    f"{self.api_base_url}/admin/examenes/{examen['id_examen']}",
                    json=dlg.get_data(), headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code == 200:
                    self.abrir_carrera_nav({"id_carrera": self.carrera_nav_id, "nombre": self.examen_nav_title.text().replace("Exámenes de ", "")})
                else:
                    QMessageBox.warning(self, "Examen", str(respuesta.json().get("detail", "No se pudo editar.")))
            except Exception as error:
                QMessageBox.critical(self, "Examen", f"Error de conexión: {error}")

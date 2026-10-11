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


class CarrerasMixin:
    def abrir_carrera_nav(self, carrera):
        self.carrera_nav_id = carrera.get("id_carrera")
        self.examen_nav_title.setText(f"Exámenes de {carrera.get('nombre', 'carrera')}")
        self.examenes_nav = [
            examen for examen in self._obtener_lista("/admin/examenes")
            if examen.get("id_gestion") == self.gestion_nav_id
            and examen.get("id_carrera") == self.carrera_nav_id
        ]
        self.examenes_nav_table.setRowCount(len(self.examenes_nav))
        for fila, examen in enumerate(self.examenes_nav):
            valores = (
                examen.get("materia"), examen.get("fecha"),
                f"{examen.get('hora_inicio')} - {examen.get('hora_fin')}"
            )
            for columna, valor in enumerate(valores):
                self.examenes_nav_table.setItem(fila, columna, QTableWidgetItem(str(valor or "")))
            acciones = QWidget()
            acciones_layout = QHBoxLayout(acciones)
            acciones_layout.setContentsMargins(2, 2, 2, 2)
            acciones_layout.setSpacing(4)
            boton = QPushButton("Abrir")
            boton.setMinimumSize(70, 32)
            boton.setMaximumHeight(36)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setStyleSheet("background-color: #059669; color: white; padding: 4px 8px; border-radius: 4px; border: none; font-size: 11px;")
            boton.clicked.connect(lambda _, item=examen: self.abrir_workspace_desde_nav(item))
            btn_editar = QPushButton("Editar")
            btn_editar.setMinimumSize(60, 32)
            btn_editar.setMaximumHeight(36)
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet("background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;")
            btn_editar.clicked.connect(lambda _, item=examen: self.editar_examen_nav(item))
            acciones_layout.addWidget(boton)
            acciones_layout.addWidget(btn_editar)
            self.examenes_nav_table.setCellWidget(fila, 3, acciones)
            self.examenes_nav_table.setRowHeight(fila, 50)
        self.academico_stack.setCurrentIndex(2)

    def crear_carrera_nav(self):
        dlg = DialogCarrera(None, self)
        if dlg.exec():
            self._crear_catalogo("/admin/carreras", dlg.get_data(), "Carrera")
            self.abrir_gestion_nav({"id_gestion": self.gestion_nav_id, "nombre": self.carrera_nav_title.text().replace("Carreras de ", "")})

    def editar_carrera_nav(self, carrera):
        dlg = DialogCarrera(carrera, self)
        if dlg.exec():
            try:
                respuesta = requests.patch(
                    f"{self.api_base_url}/admin/carreras/{carrera['id_carrera']}",
                    json=dlg.get_data(), headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code == 200:
                    self.abrir_gestion_nav({"id_gestion": self.gestion_nav_id, "nombre": self.carrera_nav_title.text().replace("Carreras de ", "")})
                else:
                    QMessageBox.warning(self, "Carrera", str(respuesta.json().get("detail", "No se pudo editar.")))
            except Exception as error:
                QMessageBox.critical(self, "Carrera", f"Error de conexión: {error}")

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


class GestionesMixin:
    def cargar_gestiones_nav(self):
        self.gestiones_nav = self._obtener_lista("/admin/gestiones")
        self.gestiones_nav_table.setRowCount(len(self.gestiones_nav))
        for fila, gestion in enumerate(self.gestiones_nav):
            valores = (gestion.get("nombre"), gestion.get("anio"), gestion.get("estado"))
            for columna, valor in enumerate(valores):
                self.gestiones_nav_table.setItem(fila, columna, QTableWidgetItem(str(valor or "")))
            acciones = QWidget()
            acciones_layout = QHBoxLayout(acciones)
            acciones_layout.setContentsMargins(2, 2, 2, 2)
            acciones_layout.setSpacing(4)
            boton = QPushButton("Abrir")
            boton.setMinimumSize(70, 32)
            boton.setMaximumHeight(36)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setStyleSheet("background-color: #2563EB; color: white; padding: 4px 8px; border-radius: 4px; border: none; font-size: 11px;")
            boton.clicked.connect(lambda _, item=gestion: self.abrir_gestion_nav(item))
            btn_editar = QPushButton("Editar")
            btn_editar.setMinimumSize(60, 32)
            btn_editar.setMaximumHeight(36)
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet("background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;")
            btn_editar.clicked.connect(lambda _, item=gestion: self.editar_gestion_nav(item))
            acciones_layout.addWidget(boton)
            acciones_layout.addWidget(btn_editar)
            self.gestiones_nav_table.setCellWidget(fila, 3, acciones)
            self.gestiones_nav_table.setRowHeight(fila, 50)

    def abrir_gestion_nav(self, gestion):
        self.gestion_nav_id = gestion.get("id_gestion")
        self.carrera_nav_title.setText(f"Carreras de {gestion.get('nombre', 'gestión')}")
        self.carreras_nav = [
            carrera for carrera in self._obtener_lista("/admin/carreras")
            if carrera.get("activa", True)
        ]
        self.carreras_nav_table.setRowCount(len(self.carreras_nav))
        for fila, carrera in enumerate(self.carreras_nav):
            self.carreras_nav_table.setItem(fila, 0, QTableWidgetItem(str(carrera.get("nombre", ""))))
            self.carreras_nav_table.setItem(fila, 1, QTableWidgetItem(str(carrera.get("codigo", ""))))
            acciones = QWidget()
            acciones_layout = QHBoxLayout(acciones)
            acciones_layout.setContentsMargins(2, 2, 2, 2)
            acciones_layout.setSpacing(4)
            boton = QPushButton("Examenes")
            boton.setMinimumSize(70, 32)
            boton.setMaximumHeight(36)
            boton.setCursor(Qt.PointingHandCursor)
            boton.setStyleSheet("background-color: #2563EB; color: white; padding: 4px 8px; border-radius: 4px; border: none; font-size: 11px;")
            boton.clicked.connect(lambda _, item=carrera: self.abrir_carrera_nav(item))
            btn_editar = QPushButton("Editar")
            btn_editar.setMinimumSize(60, 32)
            btn_editar.setMaximumHeight(36)
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet("background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;")
            btn_editar.clicked.connect(lambda _, item=carrera: self.editar_carrera_nav(item))
            acciones_layout.addWidget(boton)
            acciones_layout.addWidget(btn_editar)
            self.carreras_nav_table.setCellWidget(fila, 2, acciones)
            self.carreras_nav_table.setRowHeight(fila, 50)
        self.academico_stack.setCurrentIndex(1)

    def crear_gestion_nav(self):
        dlg = DialogGestion(None, self)
        if dlg.exec():
            self._crear_catalogo("/admin/gestiones", dlg.get_data(), "Gestión")
            self.cargar_gestiones_nav()

    def editar_gestion_nav(self, gestion):
        dlg = DialogGestion(gestion, self)
        if dlg.exec():
            try:
                respuesta = requests.patch(
                    f"{self.api_base_url}/admin/gestiones/{gestion['id_gestion']}",
                    json=dlg.get_data(), headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code == 200:
                    self.cargar_gestiones_nav()
                else:
                    QMessageBox.warning(self, "Gestión", str(respuesta.json().get("detail", "No se pudo editar.")))
            except Exception as error:
                QMessageBox.critical(self, "Gestión", f"Error de conexión: {error}")

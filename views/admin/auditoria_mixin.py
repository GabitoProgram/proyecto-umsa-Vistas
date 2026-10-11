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


class AuditoriaMixin:
    def _crear_auditoria_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Registro de Auditoria")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(title)

        filtros = QHBoxLayout()
        filtros.setSpacing(10)

        self.txt_filtro_accion = QLineEdit()
        self.txt_filtro_accion.setPlaceholderText("Filtrar por accion...")
        self.txt_filtro_accion.setMinimumHeight(38)

        self.txt_filtro_entidad = QLineEdit()
        self.txt_filtro_entidad.setPlaceholderText("Filtrar por entidad...")
        self.txt_filtro_entidad.setMinimumHeight(38)

        btn_filtrar = QPushButton("Filtrar")
        btn_filtrar.setCursor(Qt.PointingHandCursor)
        btn_filtrar.setMinimumHeight(38)
        btn_filtrar.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; color: white;
                padding: 8px 20px; border-radius: 6px;
                font-weight: 600; font-size: 13px; border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        btn_filtrar.clicked.connect(self.cargar_auditoria_panel)

        filtros.addWidget(self.txt_filtro_accion)
        filtros.addWidget(self.txt_filtro_entidad)
        filtros.addWidget(btn_filtrar)
        layout.addLayout(filtros)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["Fecha", "Usuario", "Accion", "Entidad", "Detalle"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        self.auditoria_table = table
        layout.addWidget(table)
        self.cargar_auditoria_panel()
        return w

    def cargar_auditoria_panel(self):
        try:
            params = {}
            accion = self.txt_filtro_accion.text().strip()
            entidad = self.txt_filtro_entidad.text().strip()
            if accion:
                params["accion"] = accion
            if entidad:
                params["entidad"] = entidad
            response = requests.get(
                f"{self.api_base_url}/admin/auditoria",
                params=params,
                headers=self._auth_headers(),
                timeout=5
            )
            data = response.json() if response.status_code == 200 else []
            fields = ["fecha_hora", "id_usuario", "accion", "entidad_afectada", "detalle"]
            self.auditoria_table.setRowCount(len(data))
            for row, item in enumerate(data):
                for column, field in enumerate(fields):
                    self.auditoria_table.setItem(
                        row, column, QTableWidgetItem(str(item.get(field) or ""))
                    )
        except (requests.RequestException, ValueError):
            self.auditoria_table.setRowCount(0)

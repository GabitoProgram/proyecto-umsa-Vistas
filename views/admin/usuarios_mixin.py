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


class UsuariosMixin:
    def _crear_usuarios_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Usuarios y Roles")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")

        encabezado = QHBoxLayout()
        encabezado.addWidget(title)
        encabezado.addStretch()

        btn_style = """
            QPushButton {
                background-color: #2563EB; color: white;
                padding: 8px 16px; border-radius: 6px;
                font-weight: 600; font-size: 13px; border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """
        btn_secondary = """
            QPushButton {
                background-color: #F1F5F9; color: #334155;
                padding: 8px 16px; border-radius: 6px;
                font-weight: 600; font-size: 13px;
                border: 1px solid #CBD5E1;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """

        btn_nuevo = QPushButton("+ Nuevo usuario")
        btn_nuevo.setCursor(Qt.PointingHandCursor)
        btn_nuevo.setStyleSheet(btn_style)
        btn_nuevo.clicked.connect(self.crear_usuario_panel)

        btn_estado = QPushButton("Cambiar estado")
        btn_estado.setCursor(Qt.PointingHandCursor)
        btn_estado.setStyleSheet(btn_secondary)
        btn_estado.clicked.connect(self.cambiar_estado_usuario)

        btn_refrescar = QPushButton("Actualizar")
        btn_refrescar.setCursor(Qt.PointingHandCursor)
        btn_refrescar.setStyleSheet(btn_secondary)
        btn_refrescar.clicked.connect(self.cargar_usuarios_panel)

        encabezado.addWidget(btn_nuevo)
        encabezado.addWidget(btn_estado)
        encabezado.addWidget(btn_refrescar)
        layout.addLayout(encabezado)

        self.usuarios_table = QTableWidget(0, 5)
        self.usuarios_table.setHorizontalHeaderLabels(["ID", "Usuario", "Nombre", "Rol", "Activo"])
        self.usuarios_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.usuarios_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.usuarios_table.setAlternatingRowColors(True)
        layout.addWidget(self.usuarios_table)
        self.cargar_usuarios_panel()
        return w

    def cargar_usuarios_panel(self):
        self._cargar_tabla_simple(
            self.usuarios_table, "/admin/usuarios",
            ["id_usuario", "usuario", "nombre_completo", "rol", "activo"]
        )

    def cambiar_estado_usuario(self):
        fila = self.usuarios_table.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Usuarios", "Seleccione un usuario primero.")
            return
        id_usuario = int(self.usuarios_table.item(fila, 0).text())
        activo_actual = self.usuarios_table.item(fila, 4).text().lower() == "true"
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/admin/usuarios/{id_usuario}",
                json={"activo": not activo_actual},
                headers=self._auth_headers(),
                timeout=5
            )
            if respuesta.status_code == 200:
                self.cargar_usuarios_panel()
            else:
                detalle = respuesta.json().get("detail", "No se pudo actualizar el usuario.")
                QMessageBox.warning(self, "Usuarios", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Usuarios", f"Error de conexión: {error}")

    def crear_usuario_panel(self):
        usuario, aceptado = QInputDialog.getText(self, "Nuevo usuario", "Nombre de usuario:")
        if not aceptado or not usuario.strip():
            return
        nombre, aceptado = QInputDialog.getText(self, "Nuevo usuario", "Nombre completo:")
        if not aceptado or not nombre.strip():
            return
        password, aceptado = QInputDialog.getText(
            self, "Nuevo usuario", "Contraseña:", QLineEdit.Password
        )
        if not aceptado or not password:
            return
        rol, aceptado = QInputDialog.getItem(
            self, "Nuevo usuario", "Rol:", ["ADMIN", "SUPER_ADMIN"], 0, False
        )
        if not aceptado:
            return
        try:
            respuesta = requests.post(
                f"{self.api_base_url}/admin/usuarios",
                json={
                    "usuario": usuario.strip(),
                    "nombre_completo": nombre.strip(),
                    "password": password,
                    "rol": rol,
                    "activo": True
                },
                headers=self._auth_headers(),
                timeout=5
            )
            if respuesta.status_code in (200, 201):
                self.cargar_usuarios_panel()
                QMessageBox.information(self, "Usuarios", "Usuario creado correctamente.")
            else:
                detalle = respuesta.json().get("detail", "No se pudo crear el usuario.")
                QMessageBox.warning(self, "Usuarios", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Usuarios", f"Error de conexión: {error}")

import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from desktop.views.admin.aulas.aula_dialog import DialogAula
from desktop.views.admin.aulas.asientos_dialog import DialogAsientosAula


class AulasMixin:
    def _crear_aulas_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Aulas y Asientos")
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")

        encabezado = QHBoxLayout()
        encabezado.addWidget(title)
        encabezado.addStretch()

        btn_nueva = QPushButton("+ Nueva aula")
        btn_nueva.setCursor(Qt.PointingHandCursor)
        btn_nueva.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px; border: none;"
        )
        btn_nueva.clicked.connect(self.crear_aula_panel)

        btn_refrescar = QPushButton("Actualizar")
        btn_refrescar.setCursor(Qt.PointingHandCursor)
        btn_refrescar.setStyleSheet(
            "background-color: #F1F5F9; color: #334155; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px; border: 1px solid #CBD5E1;"
        )
        btn_refrescar.clicked.connect(self.cargar_aulas_panel)

        encabezado.addWidget(btn_nueva)
        encabezado.addWidget(btn_refrescar)
        layout.addLayout(encabezado)

        self.aulas_table = QTableWidget(0, 6)
        self.aulas_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Ubicación", "Capacidad", "Asientos", "Acciones"
        ])
        self.aulas_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.aulas_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.aulas_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Fixed)
        self.aulas_table.horizontalHeader().resizeSection(5, 250)
        self.aulas_table.verticalHeader().setDefaultSectionSize(50)
        self.aulas_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.aulas_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.aulas_table.setAlternatingRowColors(True)
        layout.addWidget(self.aulas_table)
        self.cargar_aulas_panel()
        return w

    def cargar_aulas_panel(self):
        self.aulas_data = self._obtener_lista("/admin/aulas")
        self.aulas_table.setRowCount(len(self.aulas_data))
        for fila, aula in enumerate(self.aulas_data):
            activa = aula.get("activa", True)
            id_item = QTableWidgetItem(str(aula.get("id_aula", "")))
            id_item.setTextAlignment(Qt.AlignCenter)
            self.aulas_table.setItem(fila, 0, id_item)
            self.aulas_table.setItem(fila, 1, QTableWidgetItem(str(aula.get("nombre", ""))))
            self.aulas_table.setItem(fila, 2, QTableWidgetItem(str(aula.get("ubicacion") or "—")))
            cap_item = QTableWidgetItem(str(aula.get("capacidad", 0)))
            cap_item.setTextAlignment(Qt.AlignCenter)
            self.aulas_table.setItem(fila, 3, cap_item)

            total = aula.get("total_asientos", 0)
            habilitados = aula.get("asientos_habilitados", 0)
            asientos_item = QTableWidgetItem(f"{habilitados}/{total}")
            asientos_item.setTextAlignment(Qt.AlignCenter)
            self.aulas_table.setItem(fila, 4, asientos_item)

            acciones = QWidget()
            h = QHBoxLayout(acciones)
            h.setContentsMargins(2, 2, 2, 2)
            h.setSpacing(4)

            btn_abrir = QPushButton("Abrir")
            btn_abrir.setCursor(Qt.PointingHandCursor)
            btn_abrir.setStyleSheet(
                "background-color: #059669; color: white; padding: 4px 8px; "
                "border-radius: 4px; border: none; font-size: 11px; font-weight: bold;"
            )
            btn_abrir.clicked.connect(lambda _, a=aula: self.abrir_asientos_aula(a))

            btn_editar = QPushButton("Editar")
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet(
                "background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; "
                "border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;"
            )
            btn_editar.clicked.connect(lambda _, a=aula: self.editar_aula_panel(a))

            btn_estado = QPushButton("Deshabilitar" if activa else "Habilitar")
            btn_estado.setCursor(Qt.PointingHandCursor)
            btn_estado.setStyleSheet(
                "background-color: #FEF3C7; color: #92400E; padding: 4px 8px; "
                "border-radius: 4px; border: 1px solid #FCD34D; font-size: 11px;"
            )
            btn_estado.clicked.connect(lambda _, a=aula: self.cambiar_estado_aula(a, not activa))

            h.addWidget(btn_abrir)
            h.addWidget(btn_editar)
            h.addWidget(btn_estado)
            self.aulas_table.setCellWidget(fila, 5, acciones)
            self.aulas_table.setRowHeight(fila, 50)

    def crear_aula_panel(self):
        dlg = DialogAula(None, self)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Aula", "El nombre es obligatorio.")
            return
        try:
            respuesta = requests.post(
                f"{self.api_base_url}/admin/aulas",
                json=datos,
                headers=self._auth_headers(),
                timeout=6,
            )
            if respuesta.status_code in (200, 201):
                self.cargar_aulas_panel()
                QMessageBox.information(self, "Aula", "Aula creada correctamente.")
            else:
                QMessageBox.warning(
                    self, "Aula",
                    str(respuesta.json().get("detail", "No se pudo crear el aula.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Aula", f"Error de conexión: {error}")

    def editar_aula_panel(self, aula):
        dlg = DialogAula(aula, self)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Aula", "El nombre es obligatorio.")
            return
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/admin/aulas/{aula['id_aula']}",
                json=datos,
                headers=self._auth_headers(),
                timeout=6,
            )
            if respuesta.status_code == 200:
                self.cargar_aulas_panel()
                QMessageBox.information(self, "Aula", "Aula actualizada correctamente.")
            else:
                QMessageBox.warning(
                    self, "Aula",
                    str(respuesta.json().get("detail", "No se pudo actualizar el aula.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Aula", f"Error de conexión: {error}")

    def cambiar_estado_aula(self, aula, activa):
        accion = "habilitar" if activa else "deshabilitar"
        confirmacion = QMessageBox.question(
            self, "Aula",
            f"¿{accion.capitalize()} el aula '{aula.get('nombre')}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/admin/aulas/{aula['id_aula']}",
                json={"activa": activa},
                headers=self._auth_headers(),
                timeout=6,
            )
            if respuesta.status_code == 200:
                self.cargar_aulas_panel()
            else:
                QMessageBox.warning(
                    self, "Aula",
                    str(respuesta.json().get("detail", "No se pudo actualizar el aula.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Aula", f"Error de conexión: {error}")

    def abrir_asientos_aula(self, aula):
        dlg = DialogAsientosAula(aula, self.api_base_url, self._auth_headers(), self)
        dlg.exec()
        # Al cerrar, refrescar el conteo de asientos del aula
        self.cargar_aulas_panel()

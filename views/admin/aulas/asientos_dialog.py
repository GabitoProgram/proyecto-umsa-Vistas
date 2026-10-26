from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QSpinBox, QInputDialog, QWidget
)
from PySide6.QtCore import Qt
import requests


class DialogAsientosAula(QDialog):
    """Muestra y gestiona los asientos de un aula (agregar, habilitar/deshabilitar, eliminar)."""

    def __init__(self, aula, api_base_url, headers, parent=None):
        super().__init__(parent)
        self.aula = aula
        self.api_base_url = api_base_url
        self.headers = headers
        self.setWindowTitle(f"Asientos - {aula.get('nombre', 'Aula')}")
        self.setMinimumSize(720, 560)
        self.init_ui()
        self.cargar_asientos()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        lbl_tit = QLabel(f"Asientos de {self.aula.get('nombre', 'Aula')}")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        # Resumen
        self.lbl_resumen = QLabel("")
        self.lbl_resumen.setStyleSheet("font-size: 13px; color: #475569;")
        layout.addWidget(self.lbl_resumen)

        # Barra para agregar asientos
        barra = QHBoxLayout()
        barra.addWidget(QLabel("Cantidad:"))
        self.spin_cantidad = QSpinBox()
        self.spin_cantidad.setRange(1, 1000)
        self.spin_cantidad.setValue(1)
        self.spin_cantidad.setMinimumWidth(90)
        barra.addWidget(self.spin_cantidad)

        barra.addWidget(QLabel("Número inicial:"))
        self.spin_inicio = QSpinBox()
        self.spin_inicio.setRange(1, 100000)
        self.spin_inicio.setValue(1)
        self.spin_inicio.setMinimumWidth(90)
        barra.addWidget(self.spin_inicio)

        btn_agregar = QPushButton("+ Agregar asientos")
        btn_agregar.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; border: none;"
        )
        btn_agregar.setCursor(Qt.PointingHandCursor)
        btn_agregar.clicked.connect(self.agregar_asientos)
        barra.addWidget(btn_agregar)
        barra.addStretch()
        layout.addLayout(barra)

        # Tabla de asientos
        self.tabla = QTableWidget(0, 4)
        self.tabla.setHorizontalHeaderLabels(["ID", "Número", "Estado", "Acciones"])
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.setMinimumHeight(40)
        btn_cerrar.setCursor(Qt.PointingHandCursor)
        btn_cerrar.clicked.connect(self.accept)
        box = QHBoxLayout()
        box.addStretch()
        box.addWidget(btn_cerrar)
        layout.addLayout(box)

    def cargar_asientos(self):
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/aulas/{self.aula['id_aula']}/asientos",
                headers=self.headers,
                timeout=5,
            )
            asientos = respuesta.json() if respuesta.status_code == 200 else []
        except (requests.RequestException, ValueError):
            asientos = []
        self._asientos = asientos
        self.tabla.setRowCount(len(asientos))
        for fila, asiento in enumerate(asientos):
            self.tabla.setItem(fila, 0, QTableWidgetItem(str(asiento.get("id_asiento", ""))))
            num_item = QTableWidgetItem(str(asiento.get("numero_asiento", "")))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.tabla.setItem(fila, 1, num_item)
            habilitado = asiento.get("habilitado", False)
            estado_item = QTableWidgetItem("HABILITADO" if habilitado else "DESHABILITADO")
            estado_item.setTextAlignment(Qt.AlignCenter)
            estado_item.setForeground(Qt.darkGreen if habilitado else Qt.darkGray)
            self.tabla.setItem(fila, 2, estado_item)

            acciones = QWidget()
            h = QHBoxLayout(acciones)
            h.setContentsMargins(2, 2, 2, 2)
            h.setSpacing(4)
            btn_toggle = QPushButton("Deshabilitar" if habilitado else "Habilitar")
            btn_toggle.setCursor(Qt.PointingHandCursor)
            btn_toggle.setStyleSheet(
                "background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; "
                "border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;"
            )
            btn_toggle.clicked.connect(
                lambda _, a=asiento: self.cambiar_habilitado(a, not a.get("habilitado", False))
            )
            btn_eliminar = QPushButton("Eliminar")
            btn_eliminar.setCursor(Qt.PointingHandCursor)
            btn_eliminar.setStyleSheet(
                "background-color: #FEE2E2; color: #991B1B; padding: 4px 8px; "
                "border-radius: 4px; border: 1px solid #FCA5A5; font-size: 11px;"
            )
            btn_eliminar.setVisible(
                not self.parent() or getattr(self.parent(), "rol", "") == "SUPER_ADMIN"
            )
            btn_eliminar.clicked.connect(lambda _, a=asiento: self.eliminar_asiento(a))
            h.addWidget(btn_toggle)
            h.addWidget(btn_eliminar)
            self.tabla.setCellWidget(fila, 3, acciones)
            self.tabla.setRowHeight(fila, 44)

        habilitados = sum(1 for a in asientos if a.get("habilitado"))
        self.lbl_resumen.setText(
            f"Total: {len(asientos)} asientos | Habilitados: {habilitados} | "
            f"Deshabilitados: {len(asientos) - habilitados}"
        )

    def agregar_asientos(self):
        cantidad = self.spin_cantidad.value()
        inicio = self.spin_inicio.value()
        try:
            respuesta = requests.post(
                f"{self.api_base_url}/admin/aulas/{self.aula['id_aula']}/asientos",
                json={"cantidad": cantidad, "numero_inicial": inicio},
                headers=self.headers,
                timeout=5,
            )
            if respuesta.status_code == 200:
                self.cargar_asientos()
            else:
                QMessageBox.warning(
                    self, "Asientos",
                    str(respuesta.json().get("detail", "No se pudieron crear los asientos.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Asientos", f"Error de conexión: {error}")

    def cambiar_habilitado(self, asiento, habilitado):
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/admin/asientos/{asiento['id_asiento']}/habilitado",
                params={"habilitado": habilitado},
                headers=self.headers,
                timeout=5,
            )
            if respuesta.status_code == 200:
                self.cargar_asientos()
            else:
                QMessageBox.warning(
                    self, "Asiento",
                    str(respuesta.json().get("detail", "No se pudo actualizar el asiento.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Asiento", f"Error de conexión: {error}")

    def eliminar_asiento(self, asiento):
        confirmacion = QMessageBox.question(
            self, "Eliminar asiento",
            f"¿Eliminar el asiento #{asiento.get('numero_asiento')}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/admin/asientos/{asiento['id_asiento']}",
                headers=self.headers,
                timeout=5,
            )
            if respuesta.status_code in (200, 204):
                self.cargar_asientos()
            else:
                QMessageBox.warning(
                    self, "Asiento",
                    str(respuesta.json().get("detail", "No se pudo eliminar el asiento.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Asiento", f"Error de conexión: {error}")

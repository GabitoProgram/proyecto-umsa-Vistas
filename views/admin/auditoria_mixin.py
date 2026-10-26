import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
)
from PySide6.QtCore import Qt, QTimer


class AuditoriaMixin:
    def _crear_auditoria_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Registro de Auditoría", w)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(title)

        filtros = QHBoxLayout()
        filtros.setSpacing(10)

        self.txt_filtro_accion = QLineEdit(w)
        self.txt_filtro_accion.setPlaceholderText("Filtrar por acción...")
        self.txt_filtro_accion.setMinimumHeight(38)

        self.txt_filtro_entidad = QLineEdit(w)
        self.txt_filtro_entidad.setPlaceholderText("Filtrar por entidad...")
        self.txt_filtro_entidad.setMinimumHeight(38)

        btn_filtrar = QPushButton("Filtrar", w)
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

        table = QTableWidget(0, 5, w)
        table.setHorizontalHeaderLabels(["Fecha", "Usuario", "Acción", "Entidad", "Detalle"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        self.auditoria_table = table
        layout.addWidget(table)

        # Carga diferida: corre cuando la ventana ya está visible.
        QTimer.singleShot(0, self.cargar_auditoria_panel)
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
                timeout=5,
            )
            data = response.json() if response.status_code == 200 else []
            fields = ["fecha_hora", "id_usuario", "accion", "entidad_afectada", "detalle"]
            self.auditoria_table.setUpdatesEnabled(False)
            self.auditoria_table.setRowCount(len(data))
            for row, item in enumerate(data):
                for column, field in enumerate(fields):
                    self.auditoria_table.setItem(
                        row, column, QTableWidgetItem(str(item.get(field) or ""))
                    )
            self.auditoria_table.setUpdatesEnabled(True)
        except (requests.RequestException, ValueError):
            self.auditoria_table.setUpdatesEnabled(True)
            self.auditoria_table.setRowCount(0)
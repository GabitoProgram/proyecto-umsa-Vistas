import cv2
import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QListWidget, QListWidgetItem, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QImage, QPixmap, QKeyEvent
from desktop.config.app_config import AppConfig


class ContadorMixin:
    def actualizar_contador(self):
        id_examen = self.info_examen.get("id_examen")
        if not id_examen:
            return
        try:
            app_key = AppConfig.get_app_key()
            res = requests.get(
                f"{self.api_base_url}/examenes/activos-ahora/contadores",
                headers={"X-App-Key": app_key} if app_key else {},
                timeout=2
            )
            if res.status_code == 200:
                contadores = res.json()
                self.tabla_contadores.setRowCount(len(contadores))
                for row, contador in enumerate(contadores):
                    valores = (
                        contador.get("materia", "Examen"),
                        contador.get("total_ingresados", 0),
                        contador.get("total_pendientes", 0),
                        f"{contador.get('porcentaje_asistencia', 0.0)}%"
                    )
                    for column, value in enumerate(valores):
                        self.tabla_contadores.setItem(row, column, QTableWidgetItem(str(value)))
                data = next((item for item in contadores if item.get("id_examen") == id_examen), {})
                total = data.get("total_asignados", 0)
                ingresados = data.get("total_ingresados", 0)
                porcentaje = data.get("porcentaje_asistencia", 0.0)

                self.lbl_contador_grande.setText(f"Ingresados: {ingresados} / {total} ({porcentaje}%)")
                self.progress_asistencia.setValue(int(porcentaje))

                ultimos = data.get("ultimos_ingresos", [])
                self.tabla_ultimos.setRowCount(len(ultimos))
                for row, item in enumerate(ultimos):
                    self.tabla_ultimos.setItem(row, 0, QTableWidgetItem(item.get("hora", "")))
                    self.tabla_ultimos.setItem(row, 1, QTableWidgetItem(item.get("metodo", "")))
                    self.tabla_ultimos.setItem(row, 2, QTableWidgetItem(item.get("resultado", "")))
                    self.tabla_ultimos.setItem(row, 3, QTableWidgetItem(item.get("estacion", "")))
        except Exception:
            pass

    def _construir_tab_contador(self):
        # ═══ TAB 2: CONTADOR EN VIVO ═══
        tab_contador = QWidget()
        layout_cont = QVBoxLayout(tab_contador)
        layout_cont.setContentsMargins(16, 16, 16, 16)
        layout_cont.setSpacing(14)

        self.lbl_contador_grande = QLabel("Ingresados: 0 / 0 (0%)")
        self.lbl_contador_grande.setAlignment(Qt.AlignCenter)
        self.lbl_contador_grande.setStyleSheet(
            "font-size: 30px; font-weight: 900; color: #0F2C59; "
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; "
            "border-radius: 10px; padding: 20px;"
        )
        layout_cont.addWidget(self.lbl_contador_grande)

        self.progress_asistencia = QProgressBar()
        self.progress_asistencia.setFixedHeight(24)
        self.progress_asistencia.setStyleSheet("""
            QProgressBar {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                font-size: 12px;
                background-color: #F1F5F9;
            }
            QProgressBar::chunk {
                background-color: #16A34A;
                border-radius: 7px;
            }
        """)
        layout_cont.addWidget(self.progress_asistencia)

        self.tabla_contadores = QTableWidget(0, 4)
        self.tabla_contadores.setHorizontalHeaderLabels([
            "Examen", "Ingresados", "Pendientes", "Asistencia"
        ])
        self.tabla_contadores.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_contadores.setAlternatingRowColors(True)
        layout_cont.addWidget(self.tabla_contadores)

        lbl_historial = QLabel("Últimos ingresos registrados:")
        lbl_historial.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F2C59;")
        layout_cont.addWidget(lbl_historial)

        self.tabla_ultimos = QTableWidget(0, 4)
        self.tabla_ultimos.setHorizontalHeaderLabels(["Hora", "Método", "Resultado", "Cliente"])
        self.tabla_ultimos.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla_ultimos.setAlternatingRowColors(True)
        layout_cont.addWidget(self.tabla_ultimos)

        self.tabs.addTab(tab_contador, "Contador en Vivo")


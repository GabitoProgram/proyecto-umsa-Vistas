from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2


class DialogGestion(QDialog):
    def __init__(self, gestion=None, parent=None):
        super().__init__(parent)
        self.gestion = gestion or {}
        self.setWindowTitle("Editar Gestión" if gestion else "Nueva Gestión")
        self.setFixedSize(400, 380)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        
        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)
        
        form = QFormLayout()
        self.txt_nombre = QLineEdit(self.gestion.get("nombre", ""))
        self.spin_anio = QLineEdit(str(self.gestion.get("anio", date.today().year)))
        self.combo_periodo = QComboBox()
        self.combo_periodo.addItems(["I", "II", "ANUAL"])
        if "periodo" in self.gestion:
            self.combo_periodo.setCurrentText(self.gestion["periodo"])
        self.txt_inicio = QLineEdit(self.gestion.get("fecha_inicio", ""))
        self.txt_inicio.setPlaceholderText("YYYY-MM-DD")
        self.txt_fin = QLineEdit(self.gestion.get("fecha_fin", ""))
        self.txt_fin.setPlaceholderText("YYYY-MM-DD")
        
        for w in [self.txt_nombre, self.spin_anio, self.combo_periodo, self.txt_inicio, self.txt_fin]:
            w.setMinimumHeight(34)
            
        form.addRow("Nombre *:", self.txt_nombre)
        form.addRow("Año *:", self.spin_anio)
        form.addRow("Periodo:", self.combo_periodo)
        form.addRow("Fecha Inicio *:", self.txt_inicio)
        form.addRow("Fecha Fin *:", self.txt_fin)
        
        layout.addLayout(form)
        layout.addStretch()
        
        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("BtnPrimario")
        btn_save.clicked.connect(self.accept)
        for b in [btn_cancel, btn_save]:
            b.setMinimumHeight(38)
            b.setCursor(Qt.PointingHandCursor)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)
        
    def get_data(self):
        return {
            "nombre": self.txt_nombre.text().strip(),
            "anio": int(self.spin_anio.text().strip() or date.today().year),
            "periodo": self.combo_periodo.currentText(),
            "fecha_inicio": self.txt_inicio.text().strip(),
            "fecha_fin": self.txt_fin.text().strip(),
            "estado": self.gestion.get("estado", "ACTIVO") if self.gestion else "ACTIVO"
        }

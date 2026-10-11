from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2


class DialogCarrera(QDialog):
    def __init__(self, carrera=None, parent=None):
        super().__init__(parent)
        self.carrera = carrera or {}
        self.setWindowTitle("Editar Carrera" if carrera else "Nueva Carrera")
        self.setFixedSize(400, 250)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        
        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)
        
        form = QFormLayout()
        self.txt_nombre = QLineEdit(self.carrera.get("nombre", ""))
        self.txt_codigo = QLineEdit(self.carrera.get("codigo", ""))
        for w in [self.txt_nombre, self.txt_codigo]:
            w.setMinimumHeight(34)
            
        form.addRow("Nombre *:", self.txt_nombre)
        form.addRow("Código *:", self.txt_codigo)
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
            "codigo": self.txt_codigo.text().strip(),
            "activa": self.carrera.get("activa", True) if self.carrera else True
        }

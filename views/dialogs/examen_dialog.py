from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2


class DialogExamen(QDialog):
    def __init__(self, examen=None, gestion_id=None, carrera_id=None, parent=None):
        super().__init__(parent)
        self.examen = examen or {"id_gestion": gestion_id, "id_carrera": carrera_id}
        self.setWindowTitle("Editar Examen" if examen else "Nuevo Examen")
        self.setFixedSize(400, 380)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        
        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)
        
        form = QFormLayout()
        self.txt_materia = QLineEdit(self.examen.get("materia", ""))
        self.txt_fecha = QLineEdit(self.examen.get("fecha", ""))
        self.txt_fecha.setPlaceholderText("YYYY-MM-DD")
        self.txt_inicio = QLineEdit(self.examen.get("hora_inicio", ""))
        self.txt_inicio.setPlaceholderText("HH:MM")
        self.txt_fin = QLineEdit(self.examen.get("hora_fin", ""))
        self.txt_fin.setPlaceholderText("HH:MM")
        
        for w in [self.txt_materia, self.txt_fecha, self.txt_inicio, self.txt_fin]:
            w.setMinimumHeight(34)
            
        form.addRow("Materia *:", self.txt_materia)
        form.addRow("Fecha *:", self.txt_fecha)
        form.addRow("Hora Inicio *:", self.txt_inicio)
        form.addRow("Hora Fin *:", self.txt_fin)
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
        d = dict(self.examen)
        # id_examen no es parte del schema de actualización; se ignora en el backend
        d.pop("id_examen", None)
        d.update({
            "materia": self.txt_materia.text().strip(),
            "fecha": self.txt_fecha.text().strip(),
            "hora_inicio": self.txt_inicio.text().strip(),
            "hora_fin": self.txt_fin.text().strip(),
        })
        # Al crear no existe estado/tolerancia; al editar se conservan los actuales
        d.setdefault("estado", "PROGRAMADO")
        d.setdefault("tolerancia_minutos", 10)
        return d

from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2


class DialogCapturaRostro(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Captura de Rostro")
        self.setFixedSize(640, 520)
        self.imagen_capturada = None
        self.cap = None
        
        self.init_ui()
        self.iniciar_camara()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)
        
        lbl_tit = QLabel("Toma de fotografía facial")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: bold; color: #0F2C59;")
        layout.addWidget(lbl_tit)
        
        self.visor = QLabel("Iniciando cámara...")
        self.visor.setAlignment(Qt.AlignCenter)
        self.visor.setFixedSize(600, 400)
        self.visor.setStyleSheet("background-color: #0F172A; color: white; border-radius: 8px;")
        layout.addWidget(self.visor)
        
        btn_box = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)
        
        self.btn_capturar = QPushButton("Tomar Foto [Espacio]")
        self.btn_capturar.setObjectName("BtnPrimario")
        self.btn_capturar.setMinimumHeight(40)
        self.btn_capturar.setCursor(Qt.PointingHandCursor)
        self.btn_capturar.clicked.connect(self.capturar)
        
        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancelar)
        btn_box.addWidget(self.btn_capturar)
        layout.addLayout(btn_box)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_frame)
        
    def iniciar_camara(self):
        # Probar varios índices por si la cámara principal está ocupada
        self.cap = None
        for indice in (0, 1, 2):
            cap = cv2.VideoCapture(indice)
            if cap.isOpened():
                self.cap = cap
                break
            cap.release()
        if self.cap is None or not self.cap.isOpened():
            self.cap = None
            self.visor.setText(
                "No se pudo acceder a la cámara.\n"
                "Verifique que no esté en uso por otra aplicación\ny vuelva a intentarlo."
            )
            self.btn_capturar.setEnabled(False)
        else:
            self.timer.start(30)
            
    def actualizar_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                h, w, _ = frame.shape
                # Guía centrada
                cv2.rectangle(frame, (w//4, h//6), (3*w//4, 5*h//6), (37, 99, 235), 2)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, 3*w, QImage.Format_RGB888)
                self.visor.setPixmap(QPixmap.fromImage(qimg).scaled(600, 400, Qt.KeepAspectRatio))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Space:
            self.capturar()
        else:
            super().keyPressEvent(event)

    def capturar(self):
        if not self.cap or not self.cap.isOpened():
            QMessageBox.warning(
                self, "Cámara no disponible",
                "No se pudo acceder a la cámara. Cierre otras aplicaciones que la usen "
                "(o el registro de check-in) y vuelva a intentarlo."
            )
            return
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(
                self, "Captura fallida",
                "No se pudo leer la imagen de la cámara. Intente nuevamente."
            )
            return
        ok, encoded = cv2.imencode('.jpg', frame)
        if not ok:
            QMessageBox.warning(
                self, "Captura fallida",
                "No se pudo codificar la imagen capturada. Intente nuevamente."
            )
            return
        self.imagen_capturada = encoded.tobytes()
        self.accept()
                    
    def closeEvent(self, event):
        self.detener_camara()
        super().closeEvent(event)
        
    def reject(self):
        self.detener_camara()
        super().reject()
        
    def accept(self):
        self.detener_camara()
        super().accept()
        
    def detener_camara(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

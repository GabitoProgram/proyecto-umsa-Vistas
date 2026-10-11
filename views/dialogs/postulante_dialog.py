from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2


class DialogEditarPostulante(QDialog):
    def __init__(self, postulante, parent=None, carreras_texto=None):
        super().__init__(parent)
        self.postulante = postulante
        self.carreras_texto = carreras_texto
        self.setWindowTitle("Editar Postulante")
        self.setFixedSize(450, 640 if carreras_texto else 580)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_tit = QLabel("Editar Datos del Postulante")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_nombres = QLineEdit(self.postulante.get("nombres", ""))
        self.txt_nombres.setMinimumHeight(36)

        self.txt_apellidos = QLineEdit(self.postulante.get("apellidos", ""))
        self.txt_apellidos.setMinimumHeight(36)
        
        self.combo_genero = QComboBox()
        self.combo_genero.addItems(["MASCULINO", "FEMENINO"])
        self.combo_genero.setMinimumHeight(36)
        genero_actual = self.postulante.get("genero", "MASCULINO")
        index_gen = self.combo_genero.findText(genero_actual)
        if index_gen >= 0:
            self.combo_genero.setCurrentIndex(index_gen)

        self.txt_telefono = QLineEdit(str(self.postulante.get("telefono") or ""))
        self.txt_telefono.setMinimumHeight(36)

        self.txt_correo = QLineEdit(str(self.postulante.get("correo") or ""))
        self.txt_correo.setPlaceholderText("Opcional")
        self.txt_correo.setMinimumHeight(36)

        self.txt_direccion = QLineEdit(str(self.postulante.get("direccion") or ""))
        self.txt_direccion.setPlaceholderText("Opcional")
        self.txt_direccion.setMinimumHeight(36)

        form.addRow("Nombres *:", self.txt_nombres)
        form.addRow("Apellidos *:", self.txt_apellidos)
        form.addRow("Género:", self.combo_genero)
        form.addRow("Teléfono:", self.txt_telefono)
        form.addRow("Correo:", self.txt_correo)
        form.addRow("Dirección:", self.txt_direccion)

        layout.addLayout(form)
        layout.addSpacing(12)

        # Carreras inscritas en la gestión (solo lectura)
        if self.carreras_texto:
            lbl_carr = QLabel("Carreras inscritas en esta gestión:")
            lbl_carr.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
            layout.addWidget(lbl_carr)
            lbl_carr_val = QLabel(self.carreras_texto)
            lbl_carr_val.setWordWrap(True)
            lbl_carr_val.setStyleSheet(
                "font-size: 13px; color: #0F2C59; background-color: #F1F5F9; "
                "border: 1px solid #E2E8F0; border-radius: 6px; padding: 8px 10px;"
            )
            layout.addWidget(lbl_carr_val)
            layout.addSpacing(12)
        
        # Biometric editing options
        lbl_bio = QLabel("Actualizar Biometría:")
        lbl_bio.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
        layout.addWidget(lbl_bio)
        
        bio_box = QHBoxLayout()
        self.btn_rostro = QPushButton("Actualizar Rostro")
        self.btn_rostro.setMinimumHeight(38)
        self.btn_rostro.setCursor(Qt.PointingHandCursor)
        self.btn_rostro.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.btn_rostro.clicked.connect(self.actualizar_rostro)
        
        self.btn_huella = QPushButton("Actualizar Huella")
        self.btn_huella.setMinimumHeight(38)
        self.btn_huella.setCursor(Qt.PointingHandCursor)
        self.btn_huella.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.btn_huella.clicked.connect(self.actualizar_huella)
        
        bio_box.addWidget(self.btn_rostro)
        bio_box.addWidget(self.btn_huella)
        layout.addLayout(bio_box)
        
        layout.addSpacing(16)

        btn_box = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Guardar Cambios")
        self.btn_guardar.setObjectName("BtnPrimario")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self.accept)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancelar)
        btn_box.addWidget(self.btn_guardar)
        layout.addLayout(btn_box)

    def actualizar_rostro(self):
        if self.parent() and hasattr(self.parent(), 'registrar_rostro_gestion'):
            self.parent().registrar_rostro_gestion(self.postulante, self.btn_rostro)
            
    def actualizar_huella(self):
        if self.parent() and hasattr(self.parent(), 'registrar_huella_gestion'):
            self.parent().registrar_huella_gestion(self.postulante, self.btn_huella)

    def get_data(self):
        return {
            "nombres": self.txt_nombres.text().strip(),
            "apellidos": self.txt_apellidos.text().strip(),
            "genero": self.combo_genero.currentText(),
            "telefono": self.txt_telefono.text().strip() or None,
            "correo": self.txt_correo.text().strip() or None,
            "direccion": self.txt_direccion.text().strip() or None,
        }


class DialogNuevoPostulanteGestion(QDialog):
    """Crea un postulante y permite elegir hasta 2 carreras de la gestión."""

    def __init__(self, carreras, parent=None):
        super().__init__(parent)
        self.carreras = carreras or []
        self.checks = {}
        self.setWindowTitle("Nuevo postulante")
        self.setFixedSize(480, 640)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(12)

        lbl_tit = QLabel("Datos del Postulante")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_ci = QLineEdit()
        self.txt_ci.setPlaceholderText("Ej: 8472910")
        self.txt_nombres = QLineEdit()
        self.txt_apellidos = QLineEdit()
        self.combo_genero = QComboBox()
        self.combo_genero.addItems(["MASCULINO", "FEMENINO"])
        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Opcional")
        self.txt_correo = QLineEdit()
        self.txt_correo.setPlaceholderText("Opcional")
        self.txt_direccion = QLineEdit()
        self.txt_direccion.setPlaceholderText("Opcional")
        for w in (self.txt_ci, self.txt_nombres, self.txt_apellidos, self.combo_genero,
                  self.txt_telefono, self.txt_correo, self.txt_direccion):
            w.setMinimumHeight(36)

        form.addRow("C.I. *:", self.txt_ci)
        form.addRow("Nombres *:", self.txt_nombres)
        form.addRow("Apellidos *:", self.txt_apellidos)
        form.addRow("Género:", self.combo_genero)
        form.addRow("Teléfono:", self.txt_telefono)
        form.addRow("Correo:", self.txt_correo)
        form.addRow("Dirección:", self.txt_direccion)
        layout.addLayout(form)

        lbl_carr = QLabel("Carreras (elija 1 o 2):")
        lbl_carr.setStyleSheet("font-size: 14px; font-weight: bold; color: #475569;")
        layout.addWidget(lbl_carr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(150)
        contenedor = QWidget()
        cont_layout = QVBoxLayout(contenedor)
        cont_layout.setContentsMargins(4, 4, 4, 4)
        cont_layout.setSpacing(6)
        for carrera in self.carreras:
            check = QCheckBox(carrera.get("nombre", "Carrera"))
            check.stateChanged.connect(self._limitar_seleccion)
            self.checks[carrera.get("id_carrera")] = check
            cont_layout.addWidget(check)
        cont_layout.addStretch()
        scroll.setWidget(contenedor)
        layout.addWidget(scroll)

        self.lbl_aviso = QLabel("Máximo 2 carreras por gestión.")
        self.lbl_aviso.setStyleSheet("font-size: 11px; color: #94A3B8;")
        layout.addWidget(self.lbl_aviso)

        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Registrar")
        btn_save.setObjectName("BtnPrimario")
        btn_save.clicked.connect(self.accept)
        for b in (btn_cancel, btn_save):
            b.setMinimumHeight(40)
            b.setCursor(Qt.PointingHandCursor)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def _limitar_seleccion(self):
        marcados = [c for c in self.checks.values() if c.isChecked()]
        if len(marcados) >= 2:
            for check in self.checks.values():
                if not check.isChecked():
                    check.setEnabled(False)
        else:
            for check in self.checks.values():
                check.setEnabled(True)

    def carreras_seleccionadas(self):
        return [
            id_carrera for id_carrera, check in self.checks.items()
            if check.isChecked()
        ]

    def get_data(self):
        return {
            "ci": self.txt_ci.text().strip(),
            "nombres": self.txt_nombres.text().strip(),
            "apellidos": self.txt_apellidos.text().strip(),
            "genero": self.combo_genero.currentText(),
            "telefono": self.txt_telefono.text().strip() or None,
            "correo": self.txt_correo.text().strip() or None,
            "direccion": self.txt_direccion.text().strip() or None,
        }

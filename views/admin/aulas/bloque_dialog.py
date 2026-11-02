from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt


class DialogBloque(QDialog):
    """Diálogo para crear o editar un bloque (edificio)."""

    def __init__(self, bloque=None, parent=None):
        super().__init__(parent)
        self.bloque = bloque or {}
        self.setWindowTitle("Editar Bloque" if bloque else "Nuevo Bloque")
        self.setFixedSize(440, 380)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_nombre = QLineEdit(self.bloque.get("nombre", ""))
        self.txt_nombre.setPlaceholderText("Ej: Bloque A")
        self.txt_nombre.setMinimumHeight(36)

        self.txt_direccion = QLineEdit(self.bloque.get("direccion") or "")
        self.txt_direccion.setPlaceholderText("Ej: Av. Arce N° 123")
        self.txt_direccion.setMinimumHeight(36)

        self.txt_referencia = QLineEdit(self.bloque.get("referencia") or "")
        self.txt_referencia.setPlaceholderText("Ej: Frente a la plaza, portón azul")
        self.txt_referencia.setMinimumHeight(36)

        self.chk_activo = QCheckBox("Bloque activo")
        self.chk_activo.setChecked(bool(self.bloque.get("activo", True)))

        form.addRow("Nombre *:", self.txt_nombre)
        form.addRow("Dirección:", self.txt_direccion)
        form.addRow("Referencia:", self.txt_referencia)
        form.addRow("", self.chk_activo)
        layout.addLayout(form)
        layout.addStretch()

        btn_box = QHBoxLayout()
        btn_cancel = QPushButton("Cancelar")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("BtnPrimario")
        btn_save.clicked.connect(self.accept)
        for b in (btn_cancel, btn_save):
            b.setMinimumHeight(40)
            b.setCursor(Qt.PointingHandCursor)
        btn_box.addStretch()
        btn_box.addWidget(btn_cancel)
        btn_box.addWidget(btn_save)
        layout.addLayout(btn_box)

    def get_data(self):
        return {
            "nombre": self.txt_nombre.text().strip(),
            "direccion": self.txt_direccion.text().strip() or None,
            "referencia": self.txt_referencia.text().strip() or None,
            "activo": self.chk_activo.isChecked(),
        }

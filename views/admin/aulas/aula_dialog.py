from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt


class DialogAula(QDialog):
    """Diálogo para crear o editar un aula."""

    def __init__(self, aula=None, parent=None):
        super().__init__(parent)
        self.aula = aula or {}
        self.setWindowTitle("Editar Aula" if aula else "Nueva Aula")
        self.setFixedSize(420, 360)
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

        self.txt_nombre = QLineEdit(self.aula.get("nombre", ""))
        self.txt_nombre.setPlaceholderText("Ej: Aula 101")
        self.txt_nombre.setMinimumHeight(36)

        self.txt_ubicacion = QLineEdit(self.aula.get("ubicacion") or "")
        self.txt_ubicacion.setPlaceholderText("Ej: Piso 2 - Bloque B")
        self.txt_ubicacion.setMinimumHeight(36)

        self.spin_capacidad = QSpinBox()
        self.spin_capacidad.setRange(1, 1000)
        self.spin_capacidad.setValue(int(self.aula.get("capacidad", 30) or 30))
        self.spin_capacidad.setMinimumHeight(36)
        if self.aula:
            self.spin_capacidad.setToolTip(
                "Al guardar, la cantidad de asientos se ajustará a esta capacidad "
                "(se agregan o quitan asientos automáticamente)."
            )

        self.chk_activa = QCheckBox("Aula activa")
        self.chk_activa.setChecked(bool(self.aula.get("activa", True)))

        self.chk_asientos = QCheckBox("Generar asientos automáticamente (1 por capacidad)")
        # Solo tiene sentido al crear; al editar se oculta
        self.chk_asientos.setChecked(True)
        self.chk_asientos.setVisible(not self.aula)
        if not self.aula:
            self.chk_asientos.setToolTip(
                "Si se marca, se crean asientos numerados del 1 a la capacidad."
            )

        form.addRow("Nombre *:", self.txt_nombre)
        form.addRow("Ubicación:", self.txt_ubicacion)
        form.addRow("Capacidad *:", self.spin_capacidad)
        form.addRow("", self.chk_activa)
        if not self.aula:
            form.addRow("", self.chk_asientos)
        layout.addLayout(form)

        if self.aula:
            lbl_nota = QLabel(
                "Nota: al guardar, los asientos se ajustarán automáticamente a la capacidad indicada."
            )
            lbl_nota.setWordWrap(True)
            lbl_nota.setStyleSheet("font-size: 11px; color: #94A3B8;")
            layout.addWidget(lbl_nota)

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
        data = {
            "nombre": self.txt_nombre.text().strip(),
            "ubicacion": self.txt_ubicacion.text().strip() or None,
            "capacidad": self.spin_capacidad.value(),
            "activa": self.chk_activa.isChecked(),
        }
        if not self.aula:
            data["generar_asientos_auto"] = self.chk_asientos.isChecked()
        return data

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QFormLayout
)
from PySide6.QtCore import Qt


class _SpinNumeroPiso(QSpinBox):
    """SpinBox que salta los números de piso ya ocupados en el bloque."""

    def __init__(self, ocupados, parent=None):
        super().__init__(parent)
        self._ocupados = set(ocupados)
        self.setRange(0, 100)

    def _libre(self, inicio, direccion=1):
        minimo, maximo = self.minimum(), self.maximum()
        valor = min(max(int(inicio), minimo), maximo)
        if direccion >= 0:
            rango = range(valor, maximo + 1)
        else:
            rango = range(valor, minimo - 1, -1)
        for numero in rango:
            if numero not in self._ocupados:
                return numero
        for numero in range(minimo, maximo + 1):
            if numero not in self._ocupados:
                return numero
        return valor

    def primer_libre(self, desde=0):
        return self._libre(desde, 1)

    def stepBy(self, steps):
        if steps:
            self.setValue(
                self._libre(self.value() + steps, 1 if steps > 0 else -1)
            )

    def valueFromText(self, text):
        return self._libre(super().valueFromText(text), 1)


class DialogPiso(QDialog):
    """Diálogo para crear o editar un piso dentro de un bloque."""

    def __init__(self, piso=None, parent=None, bloque=None):
        super().__init__(parent)
        self.piso = piso or {}
        self.bloque = bloque or {}
        self.setWindowTitle("Editar Piso" if piso else "Nuevo Piso")
        self.setFixedSize(440, 430)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_tit = QLabel(self.windowTitle())
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        nombre_bloque = self.bloque.get("nombre")
        if nombre_bloque:
            lbl_bloque = QLabel(f"Bloque: {nombre_bloque}")
            lbl_bloque.setStyleSheet("font-size: 12px; color: #64748B; font-weight: 600;")
            layout.addWidget(lbl_bloque)

        form = QFormLayout()
        form.setSpacing(10)

        id_actual = self.piso.get("id_piso")
        ocupados = set()
        for otro in (self.bloque.get("pisos") or []):
            if id_actual is not None and otro.get("id_piso") == id_actual:
                continue
            try:
                ocupados.add(int(otro.get("numero")))
            except (TypeError, ValueError):
                continue

        self.spin_numero = _SpinNumeroPiso(ocupados)
        numero_actual = int(self.piso.get("numero", 1) or 1)
        self.spin_numero.setValue(self.spin_numero.primer_libre(numero_actual))
        self.spin_numero.setMinimumHeight(36)

        self.txt_nombre = QLineEdit(self.piso.get("nombre") or "")
        self.txt_nombre.setPlaceholderText("Ej: Planta baja, Piso 1")
        self.txt_nombre.setMinimumHeight(36)

        self.txt_descripcion = QLineEdit(self.piso.get("descripcion") or "")
        self.txt_descripcion.setPlaceholderText("Opcional")
        self.txt_descripcion.setMinimumHeight(36)

        self.chk_activo = QCheckBox("Piso activo")
        self.chk_activo.setChecked(bool(self.piso.get("activo", True)))

        form.addRow("Número *:", self.spin_numero)
        form.addRow("Nombre:", self.txt_nombre)
        form.addRow("Descripción:", self.txt_descripcion)
        form.addRow("", self.chk_activo)
        if ocupados:
            lbl_ocupados = QLabel(
                "Ya usados: " + ", ".join(str(n) for n in sorted(ocupados))
            )
            lbl_ocupados.setWordWrap(True)
            lbl_ocupados.setStyleSheet(
                "font-size: 12px; color: #64748B; font-weight: 600;"
            )
            form.addRow("", lbl_ocupados)
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
            "numero": self.spin_numero.value(),
            "nombre": self.txt_nombre.text().strip() or None,
            "descripcion": self.txt_descripcion.text().strip() or None,
            "activo": self.chk_activo.isChecked(),
        }

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox,
    QCheckBox, QPushButton, QFormLayout, QComboBox
)
from PySide6.QtCore import Qt


class DialogAula(QDialog):
    """Diálogo para crear o editar un aula dentro de un piso."""

    def __init__(self, aula=None, parent=None, bloques=None, id_piso=None):
        super().__init__(parent)
        self.aula = aula or {}
        self.bloques = bloques or []
        self.id_piso_inicial = (
            id_piso if id_piso is not None else self.aula.get("id_piso")
        )
        self.setWindowTitle("Editar Aula" if aula else "Nueva Aula")
        self.setFixedSize(460, 460)
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

        self.combo_bloque = QComboBox()
        self.combo_bloque.setMinimumHeight(36)
        self.combo_piso = QComboBox()
        self.combo_piso.setMinimumHeight(36)

        for bloque in self.bloques:
            self.combo_bloque.addItem(
                str(bloque.get("nombre", "")), userData=bloque
            )

        self.txt_nombre = QLineEdit(self.aula.get("nombre", ""))
        self.txt_nombre.setPlaceholderText("Ej: Aula 101")
        self.txt_nombre.setMinimumHeight(36)

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
        self.chk_asientos.setChecked(True)
        self.chk_asientos.setVisible(not self.aula)
        if not self.aula:
            self.chk_asientos.setToolTip(
                "Si se marca, se crean asientos numerados del 1 a la capacidad."
            )

        form.addRow("Bloque *:", self.combo_bloque)
        form.addRow("Piso *:", self.combo_piso)
        form.addRow("Nombre *:", self.txt_nombre)
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

        self.combo_bloque.currentIndexChanged.connect(self._cargar_pisos)
        self._seleccionar_bloque_inicial()

    def _seleccionar_bloque_inicial(self):
        id_bloque = self.aula.get("id_bloque")
        if id_bloque is None and self.id_piso_inicial is not None:
            for bloque in self.bloques:
                if any(
                    piso.get("id_piso") == self.id_piso_inicial
                    for piso in bloque.get("pisos", [])
                ):
                    id_bloque = bloque.get("id_bloque")
                    break
        indice = -1
        if id_bloque is not None:
            for i in range(self.combo_bloque.count()):
                bloque = self.combo_bloque.itemData(i)
                if bloque and bloque.get("id_bloque") == id_bloque:
                    indice = i
                    break
        self.combo_bloque.setCurrentIndex(indice if indice >= 0 else 0)
        self._cargar_pisos()

    def _cargar_pisos(self):
        bloque = self.combo_bloque.currentData()
        self.combo_piso.clear()
        if not bloque:
            return
        for piso in bloque.get("pisos", []):
            etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
            self.combo_piso.addItem(etiqueta, userData=piso)
        indice = -1
        if self.id_piso_inicial is not None:
            for i in range(self.combo_piso.count()):
                piso = self.combo_piso.itemData(i)
                if piso and piso.get("id_piso") == self.id_piso_inicial:
                    indice = i
                    break
        if indice >= 0:
            self.combo_piso.setCurrentIndex(indice)

    def get_data(self):
        piso = self.combo_piso.currentData()
        data = {
            "nombre": self.txt_nombre.text().strip(),
            "id_piso": piso.get("id_piso") if piso else None,
            "capacidad": self.spin_capacidad.value(),
            "activa": self.chk_activa.isChecked(),
        }
        if not self.aula:
            data["generar_asientos_auto"] = self.chk_asientos.isChecked()
        return data

import os
import unicodedata
import pandas as pd
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialog, QFormLayout,
    QMessageBox, QFileDialog, QFrame, QComboBox
)
from PySide6.QtCore import Qt, QThread, Signal
from desktop.api.client import api

class DialogNuevoPostulante(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Registrar Nuevo Postulante")
        self.setFixedSize(450, 400)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_tit = QLabel("Datos del Postulante")
        lbl_tit.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_tit)

        form = QFormLayout()
        form.setSpacing(10)

        self.txt_ci = QLineEdit()
        self.txt_ci.setPlaceholderText("Ej: 8472910")
        self.txt_ci.setMinimumHeight(36)

        self.txt_nombres = QLineEdit()
        self.txt_nombres.setPlaceholderText("Ej: Juan Carlos")
        self.txt_nombres.setMinimumHeight(36)

        self.txt_apellidos = QLineEdit()
        self.txt_apellidos.setPlaceholderText("Ej: Pérez Mamani")
        self.txt_apellidos.setMinimumHeight(36)

        self.combo_genero = QComboBox()
        self.combo_genero.addItems(["MASCULINO", "FEMENINO"])
        self.combo_genero.setMinimumHeight(36)

        self.txt_telefono = QLineEdit()
        self.txt_telefono.setPlaceholderText("Ej: 71234567 (Opcional)")
        self.txt_telefono.setMinimumHeight(36)

        form.addRow("C.I. *:", self.txt_ci)
        form.addRow("Nombres *:", self.txt_nombres)
        form.addRow("Apellidos *:", self.txt_apellidos)
        form.addRow("Género:", self.combo_genero)
        form.addRow("Teléfono:", self.txt_telefono)

        layout.addLayout(form)
        layout.addSpacing(12)

        btn_box = QHBoxLayout()
        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setMinimumHeight(40)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.reject)

        self.btn_guardar = QPushButton("Registrar")
        self.btn_guardar.setObjectName("BtnPrimario")
        self.btn_guardar.setFixedHeight(40)
        self.btn_guardar.setCursor(Qt.PointingHandCursor)
        self.btn_guardar.clicked.connect(self.guardar)

        btn_box.addStretch()
        btn_box.addWidget(self.btn_cancelar)
        btn_box.addWidget(self.btn_guardar)
        layout.addLayout(btn_box)

    def guardar(self):
        ci = self.txt_ci.text().strip()
        nombres = self.txt_nombres.text().strip()
        apellidos = self.txt_apellidos.text().strip()

        if not ci or not nombres or not apellidos:
            QMessageBox.warning(self, "Campos Requeridos", "Complete todos los campos marcados con (*).")
            return

        payload = {
            "ci": ci,
            "nombres": nombres,
            "apellidos": apellidos,
            "genero": self.combo_genero.currentText(),
            "telefono": self.txt_telefono.text().strip() or None
        }

        data, status = api.crear_postulante(payload)
        if status in [200, 201]:
            QMessageBox.information(self, "Éxito", f"Postulante {nombres} {apellidos} registrado correctamente.")
            self.accept()
        else:
            detalle = data.get("detail", str(data))
            QMessageBox.critical(self, "Error al registrar", f"El servidor respondió:\n{detalle}")


class ExcelImportThread(QThread):
    finalizado = Signal(bool, str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        res, status = api.importar_excel_postulantes(self.file_path)
        if status in [200, 201]:
            msg = res.get("mensaje", "Importación completada con éxito.")
            self.finalizado.emit(True, msg)
        else:
            err = res.get("detail", "Error al procesar el archivo en el servidor.")
            self.finalizado.emit(False, str(err))


class PostulantesView(QWidget):
    def __init__(self):
        super().__init__()
        self.postulantes_data = []
        self.init_ui()
        self.cargar_postulantes()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(16)

        # Header con título y botones de acción
        header_layout = QHBoxLayout()
        lbl_titulo = QLabel("Gestión de Postulantes")
        lbl_titulo.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")

        self.btn_nuevo = QPushButton("+ Nuevo Postulante")
        self.btn_nuevo.setObjectName("BtnPrimario")
        self.btn_nuevo.setFixedHeight(40)
        self.btn_nuevo.setCursor(Qt.PointingHandCursor)
        self.btn_nuevo.clicked.connect(self.abrir_modal_nuevo)

        self.btn_excel = QPushButton("Carga Masiva (Excel)")
        self.btn_excel.setObjectName("BtnExito")
        self.btn_excel.setFixedHeight(40)
        self.btn_excel.setCursor(Qt.PointingHandCursor)
        self.btn_excel.clicked.connect(self.importar_excel)

        header_layout.addWidget(lbl_titulo)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_excel)
        header_layout.addSpacing(8)
        header_layout.addWidget(self.btn_nuevo)
        layout.addLayout(header_layout)

        # Barra de filtro
        filtro_layout = QHBoxLayout()
        filtro_layout.setSpacing(10)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("Buscar por C.I., nombres o apellidos...")
        self.txt_buscar.setMinimumHeight(40)
        self.txt_buscar.textChanged.connect(self.filtrar_tabla)

        self.lbl_resultados = QLabel("0 postulantes")
        self.lbl_resultados.setStyleSheet("color: #64748B; font-size: 12px;")

        self.btn_refrescar = QPushButton("Actualizar")
        self.btn_refrescar.setFixedHeight(40)
        self.btn_refrescar.setCursor(Qt.PointingHandCursor)
        self.btn_refrescar.clicked.connect(self.cargar_postulantes)

        filtro_layout.addWidget(self.txt_buscar)
        filtro_layout.addWidget(self.lbl_resultados)
        filtro_layout.addWidget(self.btn_refrescar)
        layout.addLayout(filtro_layout)

        # Tabla de postulantes
        self.tabla = QTableWidget()
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "ID", "C.I.", "Nombre Completo", "Teléfono", "Biometría Facial", "Biometría Dactilar"
        ])
        self.tabla.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tabla.setSelectionBehavior(QTableWidget.SelectRows)
        self.tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        layout.addWidget(self.tabla)

    def cargar_postulantes(self):
        self.btn_refrescar.setEnabled(False)
        self.postulantes_data = api.listar_postulantes(limit=1000)
        self.poblar_tabla(self.postulantes_data)
        self.btn_refrescar.setEnabled(True)

    def poblar_tabla(self, lista):
        self.tabla.setRowCount(0)
        self.lbl_resultados.setText(
            f"{len(lista)} postulante{'s' if len(lista) != 1 else ''}"
        )
        for row_idx, p in enumerate(lista):
            self.tabla.insertRow(row_idx)

            id_val = str(p.get("id_postulante", ""))
            ci_val = str(p.get("ci", ""))
            nombre = f"{p.get('nombres', '')} {p.get('apellidos', '')}".strip()
            telefono = str(p.get("telefono") or "---")

            tiene_rostro = p.get("tiene_rostro", False)
            rostro_registrado = p.get("rostro_registrado", tiene_rostro)
            cant_huellas = p.get("cantidad_huellas", 0)

            item_id = QTableWidgetItem(id_val)
            item_id.setTextAlignment(Qt.AlignCenter)
            item_ci = QTableWidgetItem(ci_val)
            item_ci.setTextAlignment(Qt.AlignCenter)
            item_nombre = QTableWidgetItem(nombre)
            item_tel = QTableWidgetItem(telefono)
            item_tel.setTextAlignment(Qt.AlignCenter)

            if tiene_rostro:
                item_face = QTableWidgetItem("HABILITADO")
                item_face.setForeground(Qt.darkGreen)
            elif rostro_registrado:
                item_face = QTableWidgetItem("POR HABILITAR")
                item_face.setForeground(Qt.darkYellow)
            else:
                item_face = QTableWidgetItem("PENDIENTE")
                item_face.setForeground(Qt.darkGray)
            item_face.setTextAlignment(Qt.AlignCenter)

            item_huella = QTableWidgetItem(f"({cant_huellas}/10)" if cant_huellas > 0 else "PENDIENTE")
            item_huella.setTextAlignment(Qt.AlignCenter)
            if cant_huellas >= 2:
                item_huella.setForeground(Qt.darkGreen)
            elif cant_huellas > 0:
                item_huella.setForeground(Qt.darkYellow)
            else:
                item_huella.setForeground(Qt.darkGray)

            self.tabla.setItem(row_idx, 0, item_id)
            self.tabla.setItem(row_idx, 1, item_ci)
            self.tabla.setItem(row_idx, 2, item_nombre)
            self.tabla.setItem(row_idx, 3, item_tel)
            self.tabla.setItem(row_idx, 4, item_face)
            self.tabla.setItem(row_idx, 5, item_huella)

    def filtrar_tabla(self, texto: str):
        texto = self._normalizar_busqueda(texto)
        if not texto:
            self.poblar_tabla(self.postulantes_data)
            return

        filtrados = []
        for p in self.postulantes_data:
            ci = self._normalizar_busqueda(p.get("ci", ""))
            nombres = self._normalizar_busqueda(p.get("nombres", ""))
            apellidos = self._normalizar_busqueda(p.get("apellidos", ""))
            if (
                texto in ci
                or texto in nombres
                or texto in apellidos
                or texto in f"{nombres} {apellidos}"
            ):
                filtrados.append(p)

        self.poblar_tabla(filtrados)

    @staticmethod
    def _normalizar_busqueda(valor):
        texto = str(valor or "").casefold()
        return "".join(
            caracter
            for caracter in unicodedata.normalize("NFD", texto)
            if unicodedata.category(caracter) != "Mn"
        )

    def abrir_modal_nuevo(self):
        dlg = DialogNuevoPostulante(self)
        if dlg.exec():
            self.cargar_postulantes()

    def importar_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel de Postulantes", "", "Archivos Excel (*.xlsx *.xls)"
        )
        if not file_path:
            return

        try:
            df = pd.read_excel(file_path)
            cols_requeridas = {"ci", "nombres", "apellidos"}
            cols_encontradas = {str(c).lower().strip() for c in df.columns}

            if not cols_requeridas.issubset(cols_encontradas):
                QMessageBox.critical(
                    self, "Formato Inválido",
                    f"El archivo debe contener al menos las columnas: {', '.join(cols_requeridas)}.\n"
                    f"Columnas detectadas: {', '.join(df.columns)}"
                )
                return

            confirmacion = QMessageBox.question(
                self, "Confirmar Carga Masiva",
                f"Se detectaron {len(df)} registros en '{os.path.basename(file_path)}'.\n¿Desea importarlos a la base de datos?",
                QMessageBox.Yes | QMessageBox.No
            )

            if confirmacion == QMessageBox.Yes:
                self.btn_excel.setEnabled(False)
                self.btn_excel.setText("Importando...")
                self.thread_import = ExcelImportThread(file_path)
                self.thread_import.finalizado.connect(self.on_importacion_terminada)
                self.thread_import.start()

        except Exception as e:
            QMessageBox.critical(self, "Error de Lectura", f"No se pudo procesar el archivo Excel:\n{str(e)}")

    def on_importacion_terminada(self, exito: bool, mensaje: str):
        self.btn_excel.setEnabled(True)
        self.btn_excel.setText("Carga Masiva (Excel)")
        if exito:
            QMessageBox.information(self, "Importación Exitosa", mensaje)
            self.cargar_postulantes()
        else:
            QMessageBox.critical(self, "Error en la Importación", mensaje)

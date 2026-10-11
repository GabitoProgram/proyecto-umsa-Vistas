import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QMessageBox,
    QLineEdit, QSpinBox, QComboBox, QFileDialog, QDialog, QCheckBox,
    QDialogButtonBox, QInputDialog, QListWidget, QListWidgetItem,
    QScrollArea, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal


class ExamenWorkspaceView(QWidget):
    volver = Signal()

    def __init__(self, examen_data, token_data=None, api_base_url="http://localhost:8000/api/v1", parent=None):
        super().__init__(parent)
        self.examen = examen_data
        self.token_data = token_data or {}
        self.api_base_url = api_base_url
        self.tolerancia_actual = self.examen.get("tolerancia_minutos", 10)
        self.aulas_disponibles = []
        self.carrera_nombre = ""
        self._resolver_carrera()
        self.init_ui()

    def get_auth_headers(self):
        token = self.token_data.get("access_token", "")
        return {"Authorization": f"Bearer {token}"}

    def _resolver_carrera(self):
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/carreras",
                headers=self.get_auth_headers(),
                timeout=4
            )
            if respuesta.status_code == 200:
                id_carrera = self.examen.get("id_carrera")
                for carrera in respuesta.json():
                    if carrera.get("id_carrera") == id_carrera:
                        self.carrera_nombre = carrera.get("nombre", "")
                        break
        except (requests.RequestException, ValueError):
            self.carrera_nombre = ""

    def init_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        contenedor = QWidget()
        main_layout = QVBoxLayout(contenedor)
        main_layout.setContentsMargins(24, 18, 24, 18)
        main_layout.setSpacing(14)

        # Barra superior con botón Volver
        barra_sup = QHBoxLayout()
        btn_volver = QPushButton("← Volver")
        btn_volver.setCursor(Qt.PointingHandCursor)
        btn_volver.setMinimumHeight(38)
        btn_volver.setMinimumWidth(120)
        btn_volver.setStyleSheet(
            "background-color: #F1F5F9; color: #334155; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; font-size: 13px; border: 1px solid #CBD5E1;"
        )
        btn_volver.clicked.connect(self.volver.emit)
        barra_sup.addWidget(btn_volver)
        barra_sup.addStretch()
        main_layout.addLayout(barra_sup)

        main_layout.addWidget(self._crear_header_examen())

        # Pestañas del workspace
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab { font-size: 13px; font-weight: bold; padding: 9px 22px; }
            QTabBar::tab:selected { color: #2563EB; border-bottom: 3px solid #2563EB; }
        """)
        self.tabs.addTab(self._crear_tab_postulantes(), "Postulantes e Inscripción")
        self.tabs.addTab(self._crear_tab_aulas_sorteo(), "Aulas y Sorteo de Asientos")
        main_layout.addWidget(self.tabs, stretch=1)

        scroll.setWidget(contenedor)
        outer.addWidget(scroll)

    def _crear_header_examen(self):
        header_card = QFrame()
        header_card.setObjectName("CardExamen")
        header_card.setStyleSheet("""
            QFrame#CardExamen {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        grid = QGridLayout(header_card)
        grid.setContentsMargins(22, 18, 22, 18)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 0)

        # Fila 0: materia + botón reporte
        lbl_materia = QLabel(self.examen.get("materia", "Examen"))
        lbl_materia.setStyleSheet("font-size: 22px; font-weight: 900; color: #0F2C59;")
        lbl_materia.setWordWrap(True)
        grid.addWidget(lbl_materia, 0, 0)

        self.btn_reporte = QPushButton("📄 Generar reporte")
        self.btn_reporte.setCursor(Qt.PointingHandCursor)
        self.btn_reporte.setMinimumWidth(170)
        self.btn_reporte.setMinimumHeight(38)
        self.btn_reporte.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; border: none;"
        )
        self.btn_reporte.clicked.connect(self.exportar_reporte)
        grid.addWidget(self.btn_reporte, 0, 1, Qt.AlignRight | Qt.AlignTop)

        # Fila 1: chips de información (fecha, horario, carrera, tolerancia)
        chips = QHBoxLayout()
        chips.setSpacing(10)
        chips.addWidget(self._chip("📅 Fecha", str(self.examen.get("fecha", "—"))))
        chips.addWidget(self._chip(
            "🕐 Horario",
            f"{self.examen.get('hora_inicio', '—')} - {self.examen.get('hora_fin', '—')}"
        ))
        chips.addWidget(self._chip("🎓 Carrera", self.carrera_nombre or "—"))
        self.chip_tolerancia = self._chip("⏱ Tolerancia actual", f"{self.tolerancia_actual} min", destacado=True, guardar_valor=True)
        chips.addWidget(self.chip_tolerancia)
        chips.addStretch()
        grid.addLayout(chips, 1, 0, 1, 2)

        # Fila 2: control de tolerancia
        tol_frame = QFrame()
        tol_frame.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;"
        )
        tol_layout = QHBoxLayout(tol_frame)
        tol_layout.setContentsMargins(14, 10, 14, 10)
        tol_layout.setSpacing(10)

        lbl_tol = QLabel("⏱ Tolerancia")
        lbl_tol.setStyleSheet("font-size: 13px; font-weight: bold; color: #0F2C59;")
        tol_layout.addWidget(lbl_tol)

        self.spin_tol = QSpinBox()
        self.spin_tol.setRange(0, 180)
        self.spin_tol.setValue(self.tolerancia_actual)
        self.spin_tol.setSuffix(" min")
        self.spin_tol.setMinimumHeight(34)
        self.spin_tol.setToolTip("Tolerancia adicional después de la hora de cierre")
        tol_layout.addWidget(self.spin_tol)

        btn_mas_5 = QPushButton("+5")
        btn_mas_5.setMinimumWidth(52)
        btn_mas_5.setMinimumHeight(34)
        btn_mas_5.setCursor(Qt.PointingHandCursor)
        btn_mas_5.setStyleSheet(
            "background-color: #E0E7FF; color: #3730A3; border: 1px solid #A5B4FC; "
            "padding: 4px 10px; border-radius: 6px; font-weight: bold;"
        )
        btn_mas_5.clicked.connect(lambda: self.ajustar_tolerancia(self.tolerancia_actual + 5))
        tol_layout.addWidget(btn_mas_5)

        btn_mas_10 = QPushButton("+10")
        btn_mas_10.setMinimumWidth(52)
        btn_mas_10.setMinimumHeight(34)
        btn_mas_10.setCursor(Qt.PointingHandCursor)
        btn_mas_10.setStyleSheet(
            "background-color: #E0E7FF; color: #3730A3; border: 1px solid #A5B4FC; "
            "padding: 4px 10px; border-radius: 6px; font-weight: bold;"
        )
        btn_mas_10.clicked.connect(lambda: self.ajustar_tolerancia(self.tolerancia_actual + 10))
        tol_layout.addWidget(btn_mas_10)

        btn_aplicar = QPushButton("Aplicar")
        btn_aplicar.setMinimumWidth(90)
        btn_aplicar.setMinimumHeight(34)
        btn_aplicar.setCursor(Qt.PointingHandCursor)
        btn_aplicar.setStyleSheet(
            "background-color: #0F2C59; color: white; padding: 6px 16px; "
            "border-radius: 6px; font-weight: bold; border: none;"
        )
        btn_aplicar.clicked.connect(lambda: self.ajustar_tolerancia(self.spin_tol.value()))
        tol_layout.addWidget(btn_aplicar)

        lbl_tol_help = QLabel("Permite el ingreso hasta hora_fin + tolerancia.")
        lbl_tol_help.setStyleSheet("font-size: 11px; color: #94A3B8;")
        lbl_tol_help.setWordWrap(True)
        tol_layout.addWidget(lbl_tol_help)
        tol_layout.addStretch()

        grid.addWidget(tol_frame, 2, 0, 1, 2)
        return header_card

    def _chip(self, etiqueta, valor, destacado=False, guardar_valor=False):
        chip = QFrame()
        bg = "#FEF2F2" if destacado else "#F1F5F9"
        borde = "#FCA5A5" if destacado else "#E2E8F0"
        color_val = "#B91C1C" if destacado else "#0F2C59"
        chip.setStyleSheet(
            f"background-color: {bg}; border: 1px solid {borde}; border-radius: 8px;"
        )
        lay = QVBoxLayout(chip)
        lay.setContentsMargins(12, 6, 12, 6)
        lay.setSpacing(0)
        lbl_e = QLabel(etiqueta)
        lbl_e.setStyleSheet("font-size: 10px; color: #64748B; font-weight: 600;")
        lbl_v = QLabel(str(valor))
        lbl_v.setStyleSheet(f"font-size: 13px; color: {color_val}; font-weight: bold;")
        lbl_v.setWordWrap(True)
        lay.addWidget(lbl_e)
        lay.addWidget(lbl_v)
        if guardar_valor:
            chip.lbl_valor = lbl_v
        return chip

    # ══════════════════ PESTAÑA POSTULANTES ══════════════════
    def _crear_tab_postulantes(self):
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(12)

        bar = QHBoxLayout()
        bar.setSpacing(10)
        self.txt_buscar = QLineEdit()
        self.txt_buscar.setPlaceholderText("🔍 Buscar postulante por CI, nombre o apellido...")
        self.txt_buscar.setMinimumHeight(38)
        self.txt_buscar.textChanged.connect(self.filtrar_postulantes)

        btn_manual = QPushButton("+ Inscripción Manual")
        btn_manual.setMinimumHeight(38)
        btn_manual.setMinimumWidth(180)
        btn_manual.setCursor(Qt.PointingHandCursor)
        btn_manual.setStyleSheet(
            "background-color: #2563EB; color: white; padding: 8px 14px; "
            "border-radius: 6px; font-weight: bold; border: none;"
        )
        btn_manual.clicked.connect(self.inscribir_manual)

        btn_excel = QPushButton("📁 Carga Masiva Excel")
        btn_excel.setMinimumHeight(38)
        btn_excel.setMinimumWidth(180)
        btn_excel.setCursor(Qt.PointingHandCursor)
        btn_excel.setStyleSheet(
            "background-color: #16A34A; color: white; padding: 8px 14px; "
            "border-radius: 6px; font-weight: bold; border: none;"
        )
        btn_excel.clicked.connect(self.importar_postulantes_excel)

        bar.addWidget(self.txt_buscar, stretch=1)
        bar.addWidget(btn_manual)
        bar.addWidget(btn_excel)
        l.addLayout(bar)

        self.tabla_postulantes = QTableWidget(0, 7)
        self.tabla_postulantes.setHorizontalHeaderLabels([
            "CI", "Postulante", "Inscripción", "Aula", "Asiento", "Huellas", "Rostro"
        ])
        header = self.tabla_postulantes.horizontalHeader()
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        for col in (0, 2, 4, 5, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.tabla_postulantes.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_postulantes.setAlternatingRowColors(True)
        self.tabla_postulantes.verticalHeader().setDefaultSectionSize(40)
        l.addWidget(self.tabla_postulantes, stretch=1)

        self.postulantes_examen = []
        self.cargar_postulantes_examen()
        return w

    def cargar_postulantes_examen(self):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/examenes/{id_examen}/postulantes",
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code == 200:
                self.postulantes_examen = respuesta.json()
                self.filtrar_postulantes("")
        except requests.RequestException:
            self.postulantes_examen = []

    def inscribir_manual(self):
        datos = {}
        for campo, etiqueta in (
            ("ci", "C.I."),
            ("nombres", "Nombres"),
            ("apellidos", "Apellidos")
        ):
            valor, aceptado = QInputDialog.getText(self, "Inscripción manual", f"{etiqueta}:")
            if not aceptado or not valor.strip():
                return
            datos[campo] = valor.strip()
        datos["genero"] = None
        try:
            postulante = requests.post(
                f"{self.api_base_url}/postulantes/",
                json=datos,
                headers=self.get_auth_headers(),
                timeout=6
            )
            if postulante.status_code not in (200, 201):
                QMessageBox.warning(self, "Inscripción", str(postulante.json().get("detail", "No se pudo registrar el postulante.")))
                return
            id_postulante = postulante.json().get("id_postulante")
            inscripcion = requests.post(
                f"{self.api_base_url}/inscripciones",
                json={
                    "id_postulante": id_postulante,
                    "id_gestion": self.examen.get("id_gestion"),
                    "id_carrera": self.examen.get("id_carrera"),
                    "estado": "HABILITADO"
                },
                headers=self.get_auth_headers(),
                timeout=6
            )
            if inscripcion.status_code in (200, 201):
                self.cargar_postulantes_examen()
                QMessageBox.information(self, "Inscripción", "Postulante inscrito correctamente.")
            else:
                QMessageBox.warning(self, "Inscripción", str(inscripcion.json().get("detail", "No se pudo crear la inscripción.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Inscripción", f"Error de conexión: {error}")

    def importar_postulantes_excel(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar archivo Excel", "", "Excel (*.xlsx *.xls)"
        )
        if not archivo:
            return
        try:
            with open(archivo, "rb") as contenido:
                respuesta = requests.post(
                    f"{self.api_base_url}/postulantes/importar-excel",
                    files={"file": (archivo.split("/")[-1], contenido, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
                    headers=self.get_auth_headers(),
                    timeout=30
                )
            if respuesta.status_code == 200:
                self.cargar_postulantes_examen()
                QMessageBox.information(self, "Importación", respuesta.json().get("mensaje", "Importación completada."))
            else:
                QMessageBox.warning(self, "Importación", str(respuesta.json().get("detail", "No se pudo importar el archivo.")))
        except (OSError, requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Importación", f"Error al importar: {error}")

    def filtrar_postulantes(self, texto):
        texto = texto.strip().lower()
        filas = [p for p in self.postulantes_examen if not texto or texto in (
            f"{p.get('ci', '')} {p.get('nombre_completo', '')}"
        ).lower()]
        self.tabla_postulantes.setRowCount(len(filas))
        for fila, postulante in enumerate(filas):
            huellas = [h for h in postulante.get("huellas", []) if h.get("habilitada")]
            aula = postulante.get("nombre_aula") or "sin asignar"
            asiento = postulante.get("numero_asiento")

            valores = (
                postulante.get("ci"),
                postulante.get("nombre_completo"),
                postulante.get("estado_inscripcion"),
                aula,
                f"#{asiento}" if asiento else "—",
                ", ".join(str(h.get("tipo_dedo")) for h in huellas) or "ninguna",
                "HABILITADO" if postulante.get("rostro_habilitado") else "DESHABILITADO",
            )
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(str(valor))
                item.setTextAlignment(Qt.AlignCenter)
                if columna == 3:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    if postulante.get("nombre_aula"):
                        item.setForeground(Qt.darkGreen)
                if columna == 6 and postulante.get("rostro_habilitado"):
                    item.setForeground(Qt.darkGreen)
                self.tabla_postulantes.setItem(fila, columna, item)

    # ══════════════════ PESTAÑA AULAS Y SORTEO ══════════════════
    def _crear_tab_aulas_sorteo(self):
        w = QWidget()
        l = QHBoxLayout(w)
        l.setContentsMargins(16, 16, 16, 16)
        l.setSpacing(16)

        # ── Columna izquierda: selección de aulas ──
        izquierda = QVBoxLayout()
        izquierda.setSpacing(10)

        lbl_aulas = QLabel("1. Seleccione las aulas para este examen")
        lbl_aulas.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F2C59;")
        izquierda.addWidget(lbl_aulas)

        lbl_help = QLabel("Puede elegir una o varias aulas (se marcan con la casilla).")
        lbl_help.setStyleSheet("font-size: 12px; color: #64748B;")
        izquierda.addWidget(lbl_help)

        self.lista_aulas = QListWidget()
        self.lista_aulas.setStyleSheet(
            "QListWidget { background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 8px; padding: 6px; }"
            "QListWidget::item { padding: 8px; border-bottom: 1px solid #F1F5F9; }"
        )
        self.lista_aulas.itemChanged.connect(self._on_aulas_seleccionadas)
        izquierda.addWidget(self.lista_aulas, stretch=1)

        btn_refrescar = QPushButton("Actualizar aulas")
        btn_refrescar.setCursor(Qt.PointingHandCursor)
        btn_refrescar.setStyleSheet(
            "background-color: #F1F5F9; color: #334155; padding: 8px 16px; "
            "border-radius: 6px; font-weight: 600; border: 1px solid #CBD5E1;"
        )
        btn_refrescar.clicked.connect(self.cargar_aulas_sorteo)
        izquierda.addWidget(btn_refrescar)

        l.addLayout(izquierda, stretch=2)

        # ── Columna derecha: disponibilidad + acciones + asignaciones ──
        derecha = QVBoxLayout()
        derecha.setSpacing(10)

        lbl_resumen = QLabel("2. Disponibilidad de sillas")
        lbl_resumen.setStyleSheet("font-size: 15px; font-weight: bold; color: #0F2C59;")
        derecha.addWidget(lbl_resumen)

        # Tarjeta de disponibilidad
        self.card_disp = QFrame()
        self.card_disp.setStyleSheet(
            "background-color: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 10px;"
        )
        disp_layout = QVBoxLayout(self.card_disp)
        disp_layout.setContentsMargins(18, 14, 18, 14)
        disp_layout.setSpacing(6)

        self.lbl_pendientes = QLabel("Postulantes pendientes: —")
        self.lbl_pendientes.setStyleSheet("font-size: 14px; color: #334155;")
        self.lbl_sillas = QLabel("Sillas libres en aulas seleccionadas: —")
        self.lbl_sillas.setStyleSheet("font-size: 14px; color: #334155;")
        self.lbl_estado_sillas = QLabel("Seleccione al menos un aula.")
        self.lbl_estado_sillas.setWordWrap(True)
        self.lbl_estado_sillas.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #475569; "
            "background-color: #F1F5F9; border-radius: 8px; padding: 10px;"
        )
        disp_layout.addWidget(self.lbl_pendientes)
        disp_layout.addWidget(self.lbl_sillas)
        disp_layout.addWidget(self.lbl_estado_sillas)
        derecha.addWidget(self.card_disp)

        # Botones de acción
        acciones = QHBoxLayout()
        self.btn_sorteo = QPushButton("🎲 Ejecutar sorteo de asientos")
        self.btn_sorteo.setCursor(Qt.PointingHandCursor)
        self.btn_sorteo.setStyleSheet(
            "background-color: #0F2C59; color: white; padding: 10px 16px; "
            "border-radius: 6px; font-weight: bold; font-size: 13px; border: none;"
        )
        self.btn_sorteo.clicked.connect(self.ejecutar_sorteo)

        self.btn_limpiar = QPushButton("Limpiar asignaciones")
        self.btn_limpiar.setCursor(Qt.PointingHandCursor)
        self.btn_limpiar.setStyleSheet(
            "background-color: #FEF2F2; color: #991B1B; padding: 10px 16px; "
            "border-radius: 6px; font-weight: bold; font-size: 13px; border: 1px solid #FCA5A5;"
        )
        self.btn_limpiar.clicked.connect(self.limpiar_asignaciones)

        acciones.addWidget(self.btn_sorteo, stretch=2)
        acciones.addWidget(self.btn_limpiar, stretch=1)
        derecha.addLayout(acciones)

        lbl_asig = QLabel("Asignaciones actuales de este examen")
        lbl_asig.setStyleSheet("font-size: 14px; font-weight: bold; color: #0F2C59;")
        derecha.addWidget(lbl_asig)

        self.tabla_asignaciones = QTableWidget(0, 4)
        self.tabla_asignaciones.setHorizontalHeaderLabels([
            "Inscripción", "Aula", "Asiento", "Fecha"
        ])
        self.tabla_asignaciones.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabla_asignaciones.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_asignaciones.setAlternatingRowColors(True)
        derecha.addWidget(self.tabla_asignaciones, stretch=1)

        l.addLayout(derecha, stretch=3)

        self.cargar_aulas_sorteo()
        self.cargar_asignaciones()
        return w

    def cargar_aulas_sorteo(self):
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/aulas",
                headers=self.get_auth_headers(),
                timeout=5
            )
            self.aulas_disponibles = [
                a for a in (respuesta.json() if respuesta.status_code == 200 else [])
                if a.get("activa", True)
            ]
        except (requests.RequestException, ValueError):
            self.aulas_disponibles = []

        self.lista_aulas.blockSignals(True)
        self.lista_aulas.clear()
        if not self.aulas_disponibles:
            item = QListWidgetItem("No hay aulas activas. Créelas en 'Aulas y Asientos'.")
            item.setFlags(Qt.NoItemFlags)
            self.lista_aulas.addItem(item)
        for aula in self.aulas_disponibles:
            habilitados = aula.get("asientos_habilitados", 0)
            item = QListWidgetItem(
                f"{aula.get('nombre')}  ({habilitados}/{aula.get('capacidad', 0)} asientos)"
            )
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setData(Qt.UserRole, aula)
            self.lista_aulas.addItem(item)
        self.lista_aulas.blockSignals(False)
        self._on_aulas_seleccionadas()

    def aulas_seleccionadas(self):
        seleccionadas = []
        for i in range(self.lista_aulas.count()):
            item = self.lista_aulas.item(i)
            if item.flags() & Qt.ItemIsUserCheckable and item.checkState() == Qt.Checked:
                seleccionadas.append(item.data(Qt.UserRole))
        return seleccionadas

    def _on_aulas_seleccionadas(self):
        aulas = self.aulas_seleccionadas()
        self.btn_sorteo.setEnabled(bool(aulas))
        self._actualizar_disponibilidad(aulas)

    def _actualizar_disponibilidad(self, aulas):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        params = [("id_aulas", a["id_aula"]) for a in aulas]
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/asignaciones/examen/{id_examen}/disponibilidad",
                params=params,
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code != 200:
                return
            d = respuesta.json()
        except (requests.RequestException, ValueError):
            return

        self.lbl_pendientes.setText(
            f"Postulantes por asignar: {d.get('pendientes', 0)} "
            f"(ya asignados: {d.get('ya_asignados', 0)} de {d.get('total_postulantes', 0)})"
        )
        self.lbl_sillas.setText(f"Sillas libres en aulas seleccionadas: {d.get('asientos_libres', 0)}")

        diferencia = d.get("diferencia", 0)
        if not aulas:
            texto = "Seleccione al menos un aula."
            color_txt = "#475569"
            color_bg = "#F1F5F9"
        elif d.get("suficiente"):
            if diferencia == 0:
                texto = "✓ Sillas exactas para los postulantes pendientes."
            else:
                texto = f"✓ Sillas suficientes. Sobran {diferencia} silla(s)."
            color_txt = "#166534"
            color_bg = "#DCFCE7"
        else:
            texto = f"⚠ Faltan {abs(diferencia)} silla(s). Puede sortear igual; los que no alcancen quedarán pendientes."
            color_txt = "#92400E"
            color_bg = "#FEF3C7"
        self.lbl_estado_sillas.setText(texto)
        self.lbl_estado_sillas.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {color_txt}; "
            f"background-color: {color_bg}; border-radius: 8px; padding: 10px;"
        )

    def cargar_asignaciones(self):
        id_examen = self.examen.get("id_examen")
        if not id_examen:
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/asignaciones/examen/{id_examen}",
                headers=self.get_auth_headers(),
                timeout=5
            )
            if respuesta.status_code != 200:
                return
            asignaciones = respuesta.json()
            self.tabla_asignaciones.setRowCount(len(asignaciones))
            for fila, asignacion in enumerate(asignaciones):
                valores = (
                    asignacion.get("id_inscripcion"),
                    asignacion.get("nombre_aula"),
                    f"#{asignacion.get('numero_asiento')}",
                    asignacion.get("fecha_asignacion")
                )
                for columna, valor in enumerate(valores):
                    self.tabla_asignaciones.setItem(
                        fila, columna, QTableWidgetItem(str(valor or ""))
                    )
        except requests.RequestException:
            self.tabla_asignaciones.setRowCount(0)

    def ejecutar_sorteo(self):
        aulas = self.aulas_seleccionadas()
        if not aulas:
            QMessageBox.warning(self, "Sin aula", "Seleccione al menos un aula antes de sortear.")
            return
        nombres = ", ".join(a.get("nombre", "") for a in aulas)
        confirm = QMessageBox.question(
            self, "Confirmar Sorteo",
            f"¿Ejecutar el sorteo de asientos en {len(aulas)} aula(s):\n{nombres}?\n\n"
            "Se asignará aleatoriamente una butaca a cada postulante pendiente.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return

        try:
            respuesta = requests.post(
                f"{self.api_base_url}/asignaciones/sortear-examen",
                json={
                    "id_examen": self.examen.get("id_examen"),
                    "id_aulas": [a["id_aula"] for a in aulas],
                },
                headers=self.get_auth_headers(),
                timeout=15
            )
            if respuesta.status_code == 200:
                cantidad = len(respuesta.json())
                QMessageBox.information(
                    self, "Sorteo completado",
                    f"Se asignaron {cantidad} postulantes en {len(aulas)} aula(s)."
                )
                self.cargar_asignaciones()
                self.cargar_postulantes_examen()
                self._on_aulas_seleccionadas()
            else:
                detalle = respuesta.json().get("detail", "No se pudo ejecutar el sorteo.")
                QMessageBox.warning(self, "Sorteo no realizado", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Error de red", f"No se pudo contactar al servidor: {error}")

    def limpiar_asignaciones(self):
        confirm = QMessageBox.question(
            self, "Limpiar asignaciones",
            "¿Eliminar todas las asignaciones de asientos de este examen?\n"
            "Esto permite volver a sortear desde cero.",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/asignaciones/examen/{self.examen.get('id_examen')}",
                headers=self.get_auth_headers(),
                timeout=10
            )
            if respuesta.status_code == 200:
                QMessageBox.information(self, "Asignaciones", respuesta.json().get("mensaje", "Asignaciones eliminadas."))
                self.cargar_asignaciones()
                self.cargar_postulantes_examen()
                self._on_aulas_seleccionadas()
            else:
                QMessageBox.warning(self, "Asignaciones", str(respuesta.json().get("detail", "No se pudo limpiar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Error de red", f"No se pudo contactar al servidor: {error}")

    def ajustar_tolerancia(self, nuevos_minutos):
        id_examen = self.examen.get("id_examen")
        try:
            res = requests.patch(
                f"{self.api_base_url}/examenes/{id_examen}/tolerancia",
                json={"tolerancia_minutos": nuevos_minutos},
                headers=self.get_auth_headers(),
                timeout=3
            )
            if res.status_code == 200:
                self.tolerancia_actual = nuevos_minutos
                self.spin_tol.setValue(nuevos_minutos)
                self.chip_tolerancia.lbl_valor.setText(f"{self.tolerancia_actual} min")
                QMessageBox.information(self, "Tolerancia Actualizada", f"La tolerancia se actualizó a {nuevos_minutos} minutos.")
            else:
                QMessageBox.warning(self, "Error", "No se pudo actualizar la tolerancia.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error de red: {str(e)}")

    def exportar_reporte(self):
        id_examen = self.examen.get("id_examen")
        destino, filtro = QFileDialog.getSaveFileName(
            self, "Guardar reporte de asistencia", f"reporte_examen_{id_examen}.xlsx",
            "Excel (*.xlsx);;PDF (*.pdf)"
        )
        if not destino:
            return
        es_pdf = "PDF" in filtro
        extension = ".pdf" if es_pdf else ".xlsx"
        if not destino.lower().endswith(extension):
            destino += extension
        try:
            formato = "pdf" if es_pdf else "excel"
            respuesta = requests.get(
                f"{self.api_base_url}/reportes/examen/{id_examen}/{formato}",
                headers=self.get_auth_headers(),
                timeout=15
            )
            if respuesta.status_code != 200:
                QMessageBox.warning(self, "Reporte", "No se pudo generar el reporte.")
                return
            with open(destino, "wb") as archivo:
                archivo.write(respuesta.content)
            QMessageBox.information(self, "Reporte generado", f"Archivo guardado en:\n{destino}")
        except (OSError, requests.RequestException) as error:
            QMessageBox.critical(self, "Reporte", f"No se pudo guardar el archivo: {error}")

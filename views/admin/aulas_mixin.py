import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QFrame,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QSplitter, QTreeWidget, QTreeWidgetItem, QAbstractItemView, QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont

from desktop.views.admin.aulas.aula_dialog import DialogAula
from desktop.views.admin.aulas.bloque_dialog import DialogBloque
from desktop.views.admin.aulas.piso_dialog import DialogPiso
from desktop.views.admin.aulas.asientos_dialog import DialogAsientosAula


# ---------------------------------------------------------------------------
# Sistema de diseño (un solo lugar para colores y variantes de botones)
# ---------------------------------------------------------------------------
PALETA = {
    "navy": "#0F2C59",
    "texto": "#1E293B",
    "texto_suave": "#64748B",
    "texto_apagado": "#94A3B8",
    "borde": "#E2E8F0",
    "fondo": "#F8FAFC",
    "card": "#FFFFFF",
    "fila_alterna": "#F8FAFC",
    "hover_fila": "#EFF6FF",
    "seleccion": "#DBEAFE",
    "ok": "#047857",
    "ok_fondo": "#D1FAE5",
}

# variante: (fondo, texto, borde, fondo_hover)
VARIANTES_BOTON = {
    "azul": ("#2563EB", "#FFFFFF", "#2563EB", "#1D4ED8"),
    "verde": ("#059669", "#FFFFFF", "#059669", "#047857"),
    "morado": ("#7C3AED", "#FFFFFF", "#7C3AED", "#6D28D9"),
    "neutro": ("#FFFFFF", "#334155", "#CBD5E1", "#F1F5F9"),
    "editar": ("#EEF2FF", "#3730A3", "#C7D2FE", "#E0E7FF"),
    "aviso": ("#FFFBEB", "#92400E", "#FDE68A", "#FEF3C7"),
    "habilitar": ("#ECFDF5", "#065F46", "#A7F3D0", "#D1FAE5"),
}


def estilo_boton(variante, compacto=False):
    fondo, texto, borde, hover = VARIANTES_BOTON[variante]
    padding = "5px 10px" if compacto else "9px 16px"
    tam = 11 if compacto else 12
    radio = 5 if compacto else 8
    return (
        f"QPushButton {{ background-color: {fondo}; color: {texto}; "
        f"border: 1px solid {borde}; border-radius: {radio}px; "
        f"padding: {padding}; font-size: {tam}px; font-weight: 600; }}"
        f"QPushButton:hover {{ background-color: {hover}; }}"
        f"QPushButton:pressed {{ background-color: {hover}; padding-top: 6px; }}"
        "QPushButton:disabled { background-color: #F1F5F9; color: #94A3B8; "
        "border: 1px solid #E2E8F0; }"
    )


ESTILO_VISTA = f"""
QWidget#vistaInfra {{
    background-color: {PALETA['fondo']};
}}
QLabel#tituloPagina {{
    font-size: 24px; font-weight: 800; color: {PALETA['navy']};
}}
QLabel#subtituloPagina {{
    font-size: 12px; color: {PALETA['texto_suave']};
}}

/* Tarjetas */
QFrame#card {{
    background-color: {PALETA['card']};
    border: 1px solid {PALETA['borde']};
    border-radius: 12px;
}}
QLabel#cardTitulo {{
    font-size: 18px; font-weight: 800; color: {PALETA['navy']};
    background: transparent;
}}
QLabel#cardSubtitulo {{
    font-size: 12px; color: {PALETA['texto_suave']};
    background: transparent;
}}
QLabel#etiquetaSeccion {{
    font-size: 11px; font-weight: 700; color: {PALETA['texto_suave']};
    background: transparent;
}}

/* Splitter */
QSplitter::handle {{
    background: transparent;
}}

/* Árbol */
QTreeWidget {{
    background-color: {PALETA['card']};
    border: none;
    outline: 0;
    font-size: 13px;
    color: {PALETA['texto']};
}}
QTreeWidget::item {{
    padding: 6px 4px;
    border-radius: 6px;
}}
QTreeWidget::item:hover {{
    background-color: {PALETA['hover_fila']};
}}
QTreeWidget::item:selected {{
    background-color: {PALETA['seleccion']};
    color: {PALETA['navy']};
}}

/* Tabla */
QTableWidget {{
    background-color: {PALETA['card']};
    alternate-background-color: {PALETA['fila_alterna']};
    border: none;
    gridline-color: transparent;
    outline: 0;
    font-size: 13px;
    color: {PALETA['texto']};
    selection-background-color: {PALETA['seleccion']};
    selection-color: {PALETA['navy']};
}}
QTableWidget::item {{
    padding: 4px 8px;
    border-bottom: 1px solid {PALETA['borde']};
}}
QTableWidget::item:hover {{
    background-color: {PALETA['hover_fila']};
}}
QHeaderView {{
    background: transparent;
}}
QHeaderView::section {{
    background-color: {PALETA['fondo']};
    color: {PALETA['texto_suave']};
    border: none;
    border-bottom: 1px solid {PALETA['borde']};
    padding: 9px 8px;
    font-size: 11px;
    font-weight: 700;
}}

/* Scrollbars */
QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #CBD5E1; border-radius: 4px; min-height: 28px;
}}
QScrollBar::handle:vertical:hover {{ background: #94A3B8; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 10px; margin: 2px;
}}
QScrollBar::handle:horizontal {{
    background: #CBD5E1; border-radius: 4px; min-width: 28px;
}}
QScrollBar::handle:horizontal:hover {{ background: #94A3B8; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
"""


def _crear_card():
    card = QFrame()
    card.setObjectName("card")
    return card


class AulasMixin:
    """Pantalla de infraestructura: bloques -> pisos -> aulas."""

    def _crear_aulas_view(self):
        w = QWidget()
        w.setObjectName("vistaInfra")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setStyleSheet(ESTILO_VISTA)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # --- Encabezado de página ---
        encabezado = QHBoxLayout()
        encabezado.setSpacing(8)

        bloque_titulo = QVBoxLayout()
        bloque_titulo.setSpacing(2)
        title = QLabel("Infraestructura")
        title.setObjectName("tituloPagina")
        sub = QLabel("Administra bloques, pisos y aulas del campus")
        sub.setObjectName("subtituloPagina")
        bloque_titulo.addWidget(title)
        bloque_titulo.addWidget(sub)
        encabezado.addLayout(bloque_titulo)
        encabezado.addStretch()

        self.btn_nuevo_bloque = self._boton_infra("+ Nuevo bloque", "azul")
        self.btn_nuevo_bloque.clicked.connect(self.crear_bloque_panel)
        self.btn_nuevo_piso = self._boton_infra("+ Nuevo piso", "verde")
        self.btn_nuevo_piso.clicked.connect(self.crear_piso_panel)
        self.btn_nueva_aula = self._boton_infra("+ Nueva aula", "morado")
        self.btn_nueva_aula.clicked.connect(self.crear_aula_panel)
        btn_refrescar = self._boton_infra("Actualizar", "neutro")
        btn_refrescar.clicked.connect(self.cargar_aulas_panel)

        encabezado.addWidget(self.btn_nuevo_bloque)
        encabezado.addWidget(self.btn_nuevo_piso)
        encabezado.addWidget(self.btn_nueva_aula)
        encabezado.addSpacing(8)
        encabezado.addWidget(btn_refrescar)
        layout.addLayout(encabezado)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(14)

        # --- Tarjeta izquierda: árbol ---
        card_arbol = _crear_card()
        arbol_layout = QVBoxLayout(card_arbol)
        arbol_layout.setContentsMargins(12, 12, 12, 12)
        arbol_layout.setSpacing(8)

        etiqueta_arbol = QLabel("ESTRUCTURA")
        etiqueta_arbol.setObjectName("etiquetaSeccion")
        arbol_layout.addWidget(etiqueta_arbol)

        self.infra_tree = QTreeWidget()
        self.infra_tree.setColumnCount(2)
        self.infra_tree.setHeaderLabels(["Estructura", "Detalle"])
        self.infra_tree.setHeaderHidden(True)
        self.infra_tree.setIndentation(18)
        self.infra_tree.setAnimated(True)
        self.infra_tree.setMinimumWidth(380)
        self.infra_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.infra_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.infra_tree.currentItemChanged.connect(self._al_cambiar_seleccion)
        arbol_layout.addWidget(self.infra_tree, 1)
        splitter.addWidget(card_arbol)

        # --- Tarjeta derecha: detalle + tabla ---
        card_panel = _crear_card()
        panel_layout = QVBoxLayout(card_panel)
        panel_layout.setContentsMargins(18, 16, 18, 12)
        panel_layout.setSpacing(12)

        cab = QHBoxLayout()
        cab.setSpacing(8)
        textos = QVBoxLayout()
        textos.setSpacing(3)
        self.infra_titulo = QLabel("Selecciona un bloque o piso")
        self.infra_titulo.setObjectName("cardTitulo")
        self.infra_subtitulo = QLabel("")
        self.infra_subtitulo.setObjectName("cardSubtitulo")
        self.infra_subtitulo.setWordWrap(True)
        textos.addWidget(self.infra_titulo)
        textos.addWidget(self.infra_subtitulo)
        cab.addLayout(textos, 1)

        self.btn_editar_sel = self._boton_infra("Editar", "editar")
        self.btn_editar_sel.clicked.connect(self._editar_seleccion)
        self.btn_estado_sel = self._boton_infra("Deshabilitar", "aviso")
        self.btn_estado_sel.clicked.connect(self._cambiar_estado_seleccion)
        self.btn_editar_sel.setEnabled(False)
        self.btn_estado_sel.setEnabled(False)
        cab.addWidget(self.btn_editar_sel, 0, Qt.AlignTop)
        cab.addWidget(self.btn_estado_sel, 0, Qt.AlignTop)
        panel_layout.addLayout(cab)

        separador = QFrame()
        separador.setFixedHeight(1)
        separador.setStyleSheet(f"background-color: {PALETA['borde']}; border: none;")
        panel_layout.addWidget(separador)

        self.aulas_table = QTableWidget(0, 6)
        self.aulas_table.setHorizontalHeaderLabels([
            "PISO", "AULA", "CAPACIDAD", "ASIENTOS", "ESTADO", "ACCIONES"
        ])
        header = self.aulas_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 120)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.resizeSection(5, 310)
        header.setHighlightSections(False)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.aulas_table.verticalHeader().setVisible(False)
        self.aulas_table.verticalHeader().setDefaultSectionSize(50)
        self.aulas_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.aulas_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.aulas_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.aulas_table.setAlternatingRowColors(True)
        self.aulas_table.setShowGrid(False)
        self.aulas_table.setFocusPolicy(Qt.NoFocus)
        panel_layout.addWidget(self.aulas_table, 1)

        splitter.addWidget(card_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        self.infra_data = {"bloques": [], "aulas_sin_piso": []}
        self._bloques_data = []
        self.infra_seleccion = None
        self.cargar_aulas_panel()
        self._limpiar_detalle()
        return w

    # -- Utilidades de UI -------------------------------------------------
    @staticmethod
    def _boton_infra(texto, variante="neutro", compacto=False):
        btn = QPushButton(texto)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(estilo_boton(variante, compacto))
        return btn

    @staticmethod
    def _item_arbol(texto, detalle, datos, nivel=None, apagado=False):
        """nivel: 'bloque' (negrita), 'piso' (medio), 'aula' (normal)."""
        item = QTreeWidgetItem([texto, detalle])
        item.setData(0, Qt.UserRole, datos)
        fuente = QFont()
        if nivel == "bloque":
            fuente.setBold(True)
            item.setForeground(0, QBrush(QColor(PALETA["navy"])))
        elif nivel == "piso":
            fuente.setWeight(QFont.DemiBold)
            item.setForeground(0, QBrush(QColor(PALETA["texto"])))
        item.setFont(0, fuente)
        item.setForeground(1, QBrush(QColor(PALETA["texto_suave"])))
        if apagado:
            item.setForeground(0, QBrush(QColor(PALETA["texto_apagado"])))
            item.setForeground(1, QBrush(QColor(PALETA["texto_apagado"])))
        return item

    def _datos_item(self, item):
        if item is None:
            return None
        return item.data(0, Qt.UserRole)

    def _bloque_de_item(self, item):
        datos = self._datos_item(item)
        if not datos:
            return None
        if datos["tipo"] == "bloque":
            return datos["bloque"]
        if datos["tipo"] == "piso":
            return datos.get("bloque")
        if datos["tipo"] == "aula":
            return datos.get("bloque")
        return None

    def _piso_de_item(self, item):
        datos = self._datos_item(item)
        if not datos:
            return None
        if datos["tipo"] == "piso":
            return datos["piso"]
        if datos["tipo"] == "aula":
            return datos.get("piso")
        return None

    def _aula_de_item(self, item):
        datos = self._datos_item(item)
        if datos and datos["tipo"] == "aula":
            return datos.get("aula")
        return None

    # -- Carga de datos ---------------------------------------------------
    def cargar_aulas_panel(self):
        seleccion = self.infra_seleccion
        self.infra_data = self._obtener_objeto("/admin/infraestructura") or {
            "bloques": [], "aulas_sin_piso": []
        }
        self._bloques_data = self.infra_data.get("bloques", [])
        self._poblar_arbol()
        self._restaurar_seleccion(seleccion)

    def _poblar_arbol(self):
        self.infra_tree.blockSignals(True)
        self.infra_tree.clear()

        for bloque in self._bloques_data:
            pisos = bloque.get("pisos", [])
            total_aulas = sum(len(p.get("aulas", [])) for p in pisos)
            detalle = f"{len(pisos)} piso(s) · {total_aulas} aula(s)"
            item_bloque = self._item_arbol(
                str(bloque.get("nombre", "")), detalle,
                {"tipo": "bloque", "bloque": bloque},
                nivel="bloque", apagado=not bloque.get("activo", True),
            )
            self.infra_tree.addTopLevelItem(item_bloque)

            for piso in pisos:
                etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
                item_piso = self._item_arbol(
                    etiqueta, f"{len(piso.get('aulas', []))} aula(s)",
                    {"tipo": "piso", "piso": piso, "bloque": bloque},
                    nivel="piso", apagado=not piso.get("activo", True),
                )
                item_bloque.addChild(item_piso)

                for aula in piso.get("aulas", []):
                    habilitados = aula.get("asientos_habilitados", 0)
                    detalle_aula = (
                        f"{habilitados}/{aula.get('total_asientos', 0)} asientos"
                    )
                    item_aula = self._item_arbol(
                        str(aula.get("nombre", "")), detalle_aula,
                        {"tipo": "aula", "aula": aula, "piso": piso, "bloque": bloque},
                        nivel="aula", apagado=not aula.get("activa", True),
                    )
                    item_piso.addChild(item_aula)
                item_piso.setExpanded(True)

            item_bloque.setExpanded(True)

        sin_piso = self.infra_data.get("aulas_sin_piso", [])
        if sin_piso:
            item_sin = self._item_arbol(
                "Sin bloque/piso", f"{len(sin_piso)} aula(s)",
                {"tipo": "sin_piso"}, nivel="bloque",
            )
            self.infra_tree.addTopLevelItem(item_sin)
            for aula in sin_piso:
                item_aula = self._item_arbol(
                    str(aula.get("nombre", "")),
                    f"{aula.get('asientos_habilitados', 0)}/"
                    f"{aula.get('total_asientos', 0)} asientos",
                    {"tipo": "aula", "aula": aula, "piso": None, "bloque": None},
                    nivel="aula", apagado=not aula.get("activa", True),
                )
                item_sin.addChild(item_aula)
            item_sin.setExpanded(True)

        self.infra_tree.blockSignals(False)

    def _restaurar_seleccion(self, seleccion):
        if not seleccion:
            self._limpiar_detalle()
            return
        tipo, ident = seleccion
        item = self._buscar_item(tipo, ident)
        if item is not None:
            self.infra_tree.setCurrentItem(item)
        else:
            self._limpiar_detalle()

    def _buscar_item(self, tipo, ident):
        clave = "id_bloque" if tipo == "bloque" else (
            "id_piso" if tipo == "piso" else "id_aula"
        )
        pila = [self.infra_tree.topLevelItem(i) for i in range(self.infra_tree.topLevelItemCount())]
        while pila:
            item = pila.pop()
            datos = self._datos_item(item)
            if datos and datos.get("tipo") == tipo:
                objeto = (
                    datos.get("bloque") if tipo == "bloque"
                    else datos.get("piso") if tipo == "piso"
                    else datos.get("aula")
                )
                if objeto and objeto.get(clave) == ident:
                    return item
            pila.extend(item.child(i) for i in range(item.childCount()))
        return None

    # -- Selección y panel derecho ---------------------------------------
    def _al_cambiar_seleccion(self, actual, _anterior=None):
        datos = self._datos_item(actual)
        if not datos:
            self._limpiar_detalle()
            return
        self.infra_seleccion = (
            datos["tipo"],
            (
                datos["bloque"].get("id_bloque") if datos["tipo"] == "bloque"
                else datos["piso"].get("id_piso") if datos["tipo"] == "piso"
                else datos["aula"].get("id_aula") if datos["tipo"] == "aula"
                else 0
            ),
        )
        if datos["tipo"] == "bloque":
            self._mostrar_bloque(datos["bloque"])
        elif datos["tipo"] == "piso":
            self._mostrar_piso(datos["bloque"], datos["piso"])
        elif datos["tipo"] == "aula":
            self._mostrar_aula(datos["bloque"], datos["piso"], datos["aula"])
        else:
            self._mostrar_sin_piso()

    def _limpiar_detalle(self):
        self.infra_seleccion = None
        self.infra_titulo.setText("Selecciona un bloque o piso")
        self.infra_subtitulo.setText(
            "Elige un elemento del árbol para ver y administrar sus aulas."
        )
        self.aulas_table.setRowCount(0)
        self.btn_editar_sel.setEnabled(False)
        self.btn_estado_sel.setEnabled(False)
        self.btn_nuevo_piso.setEnabled(False)
        self.btn_nueva_aula.setEnabled(False)

    def _actualizar_botones(self, activo, etiqueta_estado):
        self.btn_editar_sel.setEnabled(True)
        self.btn_estado_sel.setEnabled(True)
        if activo:
            self.btn_estado_sel.setText(etiqueta_estado)
            self.btn_estado_sel.setStyleSheet(estilo_boton("aviso"))
        else:
            self.btn_estado_sel.setText("Habilitar")
            self.btn_estado_sel.setStyleSheet(estilo_boton("habilitar"))
        self.btn_nuevo_piso.setEnabled(True)
        self.btn_nueva_aula.setEnabled(True)

    def _mostrar_bloque(self, bloque):
        self.infra_titulo.setText(str(bloque.get("nombre", "Bloque")))
        partes = []
        if bloque.get("direccion"):
            partes.append(f"Dirección: {bloque['direccion']}")
        if bloque.get("referencia"):
            partes.append(f"Referencia: {bloque['referencia']}")
        self.infra_subtitulo.setText(" · ".join(partes) or "Sin datos de ubicación")
        self._actualizar_botones(
            bloque.get("activo", True),
            "Deshabilitar bloque",
        )
        self._poblar_tabla_bloque(bloque)

    def _mostrar_piso(self, bloque, piso):
        etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
        self.infra_titulo.setText(etiqueta)
        partes = [str(bloque.get("nombre", ""))]
        if bloque.get("direccion"):
            partes.append(bloque["direccion"])
        if piso.get("descripcion"):
            partes.append(piso["descripcion"])
        self.infra_subtitulo.setText(" · ".join(p for p in partes if p))
        self._actualizar_botones(piso.get("activo", True), "Deshabilitar piso")
        self._poblar_tabla_piso(piso)

    def _mostrar_aula(self, bloque, piso, aula):
        self.infra_titulo.setText(str(aula.get("nombre", "Aula")))
        partes = []
        if bloque:
            partes.append(str(bloque.get("nombre", "")))
        if piso:
            partes.append(piso.get("nombre") or f"Piso {piso.get('numero')}")
        self.infra_subtitulo.setText(" · ".join(p for p in partes if p))
        self._actualizar_botones(aula.get("activa", True), "Deshabilitar aula")
        if piso:
            self._poblar_tabla_piso(piso)
        elif bloque:
            self._poblar_tabla_bloque(bloque)
        else:
            self._poblar_tabla_sin_piso()

    def _mostrar_sin_piso(self):
        self.infra_titulo.setText("Aulas sin bloque/piso")
        self.infra_subtitulo.setText(
            "Estas aulas son antiguas. Edítalas para asignarles un bloque y piso."
        )
        self.btn_editar_sel.setEnabled(False)
        self.btn_estado_sel.setEnabled(False)
        self.btn_nuevo_piso.setEnabled(False)
        self.btn_nueva_aula.setEnabled(bool(self._bloques_data))
        self._poblar_tabla_sin_piso()

    def _poblar_tabla_bloque(self, bloque):
        filas = []
        for piso in bloque.get("pisos", []):
            etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
            for aula in piso.get("aulas", []):
                filas.append((etiqueta, aula))
        self._renderizar_aulas(filas)

    def _poblar_tabla_piso(self, piso):
        etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
        filas = [(etiqueta, aula) for aula in piso.get("aulas", [])]
        self._renderizar_aulas(filas)

    def _poblar_tabla_sin_piso(self):
        filas = [("—", aula) for aula in self.infra_data.get("aulas_sin_piso", [])]
        self._renderizar_aulas(filas)

    def _renderizar_aulas(self, filas):
        apagado = QBrush(QColor(PALETA["texto_apagado"]))
        self.aulas_table.setRowCount(len(filas))
        for i, (etiqueta_piso, aula) in enumerate(filas):
            activa = aula.get("activa", True)

            item_piso = QTableWidgetItem(str(etiqueta_piso))
            item_piso.setForeground(apagado if not activa else QBrush(QColor(PALETA["texto_suave"])))
            self.aulas_table.setItem(i, 0, item_piso)

            item_nombre = QTableWidgetItem(str(aula.get("nombre", "")))
            fuente = QFont()
            fuente.setWeight(QFont.DemiBold)
            item_nombre.setFont(fuente)
            if not activa:
                item_nombre.setForeground(apagado)
            self.aulas_table.setItem(i, 1, item_nombre)

            cap = QTableWidgetItem(str(aula.get("capacidad", 0)))
            cap.setTextAlignment(Qt.AlignCenter)
            if not activa:
                cap.setForeground(apagado)
            self.aulas_table.setItem(i, 2, cap)

            asientos = f"{aula.get('asientos_habilitados', 0)}/{aula.get('total_asientos', 0)}"
            item_asientos = QTableWidgetItem(asientos)
            item_asientos.setTextAlignment(Qt.AlignCenter)
            if not activa:
                item_asientos.setForeground(apagado)
            self.aulas_table.setItem(i, 3, item_asientos)

            self.aulas_table.setCellWidget(i, 4, self._insignia_estado(activa))
            self.aulas_table.setCellWidget(i, 5, self._acciones_aula(aula))
            self.aulas_table.setRowHeight(i, 50)

    @staticmethod
    def _insignia_estado(activa):
        """Pastilla de color para el estado, centrada en la celda."""
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        h = QHBoxLayout(contenedor)
        h.setContentsMargins(6, 0, 6, 0)
        etiqueta = QLabel("● Activa" if activa else "● Inactiva")
        if activa:
            fondo, texto = PALETA["ok_fondo"], PALETA["ok"]
        else:
            fondo, texto = "#F1F5F9", "#64748B"
        etiqueta.setStyleSheet(
            f"background-color: {fondo}; color: {texto}; border-radius: 10px; "
            "padding: 3px 10px; font-size: 11px; font-weight: 700;"
        )
        etiqueta.setAlignment(Qt.AlignCenter)
        etiqueta.setMinimumWidth(etiqueta.sizeHint().width() + 4)
        etiqueta.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        h.addStretch()
        h.addWidget(etiqueta)
        h.addStretch()
        return contenedor

    def _acciones_aula(self, aula):
        contenedor = QWidget()
        contenedor.setStyleSheet("background: transparent;")
        h = QHBoxLayout(contenedor)
        h.setContentsMargins(4, 4, 4, 4)
        h.setSpacing(6)

        btn_abrir = self._boton_infra("Abrir", "verde", compacto=True)
        btn_abrir.clicked.connect(lambda _, a=aula: self.abrir_asientos_aula(a))

        btn_editar = self._boton_infra("Editar", "editar", compacto=True)
        btn_editar.clicked.connect(lambda _, a=aula: self.editar_aula_panel(a))

        activa = aula.get("activa", True)
        btn_estado = self._boton_infra(
            "Deshabilitar" if activa else "Habilitar",
            "aviso" if activa else "habilitar",
            compacto=True,
        )
        btn_estado.clicked.connect(
            lambda _, a=aula: self.cambiar_estado_aula(a, not a.get("activa", True))
        )

        # Que ningún botón se recorte: ancho mínimo = tamaño real del texto
        for btn in (btn_abrir, btn_editar, btn_estado):
            btn.setMinimumWidth(btn.sizeHint().width() + 4)
            btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        h.addWidget(btn_abrir)
        h.addWidget(btn_editar)
        h.addWidget(btn_estado)
        h.addStretch()
        return contenedor

    # -- CRUD de bloques y pisos -----------------------------------------
    def crear_bloque_panel(self):
        dlg = DialogBloque(None, self)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Bloque", "El nombre es obligatorio.")
            return
        self._guardar_infra("post", "/admin/bloques", datos, "Bloque creado correctamente.")

    def editar_bloque_panel(self, bloque):
        dlg = DialogBloque(bloque, self)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Bloque", "El nombre es obligatorio.")
            return
        self._guardar_infra(
            "patch", f"/admin/bloques/{bloque['id_bloque']}", datos,
            "Bloque actualizado correctamente.",
        )

    def crear_piso_panel(self):
        bloque = self._bloque_de_item(self.infra_tree.currentItem())
        if not bloque:
            QMessageBox.information(self, "Piso", "Selecciona primero un bloque.")
            return
        dlg = DialogPiso(None, self, bloque=bloque)
        if not dlg.exec():
            return
        self._guardar_infra(
            "post", f"/admin/bloques/{bloque['id_bloque']}/pisos", dlg.get_data(),
            "Piso creado correctamente.",
        )

    def editar_piso_panel(self, bloque, piso):
        dlg = DialogPiso(piso, self, bloque=bloque or {})
        if not dlg.exec():
            return
        self._guardar_infra(
            "patch", f"/admin/pisos/{piso['id_piso']}", dlg.get_data(),
            "Piso actualizado correctamente.",
        )

    def _editar_seleccion(self):
        datos = self._datos_item(self.infra_tree.currentItem())
        if not datos:
            return
        if datos["tipo"] == "bloque":
            self.editar_bloque_panel(datos["bloque"])
        elif datos["tipo"] == "piso":
            self.editar_piso_panel(datos.get("bloque"), datos["piso"])
        elif datos["tipo"] == "aula":
            self.editar_aula_panel(datos["aula"])

    def _cambiar_estado_seleccion(self):
        datos = self._datos_item(self.infra_tree.currentItem())
        if not datos:
            return
        if datos["tipo"] == "bloque":
            bloque = datos["bloque"]
            self._cambiar_estado_infra(
                f"/admin/bloques/{bloque['id_bloque']}",
                not bloque.get("activo", True),
                f"bloque '{bloque.get('nombre')}'",
            )
        elif datos["tipo"] == "piso":
            piso = datos["piso"]
            etiqueta = piso.get("nombre") or f"Piso {piso.get('numero')}"
            self._cambiar_estado_infra(
                f"/admin/pisos/{piso['id_piso']}",
                not piso.get("activo", True),
                f"piso '{etiqueta}'",
            )
        elif datos["tipo"] == "aula":
            aula = datos["aula"]
            self.cambiar_estado_aula(aula, not aula.get("activa", True))

    def _cambiar_estado_infra(self, endpoint, activo, descripcion):
        accion = "habilitar" if activo else "deshabilitar"
        confirmacion = QMessageBox.question(
            self, "Infraestructura",
            f"¿{accion.capitalize()} el {descripcion}?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        self._guardar_infra(
            "patch", endpoint, {"activo": activo},
            f"Se actualizó el estado del {descripcion}.", silencioso=True,
        )

    # -- CRUD de aulas ----------------------------------------------------
    def crear_aula_panel(self):
        piso = self._piso_de_item(self.infra_tree.currentItem())
        id_piso = piso.get("id_piso") if piso else None
        dlg = DialogAula(None, self, bloques=self._bloques_data, id_piso=id_piso)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Aula", "El nombre es obligatorio.")
            return
        if not datos.get("id_piso"):
            QMessageBox.warning(self, "Aula", "Selecciona el bloque y el piso.")
            return
        self._guardar_infra("post", "/admin/aulas", datos, "Aula creada correctamente.")

    def editar_aula_panel(self, aula):
        dlg = DialogAula(aula, self, bloques=self._bloques_data)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["nombre"]:
            QMessageBox.warning(self, "Aula", "El nombre es obligatorio.")
            return
        if not datos.get("id_piso"):
            QMessageBox.warning(self, "Aula", "Selecciona el bloque y el piso.")
            return
        self._guardar_infra(
            "patch", f"/admin/aulas/{aula['id_aula']}", datos,
            "Aula actualizada correctamente.",
        )

    def cambiar_estado_aula(self, aula, activa):
        accion = "habilitar" if activa else "deshabilitar"
        confirmacion = QMessageBox.question(
            self, "Aula",
            f"¿{accion.capitalize()} el aula '{aula.get('nombre')}'?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        self._guardar_infra(
            "patch", f"/admin/aulas/{aula['id_aula']}", {"activa": activa},
            f"Aula {'habilitada' if activa else 'deshabilitada'} correctamente.",
            silencioso=True,
        )

    def abrir_asientos_aula(self, aula):
        dlg = DialogAsientosAula(aula, self.api_base_url, self._auth_headers(), self)
        dlg.exec()
        self.cargar_aulas_panel()

    # -- Guardado genérico ------------------------------------------------
    def _guardar_infra(self, metodo, endpoint, datos, mensaje, silencioso=False):
        try:
            if metodo == "post":
                respuesta = requests.post(
                    f"{self.api_base_url}{endpoint}", json=datos,
                    headers=self._auth_headers(), timeout=8,
                )
            else:
                respuesta = requests.patch(
                    f"{self.api_base_url}{endpoint}", json=datos,
                    headers=self._auth_headers(), timeout=8,
                )
            if respuesta.status_code in (200, 201):
                self.cargar_aulas_panel()
                if not silencioso:
                    QMessageBox.information(self, "Infraestructura", mensaje)
            else:
                try:
                    detalle = respuesta.json().get("detail", "No se pudo guardar.")
                except ValueError:
                    detalle = "No se pudo guardar."
                QMessageBox.warning(self, "Infraestructura", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Infraestructura", f"Error de conexión: {error}")
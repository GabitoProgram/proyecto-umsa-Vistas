import requests
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor


def _item_centrado(texto="", dato=None):
    """Celda centrada. ``dato`` se guarda en Qt.UserRole (el texto lo dibuja un chip)."""
    item = QTableWidgetItem(texto)
    item.setTextAlignment(Qt.AlignCenter)
    if dato is not None:
        item.setData(Qt.UserRole, dato)
    return item


def _chip_accion(texto, estilo):
    """Chip de color centrado en la celda.

    Alto fijo y alineación al centro: el chip nunca se estira hasta tocar
    el borde de la fila.
    """
    contenedor = QWidget()
    contenedor.setObjectName("audChipContenedor")
    contenedor.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    fila = QHBoxLayout(contenedor)
    fila.setContentsMargins(6, 0, 6, 0)
    fila.setSpacing(0)

    chip = QLabel(texto)
    chip.setObjectName(estilo)
    chip.setAlignment(Qt.AlignCenter)
    chip.setFixedHeight(26)
    chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    fila.addWidget(chip, 0, Qt.AlignCenter)
    return contenedor


class AuditoriaMixin:
    ALTO_FILA_AUDITORIA = 52

    ESTILOS_AUDITORIA = """
        QWidget#auditoriaRoot { background: #F1F5F9; }
        QLabel { background: transparent; border: none; }
        QToolTip {
            background: #0F172A; color: #FFFFFF; border: none;
            padding: 6px 10px; font-size: 12px;
        }

        /* ---------- Encabezado ---------- */
        QLabel#audTitulo { color: #0F2C59; font-size: 24px; font-weight: 800; }
        QLabel#audSub { color: #64748B; font-size: 13px; font-weight: 500; }
        QLabel#audTotal {
            background: #E8F0FD; color: #1E54B7;
            border-radius: 14px; padding: 0 16px;
            font-size: 12px; font-weight: 700;
        }

        /* ---------- Filtros ---------- */
        QFrame#audPanel {
            background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 14px;
        }
        QLineEdit#audFiltro {
            min-height: 40px; padding: 0 14px;
            background: #F8FAFC; border: 1px solid #D5DEE9;
            border-radius: 10px; font-size: 13px; color: #0F172A;
            selection-background-color: #BFD6F6; selection-color: #0F172A;
        }
        QLineEdit#audFiltro:hover { border: 1px solid #A9BBD1; }
        QLineEdit#audFiltro:focus { border: 1px solid #1E54B7; background: #FFFFFF; }
        QPushButton#audBoton {
            min-width: 110px; min-height: 40px; padding: 0 22px;
            background: #1E54B7; color: #FFFFFF; border: 1px solid #1E54B7;
            border-radius: 10px; font-size: 13px; font-weight: 700;
        }
        QPushButton#audBoton:hover { background: #17449A; border: 1px solid #17449A; }
        QPushButton#audBoton:pressed { background: #123A83; border: 1px solid #123A83; }

        /* ---------- Tabla ---------- */
        QFrame#audTablaCard {
            background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 14px;
        }
        QTableWidget#audTabla {
            background: #FFFFFF; alternate-background-color: #F8FAFC;
            border: none; gridline-color: transparent; outline: 0;
            color: #0F172A; font-size: 13px;
            selection-background-color: #E8F0FD;
            selection-color: #0F2C59;
        }
        QTableWidget#audTabla::item {
            padding: 6px 12px; border-bottom: 1px solid #F1F5F9;
        }
        QTableWidget#audTabla::item:selected { background: #E8F0FD; color: #0F2C59; }
        QTableWidget#audTabla QHeaderView::section {
            background: #F8FAFC; color: #64748B;
            border: none; border-bottom: 1px solid #E2E8F0;
            padding: 12px; font-size: 11px; font-weight: 700;
        }
        QTableWidget#audTabla QTableCornerButton::section { background: #F8FAFC; border: none; }
        QWidget#audChipContenedor { background: transparent; }
        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #94A3B8; }
        QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
        QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 4px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background: #94A3B8; }
        QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

        /* ---------- Chips de acción ---------- */
        QLabel#audChipEliminar, QLabel#audChipActualizar,
        QLabel#audChipCrear, QLabel#audChipOtro {
            border-radius: 13px; padding: 0 14px;
            font-size: 11px; font-weight: 700;
        }
        QLabel#audChipEliminar { background: #FEE2E2; color: #B91C1C; }
        QLabel#audChipActualizar { background: #FEF3C7; color: #B45309; }
        QLabel#audChipCrear { background: #DCFCE7; color: #15803D; }
        QLabel#audChipOtro { background: #E0EAFB; color: #1E4E96; }
    """

    def _crear_auditoria_view(self):
        w = QWidget()
        w.setObjectName("auditoriaRoot")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setStyleSheet(self.ESTILOS_AUDITORIA)

        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(16)

        cabecera = QHBoxLayout()
        textos = QVBoxLayout()
        textos.setSpacing(2)
        title = QLabel("Registro de Auditoría", w)
        title.setObjectName("audTitulo")
        subtitle = QLabel(
            "Historial de acciones realizadas por los usuarios del sistema.", w
        )
        subtitle.setObjectName("audSub")
        textos.addWidget(title)
        textos.addWidget(subtitle)
        cabecera.addLayout(textos, 1)

        self.lbl_auditoria_total = QLabel("0 registros", w)
        self.lbl_auditoria_total.setObjectName("audTotal")
        self.lbl_auditoria_total.setAlignment(Qt.AlignCenter)
        self.lbl_auditoria_total.setFixedHeight(28)
        cabecera.addWidget(self.lbl_auditoria_total, 0, Qt.AlignBottom)
        layout.addLayout(cabecera)

        panel = QFrame(w)
        panel.setObjectName("audPanel")
        filtros = QHBoxLayout(panel)
        filtros.setContentsMargins(14, 14, 14, 14)
        filtros.setSpacing(10)

        self.txt_filtro_accion = QLineEdit(panel)
        self.txt_filtro_accion.setObjectName("audFiltro")
        self.txt_filtro_accion.setPlaceholderText(
            "Filtrar por acción, por ejemplo CREAR o ACTUALIZAR…"
        )
        self.txt_filtro_accion.setMinimumHeight(40)
        self.txt_filtro_accion.returnPressed.connect(self.cargar_auditoria_panel)

        self.txt_filtro_entidad = QLineEdit(panel)
        self.txt_filtro_entidad.setObjectName("audFiltro")
        self.txt_filtro_entidad.setPlaceholderText(
            "Filtrar por entidad, por ejemplo usuarios o aulas…"
        )
        self.txt_filtro_entidad.setMinimumHeight(40)
        self.txt_filtro_entidad.returnPressed.connect(self.cargar_auditoria_panel)

        btn_filtrar = QPushButton("Filtrar", panel)
        btn_filtrar.setObjectName("audBoton")
        btn_filtrar.setCursor(Qt.PointingHandCursor)
        btn_filtrar.setFixedHeight(40)
        btn_filtrar.clicked.connect(self.cargar_auditoria_panel)

        filtros.addWidget(self.txt_filtro_accion, 1)
        filtros.addWidget(self.txt_filtro_entidad, 1)
        filtros.addWidget(btn_filtrar)
        layout.addWidget(panel)

        # La tabla va dentro de una tarjeta con esquinas redondeadas: una tabla
        # con border-radius propio deja las esquinas de las celdas cuadradas.
        tarjeta = QFrame(w)
        tarjeta.setObjectName("audTablaCard")
        lay_tarjeta = QVBoxLayout(tarjeta)
        lay_tarjeta.setContentsMargins(8, 8, 8, 8)

        table = QTableWidget(0, 5, tarjeta)
        table.setObjectName("audTabla")
        table.setHorizontalHeaderLabels(
            ["FECHA", "USUARIO", "ACCIÓN", "ENTIDAD", "DETALLE"]
        )
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        for columna in (0, 2, 3):
            header.setSectionResizeMode(columna, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Fecha y Acción van centradas: su título también.
        for columna in (0, 2):
            item_cabecera = table.horizontalHeaderItem(columna)
            if item_cabecera:
                item_cabecera.setTextAlignment(Qt.AlignCenter)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(self.ALTO_FILA_AUDITORIA)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setFocusPolicy(Qt.NoFocus)
        table.setMinimumHeight(360)
        lay_tarjeta.addWidget(table)
        self.auditoria_table = table
        layout.addWidget(tarjeta, 1)

        # Carga diferida: corre cuando la ventana ya está visible.
        QTimer.singleShot(0, self.cargar_auditoria_panel)
        return w

    @staticmethod
    def _formatear_fecha_auditoria(valor):
        if not valor:
            return ""
        try:
            fecha = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
            return fecha.strftime("%d/%m/%Y  %H:%M")
        except (TypeError, ValueError):
            return str(valor).replace("T", " ")[:16]

    @staticmethod
    def _color_accion(accion):
        texto = (accion or "").upper()
        if any(clave in texto for clave in (
            "ELIMINAR", "ANULAR", "LIMPIAR", "BAJA",
        )):
            return QColor("#B91C1C")
        if any(clave in texto for clave in (
            "ACTUALIZAR", "CAMBIAR", "EDITAR", "MODIFICAR",
        )):
            return QColor("#B45309")
        if any(clave in texto for clave in (
            "CREAR", "REGISTRAR", "IMPORTAR", "ASIGNAR", "SORTEAR",
        )):
            return QColor("#15803D")
        return QColor("#1E54B7")

    @staticmethod
    def _estilo_chip_accion(accion):
        """Nombre del estilo del chip según el tipo de acción (mismas reglas que _color_accion)."""
        texto = (accion or "").upper()
        if any(clave in texto for clave in (
            "ELIMINAR", "ANULAR", "LIMPIAR", "BAJA",
        )):
            return "audChipEliminar"
        if any(clave in texto for clave in (
            "ACTUALIZAR", "CAMBIAR", "EDITAR", "MODIFICAR",
        )):
            return "audChipActualizar"
        if any(clave in texto for clave in (
            "CREAR", "REGISTRAR", "IMPORTAR", "ASIGNAR", "SORTEAR",
        )):
            return "audChipCrear"
        return "audChipOtro"

    def cargar_auditoria_panel(self):
        try:
            params = {}
            accion = self.txt_filtro_accion.text().strip()
            entidad = self.txt_filtro_entidad.text().strip()
            if accion:
                params["accion"] = accion
            if entidad:
                params["entidad"] = entidad
            response = requests.get(
                f"{self.api_base_url}/admin/auditoria",
                params=params,
                headers=self._auth_headers(),
                timeout=5,
            )
            data = response.json() if response.status_code == 200 else []
            if not isinstance(data, list):
                data = []

            self.auditoria_table.setUpdatesEnabled(False)
            # setRowCount(0) también elimina los chips de la carga anterior.
            self.auditoria_table.setRowCount(0)
            self.auditoria_table.setRowCount(len(data))
            for row, item in enumerate(data):
                id_usuario = item.get("id_usuario")
                nombre_usuario = (
                    item.get("usuario_nombre")
                    or item.get("usuario")
                    or (f"Usuario {id_usuario}" if id_usuario else "—")
                )
                accion_texto = str(item.get("accion") or "")
                detalle = str(item.get("detalle") or "")
                valores = (
                    self._formatear_fecha_auditoria(item.get("fecha_hora")),
                    str(nombre_usuario),
                    accion_texto,
                    str(item.get("entidad_afectada") or ""),
                    detalle,
                )
                for column, valor in enumerate(valores):
                    if column == 2:
                        # La acción se dibuja como chip; la celda guarda el dato.
                        celda = _item_centrado("", accion_texto)
                        celda.setToolTip(accion_texto)
                        self.auditoria_table.setItem(row, column, celda)
                        if accion_texto:
                            self.auditoria_table.setCellWidget(
                                row, column,
                                _chip_accion(
                                    accion_texto,
                                    self._estilo_chip_accion(accion_texto),
                                ),
                            )
                        continue

                    celda = QTableWidgetItem(valor)
                    celda.setTextAlignment(
                        Qt.AlignVCenter
                        | (Qt.AlignCenter if column == 0 else Qt.AlignLeft)
                    )
                    if column == 0:
                        celda.setForeground(QBrush(QColor("#475569")))
                    elif column == 1:
                        fuente = celda.font()
                        fuente.setBold(True)
                        celda.setFont(fuente)
                        partes = [str(nombre_usuario)]
                        if item.get("usuario"):
                            partes.append(f"Usuario: {item.get('usuario')}")
                        if id_usuario:
                            partes.append(f"ID: {id_usuario}")
                        celda.setToolTip("\n".join(partes))
                    elif column == 3:
                        celda.setForeground(QBrush(QColor("#475569")))
                    elif column == 4 and detalle:
                        celda.setToolTip(detalle)
                    self.auditoria_table.setItem(row, column, celda)

            self.lbl_auditoria_total.setText(
                f"{len(data)} registro" + ("" if len(data) == 1 else "s")
            )
        except (requests.RequestException, ValueError):
            self.auditoria_table.setRowCount(0)
            self.lbl_auditoria_total.setText("0 registros")
        finally:
            self.auditoria_table.setUpdatesEnabled(True)
import requests
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit, QFrame,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QBrush, QColor


class AuditoriaMixin:
    ESTILOS_AUDITORIA = """
        QWidget#auditoriaRoot { background: #F5F8FC; }
        QLabel#audTitulo {
            color: #0F2C59; font-size: 22px; font-weight: 800;
            background: transparent;
        }
        QLabel#audSub {
            color: #64748B; font-size: 12px; background: transparent;
        }
        QLabel#audTotal {
            background: #E8F0FD; color: #1E54B7;
            border-radius: 11px; padding: 5px 12px;
            font-size: 12px; font-weight: 700;
        }
        QFrame#audPanel {
            background: #FFFFFF; border: 1px solid #E2E8F0;
            border-radius: 14px;
        }
        QLineEdit#audFiltro {
            background: #F8FAFC; border: 1px solid #D5DEE9;
            border-radius: 9px; padding: 9px 12px;
            font-size: 13px; color: #0F172A;
        }
        QLineEdit#audFiltro:hover { border-color: #A9BBD1; }
        QLineEdit#audFiltro:focus {
            border: 2px solid #1E54B7; padding: 8px 11px;
            background: #FFFFFF;
        }
        QPushButton#audBoton {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 9px; padding: 0 20px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#audBoton:hover   { background: #17449A; }
        QPushButton#audBoton:pressed { background: #12367D; }
        QTableWidget#audTabla {
            background: #FFFFFF; alternate-background-color: #F8FAFC;
            border: 1px solid #E2E8F0; border-radius: 12px;
            gridline-color: #EEF2F7;
            selection-background-color: #E8F0FD;
            selection-color: #0F2C59;
        }
        QTableWidget#audTabla::item { padding: 6px 10px; }
        QHeaderView::section {
            background: #F1F5F9; color: #475569;
            border: none; border-bottom: 1px solid #DDE5EF;
            padding: 10px; font-size: 11px; font-weight: 800;
        }
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
        btn_filtrar.setMinimumHeight(40)
        btn_filtrar.clicked.connect(self.cargar_auditoria_panel)

        filtros.addWidget(self.txt_filtro_accion, 1)
        filtros.addWidget(self.txt_filtro_entidad, 1)
        filtros.addWidget(btn_filtrar)
        layout.addWidget(panel)

        table = QTableWidget(0, 5, w)
        table.setObjectName("audTabla")
        table.setHorizontalHeaderLabels(
            ["Fecha", "Usuario", "Acción", "Entidad", "Detalle"]
        )
        header = table.horizontalHeader()
        header.setHighlightSections(False)
        for columna in (0, 2, 3):
            header.setSectionResizeMode(columna, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        header.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(46)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setMinimumHeight(360)
        self.auditoria_table = table
        layout.addWidget(table, 1)

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
            self.auditoria_table.clearContents()
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
                    celda = QTableWidgetItem(valor)
                    celda.setTextAlignment(
                        Qt.AlignVCenter
                        | (Qt.AlignCenter if column in (0, 2) else Qt.AlignLeft)
                    )
                    if column == 1:
                        fuente = celda.font()
                        fuente.setBold(True)
                        celda.setFont(fuente)
                        partes = [str(nombre_usuario)]
                        if item.get("usuario"):
                            partes.append(f"Usuario: {item.get('usuario')}")
                        if id_usuario:
                            partes.append(f"ID: {id_usuario}")
                        celda.setToolTip("\n".join(partes))
                    elif column == 2:
                        fuente = celda.font()
                        fuente.setBold(True)
                        celda.setFont(fuente)
                        celda.setForeground(QBrush(self._color_accion(accion_texto)))
                    elif column == 3:
                        celda.setForeground(QBrush(QColor("#475569")))
                    elif column == 4 and detalle:
                        celda.setToolTip(detalle)
                    self.auditoria_table.setItem(row, column, celda)

            self.lbl_auditoria_total.setText(
                f"{len(data)} registro" + ("" if len(data) == 1 else "s")
            )
        except (requests.RequestException, ValueError):
            self.auditoria_table.clearContents()
            self.auditoria_table.setRowCount(0)
            self.lbl_auditoria_total.setText("0 registros")
        finally:
            self.auditoria_table.setUpdatesEnabled(True)

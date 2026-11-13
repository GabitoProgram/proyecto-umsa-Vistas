from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from desktop.api.client import api


class PostulantesView(QWidget):
    ESTILOS = """
        QWidget#postulantesView { background: #F1F5F9; }

        QLabel#postulantesTitulo {
            background: transparent;
            color: #0F2C59;
            font-size: 24px;
            font-weight: 800;
        }
        QLabel#postulantesSubtitulo {
            background: transparent;
            color: #64748B;
            font-size: 13px;
            font-weight: 500;
        }

        QFrame#postulantesCard {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
        }

        QLineEdit#postulantesBuscar {
            background: #F8FAFC;
            border: 1.5px solid #E2E8F0;
            border-radius: 9px;
            padding: 0 14px;
            color: #1E293B;
            font-size: 13px;
        }
        QLineEdit#postulantesBuscar:focus {
            background: #FFFFFF;
            border: 1.5px solid #2563EB;
        }

        QPushButton#postulantesActualizar,
        QPushButton#postulantesMostrarMas {
            background: #FFFFFF;
            border: 1.5px solid #D8E1EC;
            border-radius: 9px;
            color: #334155;
            font-size: 13px;
            font-weight: 600;
            padding: 0 16px;
        }
        QPushButton#postulantesActualizar:hover,
        QPushButton#postulantesMostrarMas:hover {
            background: #F8FAFC;
            border-color: #94A3B8;
        }
        QPushButton#postulantesMostrarMas {
            background: #EFF6FF;
            border-color: #BFDBFE;
            color: #2563EB;
        }
        QPushButton#postulantesMostrarMas:hover {
            background: #DBEAFE;
            border-color: #93C5FD;
        }
        QPushButton#postulantesActualizar:disabled,
        QPushButton#postulantesMostrarMas:disabled {
            background: #F1F5F9;
            border-color: #E2E8F0;
            color: #94A3B8;
        }

        QLabel#postulantesResultados {
            background: transparent;
            color: #64748B;
            font-size: 12px;
            font-weight: 500;
        }

        QTableWidget#postulantesTabla {
            background: #FFFFFF;
            alternate-background-color: #F8FAFC;
            border: none;
            border-top: 1px solid #E2E8F0;
            gridline-color: transparent;
            font-size: 13px;
            selection-background-color: #EFF6FF;
            selection-color: #1E3A8A;
        }
        QTableWidget#postulantesTabla::item {
            border-bottom: 1px solid #F1F5F9;
            padding: 0 12px;
        }
        QTableWidget#postulantesTabla::item:selected {
            background: #EFF6FF;
            color: #1E3A8A;
        }
        QTableWidget#postulantesTabla QHeaderView::section {
            background: #F8FAFC;
            border: none;
            border-bottom: 1px solid #E2E8F0;
            color: #475569;
            font-size: 11px;
            font-weight: 700;
            padding: 12px;
        }
        QTableWidget#postulantesTabla QTableCornerButton::section {
            background: #F8FAFC;
            border: none;
        }

        QWidget#chipContainer { background: transparent; }
        QLabel#chipOk {
            background: #DCFCE7;
            border-radius: 13px;
            color: #15803D;
            font-size: 11px;
            font-weight: 700;
            padding: 0 12px;
        }
        QLabel#chipWarn {
            background: #FEF3C7;
            border-radius: 13px;
            color: #B45309;
            font-size: 11px;
            font-weight: 700;
            padding: 0 12px;
        }
        QLabel#chipMuted {
            background: #F1F5F9;
            border-radius: 13px;
            color: #64748B;
            font-size: 11px;
            font-weight: 700;
            padding: 0 12px;
        }
    """

    def __init__(self):
        super().__init__()
        self.postulantes_data = []
        # La tabla carga por páginas: con miles de postulantes no conviene
        # traerlos ni dibujarlos todos de una vez.
        self._tamano_pagina = 60
        self._timer_busqueda = QTimer(self)
        self._timer_busqueda.setSingleShot(True)
        self._timer_busqueda.setInterval(300)
        self._timer_busqueda.timeout.connect(lambda: self.cargar_postulantes(True))
        self.setObjectName("postulantesView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.init_ui()
        self.setStyleSheet(self.ESTILOS)
        self.cargar_postulantes()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 28)
        layout.setSpacing(18)

        encabezado = QVBoxLayout()
        encabezado.setSpacing(4)

        lbl_titulo = QLabel("Gestión de Postulantes")
        lbl_titulo.setObjectName("postulantesTitulo")

        lbl_subtitulo = QLabel(
            "Consulta el estado biométrico y las gestiones de cada postulante."
        )
        lbl_subtitulo.setObjectName("postulantesSubtitulo")

        encabezado.addWidget(lbl_titulo)
        encabezado.addWidget(lbl_subtitulo)
        layout.addLayout(encabezado)

        tarjeta = QFrame()
        tarjeta.setObjectName("postulantesCard")
        tarjeta_layout = QVBoxLayout(tarjeta)
        tarjeta_layout.setContentsMargins(18, 18, 18, 18)
        tarjeta_layout.setSpacing(14)

        filtro_layout = QHBoxLayout()
        filtro_layout.setSpacing(10)

        self.txt_buscar = QLineEdit()
        self.txt_buscar.setObjectName("postulantesBuscar")
        self.txt_buscar.setPlaceholderText("Buscar por C.I., nombres o apellidos...")
        self.txt_buscar.setClearButtonEnabled(True)
        self.txt_buscar.setMinimumHeight(40)
        self.txt_buscar.textChanged.connect(self.filtrar_tabla)

        self.lbl_resultados = QLabel("0 postulantes")
        self.lbl_resultados.setObjectName("postulantesResultados")

        self.btn_mostrar_mas = QPushButton("Mostrar más")
        self.btn_mostrar_mas.setObjectName("postulantesMostrarMas")
        self.btn_mostrar_mas.setFixedHeight(40)
        self.btn_mostrar_mas.setCursor(Qt.PointingHandCursor)
        self.btn_mostrar_mas.setVisible(False)
        self.btn_mostrar_mas.clicked.connect(lambda: self.cargar_postulantes(False))

        self.btn_refrescar = QPushButton("Actualizar")
        self.btn_refrescar.setObjectName("postulantesActualizar")
        self.btn_refrescar.setFixedHeight(40)
        self.btn_refrescar.setCursor(Qt.PointingHandCursor)
        self.btn_refrescar.clicked.connect(lambda: self.cargar_postulantes(True))

        filtro_layout.addWidget(self.txt_buscar, 1)
        filtro_layout.addWidget(self.lbl_resultados)
        filtro_layout.addSpacing(6)
        filtro_layout.addWidget(self.btn_mostrar_mas)
        filtro_layout.addWidget(self.btn_refrescar)
        tarjeta_layout.addLayout(filtro_layout)

        self.tabla = QTableWidget()
        self.tabla.setObjectName("postulantesTabla")
        self.tabla.setColumnCount(6)
        self.tabla.setHorizontalHeaderLabels([
            "ID",
            "C.I.",
            "Nombre completo",
            "Gestiones",
            "Biometría facial",
            "Biometría dactilar",
        ])

        cabecera = self.tabla.horizontalHeader()
        cabecera.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        cabecera.setHighlightSections(False)
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(2, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(3, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        cabecera.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        self.tabla.verticalHeader().setVisible(False)
        self.tabla.verticalHeader().setDefaultSectionSize(52)
        self.tabla.setShowGrid(False)
        self.tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setWordWrap(False)
        self.tabla.setTextElideMode(Qt.ElideRight)
        self.tabla.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tabla.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)

        tarjeta_layout.addWidget(self.tabla, 1)
        layout.addWidget(tarjeta, 1)

    def cargar_postulantes(self, reiniciar=True):
        consulta = self.txt_buscar.text().strip()
        if reiniciar:
            self.postulantes_data = []
        self.btn_refrescar.setEnabled(False)
        nuevos = api.listar_postulantes(
            skip=len(self.postulantes_data),
            limit=self._tamano_pagina,
            q=consulta or None,
        )
        self.postulantes_data.extend(nuevos)
        self.poblar_tabla(self.postulantes_data)
        self.btn_refrescar.setEnabled(True)
        self.btn_mostrar_mas.setVisible(len(nuevos) >= self._tamano_pagina)

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
            gestiones = p.get("gestiones") or []
            if isinstance(gestiones, str):
                gestiones = [gestiones]
            gestiones = [
                str(gestion).strip()
                for gestion in gestiones
                if str(gestion).strip()
            ]

            tiene_rostro = p.get("tiene_rostro", False)
            rostro_registrado = p.get("rostro_registrado", tiene_rostro)
            cant_huellas = p.get("cantidad_huellas", 0)

            item_id = QTableWidgetItem(id_val)
            item_id.setTextAlignment(Qt.AlignCenter)
            item_ci = QTableWidgetItem(ci_val)
            item_ci.setTextAlignment(Qt.AlignCenter)
            item_nombre = QTableWidgetItem(nombre)
            item_nombre.setToolTip(nombre)

            texto_gestiones = " · ".join(gestiones) or "Sin gestiones"
            item_gestiones = QTableWidgetItem(texto_gestiones)
            item_gestiones.setToolTip(
                "\n".join(gestiones)
                if gestiones
                else "El postulante no tiene inscripciones registradas."
            )
            if not gestiones:
                item_gestiones.setForeground(QColor("#94A3B8"))

            if tiene_rostro:
                facial = ("HABILITADO", "chipOk")
            elif rostro_registrado:
                facial = ("POR HABILITAR", "chipWarn")
            else:
                facial = ("PENDIENTE", "chipMuted")

            if cant_huellas >= 2:
                dactilar = (f"{cant_huellas}/10", "chipOk")
            elif cant_huellas > 0:
                dactilar = (f"{cant_huellas}/10", "chipWarn")
            else:
                dactilar = ("PENDIENTE", "chipMuted")

            self.tabla.setItem(row_idx, 0, item_id)
            self.tabla.setItem(row_idx, 1, item_ci)
            self.tabla.setItem(row_idx, 2, item_nombre)
            self.tabla.setItem(row_idx, 3, item_gestiones)
            self.tabla.setCellWidget(row_idx, 4, self._chip(*facial))
            self.tabla.setCellWidget(row_idx, 5, self._chip(*dactilar))

    @staticmethod
    def _chip(texto, estilo):
        contenedor = QWidget()
        contenedor.setObjectName("chipContainer")
        contenedor.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        fila = QHBoxLayout(contenedor)
        # Margen inferior de 1px más que el superior para no tapar la
        # línea divisoria de la fila.
        fila.setContentsMargins(6, 8, 6, 9)
        fila.setSpacing(0)

        chip = QLabel(texto)
        chip.setObjectName(estilo)
        chip.setAlignment(Qt.AlignCenter)
        chip.setFixedHeight(26)
        chip.setAttribute(Qt.WA_TransparentForMouseEvents, True)

        # Qt.AlignCenter evita que el chip se estire a toda la altura de la celda.
        fila.addWidget(chip, 0, Qt.AlignCenter)
        return contenedor

    def filtrar_tabla(self, texto: str):
        # La búsqueda va al servidor (con espera): así encuentra postulantes
        # que todavía no se cargaron en la tabla.
        self._timer_busqueda.start()
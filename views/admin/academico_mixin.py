from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from desktop.views.admin.postulantes_mixin import (
    BotonImportarExcel,
    ContenedorCarnets,
    ZonaCargaExcel,
)


# ----------------------------------------------------------------------
# Íconos de línea dibujados en código (sin emojis ni archivos externos)
# ----------------------------------------------------------------------
def _pixmap_icono(nombre, color, ancho=26, alto=20):
    pm = QPixmap(ancho * 2, alto * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.translate(0, (alto - 18) / 2)
    p.setPen(QPen(QColor(color), 1.7, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)

    if nombre == "mas":
        p.drawLine(QPointF(9, 3.5), QPointF(9, 14.5))
        p.drawLine(QPointF(3.5, 9), QPointF(14.5, 9))

    elif nombre == "atras":
        ruta = QPainterPath()
        ruta.moveTo(11, 3.5)
        ruta.lineTo(5.5, 9)
        ruta.lineTo(11, 14.5)
        p.drawPath(ruta)

    elif nombre == "persona":
        p.drawEllipse(QPointF(9, 6), 3, 3)
        ruta = QPainterPath()
        ruta.moveTo(3.5, 15)
        ruta.cubicTo(4, 10.5, 14, 10.5, 14.5, 15)
        p.drawPath(ruta)

    elif nombre == "calendario":
        p.drawRoundedRect(QRectF(2.5, 4, 13, 11.5), 2, 2)
        p.drawLine(QPointF(2.5, 7.5), QPointF(15.5, 7.5))
        p.drawLine(QPointF(6, 2.5), QPointF(6, 5.5))
        p.drawLine(QPointF(12, 2.5), QPointF(12, 5.5))

    elif nombre == "subir":
        p.drawLine(QPointF(9, 12), QPointF(9, 3.5))
        flecha = QPainterPath()
        flecha.moveTo(5.5, 7)
        flecha.lineTo(9, 3.5)
        flecha.lineTo(12.5, 7)
        p.drawPath(flecha)
        bandeja = QPainterPath()
        bandeja.moveTo(3, 11)
        bandeja.lineTo(3, 14.5)
        bandeja.lineTo(15, 14.5)
        bandeja.lineTo(15, 11)
        p.drawPath(bandeja)

    elif nombre == "lupa":
        p.drawEllipse(QPointF(8, 8), 4.8, 4.8)
        p.drawLine(QPointF(11.6, 11.6), QPointF(15.5, 15.5))

    p.end()
    return pm


def _icono(nombre, color, ancho=26):
    return QIcon(_pixmap_icono(nombre, color, ancho))


class AcademicoMixin:
    # Los estilos usan objectName para no filtrarse a widgets de otras vistas
    # ni a los botones que otros mixins colocan dentro de las tablas.
    ESTILOS_ACADEMICO = """
        /* Las etiquetas nunca heredan fondo ni borde de reglas generales de
           ventanas superiores (los QLabel con color propio lo definen por ID). */
        QLabel { background: transparent; border: none; }

        QScrollArea { background: transparent; border: none; }
        QWidget#carnetsContenido { background: transparent; }

        /* ---------- Encabezado de página ---------- */
        QLabel#breadcrumb  { color: #64748B; font-size: 12px; font-weight: 600; }
        QLabel#paginaTitulo { color: #0F2C59; font-size: 26px; font-weight: 800; }
        QLabel#paginaSub   { color: #64748B; font-size: 13px; }
        QLabel#chip {
            background: #E8F0FD; color: #1E54B7;
            border-radius: 12px; padding: 5px 14px;
            font-size: 12px; font-weight: 700;
        }

        /* ---------- Botones ---------- */
        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover   { background: #17449A; }
        QPushButton#btnPrimario:pressed { background: #12367D; }

        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnSecundario:hover   { background: #F1F5F9; border: 1px solid #B6C3D4; }
        QPushButton#btnSecundario:pressed { background: #E2E8F0; }

        QPushButton#btnExito {
            background: #16A34A; color: #FFFFFF; border: none;
            border-radius: 10px; padding: 0 18px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnExito:hover   { background: #15803D; }
        QPushButton#btnExito:pressed { background: #166534; }

        QPushButton#btnFantasma {
            background: transparent; color: #475569; border: none;
            border-radius: 8px; padding: 0 12px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnFantasma:hover { background: #E2E8F0; color: #0F172A; }

        /* ---------- Tarjeta contenedora y tablas ---------- */
        QFrame#panel {
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            border-radius: 14px;
        }
        QTableWidget#tablaNav {
            background: #FFFFFF;
            alternate-background-color: #F8FAFD;
            border: none;
            outline: none;
            gridline-color: transparent;
            color: #1E293B;
            font-size: 13px;
            selection-background-color: #E3EEFC;
            selection-color: #0F2C59;
        }
        QTableWidget#tablaNav::item { padding: 6px 10px; border: none; }
        QTableWidget#tablaNav QHeaderView::section {
            background: #F8FAFC; color: #64748B;
            border: none; border-bottom: 1px solid #E2E8F0;
            padding: 12px 10px; font-size: 12px; font-weight: 700;
        }
        QTableWidget#tablaNav QTableCornerButton::section { background: #F8FAFC; border: none; }

        /* ---------- Buscador ---------- */
        QLineEdit#buscador {
            background: #FFFFFF; border: 1px solid #D5DEE9;
            border-radius: 10px; padding: 8px 12px;
            font-size: 14px; color: #0F172A;
            selection-background-color: #BFD6F6; selection-color: #0F172A;
        }
        QLineEdit#buscador:hover { border: 1px solid #A9BBD1; }
        QLineEdit#buscador:focus { border: 2px solid #1E54B7; padding: 7px 11px; }

        /* ---------- Carnet de postulante ---------- */
        QFrame#carnet {
            background: #FFFFFF;
            border: 1px solid #DDE5EF;
            border-radius: 14px;
        }
        QFrame#carnet:hover { border: 1px solid #8FB2E8; }
        QFrame#carnet[seleccionado="true"] { border: 1px solid #1E54B7; background: #FAFCFF; }

        QFrame#carnetCabecera {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #0F2C59, stop:1 #1F5FA8);
            border: none;
            border-top-left-radius: 13px;
            border-top-right-radius: 13px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }
        QLabel#carnetMarca { color: #C9DDF5; }
        QLabel#pillOk {
            background: #DCFCE7; color: #166534;
            border-radius: 9px; padding: 3px 10px;
            font-size: 10px; font-weight: 700;
        }
        QLabel#pillPendiente {
            background: #FEF3C7; color: #92400E;
            border-radius: 9px; padding: 3px 10px;
            font-size: 10px; font-weight: 700;
        }
        QLabel#carnetNombre { color: #0F172A; font-size: 15px; font-weight: 800; }
        QLabel#carnetCI     { color: #64748B; font-size: 12px; font-weight: 600; }
        QLabel#carreraChip {
            background: #EEF3FB; color: #1E4E96;
            border-radius: 8px; padding: 3px 9px;
            font-size: 11px; font-weight: 600;
        }
        QLabel#carreraChipVacio {
            background: #F1F5F9; color: #94A3B8;
            border-radius: 8px; padding: 3px 9px;
            font-size: 11px; font-weight: 600;
        }
        QFrame#carnetPie {
            background: transparent; border: none;
            border-top: 1px solid #EEF2F7;
        }

        /* Botones de acción dentro del carnet */
        QPushButton[tono] {
            border-radius: 8px; padding: 0 8px;
            font-size: 11px; font-weight: 700;
        }
        QPushButton[tono="exito"] { background: #DCFCE7; color: #166534; border: 1px solid #86EFAC; }
        QPushButton[tono="exito"]:hover { background: #BBF7D0; }
        QPushButton[tono="aviso"] { background: #FEF3C7; color: #92400E; border: 1px solid #FCD34D; }
        QPushButton[tono="aviso"]:hover { background: #FDE68A; }
        QPushButton[tono="neutro"] {
            background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1; font-weight: 600;
        }
        QPushButton[tono="neutro"]:hover { background: #F1F5F9; }
        QPushButton[tono="info"] { background: #E8F0FD; color: #1E54B7; border: 1px solid #BFD3F7; }
        QPushButton[tono="info"]:hover { background: #D6E4FB; }

        QLabel#estadoVacio { color: #64748B; font-size: 14px; padding: 56px 24px; }

        /* ---------- Scrollbar ---------- */
        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #C3D2E0; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #9FB6CB; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
    """

    # ------------------------------------------------------------------
    # Piezas reutilizables
    # ------------------------------------------------------------------
    def _estilizar_boton(self, boton, tipo="primario", icono=None):
        nombres = {
            "primario": "btnPrimario",
            "secundario": "btnSecundario",
            "exito": "btnExito",
            "fantasma": "btnFantasma",
        }
        boton.setObjectName(nombres[tipo])
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFocusPolicy(Qt.NoFocus)
        boton.setMinimumHeight(40)
        if icono:
            color = "#FFFFFF" if tipo in ("primario", "exito") else "#334155"
            boton.setIcon(_icono(icono, color))
            boton.setIconSize(QSize(26, 20))
        return boton

    def _crear_boton_nav(self, texto, tipo="primario", icono=None):
        return self._estilizar_boton(QPushButton(texto), tipo, icono)

    def _crear_cabecera_pagina(self, ruta, titulo, subtitulo, volver=None, acciones=()):
        """Encabezado: [Volver] ruta / título + subtítulo / acciones a la derecha."""
        caja = QVBoxLayout()
        caja.setSpacing(8)

        fila_ruta = QHBoxLayout()
        fila_ruta.setSpacing(8)
        if volver is not None:
            fila_ruta.addWidget(volver)
        lbl_ruta = QLabel(ruta)
        lbl_ruta.setObjectName("breadcrumb")
        fila_ruta.addWidget(lbl_ruta)
        fila_ruta.addStretch()
        caja.addLayout(fila_ruta)

        fila_titulo = QHBoxLayout()
        fila_titulo.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo.setObjectName("paginaTitulo")
        lbl_sub = QLabel(subtitulo)
        lbl_sub.setObjectName("paginaSub")
        textos.addWidget(titulo)
        textos.addWidget(lbl_sub)
        fila_titulo.addLayout(textos, 1)
        for boton in acciones:
            fila_titulo.addWidget(boton, 0, Qt.AlignBottom)
        caja.addLayout(fila_titulo)
        return caja

    def _crear_tabla_nav(self, columnas, indice_acciones, anchos=None, ancho_acciones=220):
        tabla = QTableWidget(0, len(columnas))
        tabla.setObjectName("tablaNav")
        tabla.setHorizontalHeaderLabels(columnas)

        cabecera = tabla.horizontalHeader()
        cabecera.setSectionResizeMode(0, QHeaderView.Stretch)
        cabecera.setSectionResizeMode(indice_acciones, QHeaderView.Fixed)
        cabecera.resizeSection(indice_acciones, ancho_acciones)
        cabecera.setHighlightSections(False)
        cabecera.setStretchLastSection(False)
        cabecera.setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        for columna, ancho in (anchos or {}).items():
            cabecera.resizeSection(columna, ancho)

        tabla.verticalHeader().setVisible(False)
        tabla.verticalHeader().setDefaultSectionSize(60)
        tabla.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        tabla.setFrameShape(QFrame.NoFrame)
        tabla.setShowGrid(False)
        tabla.setAlternatingRowColors(True)
        tabla.setEditTriggers(QTableWidget.NoEditTriggers)
        tabla.setSelectionBehavior(QTableWidget.SelectRows)
        return tabla

    def _envolver_en_panel(self, widget):
        panel = QFrame()
        panel.setObjectName("panel")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.addWidget(widget)
        return panel

    @staticmethod
    def _crear_pagina():
        pagina = QWidget()
        layout = QVBoxLayout(pagina)
        layout.setContentsMargins(32, 26, 32, 24)
        layout.setSpacing(18)
        return pagina, layout

    # ------------------------------------------------------------------
    # Vista principal
    # ------------------------------------------------------------------
    def _crear_academico_view(self):
        self.academico_stack = QStackedWidget()
        self.academico_stack.setStyleSheet(self.ESTILOS_ACADEMICO)
        self.gestion_nav_title = QLabel("Gestiones")
        self.carrera_nav_title = QLabel("Carreras")
        self.examen_nav_title = QLabel("Exámenes")
        self.gestion_nav_id = None
        self.carrera_nav_id = None
        self.gestiones_nav = []
        self.carreras_nav = []
        self.examenes_nav = []

        # ── PÁGINA 1: GESTIONES ──
        pagina_gestiones, layout = self._crear_pagina()
        lbl_g = QLabel("Gestiones académicas")
        btn_nueva = self._crear_boton_nav("Nueva gestión", "primario", "mas")
        btn_nueva.clicked.connect(self.crear_gestion_nav)
        layout.addLayout(self._crear_cabecera_pagina(
            "Académico  ›  Gestiones",
            lbl_g,
            "Administra los periodos académicos y accede a sus carreras y exámenes.",
            acciones=(btn_nueva,),
        ))

        self.gestiones_nav_table = self._crear_tabla_nav(
            ["Gestión", "Año", "Estado", "Acciones"], 3, anchos={1: 120, 2: 150}
        )
        layout.addWidget(self._envolver_en_panel(self.gestiones_nav_table), 1)

        # ── PÁGINA 2: CARRERAS ──
        pagina_carreras, layout_carreras = self._crear_pagina()
        volver_gestion = self._crear_boton_nav("Volver", "fantasma", "atras")
        volver_gestion.clicked.connect(lambda: self.academico_stack.setCurrentIndex(0))
        btn_nueva_carrera = self._crear_boton_nav("Nueva carrera", "primario", "mas")
        btn_nueva_carrera.clicked.connect(self.crear_carrera_nav)
        btn_postulantes = self._crear_boton_nav("Postulantes de la gestión", "secundario", "persona")
        btn_postulantes.clicked.connect(self.abrir_postulantes_gestion)
        layout_carreras.addLayout(self._crear_cabecera_pagina(
            "Académico  ›  Gestiones  ›  Carreras",
            self.carrera_nav_title,
            "Carreras de la gestión seleccionada y acceso a sus exámenes.",
            volver=volver_gestion,
            acciones=(btn_postulantes, btn_nueva_carrera),
        ))

        self.carreras_nav_table = self._crear_tabla_nav(
            ["Carrera", "Código", "Acciones"], 2, anchos={1: 160}
        )
        layout_carreras.addWidget(self._envolver_en_panel(self.carreras_nav_table), 1)

        # ── PÁGINA 3: EXÁMENES ──
        pagina_examenes, layout_examenes = self._crear_pagina()
        volver_carrera = self._crear_boton_nav("Volver", "fantasma", "atras")
        volver_carrera.clicked.connect(lambda: self.academico_stack.setCurrentIndex(1))
        btn_nuevo_examen = self._crear_boton_nav("Programar examen", "primario", "calendario")
        btn_nuevo_examen.clicked.connect(self.crear_examen_nav)
        layout_examenes.addLayout(self._crear_cabecera_pagina(
            "Académico  ›  Gestiones  ›  Carreras  ›  Exámenes",
            self.examen_nav_title,
            "Exámenes programados para la carrera seleccionada.",
            volver=volver_carrera,
            acciones=(btn_nuevo_examen,),
        ))

        self.examenes_nav_table = self._crear_tabla_nav(
            ["Materia", "Fecha", "Horario", "Acciones"], 3, anchos={1: 160, 2: 180}
        )
        layout_examenes.addWidget(self._envolver_en_panel(self.examenes_nav_table), 1)

        # ── PÁGINA 4: POSTULANTES (carnets) ──
        pagina_postulantes, layout_postulantes = self._crear_pagina()
        layout_postulantes.setSpacing(14)

        self.postulantes_nav_title = QLabel("Postulantes de la gestión")
        volver_carreras = self._crear_boton_nav("Volver", "fantasma", "atras")
        volver_carreras.clicked.connect(lambda: self.academico_stack.setCurrentIndex(1))
        btn_nuevo_postulante = self._crear_boton_nav("Nuevo postulante", "primario", "mas")
        btn_nuevo_postulante.clicked.connect(self.crear_postulante_gestion)
        btn_importar_postulantes = BotonImportarExcel("Importar Excel")
        self._estilizar_boton(btn_importar_postulantes, "exito", "subir")
        btn_importar_postulantes.clicked.connect(self.importar_postulantes_gestion)
        btn_importar_postulantes.archivo_recibido.connect(self.importar_excel_desde_archivo)
        layout_postulantes.addLayout(self._crear_cabecera_pagina(
            "Académico  ›  Gestiones  ›  Carreras  ›  Postulantes",
            self.postulantes_nav_title,
            "Busca postulantes, registra su biometría o edita sus datos. "
            "Doble clic sobre un carnet para editarlo.",
            volver=volver_carreras,
            acciones=(btn_importar_postulantes, btn_nuevo_postulante),
        ))

        fila_filtro = QHBoxLayout()
        fila_filtro.setSpacing(12)
        self.buscar_postulantes_gestion = QLineEdit()
        self.buscar_postulantes_gestion.setObjectName("buscador")
        self.buscar_postulantes_gestion.setPlaceholderText(
            "Buscar por C.I., nombres o apellidos…"
        )
        self.buscar_postulantes_gestion.setMinimumHeight(44)
        self.buscar_postulantes_gestion.setClearButtonEnabled(True)
        self.buscar_postulantes_gestion.addAction(
            _icono("lupa", "#94A3B8", ancho=20), QLineEdit.LeadingPosition
        )
        paleta = self.buscar_postulantes_gestion.palette()
        paleta.setColor(QPalette.PlaceholderText, QColor("#94A3B8"))
        self.buscar_postulantes_gestion.setPalette(paleta)
        self.buscar_postulantes_gestion.textChanged.connect(
            self._filtrar_carnets_postulantes
        )
        self.postulantes_nav_contador = QLabel("0 postulantes")
        self.postulantes_nav_contador.setObjectName("chip")
        fila_filtro.addWidget(self.buscar_postulantes_gestion, 1)
        fila_filtro.addWidget(self.postulantes_nav_contador)
        layout_postulantes.addLayout(fila_filtro)

        # Objetivo grande para arrastrar el archivo: el botón es chico y es
        # fácil no darle.
        self.zona_carga_excel = ZonaCargaExcel()
        self.zona_carga_excel.archivo_recibido.connect(self.importar_excel_desde_archivo)
        self.zona_carga_excel.seleccionar_archivo.connect(self.importar_postulantes_gestion)
        layout_postulantes.addWidget(self.zona_carga_excel)

        # Los postulantes se muestran como carnets en lugar de tabla.
        self.carnets_nav = ContenedorCarnets()
        layout_postulantes.addWidget(self.carnets_nav, 1)

        # Tabla oculta solo por compatibilidad: si algún otro módulo todavía
        # hace referencia a ``postulantes_nav_table`` no fallará.
        self.postulantes_nav_table = QTableWidget(0, 5, pagina_postulantes)
        self.postulantes_nav_table.hide()

        for pagina in (pagina_gestiones, pagina_carreras, pagina_examenes, pagina_postulantes):
            self.academico_stack.addWidget(pagina)
        self.cargar_gestiones_nav()
        return self.academico_stack
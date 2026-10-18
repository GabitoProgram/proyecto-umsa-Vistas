import requests
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, Signal
from desktop.config.app_config import AppConfig


class _EmisorContador(QObject):
    listo = Signal(object)  # lista de contadores, o None si falló


class _TareaContador(QRunnable):
    """Consulta los contadores en un hilo aparte para no congelar la ventana."""

    def __init__(self, emisor, url, headers):
        super().__init__()
        self._emisor = emisor
        self._url = url
        self._headers = headers

    def run(self):
        datos = None
        try:
            respuesta = requests.get(self._url, headers=self._headers, timeout=2)
            if respuesta.status_code == 200:
                datos = respuesta.json()
        except (requests.RequestException, ValueError):
            datos = None
        self._emisor.listo.emit(datos)


class ContadorMixin:
    def actualizar_contador(self):
        """Pide los contadores sin bloquear: la pantalla se actualiza al llegar."""
        id_examen = self.info_examen.get("id_examen")
        if not id_examen:
            return
        if getattr(self, "_contador_en_curso", False):
            return  # ya hay una consulta en camino

        if getattr(self, "_emisor_contador", None) is None:
            self._emisor_contador = _EmisorContador()
            self._emisor_contador.listo.connect(self._contador_recibido)
            self._pool_contador = QThreadPool()
            self._pool_contador.setMaxThreadCount(1)
            self._contador_previo = None

        self._contador_en_curso = True
        app_key = AppConfig.get_app_key()
        self._pool_contador.start(_TareaContador(
            self._emisor_contador,
            f"{self.api_base_url}/examenes/activos-ahora/contadores",
            {"X-App-Key": app_key} if app_key else {},
        ))

    def _contador_recibido(self, contadores):
        self._contador_en_curso = False
        id_examen = self.info_examen.get("id_examen")
        if contadores is None or not id_examen:
            return

        # Si nada cambió no se toca la pantalla (evita parpadeos y trabajo inútil).
        clave = (id_examen, contadores)
        if clave == self._contador_previo:
            return
        self._contador_previo = clave

        self._actualizar_resumen(contadores, id_examen)
        self._actualizar_tarjetas_cursos(contadores)
        data = next(
            (item for item in contadores if item.get("id_examen") == id_examen),
            {},
        )
        self._actualizar_ultimos(data.get("ultimos_ingresos", []))

    def _actualizar_resumen(self, contadores, id_examen):
        data = next(
            (item for item in contadores if item.get("id_examen") == id_examen),
            {},
        )
        total = data.get("total_asignados", 0)
        ingresados = data.get("total_ingresados", 0)
        pendientes = data.get("total_pendientes", max(0, total - ingresados))
        porcentaje = data.get("porcentaje_asistencia", 0.0)

        self.lbl_contador_numero.setText(str(ingresados))
        self.lbl_contador_total.setText(f"de {total} postulantes")
        self.lbl_contador_pendientes.setText(f"{pendientes} pendientes")
        self.lbl_contador_porcentaje.setText(f"{porcentaje:.1f}% de asistencia")
        self.progress_asistencia.setValue(int(porcentaje))

    def _actualizar_tarjetas_cursos(self, contadores):
        while self.cursos_layout.count():
            item = self.cursos_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not contadores:
            empty = QLabel("No hay cursos activos en este momento")
            empty.setObjectName("emptyCourses")
            self.cursos_layout.addWidget(empty, 0, 0)
            return

        for index, contador in enumerate(contadores):
            card = self._crear_tarjeta_curso(contador)
            self.cursos_layout.addWidget(card, index // 3, index % 3)

    def _crear_tarjeta_curso(self, contador):
        card = QFrame()
        card.setObjectName("courseCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel(contador.get("curso", "Curso"))
        title.setObjectName("courseTitle")
        subject = QLabel(contador.get("materia", "Examen"))
        subject.setObjectName("courseSubject")
        title_row.addWidget(title)
        title_row.addStretch()
        title_row.addWidget(subject)
        layout.addLayout(title_row)

        entered = contador.get("total_ingresados", 0)
        pending = contador.get("total_pendientes", 0)
        attendance = contador.get("porcentaje_asistencia", 0.0)
        attendance_label = QLabel(f"{entered} ingresaron  ·  {pending} pendientes")
        attendance_label.setObjectName("courseAttendance")
        layout.addWidget(attendance_label)

        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(int(attendance))
        progress.setFormat(f"{attendance:.1f}% de asistencia")
        progress.setAlignment(Qt.AlignCenter)
        progress.setObjectName("courseProgress")
        layout.addWidget(progress)

        seats_row = QHBoxLayout()
        occupied = contador.get("asientos_ocupados", 0)
        free = contador.get("asientos_libres", 0)
        total_seats = contador.get("total_asientos", 0)
        occupied_label = QLabel(f"● {occupied} ocupados")
        occupied_label.setObjectName("occupiedLabel")
        free_label = QLabel(f"○ {free} libres")
        free_label.setObjectName("freeLabel")
        seats_row.addWidget(occupied_label)
        seats_row.addStretch()
        seats_row.addWidget(free_label)
        layout.addLayout(seats_row)

        capacity = QLabel(f"Capacidad asignada: {total_seats} asientos")
        capacity.setObjectName("courseCapacity")
        layout.addWidget(capacity)
        return card

    def _actualizar_ultimos(self, ultimos):
        self.tabla_ultimos.setRowCount(len(ultimos))
        for row, item in enumerate(ultimos):
            values = (
                item.get("hora", ""),
                item.get("metodo", ""),
                item.get("resultado", ""),
                item.get("estacion", ""),
            )
            for column, value in enumerate(values):
                self.tabla_ultimos.setItem(row, column, QTableWidgetItem(str(value)))

    def _construir_tab_contador(self):
        tab_contador = QWidget()
        tab_contador.setObjectName("counterTab")
        tab_contador.setAttribute(Qt.WA_StyledBackground, True)
        tab_contador.setStyleSheet("""
            QWidget#counterTab { background: #F1F5F9; }

            /* Evita los bloques blancos */
            QScrollArea { background: transparent; border: 0; }
            QScrollArea > QWidget > QWidget { background: transparent; }
            QWidget#coursesContainer { background: transparent; }

            /* HERO */
            QFrame#counterHero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F2A57, stop:0.6 #17497C, stop:1 #1F7A8C);
                border-radius: 20px;
            }
            QFrame#counterHero QLabel { background: transparent; }
            QLabel#counterEyebrow { color: #A9D6EE; font-size: 11px; font-weight: 800; }
            QLabel#counterNumber  { color: #FFFFFF; font-size: 60px; font-weight: 900; }
            QLabel#counterTotal   { color: #D3ECF7; font-size: 16px; font-weight: 600; }
            QLabel#counterPending, QLabel#counterPercent {
                color: #E6F4FA; font-size: 13px; font-weight: 700;
            }
            QProgressBar#mainProgress {
                min-height: 12px; max-height: 12px;
                border: 0; border-radius: 6px; background: rgba(255,255,255,0.18);
            }
            QProgressBar#mainProgress::chunk { border-radius: 6px; background: #7DE2C3; }

            /* TÍTULOS */
            QLabel#sectionTitle {
                color: #17365D; font-size: 15px; font-weight: 800; background: transparent;
            }

            /* TARJETAS */
            QFrame#courseCard {
                background: #FFFFFF; border: 1px solid #DCE5EF; border-radius: 16px;
            }
            QFrame#courseCard:hover { border: 1px solid #4FA9D1; }
            QFrame#courseCard QLabel { background: transparent; }
            QLabel#courseTitle      { color: #163A63; font-size: 16px; font-weight: 800; }
            QLabel#courseSubject    { color: #54718E; font-size: 11px; font-weight: 700; }
            QLabel#courseAttendance { color: #36536F; font-size: 12px; font-weight: 600; }
            QLabel#courseCapacity   { color: #7890A7; font-size: 11px; }
            QLabel#occupiedLabel    { color: #C8503E; font-size: 12px; font-weight: 700; }
            QLabel#freeLabel        { color: #1F7A64; font-size: 12px; font-weight: 700; }
            QLabel#emptyCourses     { color: #71869D; font-size: 14px; padding: 24px; }

            /* Texto OSCURO para que se lea sobre pista clara y sobre la barra */
            QProgressBar#courseProgress {
                min-height: 18px; max-height: 18px;
                border: 0; border-radius: 9px;
                text-align: center; color: #12354F;
                font-size: 10px; font-weight: 800;
                background: #E3EAF2;
            }
            QProgressBar#courseProgress::chunk { border-radius: 9px; background: #6FD3B8; }

            /* TABLA */
            QTableWidget#historyTable {
                background: #FFFFFF;
                alternate-background-color: #F5F9FD;
                border: 1px solid #DCE5EF; border-radius: 10px;
                gridline-color: transparent;
                color: #294661;
                selection-background-color: #D9EAF7;
                selection-color: #12354F;
            }
            QTableWidget#historyTable::item { padding: 6px; border: 0; }
            QHeaderView::section {
                background: #EAF1F7; color: #355572;
                border: 0; padding: 8px; font-weight: 700;
            }
            QTableCornerButton::section { background: #EAF1F7; border: 0; }

            /* SCROLLBAR */
            QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
            QScrollBar::handle:vertical { background: #C3D2E0; border-radius: 4px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background: #9FB6CB; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        """)
        layout = QVBoxLayout(tab_contador)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("counterHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        hero_layout.setSpacing(3)

        eyebrow = QLabel("ASISTENCIA EN VIVO")
        eyebrow.setObjectName("counterEyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(eyebrow)

        self.lbl_contador_numero = QLabel("0")
        self.lbl_contador_numero.setObjectName("counterNumber")
        self.lbl_contador_numero.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.lbl_contador_numero)

        self.lbl_contador_total = QLabel("de 0 postulantes")
        self.lbl_contador_total.setObjectName("counterTotal")
        self.lbl_contador_total.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.lbl_contador_total)

        self.progress_asistencia = QProgressBar()
        self.progress_asistencia.setRange(0, 100)
        self.progress_asistencia.setValue(0)
        self.progress_asistencia.setFormat("")
        self.progress_asistencia.setObjectName("mainProgress")
        hero_layout.addWidget(self.progress_asistencia)

        bottom = QHBoxLayout()
        self.lbl_contador_pendientes = QLabel("0 pendientes")
        self.lbl_contador_pendientes.setObjectName("counterPending")
        self.lbl_contador_porcentaje = QLabel("0.0% de asistencia")
        self.lbl_contador_porcentaje.setObjectName("counterPercent")
        bottom.addWidget(self.lbl_contador_pendientes)
        bottom.addStretch()
        bottom.addWidget(self.lbl_contador_porcentaje)
        hero_layout.addLayout(bottom)
        layout.addWidget(hero)

        section_title = QLabel("Cursos y ocupación de asientos")
        section_title.setObjectName("sectionTitle")
        layout.addWidget(section_title)

        courses_scroll = QScrollArea()
        courses_scroll.setWidgetResizable(True)
        courses_scroll.setFrameShape(QFrame.NoFrame)
        courses_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        courses = QWidget()
        courses.setObjectName("coursesContainer")
        self.cursos_layout = QGridLayout(courses)
        self.cursos_layout.setContentsMargins(2, 2, 2, 2)
        self.cursos_layout.setSpacing(12)
        courses_scroll.setWidget(courses)
        layout.addWidget(courses_scroll, stretch=1)

        history_title = QLabel("Últimos ingresos registrados")
        history_title.setObjectName("sectionTitle")
        layout.addWidget(history_title)

        self.tabla_ultimos = QTableWidget(0, 4)
        self.tabla_ultimos.setHorizontalHeaderLabels(
            ["Hora", "Método", "Resultado", "Estación"]
        )
        self.tabla_ultimos.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.tabla_ultimos.setObjectName("historyTable")
        self.tabla_ultimos.setMaximumHeight(170)
        self.tabla_ultimos.setAlternatingRowColors(True)
        self.tabla_ultimos.verticalHeader().setVisible(False)
        self.tabla_ultimos.setShowGrid(False)
        self.tabla_ultimos.setEditTriggers(QTableWidget.NoEditTriggers)
        self.tabla_ultimos.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.tabla_ultimos)

        self.tabs.addTab(tab_contador, "Contador en Vivo")
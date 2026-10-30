import math

import requests
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
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


def _repintar(widget):
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    for hijo in widget.findChildren(QWidget):
        hijo.style().unpolish(hijo)
        hijo.style().polish(hijo)
    widget.update()


def _entero(valor, defecto=0):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


def _acotar(valor, total):
    """El numerador nunca pasa el total. Así no aparece 4 de 3 ni más de 100%."""
    valor = max(0, _entero(valor))
    total = max(0, _entero(total))
    if total > 0:
        valor = min(valor, total)
    return valor, total


def _porcentaje(valor, total):
    valor, total = _acotar(valor, total)
    if total <= 0:
        return 0
    return max(0, min(100, int(round(valor * 100 / total))))


def _estado_capacidad(contador):
    """Rojo si la sala está llena. Amarillo si solo cerró la asignación. Si no, verde.

    Si las dos cosas pasan a la vez, gana el rojo: ya no caben más personas.
    """
    ocupados = _entero(contador.get("asientos_ocupados"))
    total_asientos = _entero(contador.get("total_asientos"))
    libres = contador.get("asientos_libres")
    libres = max(0, total_asientos - ocupados) if libres is None else max(0, _entero(libres))

    asignados = _entero(contador.get("total_asignados"))
    ingresados = _entero(contador.get("total_ingresados"))
    pendientes = contador.get("total_pendientes")
    pendientes = max(0, asignados - ingresados) if pendientes is None else max(0, _entero(pendientes))

    capacidad_llena = total_asientos > 0 and (ocupados >= total_asientos or libres <= 0)
    asignacion_completa = asignados > 0 and (pendientes <= 0 or ingresados >= asignados)

    if capacidad_llena:
        return "lleno", "Capacidad al máximo"
    if asignacion_completa:
        return "asignado", "Asignación completa"
    if total_asientos <= 0 and asignados <= 0:
        return "disponible", "Sin datos de cupo"
    return "disponible", "Con cupo"


class _AnilloCursos(QWidget):
    """Contador grande al centro y una tarjeta por aula en el borde."""

    def __init__(self, centro, parent=None):
        super().__init__(parent)
        self._centro = centro
        self._tarjetas = []
        self._vacio = QLabel("No hay cursos activos en este momento")
        self._vacio.setObjectName("emptyCourses")
        self._vacio.setAlignment(Qt.AlignCenter)
        centro.setParent(self)
        self._vacio.setParent(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(720, 520)

    def set_tarjetas(self, tarjetas):
        for vieja in self._tarjetas:
            vieja.hide()
            vieja.setParent(None)
            vieja.deleteLater()
        self._tarjetas = list(tarjetas)
        for tarjeta in self._tarjetas:
            tarjeta.setParent(self)
            tarjeta.show()
            _repintar(tarjeta)
        self._vacio.setVisible(not self._tarjetas)
        self._reubicar()

    def set_mensaje_vacio(self, mensaje):
        self._vacio.setText(mensaje)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._reubicar()

    def _reubicar(self):
        ancho = max(self.width(), 1)
        alto = max(self.height(), 1)
        n = len(self._tarjetas)

        if n > 10:
            lado = min(int(ancho * 0.26), int(alto * 0.32), 300)
            tw, th = 156, 86
        elif n > 6:
            lado = min(int(ancho * 0.30), int(alto * 0.36), 340)
            tw, th = 188, 96
        else:
            lado = min(int(ancho * 0.34), int(alto * 0.42), 400)
            tw, th = 220, 108

        lado = max(lado, 220)
        alto_centro = int(lado * 0.92)
        self._centro.setGeometry(
            (ancho - lado) // 2,
            (alto - alto_centro) // 2,
            lado,
            alto_centro,
        )
        self._vacio.setGeometry(0, alto - 36, ancho, 28)

        if n == 0:
            self._centro.raise_()
            return

        margen = 10
        rx = max(70, (ancho - tw) / 2 - margen)
        ry = max(50, (alto - th) / 2 - margen)
        hueco = (2 * math.pi * ((rx + ry) / 2)) / n
        if hueco < tw + 14:
            tw = max(148, int(hueco - 14))

        cx = ancho / 2
        cy = alto / 2
        for i, tarjeta in enumerate(self._tarjetas):
            angulo = (-math.pi / 2) + (2 * math.pi * i / n)
            x = cx + math.cos(angulo) * rx - tw / 2
            y = cy + math.sin(angulo) * ry - th / 2
            tarjeta.setGeometry(int(round(x)), int(round(y)), tw, th)

        self._centro.raise_()


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

    def _actualizar_resumen(self, contadores, id_examen):
        data = next(
            (item for item in contadores if item.get("id_examen") == id_examen),
            {},
        )
        total = _entero(data.get("total_asignados"))
        ingresados, total = _acotar(data.get("total_ingresados"), total)
        pendientes = max(0, total - ingresados)
        porcentaje = _porcentaje(ingresados, total)

        self.lbl_contador_numero.setText(str(ingresados))
        self.lbl_contador_total.setText(f"de {total} postulantes")
        self.lbl_contador_pendientes.setText(f"{pendientes} pendientes")
        self.lbl_contador_porcentaje.setText(f"{porcentaje}% de asistencia")
        self.progress_asistencia.setRange(0, 100)
        self.progress_asistencia.setValue(porcentaje)

        estado, texto = _estado_capacidad(data)
        self.lbl_contador_estado.setText(texto)
        self._pintar_estado(self.lbl_contador_estado, estado)

    def _actualizar_tarjetas_cursos(self, contadores):
        tarjetas = []
        id_actual = self.info_examen.get("id_examen")
        for examen in list(contadores or []):
            if examen.get("id_examen") != id_actual:
                continue
            for aula in examen.get("aulas") or []:
                tarjetas.append(self._crear_tarjeta_aula(aula, examen))
        # No mostrar aulas de otros exámenes: confundía al operador.
        if not tarjetas:
            self._anillo.set_mensaje_vacio(
                "Este examen no tiene aulas asignadas todavía."
            )
        self._anillo.set_tarjetas(tarjetas)

    def _pintar_estado(self, widget, estado):
        widget.setProperty("estado", estado)
        if widget.parent() is not None:
            _repintar(widget)

    def _crear_tarjeta_aula(self, aula, examen=None):
        examen = examen or {}
        es_actual = examen.get("id_examen") == self.info_examen.get("id_examen")

        ocupados = _entero(aula.get("asientos_ocupados"))
        total_asientos = _entero(aula.get("total_asientos"))
        libres = aula.get("asientos_libres")
        libres = max(0, total_asientos - ocupados) if libres is None else max(0, _entero(libres))

        ingresados = _entero(aula.get("postulantes_ingresados"))
        if aula.get("faltan_ingresar") is None:
            pendientes = max(0, _entero(aula.get("asientos_ocupados")) - ingresados)
        else:
            pendientes = max(0, _entero(aula.get("faltan_ingresar")))
        # Los asignados son los que entraron más los que faltan, no los asientos ocupados.
        asignados = ingresados + pendientes

        contador_fake = {
            "asientos_ocupados": ocupados,
            "total_asientos": total_asientos,
            "asientos_libres": libres,
            "total_asignados": asignados,
            "total_ingresados": ingresados,
            "total_pendientes": pendientes,
        }
        estado, texto_estado = _estado_capacidad(contador_fake)

        ocupados_vista, total_vista = _acotar(ocupados, total_asientos)
        libres_vista = min(libres, max(0, total_vista - ocupados_vista))
        ingresados_vista, asignados_vista = _acotar(ingresados, asignados)
        pendientes_vista = max(0, asignados_vista - ingresados_vista)

        card = QFrame()
        card.setObjectName("courseCard")
        card.setAttribute(Qt.WA_StyledBackground, True)
        card.setProperty("activo", es_actual)

        fila = QHBoxLayout(card)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        franja = QFrame()
        franja.setObjectName("courseStripe")
        franja.setFixedWidth(7)
        fila.addWidget(franja)

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(10, 8, 10, 8)
        cuerpo.setSpacing(2)
        fila.addLayout(cuerpo)

        titulo_fila = QHBoxLayout()
        titulo = QLabel(str(aula.get("nombre") or "Aula"))
        titulo.setObjectName("courseTitle")
        materia = QLabel(str(examen.get("materia") or examen.get("curso") or ""))
        materia.setObjectName("courseSubject")
        materia.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        titulo_fila.addWidget(titulo, stretch=1)
        if materia.text():
            titulo_fila.addWidget(materia)
        cuerpo.addLayout(titulo_fila)

        estado_lbl = QLabel(texto_estado + ("  ·  este examen" if es_actual else ""))
        estado_lbl.setObjectName("courseState")
        cuerpo.addWidget(estado_lbl)

        asientos = QLabel(f"Asientos  {ocupados_vista}/{total_vista}   ·   {libres_vista} libres")
        asientos.setObjectName("courseMeta")
        asignacion = QLabel(
            f"Asignación  {ingresados_vista}/{asignados_vista}   ·   {pendientes_vista} pend."
        )
        asignacion.setObjectName("courseMeta")
        cuerpo.addWidget(asientos)
        cuerpo.addWidget(asignacion)

        progreso = QProgressBar()
        progreso.setObjectName("courseProgress")
        progreso.setRange(0, 100)
        progreso.setValue(_porcentaje(ocupados, total_asientos) if total_asientos else _porcentaje(ingresados, asignados))
        progreso.setTextVisible(False)
        progreso.setFixedHeight(7)
        self._pintar_estado(progreso, estado)
        cuerpo.addWidget(progreso)

        self._pintar_estado(card, estado)
        return card

    def _construir_tab_contador(self):
        tab_contador = QWidget()
        tab_contador.setObjectName("counterTab")
        tab_contador.setAttribute(Qt.WA_StyledBackground, True)
        tab_contador.setStyleSheet("""
            QWidget#counterTab { background: #F1F5F9; }

            QFrame#counterHero {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0F2A57, stop:0.6 #17497C, stop:1 #1F7A8C);
                border-radius: 28px;
            }
            QFrame#counterHero QLabel { background: transparent; }
            QLabel#counterEyebrow { color: #A9D6EE; font-size: 11px; font-weight: 800; }
            QLabel#counterNumber  { color: #FFFFFF; font-size: 58px; font-weight: 900; }
            QLabel#counterTotal   { color: #D3ECF7; font-size: 15px; font-weight: 600; }
            QLabel#counterPending, QLabel#counterPercent {
                color: #E6F4FA; font-size: 12px; font-weight: 700;
            }
            QLabel#counterState {
                font-size: 12px; font-weight: 800;
                padding: 4px 10px; border-radius: 10px;
            }
            QLabel#counterState[estado="lleno"] {
                color: #7A1E1E; background: #F6C9C4;
            }
            QLabel#counterState[estado="asignado"] {
                color: #6B4A00; background: #F8E3A8;
            }
            QLabel#counterState[estado="disponible"] {
                color: #0E5C3A; background: #B7EBD4;
            }
            QProgressBar#mainProgress {
                min-height: 12px; max-height: 12px;
                border: 0; border-radius: 6px; background: rgba(255,255,255,0.18);
            }
            QProgressBar#mainProgress::chunk {
                border-radius: 6px; background: #7DE2C3;
            }

            QLabel#sectionTitle {
                color: #17365D; font-size: 15px; font-weight: 800; background: transparent;
            }
            QLabel#legendDot { font-size: 12px; font-weight: 800; background: transparent; }
            QLabel#legendDot[estado="lleno"] { color: #C8362F; }
            QLabel#legendDot[estado="asignado"] { color: #C48A00; }
            QLabel#legendDot[estado="disponible"] { color: #1F8A5B; }
            QLabel#legendText { color: #4C647C; font-size: 12px; background: transparent; }

            QFrame#courseCard {
                background: #FFFFFF;
                border: 1px solid #D5E0EB;
                border-radius: 14px;
            }
            QFrame#courseCard[estado="lleno"] {
                background: #FFF6F5;
                border: 2px solid #E07A70;
            }
            QFrame#courseCard[estado="asignado"] {
                background: #FFFBF2;
                border: 2px solid #E3B341;
            }
            QFrame#courseCard[estado="disponible"] {
                background: #F4FBF7;
                border: 2px solid #7DCCAA;
            }
            QFrame#courseCard[activo="true"] { border-width: 3px; }
            QFrame#courseStripe { border: 0; border-radius: 0; background: #D5E0EB; }
            QFrame#courseCard[estado="lleno"] QFrame#courseStripe { background: #D64545; }
            QFrame#courseCard[estado="asignado"] QFrame#courseStripe { background: #E0A100; }
            QFrame#courseCard[estado="disponible"] QFrame#courseStripe { background: #1F9D62; }

            QFrame#courseCard QLabel { background: transparent; }
            QLabel#courseTitle { color: #163A63; font-size: 13px; font-weight: 800; }
            QLabel#courseSubject { color: #5C7892; font-size: 10px; font-weight: 700; }
            QLabel#courseMeta { color: #3E5872; font-size: 11px; font-weight: 600; }
            QLabel#courseState { font-size: 11px; font-weight: 800; }
            QFrame#courseCard[estado="lleno"] QLabel#courseState { color: #A32626; }
            QFrame#courseCard[estado="asignado"] QLabel#courseState { color: #8A5A00; }
            QFrame#courseCard[estado="disponible"] QLabel#courseState { color: #146C43; }
            QLabel#emptyCourses { color: #71869D; font-size: 13px; background: transparent; }

            QProgressBar#courseProgress {
                border: 0; border-radius: 4px; background: #E3EAF2;
            }
            QProgressBar#courseProgress[estado="lleno"]::chunk {
                border-radius: 4px; background: #D64545;
            }
            QProgressBar#courseProgress[estado="asignado"]::chunk {
                border-radius: 4px; background: #E0A100;
            }
            QProgressBar#courseProgress[estado="disponible"]::chunk {
                border-radius: 4px; background: #1F9D62;
            }
        """)

        layout = QVBoxLayout(tab_contador)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        encabezado = QHBoxLayout()
        titulo = QLabel("Aulas del examen")
        titulo.setObjectName("sectionTitle")
        encabezado.addWidget(titulo)
        encabezado.addStretch()
        for clave, nombre in (
            ("lleno", "Sala llena"),
            ("asignado", "Asignación completa"),
            ("disponible", "Con cupo"),
        ):
            punto = QLabel("●")
            punto.setObjectName("legendDot")
            self._pintar_estado(punto, clave)
            texto = QLabel(nombre)
            texto.setObjectName("legendText")
            encabezado.addWidget(punto)
            encabezado.addWidget(texto)
            encabezado.addSpacing(12)
        layout.addLayout(encabezado)

        hero = QFrame()
        hero.setObjectName("counterHero")
        hero_layout = QVBoxLayout(hero)
        hero_layout.setContentsMargins(22, 16, 22, 16)
        hero_layout.setSpacing(2)

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
        self.progress_asistencia.setTextVisible(False)
        self.progress_asistencia.setObjectName("mainProgress")
        hero_layout.addWidget(self.progress_asistencia)

        abajo = QHBoxLayout()
        self.lbl_contador_pendientes = QLabel("0 pendientes")
        self.lbl_contador_pendientes.setObjectName("counterPending")
        self.lbl_contador_porcentaje = QLabel("0% de asistencia")
        self.lbl_contador_porcentaje.setObjectName("counterPercent")
        abajo.addWidget(self.lbl_contador_pendientes)
        abajo.addStretch()
        abajo.addWidget(self.lbl_contador_porcentaje)
        hero_layout.addLayout(abajo)

        self.lbl_contador_estado = QLabel("Con cupo")
        self.lbl_contador_estado.setObjectName("counterState")
        self.lbl_contador_estado.setAlignment(Qt.AlignCenter)
        self._pintar_estado(self.lbl_contador_estado, "disponible")
        hero_layout.addWidget(self.lbl_contador_estado, alignment=Qt.AlignCenter)

        self._anillo = _AnilloCursos(hero)
        layout.addWidget(self._anillo, stretch=1)
        _repintar(tab_contador)

        self.tabs.addTab(tab_contador, "Contador en Vivo")
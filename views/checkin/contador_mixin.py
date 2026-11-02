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
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Qt, Signal
from desktop.config.app_config import AppConfig


# ---------------------------------------------------------------------------
# Hilo de consulta
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
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


def _estado_asistencia(total, ingresados):
    """Estado del día o de una carrera según cuántos postulantes ya ingresaron."""
    total = max(0, _entero(total))
    ingresados = max(0, _entero(ingresados))
    if total <= 0:
        return "sin_datos", "Sin postulantes"
    if ingresados >= total:
        return "completo", "Todos ingresaron"
    if ingresados > 0:
        return "en_curso", "En curso"
    return "pendiente", "Sin ingresos"


def _acotar_float(valor, minimo, maximo):
    return max(minimo, min(maximo, valor))


# ---------------------------------------------------------------------------
# Widgets de la tarjeta
# ---------------------------------------------------------------------------
class _EtiquetaElidida(QLabel):
    """Una línea que se corta con '…' en vez de salirse de la tarjeta."""

    def __init__(self, texto="", parent=None):
        super().__init__(texto, parent)
        self._completo = texto
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(10)

    def refrescar(self):
        elidido = self.fontMetrics().elidedText(
            self._completo, Qt.ElideRight, max(self.width(), 10)
        )
        if elidido != self.text():
            QLabel.setText(self, elidido)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refrescar()


class _TarjetaCarrera(QFrame):
    """Tarjeta de una carrera. Sus textos se escalan según el espacio disponible."""

    # (nombre del objeto, tamaño base en px, tamaño mínimo en px)
    _FUENTES = (
        ("courseTitle", 14, 10),
        ("courseBig", 28, 17),
        ("courseOf", 12, 9),
        ("coursePercent", 15, 10),
        ("courseState", 11, 9),
        ("courseMeta", 11, 9),
        ("courseBadge", 9, 7),
    )

    def __init__(self, nombre, materia, total, ingresados, estado,
                 texto_estado, es_actual):
        super().__init__()
        self._escala = None
        pendientes = max(0, total - ingresados)

        self.setObjectName("courseCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setProperty("activo", es_actual)
        self.setProperty("estado", estado)
        self.setToolTip(
            f"{nombre}\n"
            + (f"Materia: {materia}\n" if materia else "")
            + f"Inscritos: {total}\nIngresaron: {ingresados}\nFaltan: {pendientes}"
        )

        fila = QHBoxLayout(self)
        fila.setContentsMargins(0, 0, 0, 0)
        fila.setSpacing(0)

        franja = QFrame()
        franja.setObjectName("courseStripe")
        franja.setFixedWidth(8)
        fila.addWidget(franja)

        cuerpo = QVBoxLayout()
        cuerpo.setContentsMargins(12, 8, 12, 10)
        cuerpo.setSpacing(3)
        fila.addLayout(cuerpo, 1)
        cuerpo.addStretch(1)

        # Título + insignia de "tu carrera"
        arriba = QHBoxLayout()
        arriba.setSpacing(6)
        self.titulo = _EtiquetaElidida(nombre)
        self.titulo.setObjectName("courseTitle")
        arriba.addWidget(self.titulo, 1)
        cuerpo.addLayout(arriba)

        # Número grande + "de N inscritos" + porcentaje
        medio = QHBoxLayout()
        medio.setSpacing(6)
        grande = QLabel(str(ingresados))
        grande.setObjectName("courseBig")
        de = QLabel(f"de {total} inscritos")
        de.setObjectName("courseOf")
        porcentaje = QLabel(f"{_porcentaje(ingresados, total)}%")
        porcentaje.setObjectName("coursePercent")
        medio.addWidget(grande, 0, Qt.AlignBottom)
        medio.addWidget(de, 0, Qt.AlignBottom)
        medio.addStretch(1)
        medio.addWidget(porcentaje, 0, Qt.AlignBottom)
        cuerpo.addLayout(medio)

        # Barra
        self.progreso = QProgressBar()
        self.progreso.setObjectName("courseProgress")
        self.progreso.setRange(0, 100)
        self.progreso.setValue(_porcentaje(ingresados, total))
        self.progreso.setTextVisible(False)
        self.progreso.setFixedHeight(8)
        self.progreso.setProperty("estado", estado)
        cuerpo.addWidget(self.progreso)

        # Pie: estado + faltan
        pie = QHBoxLayout()
        estado_lbl = QLabel(texto_estado)
        estado_lbl.setObjectName("courseState")
        faltan = QLabel(f"Faltan {pendientes}")
        faltan.setObjectName("courseMeta")
        pie.addWidget(estado_lbl)
        pie.addStretch(1)
        pie.addWidget(faltan)
        cuerpo.addLayout(pie)
        cuerpo.addStretch(1)

    def escalar(self, factor):
        factor = round(factor * 20) / 20  # evita recalcular por cambios mínimos
        if factor == self._escala:
            return
        self._escala = factor
        for nombre, base, minimo in self._FUENTES:
            tam = max(minimo, int(round(base * factor)))
            for lbl in self.findChildren(QLabel):
                if lbl.objectName() == nombre:
                    lbl.setStyleSheet(f"font-size: {tam}px;")
        self.progreso.setFixedHeight(max(6, int(round(8 * factor))))
        QTimer.singleShot(0, self.titulo.refrescar)


# ---------------------------------------------------------------------------
# Distribución: contador al centro, tarjetas en el borde de una cuadrícula
# ---------------------------------------------------------------------------
class _AnilloCursos(QWidget):
    """
    Contador grande al centro y una tarjeta por carrera alrededor.

    Las tarjetas se colocan en las celdas del borde de una cuadrícula y el
    contador ocupa las celdas interiores. Como son zonas distintas, nunca se
    chocan, sin importar el tamaño de la pantalla. Todo se escala con el espacio.
    """

    GAP = 12
    CARD_MIN_W, CARD_MIN_H = 160, 96
    CARD_MAX_W, CARD_MAX_H = 360, 190
    HERO_MIN_W, HERO_MIN_H = 300, 170
    HERO_MAX_W, HERO_MAX_H = 860, 480

    def __init__(self, centro, parent=None):
        super().__init__(parent)
        self._centro = centro
        self._escala_centro = None
        self._tarjetas = []
        self._vacio = QLabel("No hay carreras con examen hoy")
        self._vacio.setObjectName("emptyCourses")
        self._vacio.setAlignment(Qt.AlignCenter)
        centro.setParent(self)
        self._vacio.setParent(self)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(560, 380)

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

    # -- Cálculo de la cuadrícula ---------------------------------------
    def _elegir_grilla(self, ancho, alto, n):
        """Devuelve (columnas, filas): la que deja las tarjetas más grandes."""
        gap = self.GAP
        mejor, mejor_puntaje = None, -1.0
        for cols in range(3, 9):
            for filas in range(3, 9):
                perimetro = 2 * cols + 2 * filas - 4
                if perimetro < n:
                    continue
                cw = (ancho - (cols - 1) * gap) / cols
                ch = (alto - (filas - 1) * gap) / filas
                hw = (cols - 2) * cw + (cols - 3) * gap
                hh = (filas - 2) * ch + (filas - 3) * gap
                if (cw < self.CARD_MIN_W or ch < self.CARD_MIN_H
                        or hw < self.HERO_MIN_W or hh < self.HERO_MIN_H):
                    continue
                tw = min(cw, self.CARD_MAX_W)
                th = min(ch, self.CARD_MAX_H)
                puntaje = tw * th * (0.8 + 0.2 * n / perimetro)
                if puntaje > mejor_puntaje:
                    mejor, mejor_puntaje = (cols, filas), puntaje
        if mejor:
            return mejor
        # Ventana muy pequeña: la cuadrícula más chica donde caben todas
        lado = 3
        while 2 * lado + 2 * lado - 4 < n:
            lado += 1
        return lado, lado

    @staticmethod
    def _celdas_borde(cols, filas):
        """Celdas del borde en sentido horario, empezando arriba a la izquierda."""
        return (
            [(0, c) for c in range(cols)]
            + [(r, cols - 1) for r in range(1, filas)]
            + [(filas - 1, c) for c in range(cols - 2, -1, -1)]
            + [(r, 0) for r in range(filas - 2, 0, -1)]
        )

    # -- Colocación ---------------------------------------------------------
    def _poner_centro(self, x, y, w, h):
        w, h = max(int(w), 1), max(int(h), 1)
        self._centro.setGeometry(int(x), int(y), w, h)
        self._centro.raise_()
        self._escalar_centro(_acotar_float(min(w / 460, h / 250), 0.6, 1.25))

    def _escalar_centro(self, factor):
        factor = round(factor * 20) / 20
        if factor == self._escala_centro:
            return
        self._escala_centro = factor
        reglas = {
            "counterEyebrow": (11, 8),
            "counterNumber": (58, 32),
            "counterTotal": (15, 10),
            "counterPending": (12, 9),
            "counterPercent": (12, 9),
            "counterState": (12, 9),
        }
        for lbl in self._centro.findChildren(QLabel):
            regla = reglas.get(lbl.objectName())
            if regla:
                base, minimo = regla
                lbl.setStyleSheet(
                    f"font-size: {max(minimo, int(round(base * factor)))}px;"
                )

    def _reubicar(self):
        ancho = max(self.width(), 1)
        alto = max(self.height(), 1)
        n = len(self._tarjetas)
        gap = self.GAP

        if n == 0:
            alto_util = max(alto - 36, 1)
            w = min(ancho, self.HERO_MAX_W)
            h = min(alto_util, self.HERO_MAX_H)
            self._poner_centro((ancho - w) / 2, (alto_util - h) / 2, w, h)
            self._vacio.setGeometry(0, alto - 34, ancho, 28)
            return

        cols, filas = self._elegir_grilla(ancho, alto, n)
        cw = (ancho - (cols - 1) * gap) / cols
        ch = (alto - (filas - 1) * gap) / filas

        # Contador: ocupa las celdas interiores, centrado
        rx, ry = cw + gap, ch + gap
        rw = (cols - 2) * cw + (cols - 3) * gap
        rh = (filas - 2) * ch + (filas - 3) * gap
        hw = min(rw, self.HERO_MAX_W)
        hh = min(rh, self.HERO_MAX_H)
        self._poner_centro(rx + (rw - hw) / 2, ry + (rh - hh) / 2, hw, hh)

        # Tarjetas: celdas del borde repartidas parejo; la primera arriba al centro
        celdas = self._celdas_borde(cols, filas)
        perimetro = len(celdas)
        tw = min(cw, self.CARD_MAX_W)
        th = min(ch, self.CARD_MAX_H)
        escala = _acotar_float(min(tw / 220, th / 118), 0.7, 1.6)

        for i, tarjeta in enumerate(self._tarjetas):
            indice = (int(i * perimetro / n) + cols // 2) % perimetro
            fila, col = celdas[indice]
            x = col * (cw + gap) + (cw - tw) / 2
            y = fila * (ch + gap) + (ch - th) / 2
            tarjeta.setGeometry(int(round(x)), int(round(y)), int(tw), int(th))
            tarjeta.escalar(escala)

        self._centro.raise_()


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------
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
            f"{self.api_base_url}/examenes/contadores-hoy",
            {"X-App-Key": app_key} if app_key else {},
        ))

    def _contador_recibido(self, contadores):
        self._contador_en_curso = False
        if not isinstance(contadores, dict):
            return

        # Si nada cambió no se toca la pantalla (evita parpadeos y trabajo inútil).
        clave = (self.info_examen.get("id_examen"), contadores)
        if clave == self._contador_previo:
            return
        self._contador_previo = clave

        self._actualizar_resumen(contadores)
        self._actualizar_tarjetas_carreras(contadores)

    def _actualizar_resumen(self, contadores):
        total = _entero(contadores.get("total_postulantes"))
        ingresados, total = _acotar(contadores.get("total_ingresados"), total)
        pendientes = max(0, total - ingresados)
        porcentaje = _porcentaje(ingresados, total)

        self.lbl_contador_numero.setText(str(ingresados))
        self.lbl_contador_total.setText(f"de {total} postulantes hoy")
        self.lbl_contador_pendientes.setText(f"{pendientes} pendientes")
        self.lbl_contador_porcentaje.setText(f"{porcentaje}% de asistencia")
        self.progress_asistencia.setRange(0, 100)
        self.progress_asistencia.setValue(porcentaje)

        estado, texto = _estado_asistencia(total, ingresados)
        self.lbl_contador_estado.setText(texto)
        self._pintar_estado(self.lbl_contador_estado, estado)

    def _actualizar_tarjetas_carreras(self, contadores):
        carreras = [
            item for item in (contadores.get("carreras") or [])
            if isinstance(item, dict)
        ]
        carreras.sort(key=lambda item: str(item.get("carrera") or "").casefold())
        tarjetas = [self._crear_tarjeta_carrera(item) for item in carreras]
        if not tarjetas:
            self._anillo.set_mensaje_vacio(
                "Hoy no hay carreras con examen programado."
            )
        self._anillo.set_tarjetas(tarjetas)

    def _pintar_estado(self, widget, estado):
        widget.setProperty("estado", estado)
        if widget.parent() is not None:
            _repintar(widget)

    def _crear_tarjeta_carrera(self, carrera):
        es_actual = carrera.get("id_carrera") == self.info_examen.get("id_carrera")
        nombre = str(carrera.get("carrera") or "Carrera")
        materia = str(carrera.get("materia") or "")

        total = _entero(carrera.get("total_inscritos"))
        ingresados, total = _acotar(carrera.get("total_ingresados"), total)
        estado, texto_estado = _estado_asistencia(total, ingresados)

        return _TarjetaCarrera(
            nombre, materia, total, ingresados, estado, texto_estado, es_actual
        )

    def _construir_tab_contador(self):
        tab_contador = QWidget()
        tab_contador.setObjectName("counterTab")
        tab_contador.setAttribute(Qt.WA_StyledBackground, True)
        tab_contador.setStyleSheet("""
            QWidget#counterTab { background: #F1F5F9; }

            /* ---------- Contador grande ---------- */
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
            QLabel#counterState[estado="completo"] {
                color: #0E5C3A; background: #B7EBD4;
            }
            QLabel#counterState[estado="en_curso"] {
                color: #6B4A00; background: #F8E3A8;
            }
            QLabel#counterState[estado="pendiente"] {
                color: #7A1E1E; background: #F6C9C4;
            }
            QLabel#counterState[estado="sin_datos"] {
                color: #425466; background: #E2E8F0;
            }
            QProgressBar#mainProgress {
                min-height: 12px; max-height: 12px;
                border: 0; border-radius: 6px; background: rgba(255,255,255,0.18);
            }
            QProgressBar#mainProgress::chunk {
                border-radius: 6px; background: #7DE2C3;
            }

            /* ---------- Encabezado y leyenda ---------- */
            QLabel#sectionTitle {
                color: #17365D; font-size: 15px; font-weight: 800; background: transparent;
            }
            QLabel#legendDot { font-size: 12px; font-weight: 800; background: transparent; }
            QLabel#legendDot[estado="completo"] { color: #1F8A5B; }
            QLabel#legendDot[estado="en_curso"] { color: #C48A00; }
            QLabel#legendDot[estado="pendiente"] { color: #C8362F; }
            QLabel#legendText { color: #4C647C; font-size: 12px; background: transparent; }
            QLabel#emptyCourses { color: #71869D; font-size: 13px; background: transparent; }

            /* ---------- Tarjetas de carrera ---------- */
            QFrame#courseCard {
                background: #FFFFFF;
                border: 1px solid #D5E0EB;
                border-radius: 14px;
            }
            QFrame#courseCard[estado="completo"] {
                background: #F4FBF7;
                border: 2px solid #7DCCAA;
            }
            QFrame#courseCard[estado="en_curso"] {
                background: #FFFBF2;
                border: 2px solid #E3B341;
            }
            QFrame#courseCard[estado="pendiente"] {
                background: #FFF6F5;
                border: 2px solid #E07A70;
            }
            QFrame#courseCard[estado="sin_datos"] {
                background: #F8FAFC;
                border: 2px solid #CBD5E1;
            }

            QFrame#courseStripe { border: 0; border-radius: 0; background: #D5E0EB; }
            QFrame#courseCard[estado="completo"] QFrame#courseStripe { background: #1F9D62; }
            QFrame#courseCard[estado="en_curso"] QFrame#courseStripe { background: #E0A100; }
            QFrame#courseCard[estado="pendiente"] QFrame#courseStripe { background: #D64545; }
            QFrame#courseCard[estado="sin_datos"] QFrame#courseStripe { background: #94A3B8; }

            QFrame#courseCard QLabel { background: transparent; }
            QLabel#courseTitle   { color: #163A63; font-size: 14px; font-weight: 800; }
            QLabel#courseBig     { color: #0F2A57; font-size: 28px; font-weight: 900; }
            QLabel#courseOf      { color: #5C7892; font-size: 12px; font-weight: 600; }
            QLabel#coursePercent { color: #3E5872; font-size: 15px; font-weight: 900; }
            QLabel#courseMeta    { color: #3E5872; font-size: 11px; font-weight: 700; }
            QLabel#courseState   { font-size: 11px; font-weight: 800; }

            QFrame#courseCard[estado="completo"] QLabel#courseState,
            QFrame#courseCard[estado="completo"] QLabel#coursePercent { color: #146C43; }
            QFrame#courseCard[estado="en_curso"] QLabel#courseState,
            QFrame#courseCard[estado="en_curso"] QLabel#coursePercent { color: #8A5A00; }
            QFrame#courseCard[estado="pendiente"] QLabel#courseState,
            QFrame#courseCard[estado="pendiente"] QLabel#coursePercent { color: #A32626; }
            QFrame#courseCard[estado="sin_datos"] QLabel#courseState,
            QFrame#courseCard[estado="sin_datos"] QLabel#coursePercent { color: #475569; }

            /* El selector lleva el prefijo de la tarjeta para ganarle al fondo transparente */
            QFrame#courseCard QLabel#courseBadge {
                color: #FFFFFF; background: #2563EB; border-radius: 8px;
                padding: 1px 7px; font-size: 9px; font-weight: 800;
            }

            QProgressBar#courseProgress {
                border: 0; border-radius: 4px; background: #E3EAF2;
            }
            QProgressBar#courseProgress[estado="completo"]::chunk {
                border-radius: 4px; background: #1F9D62;
            }
            QProgressBar#courseProgress[estado="en_curso"]::chunk {
                border-radius: 4px; background: #E0A100;
            }
            QProgressBar#courseProgress[estado="pendiente"]::chunk {
                border-radius: 4px; background: #D64545;
            }
            QProgressBar#courseProgress[estado="sin_datos"]::chunk {
                border-radius: 4px; background: #94A3B8;
            }
        """)

        layout = QVBoxLayout(tab_contador)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        encabezado = QHBoxLayout()
        titulo = QLabel("Carreras con examen hoy")
        titulo.setObjectName("sectionTitle")
        encabezado.addWidget(titulo)
        encabezado.addStretch()
        for clave, nombre in (
            ("completo", "Todos ingresaron"),
            ("en_curso", "En curso"),
            ("pendiente", "Sin ingresos"),
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

        eyebrow = QLabel("ASISTENCIA GENERAL DE HOY")
        eyebrow.setObjectName("counterEyebrow")
        eyebrow.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(eyebrow)

        self.lbl_contador_numero = QLabel("0")
        self.lbl_contador_numero.setObjectName("counterNumber")
        self.lbl_contador_numero.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(self.lbl_contador_numero)

        self.lbl_contador_total = QLabel("de 0 postulantes hoy")
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

        self.lbl_contador_estado = QLabel("Sin postulantes")
        self.lbl_contador_estado.setObjectName("counterState")
        self.lbl_contador_estado.setAlignment(Qt.AlignCenter)
        self._pintar_estado(self.lbl_contador_estado, "sin_datos")
        hero_layout.addWidget(self.lbl_contador_estado, alignment=Qt.AlignCenter)

        self._anillo = _AnilloCursos(hero)
        layout.addWidget(self._anillo, stretch=1)
        _repintar(tab_contador)

        self.tabs.addTab(tab_contador, "Contador en Vivo")
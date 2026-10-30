import unicodedata

import requests
from urllib.parse import quote
from PySide6.QtCore import (
    QObject, QPointF, QRectF, QRunnable, QThreadPool, Qt, QTimer, Signal,
)
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from shiboken6 import isValid

from desktop.views.dialogs.postulante_dialog import (
    DialogEditarPostulante,
    DialogNuevoPostulanteGestion,
)


# Formatos que admite la carga masiva.
_EXTENSIONES_CARGA = (".xlsx", ".xls", ".csv")

# Carnets que se dibujan por página. Con 5000 postulantes, crearlos todos
# bloqueaba la interfaz varios segundos.
PAGINA_CARNETS = 60


def _archivo_carga(mime):
    """Ruta del primer archivo de carga masiva que traiga el mime."""
    if not mime or not mime.hasUrls():
        return None
    for url in mime.urls():
        ruta = url.toLocalFile()
        if ruta.lower().endswith(_EXTENSIONES_CARGA):
            return ruta
    return None


def _tipo_mime(nombre):
    if nombre.lower().endswith(".csv"):
        return "text/csv"
    return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _normalizar(texto):
    """Minúsculas y sin tildes, para buscar sin importar acentos."""
    texto = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in texto if unicodedata.category(c) != "Mn")


def _fuente_marca(px, espaciado):
    """QSS no soporta letter-spacing; se define por código."""
    fuente = QFont()
    fuente.setPixelSize(px)
    fuente.setWeight(QFont.Bold)
    fuente.setLetterSpacing(QFont.AbsoluteSpacing, espaciado)
    return fuente


def _nombre_postulante(postulante):
    nombre = str(postulante.get("nombre_completo") or "").strip()
    if not nombre:
        nombre = f"{postulante.get('nombres', '')} {postulante.get('apellidos', '')}".strip()
    return nombre or "Sin nombre"


def _iniciales(nombre):
    partes = nombre.split()
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def _pixmap_redondeado(pixmap, ancho, alto, radio):
    """Recorta la imagen al centro con esquinas redondeadas."""
    escalado = pixmap.scaled(
        ancho, alto, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
    )
    salida = QPixmap(ancho, alto)
    salida.fill(Qt.transparent)
    pintor = QPainter(salida)
    pintor.setRenderHint(QPainter.Antialiasing)
    pintor.setRenderHint(QPainter.SmoothPixmapTransform)
    ruta = QPainterPath()
    ruta.addRoundedRect(QRectF(0, 0, ancho, alto), radio, radio)
    pintor.setClipPath(ruta)
    pintor.drawPixmap(
        (ancho - escalado.width()) // 2, (alto - escalado.height()) // 2, escalado
    )
    pintor.end()
    return salida


# Colores suaves para el avatar cuando no hay foto: (fondo, texto)
_COLORES_AVATAR = (
    ("#DBEAFE", "#1E40AF"),
    ("#DCFCE7", "#166534"),
    ("#FEF3C7", "#92400E"),
    ("#EDE9FE", "#5B21B6"),
    ("#FCE7F3", "#9D174D"),
    ("#E0F2FE", "#075985"),
)


# ======================================================================
# Importación de archivos
# ======================================================================
class BotonImportarExcel(QPushButton):
    """Botón de importación que además acepta arrastrar el archivo encima."""

    archivo_recibido = Signal(str)

    def __init__(self, texto="Importar Excel", parent=None):
        super().__init__(texto, parent)
        self.setAcceptDrops(True)
        self.setToolTip(
            "Carga masiva de postulantes.\n"
            "Formatos: .xlsx, .xls y .csv.\n"
            "También puedes arrastrar el archivo hasta este botón o hasta la "
            "zona de carga."
        )

    def dragEnterEvent(self, evento):
        if _archivo_carga(evento.mimeData()):
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dropEvent(self, evento):
        ruta = _archivo_carga(evento.mimeData())
        if ruta:
            evento.acceptProposedAction()
            self.archivo_recibido.emit(ruta)


def _icono_subir(fondo, trazo, lado=44):
    """Ícono de subida dibujado en código (flecha sobre una bandeja)."""
    pm = QPixmap(lado * 2, lado * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(fondo))
    p.drawRoundedRect(QRectF(0, 0, lado, lado), 12, 12)

    p.setPen(QPen(QColor(trazo), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.setBrush(Qt.NoBrush)
    c = lado / 2
    p.drawLine(QPointF(c, 27), QPointF(c, 13))
    flecha = QPainterPath()
    flecha.moveTo(c - 6, 19)
    flecha.lineTo(c, 13)
    flecha.lineTo(c + 6, 19)
    p.drawPath(flecha)
    bandeja = QPainterPath()
    bandeja.moveTo(12, 26)
    bandeja.lineTo(12, 32)
    bandeja.lineTo(lado - 12, 32)
    bandeja.lineTo(lado - 12, 26)
    p.drawPath(bandeja)
    p.end()
    return pm


class ZonaCargaExcel(QFrame):
    """Zona para arrastrar el archivo de carga masiva (también responde al clic)."""

    archivo_recibido = Signal(str)
    seleccionar_archivo = Signal()

    ESTILOS = """
        QFrame#zonaCarga {
            background: #F8FAFC;
            border: 2px dashed #B6C3D4;
            border-radius: 12px;
        }
        QFrame#zonaCarga:hover {
            background: #F0F6FF;
            border: 2px dashed #2F6FED;
        }
        QFrame#zonaCarga[arrastrando="true"] {
            background: #ECFDF3;
            border: 2px dashed #16A34A;
        }
        QLabel#zonaTitulo { color: #1E293B; font-size: 14px; font-weight: 700;
                            background: transparent; border: none; }
        QLabel#zonaSub    { color: #64748B; font-size: 12px;
                            background: transparent; border: none; }
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("zonaCarga")
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)
        self.setStyleSheet(self.ESTILOS)

        fila = QHBoxLayout(self)
        fila.setContentsMargins(16, 10, 16, 10)
        fila.setSpacing(14)

        self.icono = QLabel()
        self.icono.setFixedSize(44, 44)
        fila.addWidget(self.icono)

        textos = QVBoxLayout()
        textos.setSpacing(2)
        titulo = QLabel("Arrastra aquí tu archivo de postulantes")
        titulo.setObjectName("zonaTitulo")
        sub = QLabel("Formatos .xlsx, .xls o .csv. También puedes hacer clic para buscarlo.")
        sub.setObjectName("zonaSub")
        textos.addWidget(titulo)
        textos.addWidget(sub)
        fila.addLayout(textos, 1)
        self._pintar(encima=False)

    def _pintar(self, encima):
        self.setProperty("arrastrando", bool(encima))
        self.style().unpolish(self)
        self.style().polish(self)
        if encima:
            self.icono.setPixmap(_icono_subir("#D1F2DD", "#15803D"))
        else:
            self.icono.setPixmap(_icono_subir("#E0EAFB", "#2F6FED"))

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.seleccionar_archivo.emit()
        super().mousePressEvent(evento)

    def dragEnterEvent(self, evento):
        if _archivo_carga(evento.mimeData()):
            self._pintar(encima=True)
            evento.acceptProposedAction()
        else:
            evento.ignore()

    def dragMoveEvent(self, evento):
        if _archivo_carga(evento.mimeData()):
            evento.acceptProposedAction()

    def dragLeaveEvent(self, evento):
        self._pintar(encima=False)
        super().dragLeaveEvent(evento)

    def dropEvent(self, evento):
        ruta = _archivo_carga(evento.mimeData())
        self._pintar(encima=False)
        if ruta:
            evento.acceptProposedAction()
            self.archivo_recibido.emit(ruta)


# ======================================================================
# Carnet de postulante
# ======================================================================
class CarnetPostulante(QFrame):
    """Tarjeta tipo carnet con foto, datos y acciones del postulante.

    Los botones quedan expuestos (``btn_rostro``, ``btn_huella``,
    ``btn_editar``, ``btn_eliminar``) para que el mixin conecte las acciones.
    Los estilos están definidos en el stylesheet de la vista académica.
    """

    seleccionado = Signal(object)
    editar_solicitado = Signal(object)
    eliminar_solicitado = Signal(object)

    FOTO_ANCHO = 76
    FOTO_ALTO = 92

    def __init__(self, postulante, tiene_rostro, rostro_registrado, cant_huellas, parent=None):
        super().__init__(parent)
        self.setObjectName("carnet")
        self.setProperty("seleccionado", False)
        self.postulante = postulante
        self.setMinimumWidth(330)
        self.setFixedHeight(246)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        completo = bool(tiene_rostro) and cant_huellas > 0
        raiz.addWidget(self._crear_cabecera(completo))
        raiz.addLayout(self._crear_cuerpo(), 1)
        raiz.addWidget(self._crear_pie(tiene_rostro, rostro_registrado, cant_huellas))

    # -- Construcción -----------------------------------------------------
    def _crear_cabecera(self, completo):
        cabecera = QFrame()
        cabecera.setObjectName("carnetCabecera")
        cabecera.setFixedHeight(40)
        fila = QHBoxLayout(cabecera)
        fila.setContentsMargins(14, 0, 12, 0)

        marca = QLabel("UMSA  ·  MEDICINA")
        marca.setObjectName("carnetMarca")
        marca.setFont(_fuente_marca(10, 1.6))
        estado = QLabel("Biometría completa" if completo else "Biometría pendiente")
        estado.setObjectName("pillOk" if completo else "pillPendiente")

        fila.addWidget(marca, 0, Qt.AlignVCenter)
        fila.addStretch()
        fila.addWidget(estado, 0, Qt.AlignVCenter)
        return cabecera

    def _crear_cuerpo(self):
        fila = QHBoxLayout()
        fila.setContentsMargins(14, 12, 14, 10)
        fila.setSpacing(14)

        self.foto = QLabel()
        self.foto.setFixedSize(self.FOTO_ANCHO, self.FOTO_ALTO)
        self.foto.setAlignment(Qt.AlignCenter)
        self._foto_placeholder()
        fila.addWidget(self.foto, 0, Qt.AlignTop)

        columna = QVBoxLayout()
        columna.setSpacing(4)

        nombre = _nombre_postulante(self.postulante)
        lbl_nombre = QLabel(nombre if len(nombre) <= 36 else f"{nombre[:35]}…")
        lbl_nombre.setObjectName("carnetNombre")
        lbl_nombre.setWordWrap(True)
        lbl_nombre.setToolTip(nombre)
        columna.addWidget(lbl_nombre)

        lbl_ci = QLabel(f"C.I. {self.postulante.get('ci', '')}")
        lbl_ci.setObjectName("carnetCI")
        columna.addWidget(lbl_ci)
        columna.addSpacing(4)

        carreras = [
            c.get("nombre", "")
            for c in (self.postulante.get("carreras") or [])
            if c.get("nombre")
        ]
        if carreras:
            for nombre_carrera in carreras[:2]:
                columna.addLayout(self._crear_chip(
                    nombre_carrera if len(nombre_carrera) <= 24 else f"{nombre_carrera[:23]}…",
                    "carreraChip",
                    ", ".join(carreras),
                ))
            if len(carreras) > 2:
                columna.addLayout(self._crear_chip(
                    f"+{len(carreras) - 2} más", "carreraChip", ", ".join(carreras)
                ))
        else:
            columna.addLayout(self._crear_chip("Sin carreras", "carreraChipVacio", ""))

        columna.addStretch()
        fila.addLayout(columna, 1)
        return fila

    @staticmethod
    def _crear_chip(texto, objeto, tooltip):
        fila = QHBoxLayout()
        fila.setContentsMargins(0, 0, 0, 0)
        chip = QLabel(texto)
        chip.setObjectName(objeto)
        if tooltip:
            chip.setToolTip(tooltip)
        fila.addWidget(chip)
        fila.addStretch()
        return fila

    @staticmethod
    def _crear_boton(texto, tono, tooltip=""):
        boton = QPushButton(texto)
        boton.setProperty("tono", tono)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFocusPolicy(Qt.NoFocus)
        boton.setFixedHeight(32)
        if tooltip:
            boton.setToolTip(tooltip)
        return boton

    def _crear_pie(self, tiene_rostro, rostro_registrado, cant_huellas):
        pie = QFrame()
        pie.setObjectName("carnetPie")
        pie.setFixedHeight(52)
        fila = QHBoxLayout(pie)
        fila.setContentsMargins(12, 8, 12, 10)
        fila.setSpacing(8)

        # 3 estados: sin rostro (neutro), registrado sin habilitar (ámbar), habilitado (verde)
        if tiene_rostro:
            self.btn_rostro = self._crear_boton(
                "Habilitado", "exito", "Rostro habilitado. Clic para deshabilitar."
            )
        elif rostro_registrado:
            self.btn_rostro = self._crear_boton(
                "Por habilitar", "aviso",
                "Rostro registrado, pendiente de habilitación. Clic para habilitar.",
            )
        else:
            self.btn_rostro = self._crear_boton("Rostro", "neutro", "Registrar rostro")

        if cant_huellas > 0:
            self.btn_huella = self._crear_boton(
                f"Huella ({cant_huellas})", "exito", "Gestionar huellas registradas"
            )
        else:
            self.btn_huella = self._crear_boton("Huella", "neutro", "Registrar huella")

        self.btn_editar = self._crear_boton("Editar", "info", "Editar datos del postulante")
        self.btn_eliminar = self._crear_boton(
            "Eliminar", "peligro", "Eliminar definitivamente al postulante"
        )

        fila.addWidget(self.btn_rostro, 1)
        fila.addWidget(self.btn_huella, 1)
        fila.addWidget(self.btn_editar, 1)
        fila.addWidget(self.btn_eliminar, 1)
        return pie

    # -- Foto -------------------------------------------------------------
    def _foto_placeholder(self):
        nombre = _nombre_postulante(self.postulante)
        indice = sum(ord(c) for c in str(self.postulante.get("ci", nombre))) % len(_COLORES_AVATAR)
        fondo, texto = _COLORES_AVATAR[indice]
        self.foto.setText(_iniciales(nombre))
        self.foto.setToolTip("Sin foto registrada")
        self.foto.setStyleSheet(
            f"background: {fondo}; color: {texto}; border-radius: 12px;"
            "font-size: 24px; font-weight: 800;"
        )

    def poner_foto(self, datos):
        imagen = QImage()
        if not imagen.loadFromData(datos):
            return
        pixmap = QPixmap.fromImage(imagen)
        self.foto.setText("")
        self.foto.setPixmap(
            _pixmap_redondeado(pixmap, self.FOTO_ANCHO - 4, self.FOTO_ALTO - 4, 10)
        )
        self.foto.setStyleSheet(
            "background: transparent; border: 2px solid #60A5FA; border-radius: 12px;"
        )
        self.foto.setToolTip("Rostro registrado")

    # -- Selección --------------------------------------------------------
    def set_seleccionado(self, valor):
        self.setProperty("seleccionado", bool(valor))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, evento):
        self.seleccionado.emit(self)
        super().mousePressEvent(evento)

    def mouseDoubleClickEvent(self, evento):
        self.editar_solicitado.emit(self.postulante)
        super().mouseDoubleClickEvent(evento)


class ContenedorCarnets(QScrollArea):
    """Rejilla de carnets que reacomoda sus columnas según el ancho."""

    ANCHO_MIN = 330
    ESPACIO = 16

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.viewport().setAutoFillBackground(False)

        self._contenido = QWidget()
        self._contenido.setObjectName("carnetsContenido")
        self._grid = QGridLayout(self._contenido)
        self._grid.setContentsMargins(4, 4, 4, 12)
        self._grid.setSpacing(self.ESPACIO)
        self.setWidget(self._contenido)

        self._todos = []
        self._visibles = []
        self._mensaje = ""
        self._columnas = 0
        self._max_columnas = 0
        self._ultima_fila = 0

        self._vacio = QLabel("", self._contenido)
        self._vacio.setObjectName("estadoVacio")
        self._vacio.setAlignment(Qt.AlignCenter)
        self._vacio.setWordWrap(True)
        self._vacio.hide()

    def establecer(self, widgets):
        """Reemplaza todos los carnets. Después hay que llamar a ``mostrar``."""
        for widget in self._todos:
            self._grid.removeWidget(widget)
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        self._todos = list(widgets)
        for widget in self._todos:
            widget.setParent(self._contenido)

    def mostrar(self, visibles, mensaje_vacio=""):
        self._visibles = list(visibles)
        self._mensaje = mensaje_vacio
        self._reacomodar()

    def _columnas_actuales(self):
        # Se reserva el espacio de la barra de scroll para evitar saltos.
        ancho = self.width() - 26
        return max(1, (ancho + self.ESPACIO) // (self.ANCHO_MIN + self.ESPACIO))

    def _reacomodar(self):
        while self._grid.count():
            self._grid.takeAt(0)

        columnas = self._columnas = self._columnas_actuales()
        visibles = set(self._visibles)
        for widget in self._todos:
            if widget not in visibles:
                widget.hide()

        fila = columna = 0
        for widget in self._visibles:
            self._grid.addWidget(widget, fila, columna)
            widget.show()
            columna += 1
            if columna >= columnas:
                columna = 0
                fila += 1

        if self._visibles:
            self._vacio.hide()
            fila_final = fila + (1 if columna else 0)
        else:
            self._vacio.setText(self._mensaje)
            self._grid.addWidget(self._vacio, 0, 0, 1, columnas)
            self._vacio.show()
            fila_final = 1

        for c in range(max(self._max_columnas, columnas)):
            self._grid.setColumnStretch(c, 1 if c < columnas else 0)
        self._max_columnas = max(self._max_columnas, columnas)

        self._grid.setRowStretch(self._ultima_fila, 0)
        self._grid.setRowStretch(fila_final, 1)
        self._ultima_fila = fila_final

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        if self._columnas_actuales() != self._columnas:
            self._reacomodar()


# ======================================================================
# Carga de fotos en segundo plano
# ======================================================================
class _EmisorFotos(QObject):
    listo = Signal(int, object, object)  # generación, id_postulante, bytes


class _TareaFoto(QRunnable):
    def __init__(self, emisor, generacion, id_postulante, url, headers):
        super().__init__()
        self._emisor = emisor
        self._generacion = generacion
        self._id = id_postulante
        self._url = url
        self._headers = headers

    def run(self):
        try:
            respuesta = requests.get(self._url, headers=self._headers, timeout=4)
        except requests.RequestException:
            return
        if respuesta.status_code == 200 and respuesta.content:
            self._emisor.listo.emit(self._generacion, self._id, respuesta.content)


# ======================================================================
# Mixin
# ======================================================================
class PostulantesMixin:
    # -- Fotos ------------------------------------------------------------
    def _asegurar_emisor_fotos(self):
        if getattr(self, "_emisor_fotos", None) is None:
            self._emisor_fotos = _EmisorFotos()
            self._emisor_fotos.listo.connect(self._foto_recibida)
            self._pool_fotos = QThreadPool()
            self._pool_fotos.setMaxThreadCount(4)
            self._generacion_fotos = 0
            self._carnets_por_id = {}
            self._carnets_postulantes = []
            self._carnet_seleccionado = None
            self._fotos_cache = {}
            self._ultimo_filtro = None
            self._limite_carnets = PAGINA_CARNETS
            self._timer_filtro = QTimer(self)
            self._timer_filtro.setSingleShot(True)
            self._timer_filtro.setInterval(250)
            self._timer_filtro.timeout.connect(self._aplicar_filtro_carnets)

    def _foto_recibida(self, generacion, id_postulante, datos):
        if generacion != self._generacion_fotos:
            return
        self._fotos_cache[id_postulante] = datos
        carnet = self._carnets_por_id.get(id_postulante)
        if carnet is not None and isValid(carnet):
            carnet.poner_foto(datos)

    # -- Lista de postulantes ---------------------------------------------
    def abrir_postulantes_gestion(self):
        self._asegurar_emisor_fotos()
        # El backend ya devuelve los datos biométricos en esta lista; antes se
        # pedían aparte con ?limit=1000 (tope que dejaba fuera a postulantes).
        datos = self._obtener_lista(
            f"/inscripciones/gestion/{self.gestion_nav_id}/postulantes",
            timeout=15,
        )

        self.postulantes_nav_title.setText("Postulantes inscritos en la gestión")

        self._generacion_fotos += 1
        self._carnet_seleccionado = None
        self._carnets_por_id = {}
        self._carnets_postulantes = []
        self._fotos_cache = {}
        self._ultimo_filtro = None
        self._limite_carnets = PAGINA_CARNETS

        for postulante in datos:
            busqueda = _normalizar(" ".join(
                str(postulante.get(campo, ""))
                for campo in ("ci", "nombre_completo", "nombres", "apellidos")
            ))
            self._carnets_postulantes.append((postulante, busqueda))

        self._aplicar_filtro_carnets()
        self.academico_stack.setCurrentIndex(3)

    def _renderizar_carnets(self, registros):
        self._carnet_seleccionado = None
        self._carnets_por_id = {}
        widgets = []
        for postulante, _ in registros:
            carnet = self._crear_carnet(postulante, postulante)
            widgets.append(carnet)
            id_postulante = postulante.get("id_postulante")
            if not id_postulante:
                continue
            self._carnets_por_id[id_postulante] = carnet
            foto = self._fotos_cache.get(id_postulante)
            if foto:
                carnet.poner_foto(foto)
            elif (postulante.get("tiene_rostro")
                  or postulante.get("rostro_registrado")):
                self._pool_fotos.start(_TareaFoto(
                    self._emisor_fotos,
                    self._generacion_fotos,
                    id_postulante,
                    f"{self.api_base_url}/rostros/{id_postulante}/imagen",
                    self._auth_headers(),
                ))
        self.carnets_nav.establecer(widgets)
        return widgets

    # -- Habilitación masiva de rostros -----------------------------------
    def habilitar_todos_los_rostros_gestion(self):
        """Habilita el rostro registrado de todos los postulantes de la gestión."""
        self._cambiar_rostros_gestion(True)

    def deshabilitar_todos_los_rostros_gestion(self):
        """Deshabilita el rostro de todos los postulantes de la gestión."""
        self._cambiar_rostros_gestion(False)

    def _cambiar_rostros_gestion(self, habilitada):
        gestion = getattr(self, "gestion_nav_id", None)
        if not gestion:
            QMessageBox.warning(
                self, "Rostros", "Abra primero una gestión para cambiar sus rostros."
            )
            return

        accion = "habilitar" if habilitada else "deshabilitar"
        confirmacion = QMessageBox.question(
            self,
            f"{accion.capitalize()} rostros",
            (
                f"¿Desea {accion} el rostro de todos los postulantes inscritos en "
                "esta gestión?\n\n"
                "Solo se aplicará a quienes tengan un rostro registrado."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return

        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/rostros/habilitadas",
                json={"habilitada": habilitada, "id_gestion": gestion},
                headers=self._auth_headers(),
                timeout=60,
            )
            if respuesta.status_code != 200:
                try:
                    detalle = respuesta.json().get(
                        "detail", "No se pudieron actualizar los rostros."
                    )
                except ValueError:
                    detalle = respuesta.text or "No se pudieron actualizar los rostros."
                QMessageBox.warning(self, "Rostros", str(detalle))
                return

            datos = respuesta.json()
            self.abrir_postulantes_gestion()
            estado = "habilitados" if habilitada else "deshabilitados"
            QMessageBox.information(
                self,
                "Rostros",
                (
                    f"Se {estado} {datos.get('cambiados', 0)} rostro(s).\n"
                    f"Postulantes con rostro registrado: {datos.get('con_rostro', 0)}."
                ),
            )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(
                self, "Error de red", f"No se pudo contactar al servidor: {error}"
            )

    def _crear_carnet(self, postulante, full_p):
        tiene_rostro = full_p.get("tiene_rostro", False)
        rostro_registrado = full_p.get("rostro_registrado", tiene_rostro)
        id_rostro = full_p.get("id_rostro")
        cant_huellas = full_p.get("cantidad_huellas", 0)

        carnet = CarnetPostulante(postulante, tiene_rostro, rostro_registrado, cant_huellas)

        btn_rostro = carnet.btn_rostro
        if tiene_rostro:
            btn_rostro.clicked.connect(
                lambda _, p=postulante, r=id_rostro: self.cambiar_estado_rostro_gestion(p, r, False)
            )
        elif rostro_registrado:
            btn_rostro.clicked.connect(
                lambda _, p=postulante, r=id_rostro: self.cambiar_estado_rostro_gestion(p, r, True)
            )
        else:
            btn_rostro.clicked.connect(
                lambda _, p=postulante, btn=btn_rostro: self.registrar_rostro_gestion(p, btn)
            )

        carnet.btn_huella.clicked.connect(
            lambda _, p=postulante, btn=carnet.btn_huella: self.registrar_huella_gestion(p, btn)
        )
        carnet.btn_editar.clicked.connect(
            lambda _, p=postulante: self.editar_postulante_en_fila(p)
        )
        carnet.btn_eliminar.clicked.connect(
            lambda _, p=postulante: self.eliminar_postulante_gestion(p)
        )
        carnet.btn_eliminar.setVisible(self.rol == "SUPER_ADMIN")
        carnet.seleccionado.connect(self._seleccionar_carnet)
        carnet.editar_solicitado.connect(self.editar_postulante_en_fila)
        return carnet

    def eliminar_postulante_gestion(self, postulante):
        id_post = postulante.get("id_postulante")
        if not id_post:
            QMessageBox.warning(
                self, "Postulantes",
                "No se pudo identificar al postulante que se desea eliminar.",
            )
            return

        nombre = _nombre_postulante(postulante)
        confirmacion = QMessageBox.question(
            self,
            "Eliminar postulante",
            (
                f"¿Eliminar definitivamente a {nombre} (C.I. "
                f"{postulante.get('ci', '—')})?\n\n"
                "Se eliminarán sus inscripciones y datos biométricos. Esta acción no se puede deshacer."
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return

        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/postulantes/{id_post}",
                headers=self._auth_headers(),
                timeout=8,
            )
            if respuesta.status_code == 204:
                self.abrir_postulantes_gestion()
                QMessageBox.information(
                    self, "Postulantes", "El postulante fue eliminado correctamente."
                )
                return

            try:
                detalle = respuesta.json().get(
                    "detail", "No se pudo eliminar el postulante."
                )
            except ValueError:
                detalle = respuesta.text or "No se pudo eliminar el postulante."
            QMessageBox.warning(self, "Postulantes", str(detalle))
        except requests.RequestException as error:
            QMessageBox.critical(
                self, "Error de red",
                f"No se pudo contactar al servidor: {error}",
            )

    def _seleccionar_carnet(self, carnet):
        anterior = getattr(self, "_carnet_seleccionado", None)
        if anterior is not None and isValid(anterior) and anterior is not carnet:
            anterior.set_seleccionado(False)
        self._carnet_seleccionado = carnet
        carnet.set_seleccionado(True)

    def _filtrar_carnets_postulantes(self, _texto=""):
        # Se espera a que el usuario deje de escribir: redibujar en cada tecla
        # con miles de postulantes se sentía lento.
        timer = getattr(self, "_timer_filtro", None)
        if timer is None:
            self._aplicar_filtro_carnets()
        else:
            timer.start()

    def _aplicar_filtro_carnets(self):
        caja = getattr(self, "buscar_postulantes_gestion", None)
        texto = _normalizar(caja.text().strip()) if caja is not None else ""
        total = len(self._carnets_postulantes)
        if texto != getattr(self, "_ultimo_filtro", None):
            # Cada búsqueda nueva vuelve a la primera página.
            self._ultimo_filtro = texto
            self._limite_carnets = PAGINA_CARNETS

        filtrados = [
            registro for registro in self._carnets_postulantes
            if not texto or texto in registro[1]
        ]
        limite = min(getattr(self, "_limite_carnets", PAGINA_CARNETS), len(filtrados))
        pagina = filtrados[:limite]
        # _renderizar_carnets devuelve los widgets ya creados; antes se pasaba
        # la lista de diccionarios y Qt fallaba con "unhashable type: 'dict'".
        widgets = self._renderizar_carnets(pagina)

        if total == 0:
            mensaje = ("Aún no hay postulantes inscritos en esta gestión.\n"
                       "Usa «Nuevo postulante» o importa un archivo de Excel.")
        else:
            mensaje = "Ningún postulante coincide con la búsqueda."
        self.carnets_nav.mostrar(widgets, mensaje)

        boton_mas = getattr(self, "btn_mostrar_mas_carnets", None)
        if boton_mas is not None:
            restantes = len(filtrados) - limite
            boton_mas.setVisible(restantes > 0)
            boton_mas.setText(f"Mostrar más ({restantes} restantes)")

        contador = getattr(self, "postulantes_nav_contador", None)
        if contador is not None:
            palabra = "postulante" if total == 1 else "postulantes"
            if texto:
                contador.setText(f"{len(filtrados)} de {total} {palabra}")
            elif limite < len(filtrados):
                contador.setText(f"Mostrando {limite} de {len(filtrados)} {palabra}")
            else:
                contador.setText(f"{len(filtrados)} {palabra}")

    def _mostrar_mas_carnets(self):
        self._limite_carnets = (
            getattr(self, "_limite_carnets", PAGINA_CARNETS) + PAGINA_CARNETS
        )
        self._aplicar_filtro_carnets()

    # -- Carreras e inscripción -------------------------------------------
    def seleccionar_carrera_gestion(self):
        if not self.carreras_nav:
            QMessageBox.warning(self, "Postulantes", "La gestión no tiene carreras disponibles.")
            return None
        nombres = [carrera.get("nombre", "Carrera") for carrera in self.carreras_nav]
        nombre, aceptado = QInputDialog.getItem(
            self, "Carrera", "Inscribir en:", nombres, 0, False
        )
        if not aceptado:
            return None
        return next(carrera for carrera in self.carreras_nav if carrera.get("nombre") == nombre)

    def crear_postulante_gestion(self):
        carreras = self.carreras_nav
        if not carreras:
            carreras = [c for c in self._obtener_lista("/admin/carreras") if c.get("activa", True)]
        dlg = DialogNuevoPostulanteGestion(carreras, self)
        if not dlg.exec():
            return
        datos = dlg.get_data()
        if not datos["ci"] or not datos["nombres"] or not datos["apellidos"]:
            QMessageBox.warning(self, "Postulantes", "Complete C.I., nombres y apellidos.")
            return
        seleccion = dlg.carreras_seleccionadas()
        if not seleccion:
            QMessageBox.warning(self, "Postulantes", "Seleccione al menos una carrera.")
            return
        if len(seleccion) > 2:
            QMessageBox.warning(self, "Postulantes", "Como máximo 2 carreras por gestión.")
            return
        try:
            respuesta_busqueda = requests.get(
                f"{self.api_base_url}/postulantes/buscar",
                params={"ci": datos["ci"]},
                headers=self._auth_headers(), timeout=6,
            )
            if respuesta_busqueda.status_code == 200:
                existente = respuesta_busqueda.json()
                nombre = (
                    f"{existente.get('nombres', '')} "
                    f"{existente.get('apellidos', '')}"
                ).strip()
                confirmacion = QMessageBox.question(
                    self,
                    "Postulante existente",
                    (
                        f"El C.I. {datos['ci']} ya pertenece a «{nombre}».\n\n"
                        "¿Desea inscribir este mismo postulante en la gestión actual?"
                    ),
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes,
                )
                if confirmacion != QMessageBox.Yes:
                    return
                id_postulante = existente["id_postulante"]
            elif respuesta_busqueda.status_code == 404:
                respuesta = requests.post(
                    f"{self.api_base_url}/postulantes/", json=datos,
                    headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code not in (200, 201):
                    QMessageBox.warning(
                        self, "Postulantes",
                        str(respuesta.json().get("detail", "No se pudo crear el postulante."))
                    )
                    return
                id_postulante = respuesta.json()["id_postulante"]
            else:
                QMessageBox.warning(
                    self, "Postulantes",
                    str(respuesta_busqueda.json().get("detail", "No se pudo consultar el C.I."))
                )
                return

            inscritas = 0
            errores = []
            for id_carrera in seleccion:
                inscripcion = requests.post(
                    f"{self.api_base_url}/inscripciones", json={
                        "id_postulante": id_postulante,
                        "id_gestion": self.gestion_nav_id,
                        "id_carrera": id_carrera,
                        "estado": "HABILITADO"
                    }, headers=self._auth_headers(), timeout=6
                )
                if inscripcion.status_code in (200, 201):
                    inscritas += 1
                else:
                    errores.append(str(inscripcion.json().get("detail", "No se pudo inscribir.")))

            self.abrir_postulantes_gestion()
            if errores:
                QMessageBox.warning(
                    self, "Inscripción",
                    f"Postulante creado con {inscritas} inscripción(es).\n" + "\n".join(errores)
                )
            else:
                QMessageBox.information(
                    self, "Postulantes",
                    f"Postulante registrado e inscrito en {inscritas} carrera(s)."
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Postulantes", f"Error de conexión: {error}")

    # -- Importación ------------------------------------------------------
    def importar_postulantes_gestion(self):
        archivo, _ = QFileDialog.getOpenFileName(
            self, "Importar postulantes", "",
            "Archivos de carga (*.xlsx *.xls *.csv);;Excel (*.xlsx *.xls);;CSV (*.csv)")
        if archivo:
            self.importar_excel_desde_archivo(archivo)

    def importar_excel_desde_archivo(self, archivo):
        """Sube el Excel al servidor y muestra el resultado.

        Si el archivo no trae la columna «programa» (una carrera por fila),
        el servidor lo avisa y acá preguntamos en qué carrera inscribir a
        todos antes de reintentar. Así el archivo completo de la
        institución se importa sin tocar nada.
        """
        if not self.gestion_nav_id:
            QMessageBox.warning(
                self, "Importación",
                "Abra primero una gestión para importar postulantes.")
            return

        respuesta = self._subir_excel_postulantes(archivo)
        if isinstance(respuesta, str):
            QMessageBox.critical(self, "Importación", respuesta)
            return

        if respuesta.status_code == 400 and self._falta_carrera(respuesta):
            carrera = self.seleccionar_carrera_gestion()
            if not carrera:
                return
            respuesta = self._subir_excel_postulantes(archivo, carrera["id_carrera"])
            if isinstance(respuesta, str):
                QMessageBox.critical(self, "Importación", respuesta)
                return

        if respuesta.status_code == 200:
            self.abrir_postulantes_gestion()
            QMessageBox.information(
                self, "Importación", self._resumen_importacion(respuesta.json()))
        else:
            try:
                detalle = respuesta.json().get("detail", "No se pudo importar.")
            except ValueError:
                detalle = "No se pudo importar."
            QMessageBox.warning(self, "Importación", str(detalle))

    def _subir_excel_postulantes(self, archivo, id_carrera=None):
        """Devuelve la respuesta del servidor, o el texto del error de red."""
        datos = {}
        if self.gestion_nav_id:
            datos["id_gestion"] = self.gestion_nav_id
        if id_carrera:
            datos["id_carrera"] = id_carrera
        nombre = archivo.replace("\\", "/").split("/")[-1]
        try:
            with open(archivo, "rb") as contenido:
                return requests.post(
                    f"{self.api_base_url}/postulantes/importar-excel",
                    files={"file": (nombre, contenido, _tipo_mime(nombre))},
                    data=datos, headers=self._auth_headers(), timeout=300
                )
        except (OSError, requests.RequestException) as error:
            return f"Error de conexión: {error}"

    @staticmethod
    def _falta_carrera(respuesta):
        """El servidor avisó que el Excel no traía la columna «programa»."""
        if respuesta.headers.get("X-Codigo-Error") == "falta-carrera":
            return True
        try:
            return "programa" in str(respuesta.json().get("detail", "")).lower()
        except ValueError:
            return False

    @staticmethod
    def _resumen_importacion(datos):
        """Texto legible con lo que hizo el servidor con el archivo."""
        lineas = [datos.get("mensaje", "Importación completada.")]
        carreras = datos.get("carreras_creadas") or []
        if carreras:
            lineas.append("Carreras nuevas: " + ", ".join(carreras))
        avisos = datos.get("avisos") or []
        if avisos:
            lineas.append("\nAvisos:")
            lineas.extend(f"  • {aviso}" for aviso in avisos[:15])
            if len(avisos) > 15:
                lineas.append(f"  … y {len(avisos) - 15} más.")
        return "\n".join(lineas)

    # -- Edición ----------------------------------------------------------
    def editar_postulante_gestion(self):
        """Edita el carnet seleccionado (clic sobre la tarjeta)."""
        carnet = getattr(self, "_carnet_seleccionado", None)
        if carnet is None or not isValid(carnet):
            QMessageBox.information(self, "Postulantes", "Seleccione un postulante primero.")
            return
        self.editar_postulante_en_fila(carnet.postulante)

    def editar_postulante_en_fila(self, postulante):
        # Asegurarse de tener el id_postulante y los nombres/apellidos separados
        id_post = postulante.get("id_postulante")
        if not id_post:
            # Buscar en caso de que venga de la lista de inscripciones.
            ci = postulante.get("ci")
            full_postulante = (
                self._obtener_objeto(f"/postulantes/buscar?ci={quote(str(ci))}")
                if ci else None
            )
            if not full_postulante:
                QMessageBox.warning(self, "Postulantes", "No se encontraron los detalles completos del postulante.")
                return
            postulante = full_postulante
            id_post = postulante.get("id_postulante")

        # Si la lista no trae los datos de contacto (backend anterior), se pide
        # la ficha completa; si no, el formulario los mostraría vacíos.
        if postulante.get("ci") and not any(
            campo in postulante for campo in ("telefono", "correo", "direccion")
        ):
            completo = self._obtener_objeto(
                f"/postulantes/buscar?ci={quote(str(postulante.get('ci')))}"
            )
            if completo:
                postulante = {**postulante, **completo}
                id_post = postulante.get("id_postulante") or id_post

        carreras_disponibles = []
        carreras_seleccionadas = []
        carreras_texto = None
        carreras = postulante.get("carreras") or []
        nombres = [c.get("nombre") for c in carreras if c.get("nombre")]
        if self.gestion_nav_id is not None:
            carreras_disponibles = [
                carrera for carrera in self.carreras_nav
                if carrera.get("activa", True)
            ]
            inscripciones = self._obtener_lista(
                f"/inscripciones?id_gestion={self.gestion_nav_id}"
            ) or []
            for ins in inscripciones:
                if ins.get("id_postulante") == id_post:
                    id_carrera = ins.get("id_carrera")
                    if ins.get("estado") != "RETIRADO":
                        carreras_seleccionadas.append(id_carrera)
                    carrera = next(
                        (c for c in self.carreras_nav if c.get("id_carrera") == id_carrera),
                        None,
                    )
                    nombres.append(carrera.get("nombre") if carrera else f"Carrera {id_carrera}")
        if nombres:
            carreras_texto = f"{len(nombres)} carrera(s): " + ", ".join(nombres)

        dlg = DialogEditarPostulante(
            postulante,
            self,
            carreras_texto,
            carreras_disponibles,
            carreras_seleccionadas,
        )
        if not dlg.exec():
            return

        datos_actualizados = dlg.get_data()
        if not datos_actualizados["nombres"] or not datos_actualizados["apellidos"]:
            QMessageBox.warning(self, "Postulantes", "Nombres y apellidos son obligatorios.")
            return

        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/postulantes/{id_post}",
                json=datos_actualizados,
                headers=self._auth_headers(), timeout=6
            )
            if respuesta.status_code == 200:
                if self.gestion_nav_id is not None and carreras_disponibles:
                    self._sincronizar_carreras_postulante(
                        id_post,
                        carreras_seleccionadas,
                        dlg.carreras_seleccionadas(),
                    )
                self.abrir_postulantes_gestion()
            else:
                QMessageBox.warning(self, "Postulantes", str(respuesta.json().get("detail", "No se pudo editar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Postulantes", f"Error de conexión: {error}")

    def _sincronizar_carreras_postulante(self, id_postulante, actuales, nuevas):
        if len(nuevas) > 2:
            raise ValueError("Un postulante puede tener como máximo 2 carreras por gestión.")
        inscripciones = self._obtener_lista(
            f"/inscripciones?id_gestion={self.gestion_nav_id}"
        ) or []
        por_carrera = {
            ins.get("id_carrera"): ins for ins in inscripciones
            if ins.get("id_postulante") == id_postulante
        }
        headers = self._auth_headers()
        for id_carrera in set(actuales) - set(nuevas):
            inscripcion = por_carrera.get(id_carrera)
            if inscripcion and inscripcion.get("estado") != "RETIRADO":
                respuesta = requests.patch(
                    f"{self.api_base_url}/inscripciones/{inscripcion['id_inscripcion']}",
                    json={"estado": "RETIRADO"},
                    headers=headers,
                    timeout=6,
                )
                if respuesta.status_code != 200:
                    raise ValueError("No se pudo retirar una de las carreras seleccionadas.")
        for id_carrera in set(nuevas) - set(actuales):
            if id_carrera in por_carrera and por_carrera[id_carrera].get("estado") == "RETIRADO":
                respuesta = requests.patch(
                    f"{self.api_base_url}/inscripciones/{por_carrera[id_carrera]['id_inscripcion']}",
                    json={"estado": "HABILITADO"},
                    headers=headers,
                    timeout=6,
                )
            else:
                respuesta = requests.post(
                    f"{self.api_base_url}/inscripciones",
                    json={
                        "id_postulante": id_postulante,
                        "id_gestion": self.gestion_nav_id,
                        "id_carrera": id_carrera,
                        "estado": "HABILITADO",
                    },
                    headers=headers,
                    timeout=6,
                )
            if respuesta.status_code not in (200, 201):
                detalle = respuesta.json().get("detail", "No se pudo agregar una carrera.")
                raise ValueError(str(detalle))
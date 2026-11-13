import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QComboBox,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QCheckBox, QDialogButtonBox, QFrame,
)
from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import (
    QAction, QColor, QFontMetrics, QIcon, QPainter, QPainterPath, QPen, QPixmap,
)


# ======================================================================
# Estilos
# ======================================================================
def _qss_boton(fondo, texto, borde, hover, pressed, dis_texto, dis_fondo, dis_borde):
    """QSS de un botón de tabla: mismas medidas para todos, cambian solo los colores."""
    return (
        f"QPushButton {{ background: {fondo}; color: {texto}; "
        f"border: 1px solid {borde}; border-radius: 9px; "
        "padding: 0; "          # el ancho lo fija el código, no el estilo
        "font-size: 12px; font-weight: 700; } "
        f"QPushButton:hover {{ background: {hover}; }} "
        f"QPushButton:pressed {{ background: {pressed}; }} "
        f"QPushButton:disabled {{ color: {dis_texto}; background: {dis_fondo}; "
        f"border: 1px solid {dis_borde}; }}"
    )


def _icono_ojo(tachado, color="#64748B"):
    """Icono de ojo dibujado por código (sin archivos externos).

    ``tachado=False`` → ojo abierto (la contraseña está oculta; clic para mostrar).
    ``tachado=True``  → ojo tachado (la contraseña se ve; clic para ocultar).
    Se dibuja al doble de resolución para que se vea nítido en pantallas HiDPI.
    """
    lado = 20
    pix = QPixmap(lado * 2, lado * 2)
    pix.setDevicePixelRatio(2)
    pix.fill(Qt.transparent)

    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing)
    lapiz = QPen(QColor(color), 1.7)
    lapiz.setCapStyle(Qt.RoundCap)
    lapiz.setJoinStyle(Qt.RoundJoin)
    p.setPen(lapiz)
    p.setBrush(Qt.NoBrush)

    contorno = QPainterPath()
    contorno.moveTo(2, 10)
    contorno.quadTo(10, 2, 18, 10)
    contorno.quadTo(10, 18, 2, 10)
    p.drawPath(contorno)
    p.drawEllipse(QPointF(10, 10), 2.7, 2.7)
    if tachado:
        p.drawLine(QPointF(4, 16), QPointF(16, 4))
    p.end()
    return QIcon(pix)


def _agregar_ojo(campo):
    """Agrega al final de un QLineEdit un botón-ojo y devuelve su QAction."""
    accion = QAction(campo)
    accion.setCheckable(True)
    accion.setIcon(_icono_ojo(False))
    accion.setToolTip("Mostrar contraseña")
    campo.addAction(accion, QLineEdit.TrailingPosition)
    return accion


ESTILO_DIALOGO = """
    QDialog { background: #F1F5F9; }
    QLabel { color: #334155; font-weight: 600; background: transparent; border: none; }
    QLabel#tituloDialogo { color: #0F2C59; font-size: 20px; font-weight: 800; }
    QLabel#subtituloDialogo { color: #64748B; font-size: 12px; font-weight: 500; }
    QToolTip {
        background: #0F172A; color: #FFFFFF; border: none;
        padding: 6px 10px; font-size: 12px;
    }

    /* ---------- Campos ---------- */
    QLineEdit, QComboBox {
        min-height: 36px; padding: 2px 12px;
        border: 1px solid #E2E8F0; border-radius: 9px;
        background: #FFFFFF; color: #0F172A; font-size: 13px;
    }
    QLineEdit:hover, QComboBox:hover { border: 1px solid #CBD5E1; }
    QLineEdit:focus, QComboBox:focus { border: 1px solid #1E54B7; }
    QLineEdit:read-only { background: #F8FAFC; color: #64748B; }
    QComboBox QAbstractItemView {
        background: #FFFFFF; color: #0F172A;
        border: 1px solid #E2E8F0; outline: 0;
        selection-background-color: #E8F0FD; selection-color: #0F172A;
    }

    /* ---------- Botones del diálogo ----------
       Por defecto todos son secundarios (blancos). El botón predeterminado
       (Guardar, o «Aceptar» de un cuadro de mensaje) pasa a ser el principal.
       Antes la regla ':enabled' pintaba TODOS de azul, Cancelar incluido. */
    QDialogButtonBox QPushButton {
        min-width: 110px; min-height: 36px; padding: 0 18px;
        border-radius: 9px; font-size: 13px; font-weight: 700;
        background: #FFFFFF; color: #334155; border: 1px solid #CBD5E1;
    }
    QDialogButtonBox QPushButton:hover { background: #F8FAFC; border: 1px solid #94A3B8; }
    QDialogButtonBox QPushButton:pressed { background: #EEF2F7; }

    QPushButton#btnGuardar,
    QDialogButtonBox QPushButton:default {
        background: #1E54B7; color: #FFFFFF; border: 1px solid #1E54B7;
    }
    QPushButton#btnGuardar:hover,
    QDialogButtonBox QPushButton:default:hover {
        background: #17449A; border: 1px solid #17449A;
    }
    QPushButton#btnGuardar:pressed,
    QDialogButtonBox QPushButton:default:pressed {
        background: #123A83; border: 1px solid #123A83;
    }
"""


class InterruptorEstado(QCheckBox):
    """Interruptor tipo píldora con texto «Activo» / «Inactivo».

    Es un QCheckBox por dentro (``isChecked``, ``setChecked`` y ``toggled``
    funcionan igual), pero se dibuja como un interruptor.
    """

    ANCHO_PISTA = 46
    ALTO_PISTA = 24

    def __init__(self, texto_on="Usuario activo", texto_off="Usuario inactivo", parent=None):
        super().__init__(parent)
        self._texto_on = texto_on
        self._texto_off = texto_off
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(32)
        self.setFocusPolicy(Qt.StrongFocus)

    def sizeHint(self):
        fuente = self.font()
        fuente.setBold(True)
        fuente.setPixelSize(13)
        metricas = QFontMetrics(fuente)
        ancho_texto = max(
            metricas.horizontalAdvance(self._texto_on),
            metricas.horizontalAdvance(self._texto_off),
        )
        return QSize(self.ANCHO_PISTA + 12 + ancho_texto + 4, 32)

    def minimumSizeHint(self):
        return self.sizeHint()

    def hitButton(self, pos):
        return self.rect().contains(pos)   # todo el control es clicable

    def paintEvent(self, _evento):
        activo = self.isChecked()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        y = (self.height() - self.ALTO_PISTA) / 2
        pista = QRectF(0, y, self.ANCHO_PISTA, self.ALTO_PISTA)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#16A34A" if activo else "#CBD5E1"))
        p.drawRoundedRect(pista, self.ALTO_PISTA / 2, self.ALTO_PISTA / 2)

        diametro = self.ALTO_PISTA - 6
        x = self.ANCHO_PISTA - 3 - diametro if activo else 3
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, y + 3, diametro, diametro))

        if self.hasFocus():
            p.setBrush(Qt.NoBrush)
            p.setPen(QColor("#93C5FD"))
            p.drawRoundedRect(pista.adjusted(-2, -2, 2, 2), 14, 14)

        fuente = self.font()
        fuente.setBold(True)
        fuente.setPixelSize(13)
        p.setFont(fuente)
        p.setPen(QColor("#15803D" if activo else "#64748B"))
        p.drawText(
            QRectF(self.ANCHO_PISTA + 12, 0, self.width() - self.ANCHO_PISTA - 12, self.height()),
            Qt.AlignVCenter | Qt.AlignLeft,
            self._texto_on if activo else self._texto_off,
        )
        p.end()


class DialogoUsuario(QDialog):
    def __init__(self, usuario=None, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("Editar usuario" if usuario else "Nuevo usuario")
        self.setMinimumWidth(480)
        self.setModal(True)
        self.setStyleSheet(ESTILO_DIALOGO)

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(22, 20, 22, 18)
        raiz.setSpacing(14)

        titulo = QLabel("Editar usuario" if usuario else "Nuevo usuario")
        titulo.setObjectName("tituloDialogo")
        subtitulo = QLabel(
            "Modifique los datos de la cuenta." if usuario
            else "Complete los datos para crear la cuenta."
        )
        subtitulo.setObjectName("subtituloDialogo")
        encabezado = QVBoxLayout()
        encabezado.setSpacing(2)
        encabezado.addWidget(titulo)
        encabezado.addWidget(subtitulo)
        raiz.addLayout(encabezado)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjetaDialogo")
        tarjeta.setStyleSheet(
            "QFrame#tarjetaDialogo {"
            " background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px; }"
        )
        formulario = QFormLayout(tarjeta)
        formulario.setContentsMargins(22, 18, 22, 18)
        formulario.setSpacing(12)
        formulario.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.nombre = QLineEdit(usuario.get("nombre_completo", "") if usuario else "")
        self.nombre.setPlaceholderText("Nombre y apellidos")
        self.nombre_usuario = QLineEdit(usuario.get("usuario", "") if usuario else "")
        self.nombre_usuario.setPlaceholderText("usuario.sistema")
        self.nombre_usuario.setReadOnly(bool(usuario))
        self.genero = QComboBox()
        self.genero.addItems(["No especificado", "FEMENINO", "MASCULINO", "OTRO"])
        if usuario and usuario.get("genero"):
            indice = self.genero.findText(usuario["genero"])
            if indice >= 0:
                self.genero.setCurrentIndex(indice)

        self.rol = QComboBox()
        self.rol.addItems(["ADMIN", "SUPER_ADMIN"])
        if usuario:
            self.rol.setCurrentText(usuario.get("rol", "ADMIN"))

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText(
            "Obligatoria para un usuario nuevo" if not usuario else "Dejar vacía para conservarla"
        )
        self.confirmacion = QLineEdit()
        self.confirmacion.setEchoMode(QLineEdit.Password)
        self.confirmacion.setPlaceholderText("Repita la contraseña")

        # Botón «ojo» en cada campo de contraseña. Los dos van enlazados:
        # al mostrar una se muestra también la otra, para compararlas.
        self._ojos = (_agregar_ojo(self.password), _agregar_ojo(self.confirmacion))
        for ojo in self._ojos:
            ojo.toggled.connect(self._mostrar_contrasenas)

        self.activo = InterruptorEstado()
        self.activo.setChecked(usuario.get("activo", True) if usuario else True)

        formulario.addRow("Nombre completo:", self.nombre)
        formulario.addRow("Nombre de usuario:", self.nombre_usuario)
        formulario.addRow("Género:", self.genero)
        formulario.addRow("Rol:", self.rol)
        formulario.addRow("Contraseña:", self.password)
        formulario.addRow("Confirmar contraseña:", self.confirmacion)
        formulario.addRow("Estado:", self.activo)
        raiz.addWidget(tarjeta)

        botones = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            parent=self,
        )
        guardar = botones.button(QDialogButtonBox.Save)
        cancelar = botones.button(QDialogButtonBox.Cancel)
        if guardar:
            guardar.setText("Guardar")
            guardar.setObjectName("btnGuardar")
            guardar.setCursor(Qt.PointingHandCursor)
            guardar.setDefault(True)      # Enter en un campo = Guardar
        if cancelar:
            cancelar.setText("Cancelar")
            cancelar.setObjectName("btnCancelar")
            cancelar.setCursor(Qt.PointingHandCursor)
            cancelar.setAutoDefault(False)
        botones.accepted.connect(self._validar_y_aceptar)
        botones.rejected.connect(self.reject)
        raiz.addWidget(botones, 0, Qt.AlignRight)

    def _mostrar_contrasenas(self, visible):
        """Muestra u oculta las dos contraseñas a la vez (ojo de cualquiera de ellas)."""
        for campo, ojo in ((self.password, self._ojos[0]), (self.confirmacion, self._ojos[1])):
            campo.setEchoMode(QLineEdit.Normal if visible else QLineEdit.Password)
            ojo.blockSignals(True)      # evita que un ojo dispare al otro en bucle
            ojo.setChecked(visible)
            ojo.blockSignals(False)
            ojo.setIcon(_icono_ojo(visible))
            ojo.setToolTip("Ocultar contraseña" if visible else "Mostrar contraseña")

    def _validar_y_aceptar(self):
        if not self.nombre.text().strip() or not self.nombre_usuario.text().strip():
            QMessageBox.warning(self, "Datos incompletos", "Complete el nombre y el usuario.")
            return
        password = self.password.text()
        if not self.usuario and not password:
            QMessageBox.warning(self, "Datos incompletos", "La contraseña es obligatoria.")
            return
        if password and password != self.confirmacion.text():
            QMessageBox.warning(self, "Contraseña", "Las contraseñas no coinciden.")
            return
        if password and len(password) < 8:
            QMessageBox.warning(self, "Contraseña", "Use al menos 8 caracteres.")
            return
        self.accept()

    def datos(self):
        resultado = {
            "nombre_completo": self.nombre.text().strip(),
            "genero": None if self.genero.currentIndex() == 0 else self.genero.currentText(),
            "rol": self.rol.currentText(),
            "activo": self.activo.isChecked(),
        }
        if not self.usuario:
            resultado["usuario"] = self.nombre_usuario.text().strip()
            resultado["password"] = self.password.text()
        elif self.password.text():
            resultado["password"] = self.password.text()
        return resultado


def _item_etiqueta(texto, color):
    """Celda centrada, en negrita y con color (rol y estado)."""
    item = QTableWidgetItem(texto)
    item.setTextAlignment(Qt.AlignCenter)
    item.setForeground(QColor(color))
    fuente = item.font()
    fuente.setBold(True)
    item.setFont(fuente)
    return item


def _item_centrado(texto="", dato=None):
    """Celda centrada. ``dato`` se guarda en Qt.UserRole (el texto lo dibuja un chip)."""
    item = QTableWidgetItem(texto)
    item.setTextAlignment(Qt.AlignCenter)
    if dato is not None:
        item.setData(Qt.UserRole, dato)
    return item


def _chip_tabla(texto, estilo):
    """Chip de color centrado en la celda (rol y estado).

    Alto fijo y alineación vertical al centro: así el chip nunca se estira
    hasta tocar el borde de la fila.
    """
    contenedor = QWidget()
    contenedor.setObjectName("chipContenedor")
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


class UsuariosMixin:
    ALTO_FILA = 56
    ALTO_BOTON_TABLA = 30
    # Anchos fijos: el layout de la celda calcula el tamaño antes de aplicar el
    # estilo y, con tamaños automáticos, los botones se montaban uno sobre otro.
    ANCHO_BTN_EDITAR = 88
    ANCHO_BTN_ESTADO = 112
    ANCHO_COLUMNA_ACCIONES = 248

    # Se conservan los nombres por si otra vista los usa; ahora comparten medidas.
    ESTILO_BTN_EDITAR = _qss_boton(
        "#EEF3FB", "#1E4E96", "#C9D9F2", "#DCE8FA", "#CBDBF5",
        "#94A3B8", "#F1F5F9", "#E2E8F0",
    )
    ESTILO_BTN_DESACTIVAR = _qss_boton(
        "#FFFFFF", "#B91C1C", "#FCA5A5", "#FEF2F2", "#FEE2E2",
        "#FCA5A5", "#FFFFFF", "#FEE2E2",
    )
    ESTILO_BTN_ACTIVAR = _qss_boton(
        "#F0FDF4", "#15803D", "#86EFAC", "#DCFCE7", "#BBF7D0",
        "#86EFAC", "#FFFFFF", "#DCFCE7",
    )
    ESTILO_PAGINA = """
        QWidget#paginaUsuarios { background: #F1F5F9; }
        QLabel { background: transparent; border: none; }
        QFrame#tarjetaUsuarios {
            background: #FFFFFF; border: 1px solid #E2E8F0; border-radius: 16px;
        }
        QToolTip {
            background: #0F172A; color: #FFFFFF; border: none;
            padding: 6px 10px; font-size: 12px;
        }

        /* ---------- Encabezado ---------- */
        QLabel#tituloUsuarios { color: #0F2C59; font-size: 28px; font-weight: 800; }
        QLabel#subtituloUsuarios { color: #64748B; font-size: 13px; font-weight: 500; }
        QLabel#notaUsuarios {
            color: #0E4F63; background: #E6F6FA; border: 1px solid #B5E3EE;
            border-radius: 12px; padding: 10px 16px;
            font-size: 13px; font-weight: 500;
        }

        /* ---------- Chips de rol y estado ---------- */
        QWidget#chipContenedor { background: transparent; }
        QLabel#chipRolSuper, QLabel#chipRolAdmin,
        QLabel#chipActivo, QLabel#chipInactivo {
            border-radius: 13px; padding: 0 14px;
            font-size: 11px; font-weight: 700;
        }
        QLabel#chipRolSuper { background: #E0EAFB; color: #1E4E96; }
        QLabel#chipRolAdmin { background: #F1F5F9; color: #475569; }
        QLabel#chipActivo { background: #DCFCE7; color: #15803D; }
        QLabel#chipInactivo { background: #FEE2E2; color: #B91C1C; }

        /* ---------- Tabla ---------- */
        QTableWidget {
            background: #FFFFFF; border: none; gridline-color: #EEF2F7;
            color: #0F172A; font-size: 13px; outline: 0;
            alternate-background-color: #F8FAFC;
            selection-background-color: #E8F0FD; selection-color: #0F172A;
        }
        QHeaderView::section {
            background: #F8FAFC; color: #64748B;
            border: none; border-bottom: 1px solid #E2E8F0;
            padding: 12px 10px; font-size: 11px; font-weight: 700;
        }
        QTableWidget::item { padding: 6px 12px; border-bottom: 1px solid #F1F5F9; }
        QTableWidget::item:selected { background: #E8F0FD; color: #0F172A; }
        QTableCornerButton::section { background: #F8FAFC; border: none; }
        QWidget#celdaAcciones { background: transparent; }
        QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
        QScrollBar::handle:vertical { background: #CBD5E1; border-radius: 4px; min-height: 30px; }
        QScrollBar::handle:vertical:hover { background: #94A3B8; }
        QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
        QScrollBar::handle:horizontal { background: #CBD5E1; border-radius: 4px; min-width: 30px; }
        QScrollBar::handle:horizontal:hover { background: #94A3B8; }
        QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }

        /* ---------- Botones de la cabecera ---------- */
        QPushButton#btnPrimario {
            background: #1E54B7; color: #FFFFFF; border: 1px solid #1E54B7;
            border-radius: 9px; padding: 0 18px; min-height: 36px; min-width: 120px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnPrimario:hover { background: #17449A; border: 1px solid #17449A; }
        QPushButton#btnPrimario:pressed { background: #123A83; border: 1px solid #123A83; }
        QPushButton#btnPrimario:disabled {
            background: #E2E8F0; color: #94A3B8; border: 1px solid #E2E8F0;
        }
        QPushButton#btnSecundario {
            background: #FFFFFF; color: #334155;
            border: 1px solid #CBD5E1; border-radius: 9px;
            padding: 0 18px; min-height: 36px; min-width: 110px;
            font-size: 13px; font-weight: 700;
        }
        QPushButton#btnSecundario:hover { background: #F8FAFC; border: 1px solid #94A3B8; }
        QPushButton#btnSecundario:pressed { background: #EEF2F7; }
    """

    def _es_super_admin(self):
        return self.token_data.get("rol") == "SUPER_ADMIN"

    def _seleccionar_usuario(self):
        fila = self.usuarios_table.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Usuarios", "Seleccione un usuario primero.")
            return None
        return self._usuario_de_fila(fila)

    def _usuario_de_fila(self, fila):
        item_rol = self.usuarios_table.item(fila, 3)
        return {
            "id_usuario": int(self.usuarios_table.item(fila, 0).text()),
            "usuario": self.usuarios_table.item(fila, 1).text(),
            "nombre_completo": self.usuarios_table.item(fila, 2).text(),
            # El rol se dibuja con un chip; el dato real vive en UserRole.
            "rol": item_rol.data(Qt.UserRole) or item_rol.text(),
            "activo": self.usuarios_table.item(fila, 4).data(Qt.UserRole),
        }

    def _boton_tabla(self, texto, estilo, tooltip, padre, ancho):
        """Botón de la columna Acciones: tamaño fijo, solo cambian los colores."""
        boton = QPushButton(texto, padre)
        boton.setCursor(Qt.PointingHandCursor)
        boton.setFocusPolicy(Qt.NoFocus)
        boton.setFixedSize(ancho, self.ALTO_BOTON_TABLA)
        boton.setToolTip(tooltip)
        boton.setStyleSheet(estilo)
        return boton

    def _crear_usuarios_view(self):
        w = QWidget()
        w.setObjectName("paginaUsuarios")
        w.setAttribute(Qt.WA_StyledBackground, True)
        w.setStyleSheet(self.ESTILO_PAGINA)
        layout = QVBoxLayout(w)
        layout.setContentsMargins(24, 20, 24, 18)
        layout.setSpacing(14)

        encabezado = QHBoxLayout()
        encabezado.setSpacing(10)
        textos = QVBoxLayout()
        textos.setSpacing(2)
        title = QLabel("Usuarios y roles")
        title.setObjectName("tituloUsuarios")
        subtitulo = QLabel("Administre las cuentas que pueden entrar al sistema.")
        subtitulo.setObjectName("subtituloUsuarios")
        textos.addWidget(title)
        textos.addWidget(subtitulo)
        encabezado.addLayout(textos)
        encabezado.addStretch()

        btn_nuevo = QPushButton("Nuevo usuario")
        btn_nuevo.setObjectName("btnPrimario")
        btn_nuevo.setCursor(Qt.PointingHandCursor)
        btn_nuevo.setFocusPolicy(Qt.NoFocus)
        btn_nuevo.clicked.connect(self.crear_usuario_panel)
        btn_nuevo.setEnabled(self._es_super_admin())
        if not self._es_super_admin():
            btn_nuevo.setToolTip("Solo un SUPER_ADMIN puede crear usuarios")

        btn_refrescar = QPushButton("Actualizar")
        btn_refrescar.setObjectName("btnSecundario")
        btn_refrescar.setCursor(Qt.PointingHandCursor)
        btn_refrescar.setFocusPolicy(Qt.NoFocus)
        btn_refrescar.clicked.connect(self.cargar_usuarios_panel)

        encabezado.addWidget(btn_refrescar)
        encabezado.addWidget(btn_nuevo)
        layout.addLayout(encabezado)

        nota = QLabel("Solo un SUPER_ADMIN puede crear, editar o cambiar el estado de un usuario.")
        nota.setObjectName("notaUsuarios")
        nota.setWordWrap(True)
        layout.addWidget(nota)

        tarjeta = QFrame()
        tarjeta.setObjectName("tarjetaUsuarios")
        lay_tarjeta = QVBoxLayout(tarjeta)
        lay_tarjeta.setContentsMargins(8, 8, 8, 8)

        self.usuarios_table = QTableWidget(0, 6)
        self.usuarios_table.setHorizontalHeaderLabels(
            ["ID", "USUARIO", "NOMBRE", "ROL", "ESTADO", "ACCIONES"]
        )
        cabecera = self.usuarios_table.horizontalHeader()
        cabecera.setSectionResizeMode(QHeaderView.Stretch)
        cabecera.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        # La columna de botones se fija: ResizeToContents no cuenta el ancho
        # de los botones puestos con setCellWidget y los dejaba cortados.
        cabecera.setSectionResizeMode(5, QHeaderView.Fixed)
        self.usuarios_table.setColumnWidth(5, self.ANCHO_COLUMNA_ACCIONES)
        cabecera.setHighlightSections(False)
        cabecera.setDefaultAlignment(Qt.AlignCenter)
        # Las columnas de texto (usuario y nombre) van alineadas a la izquierda,
        # igual que su contenido; el resto queda centrado.
        for columna in (1, 2):
            encabezado_col = self.usuarios_table.horizontalHeaderItem(columna)
            if encabezado_col:
                encabezado_col.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.usuarios_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.usuarios_table.setSelectionMode(QTableWidget.SingleSelection)
        self.usuarios_table.setAlternatingRowColors(True)
        self.usuarios_table.verticalHeader().setVisible(False)
        self.usuarios_table.verticalHeader().setDefaultSectionSize(self.ALTO_FILA)
        self.usuarios_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.usuarios_table.setShowGrid(False)
        self.usuarios_table.setFocusPolicy(Qt.NoFocus)
        lay_tarjeta.addWidget(self.usuarios_table)
        layout.addWidget(tarjeta, 1)

        QTimer.singleShot(0, self.cargar_usuarios_panel)
        return w

    def cargar_usuarios_panel(self):
        if not self._es_super_admin():
            self.usuarios_table.setRowCount(0)
            return
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/admin/usuarios",
                headers=self._auth_headers(),
                timeout=5,
            )
            if respuesta.status_code != 200:
                raise ValueError(respuesta.json().get("detail", "No se pudo cargar usuarios."))
            usuarios = respuesta.json()

            self.usuarios_table.setUpdatesEnabled(False)
            self.usuarios_table.setRowCount(len(usuarios))
            for fila, usuario in enumerate(usuarios):
                self.usuarios_table.setItem(
                    fila, 0, _item_centrado(str(usuario["id_usuario"])))
                item_usuario = QTableWidgetItem(usuario["usuario"])
                item_usuario.setToolTip(usuario["usuario"])
                self.usuarios_table.setItem(fila, 1, item_usuario)
                item_nombre = QTableWidgetItem(usuario["nombre_completo"])
                item_nombre.setToolTip(usuario["nombre_completo"])
                self.usuarios_table.setItem(fila, 2, item_nombre)

                # Rol y estado: la celda guarda el dato (UserRole) y un chip lo dibuja.
                rol = usuario["rol"]
                es_super = rol == "SUPER_ADMIN"
                self.usuarios_table.setItem(fila, 3, _item_centrado("", rol))
                self.usuarios_table.setCellWidget(
                    fila, 3, _chip_tabla(rol, "chipRolSuper" if es_super else "chipRolAdmin"))

                activo = bool(usuario.get("activo", False))
                self.usuarios_table.setItem(fila, 4, _item_centrado("", activo))
                self.usuarios_table.setCellWidget(
                    fila, 4,
                    _chip_tabla("ACTIVO" if activo else "INACTIVO",
                                "chipActivo" if activo else "chipInactivo"))

                acciones = QWidget(self.usuarios_table)
                acciones.setObjectName("celdaAcciones")
                acciones_layout = QHBoxLayout(acciones)
                # Sin margen vertical: los botones tienen alto fijo y se centran
                # con AlignVCenter, así nunca tocan el borde de la fila.
                acciones_layout.setContentsMargins(8, 0, 8, 0)
                acciones_layout.setSpacing(10)

                btn_editar = self._boton_tabla(
                    "Editar", self.ESTILO_BTN_EDITAR, "Editar datos y contraseña",
                    acciones, self.ANCHO_BTN_EDITAR)
                btn_editar.clicked.connect(
                    lambda _checked=False, fila=fila: self.editar_usuario_fila(fila)
                )

                btn_estado = self._boton_tabla(
                    "Desactivar" if activo else "Activar",
                    self.ESTILO_BTN_DESACTIVAR if activo else self.ESTILO_BTN_ACTIVAR,
                    "Desactivar usuario" if activo else "Activar usuario",
                    acciones, self.ANCHO_BTN_ESTADO,
                )
                btn_estado.clicked.connect(
                    lambda _checked=False, fila=fila: self.cambiar_estado_fila(fila)
                )

                btn_editar.setEnabled(self._es_super_admin())
                btn_estado.setEnabled(self._es_super_admin())
                acciones_layout.addStretch(1)
                acciones_layout.addWidget(btn_editar, 0, Qt.AlignVCenter)
                acciones_layout.addWidget(btn_estado, 0, Qt.AlignVCenter)
                acciones_layout.addStretch(1)
                self.usuarios_table.setCellWidget(fila, 5, acciones)
            self.usuarios_table.setUpdatesEnabled(True)
        except (requests.RequestException, ValueError) as error:
            self.usuarios_table.setUpdatesEnabled(True)
            self.usuarios_table.setRowCount(0)
            QMessageBox.warning(self, "Usuarios", f"No se pudo cargar la lista: {error}")

    def cambiar_estado_fila(self, fila):
        if not self._es_super_admin():
            QMessageBox.warning(self, "Permisos", "Solo un SUPER_ADMIN puede cambiar estados.")
            return
        if fila >= self.usuarios_table.rowCount() or not self.usuarios_table.item(fila, 0):
            return
        usuario = self._usuario_de_fila(fila)
        activo_actual = usuario["activo"]
        siguiente = "activar" if not activo_actual else "desactivar"
        confirmacion = QMessageBox.question(
            self,
            "Confirmar cambio",
            f"¿Desea {siguiente} al usuario «{usuario['usuario']}»?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/admin/usuarios/{usuario['id_usuario']}",
                json={"activo": not activo_actual},
                headers=self._auth_headers(),
                timeout=5,
            )
            if respuesta.status_code == 200:
                self.cargar_usuarios_panel()
                QMessageBox.information(self, "Usuarios", "Estado actualizado correctamente.")
            else:
                detalle = respuesta.json().get("detail", "No se pudo actualizar el usuario.")
                QMessageBox.warning(self, "Usuarios", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Usuarios", f"Error de conexión: {error}")

    def crear_usuario_panel(self):
        self._guardar_usuario_panel(None)

    def editar_usuario_fila(self, fila):
        if not self._es_super_admin():
            QMessageBox.warning(self, "Permisos", "Solo un SUPER_ADMIN puede administrar usuarios.")
            return
        if fila >= self.usuarios_table.rowCount() or not self.usuarios_table.item(fila, 0):
            return
        self._guardar_usuario_panel(self._usuario_de_fila(fila))

    def _guardar_usuario_panel(self, usuario):
        if not self._es_super_admin():
            QMessageBox.warning(self, "Permisos", "Solo un SUPER_ADMIN puede administrar usuarios.")
            return
        dialogo = DialogoUsuario(usuario, self)
        if dialogo.exec() != QDialog.Accepted:
            return
        datos = dialogo.datos()
        endpoint = (
            f"/admin/usuarios/{usuario['id_usuario']}"
            if usuario else "/admin/usuarios"
        )
        try:
            respuesta = requests.request(
                "PATCH" if usuario else "POST",
                f"{self.api_base_url}{endpoint}",
                json=datos,
                headers=self._auth_headers(),
                timeout=5,
            )
            if respuesta.status_code in (200, 201):
                self.cargar_usuarios_panel()
                QMessageBox.information(
                    self,
                    "Usuarios",
                    "Usuario actualizado correctamente." if usuario else "Usuario creado correctamente.",
                )
            else:
                detalle = respuesta.json().get("detail", "No se pudo guardar el usuario.")
                QMessageBox.warning(self, "Usuarios", str(detalle))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Usuarios", f"Error de conexión: {error}")
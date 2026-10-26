import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QComboBox,
    QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QLineEdit,
    QDialog, QFormLayout, QCheckBox, QDialogButtonBox,
)
from PySide6.QtCore import Qt, QTimer


class DialogoUsuario(QDialog):
    def __init__(self, usuario=None, parent=None):
        super().__init__(parent)
        self.usuario = usuario
        self.setWindowTitle("Editar usuario" if usuario else "Nuevo usuario")
        self.setMinimumWidth(460)
        self.setModal(True)

        formulario = QFormLayout(self)
        formulario.setContentsMargins(28, 24, 28, 20)
        formulario.setSpacing(12)

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
        self.activo = QCheckBox("Usuario activo")
        self.activo.setChecked(usuario.get("activo", True) if usuario else True)

        formulario.addRow("Nombre completo:", self.nombre)
        formulario.addRow("Nombre de usuario:", self.nombre_usuario)
        formulario.addRow("Género:", self.genero)
        formulario.addRow("Rol:", self.rol)
        formulario.addRow("Contraseña:", self.password)
        formulario.addRow("Confirmar contraseña:", self.confirmacion)
        formulario.addRow("", self.activo)

        botones = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel,
            parent=self,
        )
        botones.accepted.connect(self._validar_y_aceptar)
        botones.rejected.connect(self.reject)
        formulario.addRow(botones)
        self.setStyleSheet("""
            QDialog { background: #F8FAFC; }
            QLabel { color: #334155; font-weight: 600; }
            QLineEdit, QComboBox {
                min-height: 34px; padding: 2px 8px;
                border: 1px solid #CBD5E1; border-radius: 6px;
                background: white;
            }
            QLineEdit:read-only { background: #E2E8F0; color: #64748B; }
            QPushButton {
                min-width: 90px; padding: 7px 14px;
                border-radius: 6px; font-weight: 600;
            }
        """)

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


class UsuariosMixin:
    ESTILO_BTN_EDITAR = (
        "QPushButton { background: #E0ECFF; color: #1D4ED8; "
        "border: 1px solid #BFDBFE; border-radius: 5px; padding: 5px 10px; "
        "font-weight: 600; } QPushButton:hover { background: #BFDBFE; }"
    )
    ESTILO_BTN_DESACTIVAR = (
        "QPushButton { background: #FEE2E2; color: #B91C1C; "
        "border: 1px solid #FECACA; border-radius: 5px; padding: 5px 10px; "
        "font-weight: 600; } QPushButton:hover { background: #FECACA; }"
    )
    ESTILO_BTN_ACTIVAR = (
        "QPushButton { background: #DCFCE7; color: #15803D; "
        "border: 1px solid #BBF7D0; border-radius: 5px; padding: 5px 10px; "
        "font-weight: 600; } QPushButton:hover { background: #BBF7D0; }"
    )

    def _es_super_admin(self):
        return self.token_data.get("rol") == "SUPER_ADMIN"

    def _seleccionar_usuario(self):
        fila = self.usuarios_table.currentRow()
        if fila < 0:
            QMessageBox.information(self, "Usuarios", "Seleccione un usuario primero.")
            return None
        return self._usuario_de_fila(fila)

    def _usuario_de_fila(self, fila):
        return {
            "id_usuario": int(self.usuarios_table.item(fila, 0).text()),
            "usuario": self.usuarios_table.item(fila, 1).text(),
            "nombre_completo": self.usuarios_table.item(fila, 2).text(),
            "rol": self.usuarios_table.item(fila, 3).text(),
            "activo": self.usuarios_table.item(fila, 4).data(Qt.UserRole),
        }

    def _crear_usuarios_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        title = QLabel("Usuarios y Roles", w)
        title.setStyleSheet("font-size: 22px; font-weight: bold; color: #0F2C59;")

        encabezado = QHBoxLayout()
        encabezado.addWidget(title)
        encabezado.addStretch()

        btn_style = """
            QPushButton {
                background-color: #2563EB; color: white;
                padding: 8px 16px; border-radius: 6px;
                font-weight: 600; font-size: 13px; border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """
        btn_secondary = """
            QPushButton {
                background-color: #F1F5F9; color: #334155;
                padding: 8px 16px; border-radius: 6px;
                font-weight: 600; font-size: 13px;
                border: 1px solid #CBD5E1;
            }
            QPushButton:hover { background-color: #E2E8F0; }
        """

        btn_nuevo = QPushButton("+ Nuevo usuario", w)
        btn_nuevo.setCursor(Qt.PointingHandCursor)
        btn_nuevo.setStyleSheet(btn_style)
        btn_nuevo.clicked.connect(self.crear_usuario_panel)
        btn_nuevo.setEnabled(self._es_super_admin())

        btn_refrescar = QPushButton("Actualizar", w)
        btn_refrescar.setCursor(Qt.PointingHandCursor)
        btn_refrescar.setStyleSheet(btn_secondary)
        btn_refrescar.clicked.connect(self.cargar_usuarios_panel)

        encabezado.addWidget(btn_nuevo)
        encabezado.addWidget(btn_refrescar)
        layout.addLayout(encabezado)

        self.usuarios_table = QTableWidget(0, 6, w)
        self.usuarios_table.setHorizontalHeaderLabels(
            ["ID", "Usuario", "Nombre", "Rol", "Estado", "Acciones"]
        )
        self.usuarios_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.usuarios_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.usuarios_table.setAlternatingRowColors(True)
        self.usuarios_table.verticalHeader().setDefaultSectionSize(48)
        self.usuarios_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.usuarios_table)

        # La carga se difiere: se ejecuta cuando la ventana ya está visible,
        # no dentro del constructor (evita widgets sueltos y bloqueos al iniciar sesión).
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
                self.usuarios_table.setItem(fila, 0, QTableWidgetItem(str(usuario["id_usuario"])))
                self.usuarios_table.setItem(fila, 1, QTableWidgetItem(usuario["usuario"]))
                self.usuarios_table.setItem(fila, 2, QTableWidgetItem(usuario["nombre_completo"]))
                rol = QTableWidgetItem(usuario["rol"])
                rol.setTextAlignment(Qt.AlignCenter)
                rol.setForeground(Qt.darkBlue if usuario["rol"] == "SUPER_ADMIN" else Qt.darkGray)
                self.usuarios_table.setItem(fila, 3, rol)

                activo = bool(usuario.get("activo", False))
                estado = QTableWidgetItem("ACTIVO" if activo else "INACTIVO")
                estado.setData(Qt.UserRole, activo)
                estado.setTextAlignment(Qt.AlignCenter)
                estado.setForeground(Qt.darkGreen if activo else Qt.darkRed)
                self.usuarios_table.setItem(fila, 4, estado)

                # Todos los widgets nacen con parent: nunca existen como ventanas sueltas.
                acciones = QWidget(self.usuarios_table)
                acciones_layout = QHBoxLayout(acciones)
                acciones_layout.setContentsMargins(6, 5, 6, 5)
                acciones_layout.setSpacing(6)

                btn_editar = QPushButton("Editar", acciones)
                btn_editar.setCursor(Qt.PointingHandCursor)
                btn_editar.setToolTip("Editar datos y contraseña")
                btn_editar.setStyleSheet(self.ESTILO_BTN_EDITAR)
                btn_editar.clicked.connect(
                    lambda _checked=False, fila=fila: self.editar_usuario_fila(fila)
                )

                btn_estado = QPushButton("Desactivar" if activo else "Activar", acciones)
                btn_estado.setCursor(Qt.PointingHandCursor)
                btn_estado.setToolTip("Desactivar usuario" if activo else "Activar usuario")
                btn_estado.setStyleSheet(
                    self.ESTILO_BTN_DESACTIVAR if activo else self.ESTILO_BTN_ACTIVAR
                )
                btn_estado.clicked.connect(
                    lambda _checked=False, fila=fila: self.cambiar_estado_fila(fila)
                )

                btn_editar.setEnabled(self._es_super_admin())
                btn_estado.setEnabled(self._es_super_admin())
                acciones_layout.addWidget(btn_editar)
                acciones_layout.addWidget(btn_estado)
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
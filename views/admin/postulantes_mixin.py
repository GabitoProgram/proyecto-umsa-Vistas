import requests
from datetime import date
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QStackedWidget, QFrame, QComboBox, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog, QLineEdit, QFileDialog, QDialog, QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QImage, QPixmap
import cv2

from desktop.views.dialogs.postulante_dialog import (
    DialogEditarPostulante,
    DialogNuevoPostulanteGestion,
)
from desktop.views.dialogs.gestion_dialog import DialogGestion
from desktop.views.dialogs.carrera_dialog import DialogCarrera
from desktop.views.dialogs.examen_dialog import DialogExamen
from desktop.views.dialogs.captura_rostro_dialog import DialogCapturaRostro
from desktop.views.admin.examen_workspace_view import ExamenWorkspaceView


# Formatos que admite la carga masiva.
_EXTENSIONES_CARGA = (".xlsx", ".xls", ".csv")


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


class ZonaCargaExcel(QFrame):
    """Zona grande y visible para arrastrar el archivo de carga masiva.

    El botón es chico y es fácil no darle: esto agranda el objetivo y deja
    claro qué se espera soltar. También responde al clic.
    """

    archivo_recibido = Signal(str)
    seleccionar_archivo = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(84)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        texto = QLabel(
            "📥 <b>Arrastra aquí tu archivo de postulantes</b><br>"
            "<span style='font-size:12px; color:#64748B'>"
            "formatos .xlsx, .xls o .csv — o haz clic para buscarlo</span>"
        )
        texto.setAlignment(Qt.AlignCenter)
        texto.setTextFormat(Qt.RichText)
        texto.setWordWrap(True)
        texto.setStyleSheet("background: transparent; border: none;")
        layout.addWidget(texto)
        self._pintar(encima=False)

    def _pintar(self, encima):
        color_borde = "#16A34A" if encima else "#94A3B8"
        color_fondo = "#DCFCE7" if encima else "#F8FAFC"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {color_fondo};
                border: 2px dashed {color_borde};
                border-radius: 10px;
            }}
        """)

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


class PostulantesMixin:
    def abrir_postulantes_gestion(self):
        datos = self._obtener_lista(f"/inscripciones/gestion/{self.gestion_nav_id}/postulantes")
        todos = {str(p.get("ci")): p for p in self._obtener_lista("/postulantes?limit=1000")}
        
        self.postulantes_nav_title.setText("Postulantes inscritos en la gestión")
        self.postulantes_nav_table.setRowCount(len(datos))
        for fila, postulante in enumerate(datos):
            ci = str(postulante.get("ci", ""))
            full_p = todos.get(ci, {})
            # Actualizamos el postulante con su info completa (importante para editar y registrar)
            postulante.update(full_p)
            
            self.postulantes_nav_table.setItem(fila, 0, QTableWidgetItem(ci))
            self.postulantes_nav_table.setItem(fila, 1, QTableWidgetItem(str(postulante.get("nombre_completo", ""))))
            carreras_lista = [c.get("nombre", "") for c in postulante.get("carreras", []) if c.get("nombre")]
            if carreras_lista:
                item_carreras = QTableWidgetItem(
                    f"{len(carreras_lista)} carrera(s): {', '.join(carreras_lista)}"
                )
                if len(carreras_lista) >= 2:
                    item_carreras.setForeground(Qt.darkGreen)
                item_carreras.setToolTip(", ".join(carreras_lista))
            else:
                item_carreras = QTableWidgetItem("Sin carreras")
                item_carreras.setForeground(Qt.darkGray)
            self.postulantes_nav_table.setItem(fila, 2, item_carreras)
            
            tiene_rostro = full_p.get("tiene_rostro", False)
            rostro_registrado = full_p.get("rostro_registrado", tiene_rostro)
            id_rostro = full_p.get("id_rostro")
            cant_huellas = full_p.get("cantidad_huellas", 0)
            
            # Action buttons
            acciones = QWidget()
            acciones_layout = QHBoxLayout(acciones)
            acciones_layout.setContentsMargins(2, 2, 2, 2)
            acciones_layout.setSpacing(4)
            
            # 3 estados: sin rostro (gris), registrado sin habilitar (amarillo), habilitado (verde)
            if tiene_rostro:
                btn_rostro = QPushButton("Habilitado")
                btn_rostro.setStyleSheet("background-color: #16A34A; color: white; border: none; padding: 4px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
                btn_rostro.setCursor(Qt.PointingHandCursor)
                btn_rostro.setToolTip("Rostro habilitado. Clic para deshabilitar.")
                btn_rostro.clicked.connect(lambda _, p=postulante, r=id_rostro: self.cambiar_estado_rostro_gestion(p, r, False))
            elif rostro_registrado:
                btn_rostro = QPushButton("Por habilitar")
                btn_rostro.setStyleSheet("background-color: #FACC15; color: #713F12; border: 1px solid #EAB308; padding: 4px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
                btn_rostro.setCursor(Qt.PointingHandCursor)
                btn_rostro.setToolTip("Rostro registrado, pendiente de habilitación. Clic para habilitar.")
                btn_rostro.clicked.connect(lambda _, p=postulante, r=id_rostro: self.cambiar_estado_rostro_gestion(p, r, True))
            else:
                btn_rostro = QPushButton("Rostro")
                btn_rostro.setStyleSheet("background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 4px 6px; border-radius: 4px; font-size: 11px;")
                btn_rostro.setCursor(Qt.PointingHandCursor)
                btn_rostro.clicked.connect(lambda _, p=postulante, btn=btn_rostro: self.registrar_rostro_gestion(p, btn))
            
            btn_rostro.setMinimumSize(75, 32)
            btn_rostro.setMaximumHeight(36)
            
            h_text = f"({cant_huellas})" if cant_huellas > 0 else "Huella"
            btn_huella = QPushButton(h_text if cant_huellas == 0 else f"Huella {h_text}")
            btn_huella.setMinimumSize(75, 32)
            btn_huella.setMaximumHeight(36)
            if cant_huellas > 0:
                btn_huella.setStyleSheet("background-color: #16A34A; color: white; border: none; padding: 4px 6px; border-radius: 4px; font-weight: bold; font-size: 11px;")
                btn_huella.setCursor(Qt.PointingHandCursor)
            else:
                btn_huella.setStyleSheet("background-color: #F1F5F9; color: #334155; border: 1px solid #CBD5E1; padding: 4px 6px; border-radius: 4px; font-size: 11px;")
                btn_huella.setCursor(Qt.PointingHandCursor)
            btn_huella.clicked.connect(lambda _, p=postulante, btn=btn_huella: self.registrar_huella_gestion(p, btn))
            
            btn_editar = QPushButton("Editar")
            btn_editar.setMinimumSize(60, 32)
            btn_editar.setMaximumHeight(36)
            btn_editar.setCursor(Qt.PointingHandCursor)
            btn_editar.setStyleSheet("background-color: #E0E7FF; color: #3730A3; padding: 4px 6px; border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;")
            btn_editar.clicked.connect(lambda _, p=postulante: self.editar_postulante_en_fila(p))
            
            acciones_layout.addWidget(btn_rostro)
            acciones_layout.addWidget(btn_huella)
            acciones_layout.addWidget(btn_editar)
            
            self.postulantes_nav_table.setCellWidget(fila, 3, acciones)
            self.postulantes_nav_table.setRowHeight(fila, 50)
            
        self.academico_stack.setCurrentIndex(3)

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
            respuesta = requests.post(
                f"{self.api_base_url}/postulantes/", json=datos,
                headers=self._auth_headers(), timeout=6
            )
            if respuesta.status_code not in (200, 201):
                QMessageBox.warning(self, "Postulantes", str(respuesta.json().get("detail", "No se pudo crear el postulante.")))
                return
            id_postulante = respuesta.json()["id_postulante"]

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

    def editar_postulante_gestion(self):
        fila = self.postulantes_nav_table.currentRow()
        if fila < 0 or not self.postulantes_nav_table.item(fila, 0):
            QMessageBox.information(self, "Postulantes", "Seleccione un postulante primero.")
            return
        ci = self.postulantes_nav_table.item(fila, 0).text()
        postulante = next((item for item in self._obtener_lista("/postulantes?limit=1000") if str(item.get("ci")) == ci), None)
        if not postulante:
            QMessageBox.warning(self, "Postulantes", "No se encontró el postulante seleccionado.")
            return
        self.editar_postulante_en_fila(postulante)

    def editar_postulante_en_fila(self, postulante):
        # Asegurarse de tener el id_postulante y los nombres/apellidos separados
        id_post = postulante.get("id_postulante")
        if not id_post:
            # Buscar en caso de que venga de la lista de inscripciones
            ci = postulante.get("ci")
            full_postulante = next((item for item in self._obtener_lista("/postulantes?limit=1000") if str(item.get("ci")) == str(ci)), None)
            if not full_postulante:
                QMessageBox.warning(self, "Postulantes", "No se encontraron los detalles completos del postulante.")
                return
            postulante = full_postulante
            id_post = postulante.get("id_postulante")

        carreras_texto = None
        carreras = postulante.get("carreras") or []
        nombres = [c.get("nombre") for c in carreras if c.get("nombre")]
        if not nombres and self.gestion_nav_id is not None:
            inscripciones = self._obtener_lista(
                f"/inscripciones?id_gestion={self.gestion_nav_id}"
            ) or []
            for ins in inscripciones:
                if ins.get("id_postulante") == id_post:
                    id_carrera = ins.get("id_carrera")
                    carrera = next(
                        (c for c in self.carreras_nav if c.get("id_carrera") == id_carrera),
                        None,
                    )
                    nombres.append(carrera.get("nombre") if carrera else f"Carrera {id_carrera}")
        if nombres:
            carreras_texto = f"{len(nombres)} carrera(s): " + ", ".join(nombres)

        dlg = DialogEditarPostulante(postulante, self, carreras_texto)
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
                self.abrir_postulantes_gestion()
            else:
                QMessageBox.warning(self, "Postulantes", str(respuesta.json().get("detail", "No se pudo editar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Postulantes", f"Error de conexión: {error}")

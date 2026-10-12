import logging
import requests
from datetime import date

log = logging.getLogger(__name__)
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
from desktop.views.dialogs.captura_huella_dialog import DialogCapturaHuella
from desktop.views.admin.examen_workspace_view import ExamenWorkspaceView


class BiometriaMixin:
    def registrar_rostro_gestion(self, postulante, boton=None):
        id_post = postulante.get("id_postulante")
        if not id_post:
            ci = postulante.get("ci")
            full_postulante = next((item for item in self._obtener_lista("/postulantes?limit=1000") if str(item.get("ci")) == str(ci)), None)
            if full_postulante:
                id_post = full_postulante.get("id_postulante")
            if not id_post:
                QMessageBox.warning(self, "Rostro", "No se encontraron los detalles del postulante.")
                return

        dlg = DialogCapturaRostro(self)
        if not dlg.exec() or not dlg.imagen_capturada:
            return
        
        # Guardar la imagen localmente como respaldo
        import os
        carpeta_rostros = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "capturas_rostros")
        os.makedirs(carpeta_rostros, exist_ok=True)
        ruta_local = os.path.join(carpeta_rostros, f"rostro_{id_post}.jpg")
        with open(ruta_local, "wb") as f:
            f.write(dlg.imagen_capturada)
        
        # Enviar al servidor
        registrado = False
        try:
            respuesta = requests.post(
                f"{self.api_base_url}/rostros/{id_post}/registrar",
                files={"file": ("captura.jpg", dlg.imagen_capturada, "image/jpeg")},
                headers=self._auth_headers(),
                timeout=20
            )
            if respuesta.status_code in (200, 201):
                registrado = True
                QMessageBox.information(
                    self, "Rostro",
                    "Rostro registrado correctamente.\nQueda PENDIENTE de habilitación antes del examen."
                )
            else:
                QMessageBox.warning(
                    self, "Rostro",
                    f"La foto se guardó localmente en:\n{ruta_local}\n\n"
                    f"Pero el servidor no pudo procesarla:\n"
                    f"{respuesta.json().get('detail', 'Error')}\n\n"
                    "El rostro NO quedó registrado en el sistema."
                )
        except (OSError, requests.RequestException, ValueError) as error:
            QMessageBox.warning(self, "Rostro", f"Foto guardada localmente en:\n{ruta_local}\n\nPero hubo error de conexión:\n{error}")

        # Refrescar la tabla solo si el servidor confirmó el registro.
        # Si el rostro quedó registrado pero sin habilitar, el botón se mostrará
        # en amarillo ("Por habilitar"); en verde solo si está habilitado.
        if registrado and self.gestion_nav_id is not None:
            self.abrir_postulantes_gestion()

    def habilitar_rostro_gestion(self, postulante, id_rostro=None):
        # Compatibilidad: habilita el rostro
        self.cambiar_estado_rostro_gestion(postulante, id_rostro, True)

    def cambiar_estado_rostro_gestion(self, postulante, id_rostro=None, habilitar=True):
        if not id_rostro:
            id_post = postulante.get("id_postulante")
            full_postulante = next(
                (item for item in self._obtener_lista("/postulantes?limit=1000")
                 if item.get("id_postulante") == id_post),
                None,
            ) or {}
            id_rostro = full_postulante.get("id_rostro")
        if not id_rostro:
            QMessageBox.warning(
                self, "Rostro",
                f"No se encontró el registro facial para {'habilitar' if habilitar else 'deshabilitar'}."
            )
            return

        accion = "habilitar" if habilitar else "deshabilitar"
        confirmacion = QMessageBox.question(
            self, f"{'Habilitar' if habilitar else 'Deshabilitar'} rostro",
            f"¿{accion.capitalize()} el rostro de este postulante para el control de acceso?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirmacion != QMessageBox.Yes:
            return
        try:
            respuesta = requests.patch(
                f"{self.api_base_url}/rostros/{id_rostro}/habilitada",
                params={"habilitada": habilitar},
                headers=self._auth_headers(),
                timeout=6
            )
            if respuesta.status_code == 200:
                QMessageBox.information(
                    self, "Rostro",
                    f"Rostro {'habilitado' if habilitar else 'deshabilitado'} correctamente."
                )
                if self.gestion_nav_id is not None:
                    self.abrir_postulantes_gestion()
            else:
                QMessageBox.warning(
                    self, "Rostro",
                    str(respuesta.json().get("detail", f"No se pudo {accion} el rostro."))
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Rostro", f"Error de conexión: {error}")

    def registrar_huella_gestion(self, postulante, boton=None):
        id_post = postulante.get("id_postulante")
        if not id_post:
            ci = postulante.get("ci")
            full_postulante = next((item for item in self._obtener_lista("/postulantes?limit=1000") if str(item.get("ci")) == str(ci)), None)
            if full_postulante:
                id_post = full_postulante.get("id_postulante")
            if not id_post:
                QMessageBox.warning(self, "Huella", "No se encontraron los detalles del postulante.")
                return

        # Dedos ya registrados y habilitados (para mostrar estado en el diálogo)
        dedos_existentes = set()
        dedos_habilitados = set()
        huellas_por_dedo = {}
        try:
            respuesta = requests.get(
                f"{self.api_base_url}/rostros/{id_post}/huellas",
                headers=self._auth_headers(),
                timeout=6
            )
            log.debug("API /rostros/%s/huellas devolvió %s: %s", id_post, respuesta.status_code, respuesta.text[:500])
            if respuesta.status_code == 200:
                for h in respuesta.json():
                    tipo_dedo = h.get("tipo_dedo")
                    if tipo_dedo:
                        dedos_existentes.add(tipo_dedo)
                        if h.get("id_huella"):
                            huellas_por_dedo[tipo_dedo] = h["id_huella"]
                        if h.get("habilitada", False):
                            dedos_habilitados.add(tipo_dedo)
                log.debug("Dedos registrados: %s, habilitados: %s", dedos_existentes, dedos_habilitados)
        except (requests.RequestException, ValueError) as e:
            log.exception("Error consultando huellas: %s", e)
        dedo_libre = next((d for d in range(1, 11) if d not in dedos_existentes), 1)

        dlg = DialogCapturaHuella(
            postulante,
            dedo_inicial=dedo_libre,
            dedos_registrados=dedos_existentes,
            dedos_habilitados=dedos_habilitados,
            huellas_por_dedo=huellas_por_dedo,
            parent=self,
        )
        if not dlg.exec():
            return

        if dlg.guardar_habilitaciones_solicitado:
            if not self._guardar_habilitaciones_huellas(
                huellas_por_dedo, dlg.obtener_dedos_habilitados()
            ):
                return

        tipo_dedo = dlg.combo_dedo.currentData() or 1
        plantilla = dlg.plantilla_final
        if not plantilla:
            return

        # Obtener el estado de habilitación seleccionado en el diálogo
        dedos_habilitados_en_dlg = dlg.obtener_dedos_habilitados()
        habilitar_este = tipo_dedo in dedos_habilitados_en_dlg

        if tipo_dedo in dedos_existentes:
            confirmacion = QMessageBox.question(
                self, "Sobrescribir huella",
                f"Ya existe una huella registrada en el dedo «{tipo_dedo}».\n"
                "¿Deseas reemplazarla por la nueva captura?",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirmacion != QMessageBox.Yes:
                return

        nombre_dedo = {1: "Pulgar izq.", 2: "Índice izq.", 3: "Medio izq.",
                       4: "Anular izq.", 5: "Meñique izq.", 6: "Pulgar der.",
                       7: "Índice der.", 8: "Medio der.", 9: "Anular der.",
                       10: "Meñique der."}.get(tipo_dedo, f"Dedo {tipo_dedo}")
        log.info("Guardando huella: id_post=%s, tipo_dedo=%s, habilitado=%s, bytes=%s",
                 id_post, tipo_dedo, habilitar_este, len(plantilla) if plantilla else 0)
        try:
            respuesta = requests.post(
                f"{self.api_base_url}/rostros/{id_post}/huellas/{tipo_dedo}",
                files={"file": (f"huella_{tipo_dedo}.bin", plantilla, "application/octet-stream")},
                data={"habilitada": str(habilitar_este).lower()},
                headers=self._auth_headers(),
                timeout=20
            )
            log.debug("API POST /rostros/%s/huellas/%s devolvió %s: %s", id_post, tipo_dedo, respuesta.status_code, respuesta.text[:500])
            if respuesta.status_code in (200, 201):
                cantidad = len(dedos_existentes | {tipo_dedo})
                QMessageBox.information(
                    self, "Huella registrada",
                    f"Huella del {nombre_dedo} registrada y habilitada.\n"
                    f"Total de dedos habilitados: {cantidad}/10"
                )
                if boton:
                    boton.setText(f"Huella ({cantidad}/10)")
                    boton.setStyleSheet("background-color: #16A34A; color: white; border: none; padding: 4px 8px; border-radius: 4px;")
                if self.gestion_nav_id is not None:
                    self.abrir_postulantes_gestion()
            else:
                QMessageBox.warning(self, "Huella", str(respuesta.json().get("detail", "No se pudo registrar la huella.")))
        except (requests.RequestException, ValueError, OSError) as error:
            QMessageBox.critical(self, "Huella", f"Error al registrar: {error}")

    def _guardar_habilitaciones_huellas(self, huellas_por_dedo, dedos_habilitados):
        """Persiste el estado de habilitación de las huellas existentes."""
        try:
            for tipo_dedo, id_huella in huellas_por_dedo.items():
                respuesta = requests.patch(
                    f"{self.api_base_url}/rostros/huellas/{id_huella}/habilitada",
                    params={"habilitada": tipo_dedo in dedos_habilitados},
                    headers=self._auth_headers(),
                    timeout=6,
                )
                if respuesta.status_code not in (200, 204):
                    try:
                        detalle = respuesta.json().get("detail", respuesta.text)
                    except ValueError:
                        detalle = respuesta.text
                    raise RuntimeError(
                        f"No se pudo actualizar el dedo {tipo_dedo}: {detalle}"
                    )
        except (requests.RequestException, RuntimeError, ValueError) as error:
            QMessageBox.critical(self, "Huellas", f"No se guardaron los cambios: {error}")
            return False

        QMessageBox.information(self, "Huellas", "Cambios guardados correctamente.")
        return True

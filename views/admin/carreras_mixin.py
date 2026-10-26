import requests
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem

from desktop.views.dialogs.carrera_dialog import DialogCarrera
from desktop.views.admin.gestiones_mixin import (
    crear_fila_acciones,
    ESTILO_PRINCIPAL_VERDE,
)


class CarrerasMixin:
    def _refrescar_carreras_nav(self):
        self.abrir_gestion_nav({
            "id_gestion": self.gestion_nav_id,
            "nombre": self.carrera_nav_title.text().replace("Carreras de ", ""),
        })

    def abrir_carrera_nav(self, carrera):
        self.carrera_nav_id = carrera.get("id_carrera")
        self.examen_nav_title.setText(f"Exámenes de {carrera.get('nombre', 'carrera')}")
        self.examenes_nav = [
            examen for examen in self._obtener_lista("/admin/examenes")
            if examen.get("id_gestion") == self.gestion_nav_id
            and examen.get("id_carrera") == self.carrera_nav_id
        ]
        tabla = self.examenes_nav_table
        tabla.setRowCount(len(self.examenes_nav))
        for fila, examen in enumerate(self.examenes_nav):
            valores = (
                examen.get("materia"), examen.get("fecha"),
                f"{examen.get('hora_inicio')} - {examen.get('hora_fin')}"
            )
            for columna, valor in enumerate(valores):
                tabla.setItem(fila, columna, QTableWidgetItem(str(valor or "")))
            tabla.setCellWidget(fila, 3, crear_fila_acciones(
                tabla,
                "Abrir",
                lambda item=examen: self.abrir_workspace_desde_nav(item),
                lambda item=examen: self.editar_examen_nav(item),
                lambda item=examen: self.eliminar_examen_nav(item),
                self.rol == "SUPER_ADMIN",
                estilo_principal=ESTILO_PRINCIPAL_VERDE,
            ))
            tabla.setRowHeight(fila, 50)
        self.academico_stack.setCurrentIndex(2)

    def crear_carrera_nav(self):
        dlg = DialogCarrera(None, self)
        if dlg.exec():
            self._crear_catalogo("/admin/carreras", dlg.get_data(), "Carrera")
            self._refrescar_carreras_nav()

    def editar_carrera_nav(self, carrera):
        dlg = DialogCarrera(carrera, self)
        if dlg.exec():
            try:
                respuesta = requests.patch(
                    f"{self.api_base_url}/admin/carreras/{carrera['id_carrera']}",
                    json=dlg.get_data(), headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code == 200:
                    self._refrescar_carreras_nav()
                else:
                    QMessageBox.warning(self, "Carrera", str(respuesta.json().get("detail", "No se pudo editar.")))
            except Exception as error:
                QMessageBox.critical(self, "Carrera", f"Error de conexión: {error}")

    def eliminar_carrera_nav(self, carrera):
        if QMessageBox.question(
            self, "Eliminar carrera",
            f"¿Eliminar la carrera «{carrera.get('nombre', '')}»?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/admin/carreras/{carrera['id_carrera']}",
                headers=self._auth_headers(), timeout=6,
            )
            if respuesta.status_code == 204:
                self._refrescar_carreras_nav()
            else:
                QMessageBox.warning(self, "Carrera", str(respuesta.json().get("detail", "No se pudo eliminar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Carrera", f"Error de conexión: {error}")

    def eliminar_examen_nav(self, examen):
        if QMessageBox.question(
            self, "Eliminar examen",
            f"¿Eliminar el examen de «{examen.get('materia', '')}»?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/admin/examenes/{examen['id_examen']}",
                headers=self._auth_headers(), timeout=6,
            )
            if respuesta.status_code == 204:
                self.abrir_carrera_nav({
                    "id_carrera": self.carrera_nav_id,
                    "nombre": self.examen_nav_title.text().replace("Exámenes de ", ""),
                })
            else:
                QMessageBox.warning(
                    self, "Examen",
                    str(respuesta.json().get("detail", "No se pudo eliminar.")),
                )
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Examen", f"Error de conexión: {error}")
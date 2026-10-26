import requests
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QMessageBox, QTableWidgetItem,
)
from PySide6.QtCore import Qt

from desktop.views.dialogs.gestion_dialog import DialogGestion

ESTILO_PRINCIPAL = (
    "background-color: #2563EB; color: white; padding: 4px 8px; "
    "border-radius: 4px; border: none; font-size: 11px;"
)
ESTILO_PRINCIPAL_VERDE = (
    "background-color: #059669; color: white; padding: 4px 8px; "
    "border-radius: 4px; border: none; font-size: 11px;"
)
ESTILO_EDITAR = (
    "background-color: #E0E7FF; color: #3730A3; padding: 4px 8px; "
    "border-radius: 4px; border: 1px solid #A5B4FC; font-size: 11px;"
)
ESTILO_ELIMINAR = (
    "background-color: #FEE2E2; color: #B91C1C; padding: 4px 8px; "
    "border-radius: 4px; border: 1px solid #FCA5A5; font-size: 11px;"
)


def _boton(texto, estilo, ancho_min, parent):
    boton = QPushButton(texto, parent)  # siempre con parent: nunca es ventana suelta
    boton.setMinimumSize(ancho_min, 32)
    boton.setMaximumHeight(36)
    boton.setCursor(Qt.PointingHandCursor)
    boton.setStyleSheet(estilo)
    return boton


def crear_fila_acciones(
    tabla, texto_principal, al_principal, al_editar, al_eliminar,
    puede_eliminar, estilo_principal=ESTILO_PRINCIPAL,
):
    """Celda de acciones. El botón Eliminar solo existe para SUPER_ADMIN."""
    acciones = QWidget(tabla)
    layout = QHBoxLayout(acciones)
    layout.setContentsMargins(2, 2, 2, 2)
    layout.setSpacing(4)

    principal = _boton(texto_principal, estilo_principal, 70, acciones)
    principal.clicked.connect(lambda _=False: al_principal())
    layout.addWidget(principal)

    editar = _boton("Editar", ESTILO_EDITAR, 60, acciones)
    editar.clicked.connect(lambda _=False: al_editar())
    layout.addWidget(editar)

    if puede_eliminar:
        eliminar = _boton("Eliminar", ESTILO_ELIMINAR, 70, acciones)
        eliminar.clicked.connect(lambda _=False: al_eliminar())
        layout.addWidget(eliminar)
    return acciones


class GestionesMixin:
    def cargar_gestiones_nav(self):
        self.gestiones_nav = self._obtener_lista("/admin/gestiones")
        tabla = self.gestiones_nav_table
        tabla.setRowCount(len(self.gestiones_nav))
        for fila, gestion in enumerate(self.gestiones_nav):
            valores = (gestion.get("nombre"), gestion.get("anio"), gestion.get("estado"))
            for columna, valor in enumerate(valores):
                tabla.setItem(fila, columna, QTableWidgetItem(str(valor or "")))
            tabla.setCellWidget(fila, 3, crear_fila_acciones(
                tabla,
                "Abrir",
                lambda item=gestion: self.abrir_gestion_nav(item),
                lambda item=gestion: self.editar_gestion_nav(item),
                lambda item=gestion: self.eliminar_gestion_nav(item),
                self.rol == "SUPER_ADMIN",
            ))
            tabla.setRowHeight(fila, 50)

    def abrir_gestion_nav(self, gestion):
        self.gestion_nav_id = gestion.get("id_gestion")
        self.carrera_nav_title.setText(f"Carreras de {gestion.get('nombre', 'gestión')}")
        self.carreras_nav = [
            carrera for carrera in self._obtener_lista("/admin/carreras")
            if carrera.get("activa", True)
        ]
        tabla = self.carreras_nav_table
        tabla.setRowCount(len(self.carreras_nav))
        for fila, carrera in enumerate(self.carreras_nav):
            tabla.setItem(fila, 0, QTableWidgetItem(str(carrera.get("nombre", ""))))
            tabla.setItem(fila, 1, QTableWidgetItem(str(carrera.get("codigo", ""))))
            tabla.setCellWidget(fila, 2, crear_fila_acciones(
                tabla,
                "Examenes",
                lambda item=carrera: self.abrir_carrera_nav(item),
                lambda item=carrera: self.editar_carrera_nav(item),
                lambda item=carrera: self.eliminar_carrera_nav(item),
                self.rol == "SUPER_ADMIN",
            ))
            tabla.setRowHeight(fila, 50)
        self.academico_stack.setCurrentIndex(1)

    def crear_gestion_nav(self):
        dlg = DialogGestion(None, self)
        if dlg.exec():
            self._crear_catalogo("/admin/gestiones", dlg.get_data(), "Gestión")
            self.cargar_gestiones_nav()

    def editar_gestion_nav(self, gestion):
        dlg = DialogGestion(gestion, self)
        if dlg.exec():
            try:
                respuesta = requests.patch(
                    f"{self.api_base_url}/admin/gestiones/{gestion['id_gestion']}",
                    json=dlg.get_data(), headers=self._auth_headers(), timeout=6
                )
                if respuesta.status_code == 200:
                    self.cargar_gestiones_nav()
                else:
                    QMessageBox.warning(self, "Gestión", str(respuesta.json().get("detail", "No se pudo editar.")))
            except Exception as error:
                QMessageBox.critical(self, "Gestión", f"Error de conexión: {error}")

    def eliminar_gestion_nav(self, gestion):
        if QMessageBox.question(
            self, "Eliminar gestión",
            f"¿Eliminar la gestión «{gestion.get('nombre', '')}»?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        try:
            respuesta = requests.delete(
                f"{self.api_base_url}/admin/gestiones/{gestion['id_gestion']}",
                headers=self._auth_headers(), timeout=6,
            )
            if respuesta.status_code == 204:
                self.cargar_gestiones_nav()
            else:
                QMessageBox.warning(self, "Gestión", str(respuesta.json().get("detail", "No se pudo eliminar.")))
        except (requests.RequestException, ValueError) as error:
            QMessageBox.critical(self, "Gestión", f"Error de conexión: {error}")
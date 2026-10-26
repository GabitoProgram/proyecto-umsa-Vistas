"""Panel auxiliar: misma plantilla administrativa sin funciones de superadmin."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget

from desktop.views.main_window import MainDashboardWindow

ROL_AUXILIAR = "ADMIN"


class AuxiliarDashboardWindow(MainDashboardWindow):
    """Panel administrativo limitado al rol ADMIN."""

    TITULO_VENTANA = "Sistema Biométrico UMSA - Panel Auxiliar"

    def __init__(
        self,
        token_data: Optional[dict] = None,
        api_base_url: Optional[str] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        datos = {**(token_data or {}), "rol": ROL_AUXILIAR}
        super().__init__(datos, api_base_url, parent)
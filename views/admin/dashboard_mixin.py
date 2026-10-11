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


class DashboardMixin:
    def _crear_dashboard_view(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(24)

        title = QLabel("Dashboard Resumen")
        title.setStyleSheet("font-size: 26px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(title)

        datos = self._cargar_resumen_dashboard()
        
        # Tarjetas superiores de resumen
        tarjetas = QHBoxLayout()
        tarjetas.setSpacing(20)
        
        for etiqueta, valor in datos:
            card = QFrame()
            card.setObjectName("Card")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(24, 24, 24, 24)
            card_layout.setSpacing(10)
            
            lbl_etiq = QLabel(etiqueta)
            lbl_etiq.setStyleSheet("font-size: 14px; font-weight: 600; color: #64748B; text-transform: uppercase;")
            card_layout.addWidget(lbl_etiq)
            
            valor_label = QLabel(str(valor))
            valor_label.setStyleSheet("font-size: 36px; font-weight: 900; color: #2563EB;")
            card_layout.addWidget(valor_label)
            
            tarjetas.addWidget(card)
            
        layout.addLayout(tarjetas)
        
        # Contenedor inferior (placeholder para futuros gráficos)
        info_card = QFrame()
        info_card.setObjectName("Card")
        info_layout = QVBoxLayout(info_card)
        info_layout.setContentsMargins(32, 32, 32, 32)
        
        lbl_bienvenida = QLabel("👋 Bienvenido al Panel Administrativo")
        lbl_bienvenida.setStyleSheet("font-size: 20px; font-weight: bold; color: #1E293B;")
        
        lbl_instrucciones = QLabel(
            "Desde este panel puedes gestionar todas las operaciones del sistema biométrico:\n"
            "• Administra postulantes e inscripciones en la pestaña 'Postulantes'.\n"
            "• Crea nuevas gestiones, carreras y programa exámenes en 'Gestiones y Exámenes'.\n"
            "• Monitorea los accesos en tiempo real iniciando un Workspace de Examen."
        )
        lbl_instrucciones.setStyleSheet("font-size: 15px; color: #475569; line-height: 1.6;")
        lbl_instrucciones.setWordWrap(True)
        
        info_layout.addWidget(lbl_bienvenida)
        info_layout.addSpacing(16)
        info_layout.addWidget(lbl_instrucciones)
        info_layout.addStretch()
        
        layout.addWidget(info_card, stretch=1)
        return w

    def _cargar_resumen_dashboard(self):
        gestiones = self._obtener_lista("/admin/gestiones")
        postulantes = self._obtener_lista("/postulantes?limit=1000")
        examenes = self._obtener_lista("/admin/examenes")
        aulas = self._obtener_lista("/admin/aulas")
        hoy = date.today().isoformat()
        gestion_activa = next((g.get("nombre") for g in gestiones if g.get("estado") == "ACTIVO"), "Sin gestión")
        pendientes = sum(
            1 for p in postulantes if str(p.get("estado_biometria", "")).upper() != "COMPLETO"
        )
        examenes_hoy = sum(1 for examen in examenes if examen.get("fecha") == hoy)
        aulas_disponibles = sum(1 for aula in aulas if aula.get("activa", True))
        return (
            ("Gestión activa", gestion_activa),
            ("Biometría pendiente", pendientes),
            ("Exámenes de hoy", examenes_hoy),
            ("Aulas disponibles", aulas_disponibles),
        )

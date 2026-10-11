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
from desktop.views.admin.postulantes_mixin import BotonImportarExcel, ZonaCargaExcel


class AcademicoMixin:
    def _crear_academico_view(self):
        self.academico_stack = QStackedWidget()
        self.gestion_nav_title = QLabel("Gestiones")
        self.carrera_nav_title = QLabel("Carreras")
        self.examen_nav_title = QLabel("Examenes")
        self.gestion_nav_id = None
        self.carrera_nav_id = None
        self.gestiones_nav = []
        self.carreras_nav = []
        self.examenes_nav = []

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
        title_style = "font-size: 22px; font-weight: bold; color: #0F2C59;"

        # ── P\u00c1GINA 1: GESTIONES ──
        pagina_gestiones = QWidget()
        layout = QVBoxLayout(pagina_gestiones)
        layout.setContentsMargins(28, 28, 28, 28)
        layout.setSpacing(14)

        lbl_g = QLabel("Gestiones Academicas")
        lbl_g.setStyleSheet(title_style)
        layout.addWidget(lbl_g)

        acciones = QHBoxLayout()
        btn_nueva = QPushButton("+ Nueva gestion")
        btn_nueva.setCursor(Qt.PointingHandCursor)
        btn_nueva.setStyleSheet(btn_style)
        btn_nueva.clicked.connect(self.crear_gestion_nav)
        acciones.addWidget(btn_nueva)
        acciones.addStretch()
        layout.addLayout(acciones)

        self.gestiones_nav_table = QTableWidget(0, 4)
        self.gestiones_nav_table.setHorizontalHeaderLabels(["Gestion", "Anio", "Estado", "Acciones"])
        self.gestiones_nav_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.gestiones_nav_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.gestiones_nav_table.horizontalHeader().resizeSection(3, 220)
        self.gestiones_nav_table.verticalHeader().setDefaultSectionSize(60)
        self.gestiones_nav_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.gestiones_nav_table.setAlternatingRowColors(True)
        self.gestiones_nav_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.gestiones_nav_table)

        # ── P\u00c1GINA 2: CARRERAS ──
        pagina_carreras = QWidget()
        layout_carreras = QVBoxLayout(pagina_carreras)
        layout_carreras.setContentsMargins(28, 28, 28, 28)
        layout_carreras.setSpacing(14)

        self.carrera_nav_title.setStyleSheet(title_style)
        layout_carreras.addWidget(self.carrera_nav_title)

        botones_carrera = QHBoxLayout()
        volver_gestion = QPushButton("< Volver a gestiones")
        volver_gestion.setCursor(Qt.PointingHandCursor)
        volver_gestion.setStyleSheet(btn_secondary)
        volver_gestion.clicked.connect(lambda: self.academico_stack.setCurrentIndex(0))
        btn_nueva_carrera = QPushButton("+ Nueva carrera")
        btn_nueva_carrera.setCursor(Qt.PointingHandCursor)
        btn_nueva_carrera.setStyleSheet(btn_style)
        btn_nueva_carrera.clicked.connect(self.crear_carrera_nav)
        btn_postulantes = QPushButton("Postulantes de la gestion")
        btn_postulantes.setCursor(Qt.PointingHandCursor)
        btn_postulantes.setStyleSheet(btn_style.replace("#2563EB", "#16A34A").replace("#1D4ED8", "#15803D"))
        btn_postulantes.clicked.connect(self.abrir_postulantes_gestion)
        botones_carrera.addWidget(volver_gestion)
        botones_carrera.addWidget(btn_nueva_carrera)
        botones_carrera.addWidget(btn_postulantes)
        botones_carrera.addStretch()
        layout_carreras.addLayout(botones_carrera)

        self.carreras_nav_table = QTableWidget(0, 3)
        self.carreras_nav_table.setHorizontalHeaderLabels(["Carrera", "Codigo", "Acciones"])
        self.carreras_nav_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.carreras_nav_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.carreras_nav_table.horizontalHeader().resizeSection(2, 220)
        self.carreras_nav_table.verticalHeader().setDefaultSectionSize(60)
        self.carreras_nav_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.carreras_nav_table.setAlternatingRowColors(True)
        self.carreras_nav_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout_carreras.addWidget(self.carreras_nav_table)

        # ── P\u00c1GINA 3: EX\u00c1MENES ──
        pagina_examenes = QWidget()
        layout_examenes = QVBoxLayout(pagina_examenes)
        layout_examenes.setContentsMargins(28, 28, 28, 28)
        layout_examenes.setSpacing(14)

        self.examen_nav_title.setStyleSheet(title_style)
        layout_examenes.addWidget(self.examen_nav_title)

        acciones_examen = QHBoxLayout()
        volver_carrera = QPushButton("< Volver a carreras")
        volver_carrera.setCursor(Qt.PointingHandCursor)
        volver_carrera.setStyleSheet(btn_secondary)
        volver_carrera.clicked.connect(lambda: self.academico_stack.setCurrentIndex(1))
        btn_nuevo_examen = QPushButton("+ Programar nuevo examen")
        btn_nuevo_examen.setCursor(Qt.PointingHandCursor)
        btn_nuevo_examen.setStyleSheet(btn_style)
        btn_nuevo_examen.clicked.connect(self.crear_examen_nav)
        acciones_examen.addWidget(volver_carrera)
        acciones_examen.addWidget(btn_nuevo_examen)
        acciones_examen.addStretch()
        layout_examenes.addLayout(acciones_examen)

        self.examenes_nav_table = QTableWidget(0, 4)
        self.examenes_nav_table.setHorizontalHeaderLabels(["Materia", "Fecha", "Horario", "Acciones"])
        self.examenes_nav_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.examenes_nav_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.examenes_nav_table.horizontalHeader().resizeSection(3, 220)
        self.examenes_nav_table.verticalHeader().setDefaultSectionSize(60)
        self.examenes_nav_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.examenes_nav_table.setAlternatingRowColors(True)
        self.examenes_nav_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout_examenes.addWidget(self.examenes_nav_table)

        # ── P\u00c1GINA 4: POSTULANTES DE GESTI\u00d3N ──
        pagina_postulantes = QWidget()
        layout_postulantes = QVBoxLayout(pagina_postulantes)
        layout_postulantes.setContentsMargins(28, 28, 28, 28)
        layout_postulantes.setSpacing(14)

        self.postulantes_nav_title = QLabel("Postulantes de la gestion")
        self.postulantes_nav_title.setStyleSheet(title_style)
        layout_postulantes.addWidget(self.postulantes_nav_title)

        acciones_postulantes = QHBoxLayout()
        volver_carreras = QPushButton("< Volver a carreras")
        volver_carreras.setCursor(Qt.PointingHandCursor)
        volver_carreras.setStyleSheet(btn_secondary)
        volver_carreras.clicked.connect(lambda: self.academico_stack.setCurrentIndex(1))
        btn_nuevo_postulante = QPushButton("+ Nuevo postulante")
        btn_nuevo_postulante.setCursor(Qt.PointingHandCursor)
        btn_nuevo_postulante.setStyleSheet(btn_style)
        btn_nuevo_postulante.clicked.connect(self.crear_postulante_gestion)
        btn_importar_postulantes = BotonImportarExcel("Importar Excel")
        btn_importar_postulantes.setCursor(Qt.PointingHandCursor)
        btn_importar_postulantes.setStyleSheet(btn_style.replace("#2563EB", "#16A34A").replace("#1D4ED8", "#15803D"))
        btn_importar_postulantes.clicked.connect(self.importar_postulantes_gestion)
        btn_importar_postulantes.archivo_recibido.connect(self.importar_excel_desde_archivo)
        acciones_postulantes.addWidget(volver_carreras)
        acciones_postulantes.addWidget(btn_nuevo_postulante)
        acciones_postulantes.addWidget(btn_importar_postulantes)
        acciones_postulantes.addStretch()
        layout_postulantes.addLayout(acciones_postulantes)

        # Objetivo grande para arrastrar el archivo: el botón es chico y es
        # fácil no darle.
        self.zona_carga_excel = ZonaCargaExcel()
        self.zona_carga_excel.archivo_recibido.connect(self.importar_excel_desde_archivo)
        self.zona_carga_excel.seleccionar_archivo.connect(self.importar_postulantes_gestion)
        layout_postulantes.addWidget(self.zona_carga_excel)

        self.postulantes_nav_table = QTableWidget(0, 4)
        self.postulantes_nav_table.setHorizontalHeaderLabels(["C.I.", "Postulante", "Carreras inscritas", "Acciones"])
        self.postulantes_nav_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.postulantes_nav_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self.postulantes_nav_table.horizontalHeader().resizeSection(3, 250)
        self.postulantes_nav_table.verticalHeader().setDefaultSectionSize(60)
        self.postulantes_nav_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.postulantes_nav_table.setAlternatingRowColors(True)
        self.postulantes_nav_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout_postulantes.addWidget(self.postulantes_nav_table)

        for pagina in (pagina_gestiones, pagina_carreras, pagina_examenes, pagina_postulantes):
            self.academico_stack.addWidget(pagina)
        self.cargar_gestiones_nav()
        return self.academico_stack

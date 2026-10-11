import cv2
import requests
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget,
    QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QLineEdit, QListWidget, QListWidgetItem, QComboBox
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread
from PySide6.QtGui import QImage, QPixmap, QKeyEvent
from desktop.config.app_config import AppConfig
from desktop.views.checkin.workers import IdentifyWorker


class ReconocimientoMixin:
    def _on_tab_changed(self, index):
        # La detección automática solo corre cuando su pestaña está visible.
        if index != self.tabs.indexOf(self.tab_reconocimiento):
            self.detener_auto_deteccion()

    def toggle_auto_deteccion(self):
        if self.auto_activo:
            self.detener_auto_deteccion()
        else:
            self.iniciar_auto_deteccion()

    def iniciar_auto_deteccion(self):
        if self.auto_activo:
            return
        self.auto_cap = cv2.VideoCapture(0)
        if self.auto_cap is None or not self.auto_cap.isOpened():
            self.auto_visor.setText(
                "No se pudo acceder a la cámara.\nVerifique que no esté en uso por otra aplicación."
            )
            self.auto_estado.setText("Cámara no disponible.")
            if self.auto_cap:
                self.auto_cap.release()
            self.auto_cap = None
            return
        self.auto_activo = True
        self.auto_ultimo_id = None
        self.btn_auto_toggle.setText("Detener detección")
        self.auto_estado.setText("Detección activa. Mire a la cámara.")
        self.auto_frame_timer.start(30)
        self._auto_fin_cooldown()

    def detener_auto_deteccion(self):
        if not self.auto_activo and self.auto_cap is None:
            return
        self.auto_activo = False
        self.auto_frame_timer.stop()
        self.auto_detect_timer.stop()
        self.auto_cooldown_timer.stop()
        if self.auto_cap is not None:
            self.auto_cap.release()
            self.auto_cap = None
        self.btn_auto_toggle.setText("Iniciar detección")
        self.auto_estado.setText("Detección detenida.")

    def _auto_actualizar_frame(self):
        if self.auto_cap and self.auto_cap.isOpened():
            ret, frame = self.auto_cap.read()
            if ret:
                h, w, _ = frame.shape
                cv2.rectangle(frame, (w // 4, h // 6), (3 * w // 4, 5 * h // 6), (37, 99, 235), 2)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                qimg = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888)
                self.auto_visor.setPixmap(
                    QPixmap.fromImage(qimg).scaled(560, 380, Qt.KeepAspectRatio)
                )

    def _auto_detectar(self):
        if not self.auto_activo or self.auto_worker is not None:
            return
        if not self.auto_cap or not self.auto_cap.isOpened():
            return
        ret, frame = self.auto_cap.read()
        if not ret:
            return
        ok, encoded = cv2.imencode(".jpg", frame)
        if not ok:
            return

        app_key = AppConfig.get_app_key()
        if not app_key:
            self.auto_estado.setText("No existe una clave APP_CLIENT_KEY válida.")
            return

        id_examen = self.info_examen.get("id_examen")
        self.auto_worker = IdentifyWorker(
            url=f"{self.api_base_url}/marcaciones/identificar-rostro",
            headers={"X-App-Key": app_key},
            id_examen=id_examen,
            image_bytes=encoded.tobytes(),
            parent=self,
        )
        self.auto_worker.resultado.connect(self._auto_mostrar_respuesta)
        self.auto_worker.finished.connect(self._auto_worker_finalizado)
        self.auto_worker.start()

    def _auto_worker_finalizado(self):
        worker, self.auto_worker = self.auto_worker, None
        if worker is not None:
            worker.deleteLater()

    def _auto_mostrar_respuesta(self, data, status_code, error):
        if error:
            self.auto_estado.setText(f"Sin conexión: {error}")
            return
        if status_code != 200:
            self.auto_estado.setText(data.get("detail", "Error del servidor"))
            return
        if not data.get("coincidencia"):
            self.auto_estado.setText(data.get("mensaje", "Rostro no reconocido."))
            return

        id_post = data.get("id_postulante")
        # Evitar reenviar repetidamente al mismo postulante.
        if id_post == self.auto_ultimo_id and self.auto_cooldown_timer.isActive():
            return
        self.auto_ultimo_id = id_post

        aceptado = data.get("resultado") == "ACEPTADO"
        color = "#16A34A" if aceptado else "#DC2626"
        self.auto_resultado.setText(
            "ACCESO CONCEDIDO" if aceptado else f"ACCESO {data.get('resultado', 'RECHAZADO')}"
        )
        self.auto_resultado.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: white; "
            f"background-color: {color}; border-radius: 8px; padding: 10px;"
        )
        self.auto_resultado.setVisible(True)

        self.auto_titulo.setText(data.get("nombre_completo", "Postulante"))
        self.auto_subtitulo.setText(data.get("mensaje", ""))

        filas = [
            ("CI", data.get("ci")),
            ("Carrera", data.get("carrera")),
            ("Materia", data.get("materia")),
            ("Aula", data.get("aula")),
            ("Asiento", data.get("numero_asiento")),
            ("Hora de ingreso", data.get("hora_ingreso") or data.get("fecha_hora")),
        ]
        html = "".join(
            f"<p style='margin:4px 0;'><b style='color:#64748B;'>{etiqueta}:</b> "
            f"<span style='color:#0F2C59;'>{valor if valor not in (None, '') else '—'}</span></p>"
            for etiqueta, valor in filas
        )
        self.auto_datos.setText(html)

        self.auto_estado.setText(
            data.get("mensaje", "Ingreso procesado.") + " | Aleje el rostro para el siguiente."
        )
        # Pausa la detección unos segundos para no duplicar al mismo postulante.
        self.auto_detect_timer.stop()
        self.auto_cooldown_timer.start(6000)
        self.actualizar_contador()

    def _auto_fin_cooldown(self):
        if self.auto_activo:
            self.auto_detect_timer.start(1200)

    def _construir_tab_reconocimiento(self):
        # ═══ TAB: RECONOCIMIENTO FACIAL AUTOMÁTICO ═══
        tab_auto = QWidget()
        layout_auto = QHBoxLayout(tab_auto)
        layout_auto.setContentsMargins(12, 12, 12, 12)
        layout_auto.setSpacing(16)

        # Lado izquierdo: cámara
        lado_cam = QVBoxLayout()
        lado_cam.setSpacing(10)
        lbl_auto = QLabel("Detección automática de rostro")
        lbl_auto.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F2C59;")
        lado_cam.addWidget(lbl_auto)

        self.auto_visor = QLabel("Iniciando cámara...")
        self.auto_visor.setAlignment(Qt.AlignCenter)
        self.auto_visor.setMinimumSize(560, 380)
        self.auto_visor.setStyleSheet(
            "background-color: #0F172A; border-radius: 10px; color: #64748B; font-size: 15px;"
        )
        lado_cam.addWidget(self.auto_visor, stretch=1)

        self.auto_estado = QLabel("Acérquese a la cámara. La identificación es automática.")
        self.auto_estado.setWordWrap(True)
        self.auto_estado.setStyleSheet("color: #475569; font-size: 12px;")
        lado_cam.addWidget(self.auto_estado)

        self.btn_auto_toggle = QPushButton("Iniciar detección")
        self.btn_auto_toggle.setMinimumHeight(44)
        self.btn_auto_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_auto_toggle.setStyleSheet("""
            QPushButton {
                background-color: #2563EB; color: white; font-size: 14px;
                font-weight: bold; padding: 10px; border-radius: 8px; border: none;
            }
            QPushButton:hover { background-color: #1D4ED8; }
        """)
        self.btn_auto_toggle.clicked.connect(self.toggle_auto_deteccion)
        lado_cam.addWidget(self.btn_auto_toggle)
        layout_auto.addLayout(lado_cam, stretch=3)

        # Lado derecho: ficha de datos
        self.auto_card = QFrame()
        self.auto_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 12px;
            }
        """)
        card_auto = QVBoxLayout(self.auto_card)
        card_auto.setContentsMargins(22, 22, 22, 22)
        card_auto.setSpacing(10)

        self.auto_titulo = QLabel("Sin identificación")
        self.auto_titulo.setStyleSheet("font-size: 22px; font-weight: 900; color: #0F2C59; background: transparent;")
        self.auto_titulo.setWordWrap(True)
        card_auto.addWidget(self.auto_titulo)

        self.auto_subtitulo = QLabel("Esperando detección de rostro...")
        self.auto_subtitulo.setStyleSheet("font-size: 13px; color: #64748B; background: transparent;")
        self.auto_subtitulo.setWordWrap(True)
        card_auto.addWidget(self.auto_subtitulo)

        self.auto_resultado = QLabel("")
        self.auto_resultado.setAlignment(Qt.AlignCenter)
        self.auto_resultado.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: white; "
            "background-color: #64748B; border-radius: 8px; padding: 10px;"
        )
        self.auto_resultado.setVisible(False)
        card_auto.addWidget(self.auto_resultado)

        self.auto_datos = QLabel("—")
        self.auto_datos.setStyleSheet("font-size: 14px; color: #1E293B; background: transparent;")
        self.auto_datos.setWordWrap(True)
        self.auto_datos.setTextFormat(Qt.RichText)
        card_auto.addWidget(self.auto_datos)

        card_auto.addStretch()
        layout_auto.addWidget(self.auto_card, stretch=2)

        self.tabs.addTab(tab_auto, "Reconocimiento Automático")
        self.tab_reconocimiento = tab_auto
        self.tabs.currentChanged.connect(self._on_tab_changed)

        # Estado interno del reconocimiento automático
        self.auto_activo = False
        self.auto_cap = None
        self.auto_worker = None
        self.auto_ultimo_id = None
        self.auto_cooldown_timer = QTimer(self)
        self.auto_cooldown_timer.setSingleShot(True)
        self.auto_cooldown_timer.timeout.connect(self._auto_fin_cooldown)
        self.auto_frame_timer = QTimer(self)
        self.auto_frame_timer.timeout.connect(self._auto_actualizar_frame)
        self.auto_detect_timer = QTimer(self)
        self.auto_detect_timer.timeout.connect(self._auto_detectar)


"""Diálogo de captura/enrolamiento de huella.

Funciona con cualquier lector soportado:
- **DigitalPersona U.are.U** (y otros compatibles con libfprint).
- **ZKTeco ZK4500/ZK9500** (con la ZKFinger SDK instalada).

Muestra vista previa de la huella, selector de dedo, selector
de lector (si hay varios) y el flujo de enrolamiento multi-etapa.
"""

import logging

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox,
    QProgressBar, QDialogButtonBox, QSizePolicy,
)

from desktop.biometria import (
    detectar_lectores,
    libfprint_disponible,
    sdk_zk_disponible,
    crear_lector,
    DEDO_NOMBRES,
    LectorNoConectadoError,
    SDKNoDisponibleError,
    PermisoUSBError,
    ErrorLector,
    prefijar_plantilla,
)

log = logging.getLogger(__name__)


class EnrolamientoController:
    """Controlador de enrolamiento que ejecuta en el hilo principal.

    libfprint necesita el main context de GLib del hilo principal,
    por lo que no se puede usar QThread. En su lugar, usamos
    QTimer.singleShot para ejecutar pasos asíncronos sin bloquear la UI.
    """

    def __init__(self, dialog, lector, dedo):
        self.dialog = dialog
        self.lector = lector
        self.dedo = dedo
        self._activo = False

    def iniciar(self):
        """Inicia el proceso de enrolamiento en el hilo principal."""
        self._activo = True
        log.debug("EnrolamientoController: iniciando conexión...")
        try:
            self.lector.conectar()
            log.debug("EnrolamientoController: lector conectado OK")
            # Usar QTimer para no bloquear la UI
            QTimer.singleShot(0, self._enrolar_paso)
        except Exception as error:
            log.exception("Error conectando lector")
            self._activo = False
            self.dialog._on_error(str(error))

    def _enrolar_paso(self):
        """Ejecuta un paso del enrolamiento (asíncrono vía QTimer)."""
        if not self._activo:
            return
        try:
            log.debug("EnrolamientoController: iniciando enrolar_dedo...")
            plantilla = self.lector.enrolar_dedo(self.dedo, self._on_avance)
            log.debug("EnrolamientoController: enrolamiento completado OK")
            self._activo = False
            self.dialog._on_plantilla_lista(plantilla, self.lector.tipo)
        except Exception as error:
            log.exception("Error en enrolamiento")
            self._activo = False
            self.dialog._on_error(str(error))
        finally:
            if self.lector and self.lector.conectado:
                try:
                    self.lector.cerrar()
                except Exception:
                    pass

    def _on_avance(self, completadas, total, imagen, ancho=0, alto=0):
        """Callback de progreso llamado por libfprint (hilo principal)."""
        if self._activo:
            self.dialog._on_avance(completadas, total, imagen, ancho, alto)

    def detener(self):
        """Detiene el proceso de enrolamiento."""
        self._activo = False


class DialogCapturaHuella(QDialog):
    MAX_HABILITADAS = 2  # Máximo de huellas habilitadas permitidas
    """Diálogo de enrolamiento de huella. Devuelve ``plantilla_final``."""

    def __init__(self, postulante=None, dedo_inicial=1, dedos_registrados=None,
                 dedos_habilitados=None, huellas_por_dedo=None, parent=None):
        super().__init__(parent)
        self.postulante = postulante or {}
        self.dedos_registrados = set(dedos_registrados or [])
        self.dedos_habilitados = set(dedos_habilitados or [])
        self.dedos_sin_habilitar = self.dedos_registrados - self.dedos_habilitados
        self.huellas_por_dedo = dict(huellas_por_dedo or {})
        self.guardar_habilitaciones_solicitado = False
        self.setWindowTitle("Registro de Huella")
        self.setMinimumWidth(560)
        self.plantilla_final = None
        self.tipo_lector = ""
        self._worker = None
        self._lector_info = []
        self._check_dedos_habilitar = {}  # numero -> QCheckBox

        self._crear_ui(dedo_inicial)
        self._actualizar_lectores()

    # ══════════════════════ INTERFAZ ══════════════════════
    def _crear_ui(self, dedo_inicial):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(14)

        # Encabezado
        nombre = self.postulante.get("nombre_completo")
        if not nombre and self.postulante.get("nombres"):
            nombre = f"{self.postulante.get('nombres')} {self.postulante.get('apellidos', '')}".strip()
        ci = self.postulante.get("ci", "")
        lbl_titulo = QLabel(
            f"Registro de huella — {nombre or 'Postulante'}"
            + (f"  (CI: {ci})" if ci else "")
        )
        lbl_titulo.setStyleSheet("font-size: 17px; font-weight: 800; color: #0F2C59;")
        layout.addWidget(lbl_titulo)

        # Banner de estado
        self.banner = QLabel()
        self.banner.setWordWrap(True)
        self.banner.setStyleSheet("font-size: 12px; padding: 8px 10px; border-radius: 6px;")
        self.banner.setVisible(False)
        layout.addWidget(self.banner)

        # Cuadrícula de dedos registrados/pendientes + checkboxes habilitar
        from PySide6.QtWidgets import QGridLayout, QPushButton, QCheckBox, QWidget
        grid_dedos = QGridLayout()
        grid_dedos.setSpacing(6)
        self.lbl_dedos = QLabel("Dedos (marca ✅ para habilitar, máx. 2):")
        self.lbl_dedos.setStyleSheet("font-size: 13px; font-weight: 700; color: #334155;")
        layout.addWidget(self.lbl_dedos)

        self.dedo_botones = {}
        self._check_dedos_habilitar = {}
        for i, (numero, nombre_dedo) in enumerate(DEDO_NOMBRES.items()):
            fila = i // 5
            col = i % 5
            contenedor = QWidget()
            vbox = QVBoxLayout(contenedor)
            vbox.setContentsMargins(2, 2, 2, 2)
            vbox.setSpacing(2)

            btn = QPushButton(f"{numero} — {nombre_dedo}")
            btn.setMinimumHeight(40)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setProperty("dedo_numero", numero)
            btn.clicked.connect(lambda _, n=numero: self._dedo_seleccionado(n))

            chk = QCheckBox("Habilitar")
            chk.setEnabled(numero in self.dedos_registrados)
            chk.setChecked(numero in self.dedos_habilitados)
            chk.stateChanged.connect(lambda state, n=numero: self._cambiar_habilitar(n, state))

            vbox.addWidget(btn)
            if numero in self.dedos_registrados:
                vbox.addWidget(chk)

            self.dedo_botones[numero] = btn
            self._check_dedos_habilitar[numero] = chk
            grid_dedos.addWidget(contenedor, fila, col)
        layout.addLayout(grid_dedos)
        # Selectores de lector y dedo
        fila_selectores = QHBoxLayout()
        fila_selectores.addWidget(QLabel("Lector:"))
        self.combo_lector = QComboBox()
        self.combo_lector.setMinimumHeight(34)
        self.combo_lector.setMinimumWidth(260)
        self.combo_lector.currentIndexChanged.connect(self._lector_cambiado)
        fila_selectores.addWidget(self.combo_lector)

        fila_selectores.addSpacing(18)
        fila_selectores.addWidget(QLabel("Dedo:"))
        self.combo_dedo = QComboBox()
        for numero, nombre_dedo in DEDO_NOMBRES.items():
            self.combo_dedo.addItem(f"{numero} — {nombre_dedo}", numero)
        if dedo_inicial in DEDO_NOMBRES:
            self.combo_dedo.setCurrentIndex(dedo_inicial - 1)
        self.combo_dedo.setMinimumHeight(34)
        self.combo_dedo.setMinimumWidth(230)
        self.combo_dedo.currentIndexChanged.connect(self._actualizar_estado_dedos)
        fila_selectores.addWidget(self.combo_dedo)
        fila_selectores.addStretch()
        layout.addLayout(fila_selectores)

        # Visor de la huella
        self.visor = QLabel()
        self.visor.setAlignment(Qt.AlignCenter)
        self.visor.setMinimumSize(256, 300)
        self.visor.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._mostrar_placeholder()
        contenedor_visor = QHBoxLayout()
        contenedor_visor.addStretch()
        contenedor_visor.addWidget(self.visor)
        contenedor_visor.addStretch()
        layout.addLayout(contenedor_visor)

        # Estado y progreso
        self.lbl_estado = QLabel("Pulsa «Iniciar captura» y coloca el dedo en el lector.")
        self.lbl_estado.setWordWrap(True)
        self.lbl_estado.setStyleSheet("font-size: 13px; color: #334155; font-weight: 600;")
        layout.addWidget(self.lbl_estado)

        self.progreso = QProgressBar()
        self.progreso.setRange(0, 3)
        self.progreso.setValue(0)
        self.progreso.setTextVisible(True)
        self.progreso.setFormat("Toques: %v/%m")
        layout.addWidget(self.progreso)

        # Botones
        self.btn_iniciar = QPushButton("▶ Iniciar captura")
        self.btn_iniciar.setMinimumHeight(42)
        self.btn_iniciar.setCursor(Qt.PointingHandCursor)
        self.btn_iniciar.setStyleSheet(
            "QPushButton { background-color: #2563EB; color: white; font-size: 14px;"
            "font-weight: bold; border-radius: 8px; padding: 8px 18px; border: none; }"
            "QPushButton:hover { background-color: #1D4ED8; }"
            "QPushButton:disabled { background-color: #93C5FD; }"
        )
        self.btn_iniciar.clicked.connect(self._iniciar_captura)

        self.btn_cancelar = QPushButton("Cancelar")
        self.btn_cancelar.setMinimumHeight(42)
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.setStyleSheet(
            "QPushButton { background-color: #F1F5F9; color: #334155; font-size: 14px;"
            "font-weight: 600; border-radius: 8px; padding: 8px 18px;"
            "border: 1px solid #CBD5E1; }"
            "QPushButton:hover { background-color: #E2E8F0; }"
        )
        self.btn_cancelar.clicked.connect(self.reject)

        fila_botones = QHBoxLayout()
        fila_botones.addStretch()
        fila_botones.addWidget(self.btn_iniciar)
        self.btn_guardar_habilitaciones = QPushButton("Guardar cambios")
        self.btn_guardar_habilitaciones.setMinimumHeight(42)
        self.btn_guardar_habilitaciones.setCursor(Qt.PointingHandCursor)
        self.btn_guardar_habilitaciones.setEnabled(bool(self.huellas_por_dedo))
        self.btn_guardar_habilitaciones.setStyleSheet(
            "QPushButton { background-color: #0F766E; color: white; font-size: 14px;"
            "font-weight: bold; border-radius: 8px; padding: 8px 18px; border: none; }"
            "QPushButton:hover { background-color: #115E59; }"
            "QPushButton:disabled { background-color: #CBD5E1; color: #64748B; }"
        )
        self.btn_guardar_habilitaciones.clicked.connect(self._guardar_habilitaciones)
        fila_botones.addWidget(self.btn_guardar_habilitaciones)
        fila_botones.addWidget(self.btn_cancelar)
        layout.addLayout(fila_botones)

        # Actualizar estado de dedos (después de que combo_dedo exista)
        self._actualizar_estado_dedos()

    def _mostrar_placeholder(self):
        self.visor.setText("👆\n\nSin captura")
        self.visor.setStyleSheet(
            "background-color: #0B1220; border: 2px solid #E2E8F0; border-radius: 10px;"
            "color: #475569; font-size: 13px;"
        )

    def _banner_info(self, texto, color_fondo="#FEF3C7", color_borde="#FCD34D", color_texto="#92400E"):
        self.banner.setText(texto)
        self.banner.setStyleSheet(
            f"font-size: 12px; padding: 8px 10px; border-radius: 6px; "
            f"background-color: {color_fondo}; border: 1px solid {color_borde}; "
            f"color: {color_texto};"
        )
        self.banner.setVisible(True)

    def _actualizar_lectores(self):
        """Detecta los lectores y llena el selector."""
        self._lector_info = []
        self.combo_lector.blockSignals(True)
        self.combo_lector.clear()
        try:
            lectores, usb_ok = detectar_lectores()
        except Exception:
            lectores, usb_ok = [], False

        libfprint_ok = libfprint_disponible()
        sdk_zk = sdk_zk_disponible()

        if not usb_ok:
            self._banner_info("⚠️ No se pudo acceder al bus USB. "
                              "Ejecuta: sudo ./setup_lectores_huella.sh")
            self.btn_iniciar.setEnabled(False)
            self.combo_lector.blockSignals(False)
            return

        if not lectores:
            self._banner_info("⚠️ No se detectó ningún lector de huella.\n"
                              "Conecta el lector por USB.")
            self.btn_iniciar.setEnabled(False)
            self.combo_lector.blockSignals(False)
            return

        # Construir la lista de lectores utilizables
        utilizables = []
        for lector in lectores:
            if lector.tipo == "libfprint":
                if libfprint_ok:
                    utilizables.append(lector)
            elif sdk_zk:
                utilizables.append(lector)

        for lector in utilizables:
            etiqueta = f"{lector.modelo} ({lector.tipo})"
            self.combo_lector.addItem(etiqueta, lector)
            self._lector_info.append(lector)

        if not utilizables:
            # Hay lectores, pero ninguno utilizable: explicar qué falta
            faltante = []
            if any(l.tipo == "zk" for l in lectores) and not sdk_zk:
                faltante.append("ZKFinger SDK de ZKTeco (para ZK4500/ZK9500)")
            if any(l.tipo == "libfprint" for l in lectores) and not libfprint_ok:
                faltante.append("libfprint-2")
            self._banner_info(
                f"Lector(es) conectado(s): "
                f"{', '.join(l.modelo for l in lectores)}\n\n"
                f"Falta por instalar: {', '.join(faltante)}.\n"
                "Ejecuta:  ./setup_lectores_huella.sh",
            )
            self.btn_iniciar.setEnabled(False)
        else:
            lista = "\n".join(f"• {l.descripcion}" for l in lectores)
            self._banner_info(
                f"✅ Lector(es) detectado(s):\n{lista}",
                color_fondo="#DCFCE7", color_borde="#86EFAC", color_texto="#166534",
            )
            self.btn_iniciar.setEnabled(True)
        self.combo_lector.blockSignals(False)
        if self.combo_lector.count() > 0:
            self.combo_lector.setCurrentIndex(0)

    def _lector_cambiado(self, _indice):
        lector = self.combo_lector.currentData()
        if lector and lector.scan_type == "swipe":
            self.lbl_estado.setText("Pulsa «Iniciar captura» y PASA el dedo por el lector.")
        else:
            self.lbl_estado.setText(
                "Pulsa «Iniciar captura»; luego levanta el dedo "
                "y colócalo en el lector."
            )

    def _actualizar_estado_dedos(self):
        """Actualiza la apariencia de los botones de dedos.
        Colores:
        - Verde: registrado y habilitado
        - Gris: solo registrado (pendiente de habilitación)
        - Rojo: no registrado
        - Azul: seleccionado actualmente
        """
        for numero, btn in self.dedo_botones.items():
            registrado = numero in self.dedos_registrados
            seleccionado = (self.combo_dedo.currentData() or 1) == numero
            if seleccionado:
                btn.setStyleSheet(
                    "background-color: #2563EB; color: white; font-weight: bold; "
                    "border: 2px solid #1D4ED8; border-radius: 6px; font-size: 11px;"
                )
            elif registrado:
                btn.setStyleSheet(
                    "background-color: #16A34A; color: white; font-weight: bold; "
                    "border: 1px solid #15803D; border-radius: 6px; font-size: 11px;"
                )
            elif numero in getattr(self, 'dedos_sin_habilitar', set()):
                btn.setStyleSheet(
                    "background-color: #9CA3AF; color: white; font-weight: bold; "
                    "border: 1px solid #6B7280; border-radius: 6px; font-size: 11px;"
                )
            else:
                btn.setStyleSheet(
                    "background-color: #EF4444; color: white; font-weight: bold; "
                    "border: 1px solid #DC2626; border-radius: 6px; font-size: 11px;"
                )

    def _dedo_seleccionado(self, numero):
        """Selecciona un dedo de la cuadrícula."""
        self.combo_dedo.setCurrentIndex(numero - 1)
        self._actualizar_estado_dedos()
        # Actualizar texto de estado
        lector = self.combo_lector.currentData()
        if lector and lector.scan_type == "swipe":
            self.lbl_estado.setText("Pulsa «Iniciar captura» y PASA el dedo por el lector.")
        else:
            self.lbl_estado.setText(
                "Pulsa «Iniciar captura»; luego levanta el dedo "
                "y colócalo en el lector."
            )

    def _cambiar_habilitar(self, numero, state):
        """Habilita/deshabilita un dedo con límite de MAX_HABILITADAS."""
        from PySide6.QtCore import Qt
        if state == Qt.Checked.value:
            # Contar cuántos hay habilitados (excluyendo este)
            otros_habilitados = [n for n, chk in self._check_dedos_habilitar.items()
                                 if chk.isChecked() and n != numero]
            if len(otros_habilitados) >= self.MAX_HABILITADAS:
                # Revertir: no permitir más de MAX_HABILITADAS
                chk = self._check_dedos_habilitar[numero]
                chk.blockSignals(True)
                chk.setChecked(False)
                chk.blockSignals(False)
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Límite alcanzado",
                    f"Solo puedes habilitar un máximo de {self.MAX_HABILITADAS} huellas.\n"
                    "Deshabilita otra primero."
                )
                return
            self.dedos_habilitados.add(numero)
            self.dedos_sin_habilitar.discard(numero)
        else:
            self.dedos_habilitados.discard(numero)
            self.dedos_sin_habilitar.add(numero)
        self._actualizar_estado_dedos()

    def obtener_dedos_habilitados(self):
        """Devuelve el conjunto de dedos habilitados."""
        return set(self.dedos_habilitados)

    def _guardar_habilitaciones(self):
        """Solicita al formulario padre persistir los checks actuales."""
        self.guardar_habilitaciones_solicitado = True
        self.accept()

    # ══════════════════════ FLUJO DE ENROLAMIENTO ══════════════════════
    def _iniciar_captura(self):
        lector_info = self.combo_lector.currentData()
        if not lector_info:
            return
        log.info("=== INICIANDO CAPTURA: lector=%s, indice=%s, dedo=%s ===",
                 lector_info.nombre, lector_info.indice_sdk, self.combo_dedo.currentData())
        self.btn_iniciar.setEnabled(False)
        self.progreso.setValue(0)
        self.progreso.setRange(0, lector_info.etapas_enrolamiento if lector_info.tipo == "libfprint" else 3)
        tipo = "swipe" if lector_info.scan_type == "swipe" else "press"
        self.lbl_estado.setText(
            "Pasa el dedo por lector…" if tipo == "swipe"
            else "Levanta el dedo y colócalo en el lector…"
        )
        # Crear el lector en el hilo principal (libfprint necesita el main context de GLib)
        log.debug("Creando lector en hilo principal...")
        try:
            lector = crear_lector(lector_info.tipo, lector_info.indice_sdk)
            log.debug("Lector creado OK: %s", lector)
        except Exception as e:
            log.exception("Error creando lector")
            self.lbl_estado.setText(f"❌ Error creando lector: {e}")
            self.btn_iniciar.setEnabled(True)
            return
        # Usar EnrolamientoController (ejecuta en el hilo principal vía QTimer)
        self._controller = EnrolamientoController(
            self, lector, self.combo_dedo.currentData() or 1
        )
        log.debug("Iniciando EnrolamientoController...")
        self._controller.iniciar()

    def _on_avance(self, completadas, total, imagen, ancho, alto):
        self.progreso.setRange(0, total)
        self.progreso.setValue(completadas)
        if imagen:
            self._mostrar_imagen(imagen, ancho, alto)
        if completadas < total:
            self.lbl_estado.setText(
                f"✅ Toque {completadas}/{total} capturado. "
                "Levanta el dedo y toca de nuevo (el MISMO dedo)."
            )

    def _on_plantilla_lista(self, plantilla, tipo_lector):
        self.plantilla_final = prefijar_plantilla(plantilla, tipo_lector)
        self.tipo_lector = tipo_lector
        self.progreso.setValue(self.progreso.maximum())
        self.lbl_estado.setText("🎉 ¡Huella registrada! La plantilla está lista.")
        self.btn_iniciar.setEnabled(False)
        self.btn_iniciar.setText("✔ Registrada")
        self.btn_cancelar.setText("Aceptar")
        # Cerrar el diálogo automáticamente para que se envíe la petición POST
        self.accept()

    def _on_error(self, mensaje):
        self.lbl_estado.setText(f"❌ {mensaje}")
        self.btn_iniciar.setEnabled(True)
        self.btn_iniciar.setText("↻ Reintentar")
        self.progreso.setValue(0)

    def _mostrar_imagen(self, imagen_bytes, ancho=0, alto=0):
        """Renderiza una imagen cruda en escala de grises."""
        if not imagen_bytes:
            return
        # Tamaño real del lector; si no viene, probamos los
        # tamaños conocidos (ZK: 256×300, uru4000: variable).
        candidatos = []
        if ancho and alto and len(imagen_bytes) >= ancho * alto:
            candidatos.append((ancho, alto))
        candidatos.extend([(256, 300), (384, 289), (320, 240), (256, 288)])
        for (w, h) in candidatos:
            if len(imagen_bytes) >= w * h:
                qimg = QImage(imagen_bytes[: w * h], w, h, w,
                              QImage.Format_Grayscale8)
                pixmap = QPixmap.fromImage(qimg)
                self.visor.setPixmap(pixmap.scaled(256, 300, Qt.KeepAspectRatio,
                                                   Qt.SmoothTransformation))
                self.visor.setStyleSheet(
                    "background-color: #0B1220; border: 2px solid #86EFAC; border-radius: 10px;"
                )
                return

    # ══════════════════════ CIERRE ══════════════════════
    def reject(self):
        self._detener_worker()
        super().reject()

    def accept(self):
        self._detener_worker()
        super().accept()

    def _detener_worker(self):
        if hasattr(self, '_controller') and self._controller:
            self._controller.detener()

    def closeEvent(self, event):
        self._detener_worker()
        super().closeEvent(event)

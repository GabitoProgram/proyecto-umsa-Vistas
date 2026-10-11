"""Pestaña de marcación biométrica por huella.

El flujo es totalmente automático: el postulante apoya el dedo en el
lector y el sistema descubre quién es, le muestra su nombre, aula y
asiento, y registra el ingreso. No hay que buscar a nadie ni elegir dedo.

El reconocimiento facial vive en su propia pestaña
(:mod:`desktop.views.checkin.reconocimiento_mixin`), así que aquí no hay
cámara ni búsqueda por nombre.
"""

import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PySide6.QtCore import Qt
from desktop.config.app_config import AppConfig
from desktop.views.checkin.workers import IdentificacionHuellaController
from desktop.biometria import (
    detectar_lectores, libfprint_disponible, sdk_zk_disponible,
)

log = logging.getLogger(__name__)

# Cuánto tiempo permanece la tarjeta de resultado en pantalla antes de
# volver al panel de espera. Antes era 3,5 s, demasiado corto para leer
# nombre, aula y asiento de un vistazo.
TIEMPO_MOSTRAR_RESULTADO_MS = 30000


class MarcacionMixin:
    # ══════════════════════ CICLO DE VIDA ══════════════════════
    def set_examen(self, data_examen: dict):
        self.info_examen = data_examen
        self.lbl_materia.setText(f"Materia: {data_examen.get('materia', '--')}")
        self.lbl_aula.setText(f"Aula: {data_examen.get('nombre_aula', '--')}")
        self.lbl_cierre.setText(f"Cierre: {data_examen.get('cierra_a_las', '--')}")
        # El examen cambia, así que también cambia quién puede marcar.
        self._resumen_huellas(0, 0)

    def iniciar_estacion(self):
        """Entra a la pantalla de registro: arranca el contador."""
        self.counter_timer.start(5000)
        self.actualizar_contador()

    def detener_estacion(self):
        """Sale de la pantalla de registro: corta todo lo que esté corriendo."""
        self.counter_timer.stop()
        self.detener_auto_deteccion()
        if self._identificacion and self._identificacion.activo:
            self._identificacion.detener()
            self._restablecer_identificacion()

    # ══════════════════════ IDENTIFICACIÓN ══════════════════════
    def identificar_huella(self):
        """Arranca la identificación automática: sólo hay que apoyar el dedo.

        No hace falta buscar al postulante ni elegir dedo: el controlador
        prueba las huellas habilitadas del examen y devuelve quién es.
        """
        if self._identificacion and self._identificacion.activo:
            return

        app_key = AppConfig.get_app_key()
        id_examen = self.info_examen.get("id_examen")
        if not app_key:
            self.mostrar_resultado(
                False, "CLIENTE NO CONFIGURADO",
                "No existe una clave APP_CLIENT_KEY válida.", "")
            return
        if not id_examen:
            self.mostrar_resultado(
                False, "SIN EXAMEN ACTIVO",
                "Esta estación no tiene un examen asignado.", "")
            return

        # Quita el resultado anterior: si no, el postulante anterior
        # sigue en pantalla mientras se busca a este.
        self.limpiar_resultado()

        self.btn_huella.setEnabled(False)
        self.btn_huella.setText("Buscando…")
        self.btn_cancelar_huella.setVisible(True)
        self.lbl_estado_lector.setText("Preparando lector de huella…")

        self._identificacion = IdentificacionHuellaController(
            self, app_key, id_examen)
        self._identificacion.iniciar()

    def cancelar_identificacion(self):
        estaba_activa = bool(self._identificacion and self._identificacion.activo)
        if estaba_activa:
            self._identificacion.detener()
        self._restablecer_identificacion()
        if estaba_activa:
            # Va después del reset, que refresca el estado del lector.
            self.lbl_estado_lector.setText("Identificación cancelada")

    # ══════════════════════ CALLBACKS ══════════════════════
    def _estado_identificacion(self, mensaje):
        """Progreso de la identificación automática."""
        self.lbl_estado_lector.setText(mensaje)

    def _resumen_huellas(self, habilitadas, sin_habilitar):
        """Cuántos postulantes del examen pueden marcar con huella."""
        if not habilitadas and not sin_habilitar:
            self.lbl_resumen_huellas.setText("Examen: —")
            return
        partes = []
        partes.append(f"{habilitadas} huella(s) habilitada(s)" if habilitadas
                      else "ninguna huella habilitada")
        if sin_habilitar:
            partes.append(f"{sin_habilitar} sin habilitar")
        self.lbl_resumen_huellas.setText("Examen: " + " · ".join(partes))

    def _identificacion_error(self, mensaje):
        self._restablecer_identificacion()
        self.mostrar_resultado(False, "NO IDENTIFICADO", mensaje, "")

    def _identificacion_lista(self, data, candidato):
        """Muestra a quién pertenece la huella y el resultado del ingreso."""
        self._restablecer_identificacion()

        nombre = data.get("nombre_completo") or candidato.get("nombre_completo", "")
        ci = data.get("ci") or candidato.get("ci", "")
        aceptado = data.get("resultado") == "ACEPTADO"
        mensaje = data.get("mensaje") or ""

        lineas = [f"<b>{nombre}</b>"]
        detalles = []
        if ci:
            detalles.append(f"CI {ci}")
        if data.get("materia"):
            detalles.append(str(data["materia"]))
        if data.get("carrera"):
            detalles.append(str(data["carrera"]))
        if detalles:
            lineas.append(
                f"<span style='font-size:13px'>{' · '.join(detalles)}</span>"
            )

        pie = ""
        if aceptado:
            partes = []
            if data.get("aula"):
                partes.append(str(data["aula"]))
            if data.get("numero_asiento"):
                partes.append(f"Asiento #{data['numero_asiento']}")
            if data.get("hora_ingreso"):
                partes.append(str(data["hora_ingreso"]))
            pie = " · ".join(partes)
        elif mensaje:
            pie = mensaje

        self.mostrar_resultado(
            aceptado,
            "ACCESO CONCEDIDO" if aceptado else "ACCESO RECHAZADO",
            "<br>".join(lineas),
            pie,
        )
        self.actualizar_contador()

    def _restablecer_identificacion(self):
        self.btn_huella.setEnabled(True)
        self.btn_huella.setText("🖐 Identificar con Huella (automático)")
        self.btn_cancelar_huella.setVisible(False)
        self._identificacion = None
        self.actualizar_estado_lector()

    # ══════════════════════ RESULTADO EN PANTALLA ══════════════════════
    def mostrar_resultado(self, exito: bool, titulo: str, detalle: str, asiento: str):
        color = "#16A34A" if exito else "#DC2626"
        self.tarjeta_resultado.setStyleSheet(
            f"background-color: {color}; border-radius: 10px; padding: 24px;"
        )
        self.lbl_res_titulo.setText(titulo)
        self.lbl_res_detalle.setText(detalle)
        self.lbl_res_asiento.setText(asiento)

        self.panel_espera.setVisible(False)
        self.tarjeta_resultado.setVisible(True)
        self.hide_result_timer.start(TIEMPO_MOSTRAR_RESULTADO_MS)

    def limpiar_resultado(self):
        """Quita la tarjeta de resultado y vuelve al panel de espera."""
        self.hide_result_timer.stop()
        self.tarjeta_resultado.setVisible(False)
        self.lbl_res_titulo.setText("RESULTADO")
        self.lbl_res_detalle.setText("")
        self.lbl_res_asiento.setText("")
        self.panel_espera.setVisible(True)

    def restaurar_panel_espera(self):
        """Vuelve al panel de espera (lo dispara el temporizador)."""
        self.tarjeta_resultado.setVisible(False)
        self.panel_espera.setVisible(True)

    # ══════════════════════ LECTOR ══════════════════════
    def actualizar_estado_lector(self):
        """Muestra en la etiqueta qué lectores de huella están conectados."""
        try:
            lectores, usb_ok = detectar_lectores()
            fprint_ok = libfprint_disponible()
            sdk_zk = sdk_zk_disponible()
        except Exception:
            lectores, usb_ok, fprint_ok, sdk_zk = [], False, False, False
        if not usb_ok:
            self.lbl_estado_lector.setText("Lector de huella: bus USB no disponible")
            self.lbl_estado_lector.setStyleSheet("color: #F87171; font-size: 11px;")
        elif not lectores:
            self.lbl_estado_lector.setText("Lector de huella: no conectado")
            self.lbl_estado_lector.setStyleSheet("color: #FBBF24; font-size: 11px;")
        else:
            utilizable = any(
                (l.tipo == "libfprint" and fprint_ok)
                or (l.tipo == "zk" and sdk_zk)
                for l in lectores
            )
            modelos = ", ".join(l.modelo for l in lectores)
            if utilizable:
                self.lbl_estado_lector.setText(f"Lector {modelos}: listo")
                self.lbl_estado_lector.setStyleSheet("color: #4ADE80; font-size: 11px;")
            else:
                falta = []
                if any(l.tipo == "zk" for l in lectores) and not sdk_zk:
                    falta.append("SDK ZKTeco")
                self.lbl_estado_lector.setText(
                    f"Lector {modelos} detectado — falta "
                    f"{', '.join(falta) or 'configuración'} (setup_lectores_huella.sh)"
                )
                self.lbl_estado_lector.setStyleSheet("color: #FBBF24; font-size: 11px;")

    # ══════════════════════ INTERFAZ ══════════════════════
    def _construir_tab_marcacion(self):
        # ═══ TAB 1: MARCACIÓN BIOMÉTRICA ═══
        tab_marcacion = QWidget()
        layout_marc = QVBoxLayout(tab_marcacion)
        layout_marc.setContentsMargins(12, 12, 12, 12)
        layout_marc.setSpacing(10)

        # Controlador de identificación automática (lo crea el mixin, no la vista)
        self._identificacion = None

        # Aviso de que la identificación por huella es automática
        self.banner_huella = QLabel(
            "🖐 <b>Marcación automática:</b> no busques tu nombre. "
            "Pulsa «Identificar con Huella», apoya el dedo en el lector y el "
            "sistema te dice quién eres y registra tu ingreso."
        )
        self.banner_huella.setWordWrap(True)
        self.banner_huella.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #14532D;
                background-color: #DCFCE7;
                border: 1px solid #86EFAC;
                border-radius: 8px;
                padding: 10px 14px;
            }
        """)
        layout_marc.addWidget(self.banner_huella)

        # Panel de espera (lo que se ve cuando no hay resultado en pantalla)
        self.panel_espera = QLabel(
            "👆<br><br>Apoya el dedo en el lector<br>"
            "<span style='font-size:13px'>y el sistema te identificará</span>"
        )
        self.panel_espera.setAlignment(Qt.AlignCenter)
        self.panel_espera.setTextFormat(Qt.RichText)
        self.panel_espera.setMinimumSize(640, 400)
        self.panel_espera.setStyleSheet(
            "background-color: #0F172A; border-radius: 10px; color: #64748B; font-size: 22px;"
        )
        layout_marc.addWidget(self.panel_espera, alignment=Qt.AlignCenter)

        # Tarjeta de resultado (ocupa el lugar del panel de espera)
        self.tarjeta_resultado = QFrame()
        self.tarjeta_resultado.setFixedSize(640, 400)
        self.tarjeta_resultado.setStyleSheet("border-radius: 10px; padding: 24px;")
        self.tarjeta_resultado.setVisible(False)
        layout_tarjeta = QVBoxLayout(self.tarjeta_resultado)
        layout_tarjeta.setAlignment(Qt.AlignCenter)
        layout_tarjeta.setSpacing(6)

        self.lbl_res_titulo = QLabel("RESULTADO")
        self.lbl_res_titulo.setAlignment(Qt.AlignCenter)
        self.lbl_res_titulo.setWordWrap(True)
        self.lbl_res_titulo.setStyleSheet(
            "font-size: 32px; font-weight: 900; color: white; background: transparent;")
        self.lbl_res_detalle = QLabel("")
        self.lbl_res_detalle.setAlignment(Qt.AlignCenter)
        self.lbl_res_detalle.setTextFormat(Qt.RichText)
        self.lbl_res_detalle.setWordWrap(True)
        self.lbl_res_detalle.setStyleSheet(
            "font-size: 20px; color: white; margin-top: 8px; background: transparent;")
        self.lbl_res_asiento = QLabel("")
        self.lbl_res_asiento.setAlignment(Qt.AlignCenter)
        self.lbl_res_asiento.setWordWrap(True)
        self.lbl_res_asiento.setStyleSheet(
            "font-size: 26px; font-weight: bold; color: white; margin-top: 12px; background: transparent;")

        layout_tarjeta.addWidget(self.lbl_res_titulo)
        layout_tarjeta.addWidget(self.lbl_res_detalle)
        layout_tarjeta.addWidget(self.lbl_res_asiento)
        layout_marc.addWidget(self.tarjeta_resultado, alignment=Qt.AlignCenter)

        # Botones
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_huella = QPushButton("🖐 Identificar con Huella (automático)")
        self.btn_huella.setMinimumHeight(48)
        self.btn_huella.setCursor(Qt.PointingHandCursor)
        self.btn_huella.setToolTip(
            "Apoya el dedo en el lector: el sistema identifica al postulante "
            "y registra su ingreso. No necesitas buscar tu nombre."
        )
        self.btn_huella.setStyleSheet("""
            QPushButton {
                background-color: #0F2C59;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 20px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #1A3E75; }
            QPushButton:disabled { background-color: #475569; color: rgba(255,255,255,0.5); }
        """)
        self.btn_huella.clicked.connect(self.identificar_huella)
        self.btn_huella.setEnabled(True)

        self.btn_cancelar_huella = QPushButton("Cancelar")
        self.btn_cancelar_huella.setMinimumHeight(48)
        self.btn_cancelar_huella.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar_huella.setVisible(False)
        self.btn_cancelar_huella.clicked.connect(self.cancelar_identificacion)
        self.btn_cancelar_huella.setStyleSheet("""
            QPushButton {
                background-color: #DC2626;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 18px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover { background-color: #B91C1C; }
        """)

        btn_layout.addWidget(self.btn_huella)
        btn_layout.addWidget(self.btn_cancelar_huella)
        layout_marc.addLayout(btn_layout)

        self.lbl_resumen_huellas = QLabel("Examen: comprobando huellas habilitadas…")
        self.lbl_resumen_huellas.setStyleSheet(
            "color: #475569; font-size: 12px; font-weight: 600;"
        )
        layout_marc.addWidget(self.lbl_resumen_huellas)

        self.lbl_estado_lector = QLabel("Lector de huella: detectando…")
        self.lbl_estado_lector.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout_marc.addWidget(self.lbl_estado_lector, alignment=Qt.AlignRight)
        self.actualizar_estado_lector()

        self.tabs.addTab(tab_marcacion, "Marcación Biométrica")

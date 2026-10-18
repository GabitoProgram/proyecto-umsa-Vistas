import base64
import logging

import requests
from PySide6.QtCore import QTimer, Signal, QThread
from desktop.biometria import (
    crear_lector,
    detectar_formato_plantilla,
    quitar_prefijo_plantilla,
    FormatoIncompatibleError,
)

log = logging.getLogger(__name__)


class IdentificacionHuellaController:
    """Identificación automática del postulante por huella (1:N).

    El postulante apoya el dedo y el sistema descubre quién es: no hace
    falta buscar su nombre antes.

    Secuencia:
        1. Descarga del servidor las huellas **habilitadas** del examen.
        2. Abre el lector y va comparando la captura viva plantilla por
           plantilla hasta dar con una.
        3. Registra el ingreso con la huella encontrada y devuelve los
           datos del postulante (nombre, aula, materia, asiento).

    Todo corre en el **hilo principal** encadenando pasos con
    ``QTimer.singleShot``: libfprint necesita el main context de GLib del
    hilo principal, así que un ``QThread`` se queda colgado. Cada
    comparación va en un tick propio para que la interfaz siga pintando
    mientras busca.

    Nota: esta build de libfprint no exporta la API de colecciones
    (``fp_print_collection_*``) que da el 1:N nativo de ``fp_device_identify``,
    así que la identificación se hace probando las huellas de una en una.
    """

    def __init__(self, vista, app_key, id_examen, datos_cache=None):
        self.vista = vista
        self.app_key = app_key
        self.id_examen = id_examen
        self.datos_cache = datos_cache
        self.lector = None
        self.candidatos = []
        self.sin_habilitar = []
        self._plantillas = []   # bytes ya sin prefijo de formato
        self._indices = []      # candidatos compatibles con el lector
        self._posicion = 0
        self._formato = None
        self._activo = False

    @property
    def activo(self):
        return self._activo

    # ── ciclo de vida ──────────────────────────────────────────────
    def iniciar(self):
        self._activo = True
        if self.datos_cache is not None:
            self.vista._estado_identificacion("Preparando lector de huella…")
            QTimer.singleShot(0, lambda: self._procesar_datos(self.datos_cache))
        else:
            self.vista._estado_identificacion("Descargando huellas del examen…")
            QTimer.singleShot(0, self._descargar)

    def detener(self):
        """Corta la identificación en curso (botón cancelar / cierre)."""
        if not self._activo:
            return
        self._activo = False
        self._cerrar_lector()

    # ── pasos ──────────────────────────────────────────────────────
    def _descargar(self):
        if not self._activo:
            return
        try:
            params = {"id_examen": self.id_examen} if self.id_examen else {}
            respuesta = requests.get(
                f"{self.vista.api_base_url}/marcaciones/plantillas-examen",
                params=params,
                headers={"X-App-Key": self.app_key},
                timeout=15,
            )
            if respuesta.status_code != 200:
                raise RuntimeError(respuesta.text or "error del servidor")
            datos = respuesta.json()
        except Exception as error:
            log.exception("Error descargando las huellas del examen")
            self._fallar(f"No se pudieron descargar las huellas: {error}")
            return

        self.vista._guardar_huellas_examen_cache(datos)
        self._procesar_datos(datos)

    def _procesar_datos(self, datos):
        if not self._activo:
            return
        self.candidatos = datos.get("candidatos") or []
        self.sin_habilitar = datos.get("sin_habilitar") or []
        self.vista._resumen_huellas(len(self.candidatos), len(self.sin_habilitar))

        if not self.candidatos:
            if self.sin_habilitar:
                self._fallar(
                    "Hay huellas registradas en este examen, pero ninguna "
                    "está habilitada para marcar asistencia."
                )
            else:
                self._fallar("Ningún postulante de este examen tiene huellas habilitadas.")
            return

        # Descodifica una vez y deja fuera lo que no es de este lector:
        # una estación usa un solo tipo de lector.
        self._plantillas = []
        formatos = []
        for candidato in self.candidatos:
            cruda = base64.b64decode(candidato["plantilla_b64"])
            formatos.append(detectar_formato_plantilla(cruda))
            self._plantillas.append(quitar_prefijo_plantilla(cruda))
        self._formato = max(set(formatos), key=formatos.count)
        self._indices = [i for i, f in enumerate(formatos) if f == self._formato]
        self._posicion = 0
        self._captura_actual = None

        QTimer.singleShot(0, self._conectar)

    def _conectar(self):
        if not self._activo:
            return
        try:
            self.lector = crear_lector(self._formato)
            self.lector.conectar()
        except Exception as error:
            log.exception("Error conectando el lector de huella")
            self._fallar(str(error))
            return
        QTimer.singleShot(0, self._comparar)

    def _comparar(self):
        """Prueba la siguiente huella habilitada con la captura viva."""
        if not self._activo:
            return
        total = len(self._indices)
        self.vista._estado_identificacion(
            f"Apoya el dedo en el lector — buscando ({self._posicion + 1}/{total})…"
        )
        try:
            indice = self._indices[self._posicion]
            if hasattr(self.lector, "comparar_captura_con_plantilla"):
                if self._captura_actual is None:
                    self.vista._estado_identificacion("Apoya el dedo en el lector…")
                    self._captura_actual = self.lector.capturar_plantilla_actual()
                coincide, score = self.lector.comparar_captura_con_plantilla(
                    self._captura_actual, self._plantillas[indice]
                )
            else:
                coincide, score = self._comparar_una(self._plantillas[indice])
        except FormatoIncompatibleError:
            coincide, score = False, 0.0
        except RuntimeError as error:
            if "No se pudo capturar la huella" in str(error):
                self._posicion = 0
                self._captura_actual = None
                self.vista._estado_identificacion("Apoya el dedo en el lector…")
                QTimer.singleShot(250, self._comparar)
                return
            log.exception("Error comparando con el lector")
            self._fallar(f"Error del lector de huella: {error}")
            return
        except Exception as error:
            log.exception("Error comparando con el lector")
            self._fallar(f"Error del lector de huella: {error}")
            return

        if coincide:
            log.info("Identificación automática: coincidencia con %s",
                     self.candidatos[indice].get("nombre_completo"))
            self._registrar(self.candidatos[indice], self._plantillas[indice], score)
            return

        self._posicion += 1
        if self._posicion >= total:
            self._sin_coincidencia()
            return
        QTimer.singleShot(0, self._comparar)

    def _comparar_una(self, plantilla):
        """Compara con un lector concreto (libfprint o ZKTeco)."""
        comparar = getattr(self.lector, "comparar_con_plantilla", None)
        if comparar is not None:
            # El dedo se declara desconocido: al identificar no sabemos qué
            # dedo ponds, y si la plantilla lo fija libfprint espera a ese
            # dedo concreto en vez de comparar.
            return comparar(plantilla, forzar_dedo_desconocido=True)
        return self.lector.verificar_plantilla(plantilla)

    # ── desenlaces ─────────────────────────────────────────────────
    def _registrar(self, candidato, plantilla, score):
        """Da de alta el ingreso con la huella que coincidió.

        Se reenvía la plantilla ya guardada: la comparación la hizo el
        lector localmente y el servidor confía en su veredicto.
        """
        self._activo = False
        self._cerrar_lector()
        try:
            respuesta = requests.post(
                f"{self.vista.api_base_url}/marcaciones/verificar-huella",
                headers={"X-App-Key": self.app_key},
                data={
                    "id_examen": self.id_examen,
                    "id_postulante": candidato["id_postulante"],
                    "tipo_dedo": candidato["tipo_dedo"],
                    "score_cliente": int(score),
                },
                files={"file": ("huella.bin", plantilla,
                                "application/octet-stream")},
                timeout=15,
            )
            try:
                payload = respuesta.json()
            except ValueError:
                payload = {"mensaje": respuesta.text or "Respuesta inválida del servidor"}
        except Exception as error:
            log.exception("Error registrando el ingreso por huella")
            self.vista._identificacion_error(f"No se pudo registrar el ingreso: {error}")
            return
        self.vista._identificacion_lista(payload, candidato)

    def _sin_coincidencia(self):
        self._activo = False
        self._cerrar_lector()
        self.vista._identificacion_error(
            "Tu huella no coincide con ningún registro habilitado. "
            "Verifica que hayas registrado tu huella en el panel admin."
        )

    def _fallar(self, mensaje):
        self._activo = False
        self._cerrar_lector()
        self.vista._identificacion_error(mensaje)

    def _cerrar_lector(self):
        if self.lector is not None:
            try:
                self.lector.cerrar()
            except Exception:  # pragma: no cover
                pass
            self.lector = None


class IdentifyWorker(QThread):
    """Envía una captura al reconocimiento facial 1:N del backend."""

    resultado = Signal(object, int, str)

    def __init__(self, url, headers, id_examen, image_bytes, parent=None):
        super().__init__(parent)
        self.url = url
        self.headers = headers
        self.id_examen = id_examen
        self.image_bytes = image_bytes

    def run(self):
        try:
            data = {}
            if self.id_examen is not None:
                data["id_examen"] = self.id_examen
            response = requests.post(
                self.url,
                headers=self.headers,
                data=data,
                files={"file": ("captura.jpg", self.image_bytes, "image/jpeg")},
                timeout=15
            )
            try:
                payload = response.json()
            except ValueError:
                payload = {"mensaje": response.text or "Respuesta inválida del servidor"}
            self.resultado.emit(payload, response.status_code, "")
        except requests.RequestException as error:
            self.resultado.emit({}, 0, str(error))

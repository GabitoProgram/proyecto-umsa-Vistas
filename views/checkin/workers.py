import base64
import logging
import time

import requests
from PySide6.QtCore import QObject, QRunnable, QThreadPool, QTimer, Signal, QThread
from desktop.biometria import (
    crear_lector,
    detectar_formato_plantilla,
    quitar_prefijo_plantilla,
    FormatoIncompatibleError,
)

log = logging.getLogger(__name__)

# Cada cuánto se pregunta al lector «¿ya hay un dedo?». Es una consulta
# instantánea, así que la interfaz queda libre entre una y otra.
INTERVALO_SONDEO_MS = 120
# Cuánto trabajo de comparación se hace seguido antes de devolver el control
# a la interfaz para que siga pintando.
PRESUPUESTO_COMPARACION_MS = 15

_ERROR_SIN_DEDO = "No se pudo capturar la huella"

# Las peticiones al servidor salen por aquí, fuera del hilo de la interfaz.
_pool_red = QThreadPool()
_pool_red.setMaxThreadCount(2)


# ══════════════════════ UTILIDADES DE SEGUNDO PLANO ══════════════════════
class _Entrega(QObject):
    """Recibe en el hilo principal el resultado de una tarea de red."""

    listo = Signal(object, object)  # resultado, error

    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        # Conexión a un método de este mismo QObject: Qt la encola sola hacia
        # el hilo principal aunque la señal se emita desde otro hilo.
        self.listo.connect(self._entregar)

    def _entregar(self, resultado, error):
        self._callback(resultado, error)


class _TareaRed(QRunnable):
    def __init__(self, funcion, entrega):
        super().__init__()
        self._funcion = funcion
        self._entrega = entrega

    def run(self):
        try:
            resultado, error = self._funcion(), None
        except Exception as excepcion:  # se informa en el hilo principal
            resultado, error = None, excepcion
        self._entrega.listo.emit(resultado, error)


def _ejecutar_en_hilo(funcion, callback):
    """Ejecuta ``funcion`` fuera de la interfaz y llama a ``callback(resultado, error)``
    en el hilo principal. Devuelve el objeto de entrega: hay que conservarlo
    hasta que llegue la respuesta."""
    entrega = _Entrega(callback)
    _pool_red.start(_TareaRed(funcion, entrega))
    return entrega


def liberar_lector_compartido(vista):
    """Cierra el lector que se deja abierto entre identificaciones.

    Hay que llamarlo al salir de la estación de registro: así el panel de
    administración (enrolamiento de huellas) puede usar el lector.
    """
    lector = getattr(vista, "_lector_abierto", None)
    vista._lector_abierto = None
    if lector is not None:
        try:
            lector.cerrar()
        except Exception:  # pragma: no cover
            log.debug("Error cerrando el lector compartido", exc_info=True)


# ══════════════════════ IDENTIFICACIÓN ══════════════════════
class IdentificacionHuellaController:
    """Identificación automática del postulante por huella (1:N).

    El postulante apoya el dedo y el sistema descubre quién es: no hace
    falta buscar su nombre antes.

    Secuencia:
        1. Obtiene las huellas **habilitadas** del examen (se descargan una
           vez, en segundo plano, y quedan en caché).
        2. Abre el lector (si ya está abierto de una vuelta anterior, lo
           reutiliza) y espera el dedo *sondeando*: consulta al lector cada
           ``INTERVALO_SONDEO_MS`` sin quedarse esperando.
        3. Compara la captura con las plantillas por lotes pequeños.
        4. Registra el ingreso en segundo plano y devuelve los datos del
           postulante (nombre, aula, materia, asiento).

    Los pasos del lector corren en el **hilo principal** encadenados con
    ``QTimer.singleShot`` (libfprint necesita el main context de GLib), pero
    ninguno espera: cada uno hace una consulta corta y devuelve el control a
    la interfaz. Las peticiones HTTP van en un hilo aparte.
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
        self._captura_actual = None
        self._aviso_espera = False
        self._activo = False
        self._cancelado = False
        self._pendiente_red = False
        self._entrega = None

    @property
    def activo(self):
        # Mientras haya una petición en vuelo sigue «activo»: así la vista no
        # arranca otra identificación encima.
        return self._activo or self._pendiente_red

    # ── ciclo de vida ──────────────────────────────────────────────
    def iniciar(self):
        self._activo = True
        if self.datos_cache is not None:
            self.vista._estado_identificacion("Preparando lector de huella…")
            QTimer.singleShot(0, lambda: self._procesar_datos(self.datos_cache))
        else:
            self.vista._estado_identificacion("Descargando huellas del examen…")
            self._descargar()

    def detener(self):
        """Corta la identificación en curso (botón cancelar / cierre)."""
        if not self.activo:
            return
        self._activo = False
        self._cancelado = True
        self._pendiente_red = False
        self._cerrar_lector()

    # ── pasos ──────────────────────────────────────────────────────
    def _descargar(self):
        if not self._activo:
            return
        url = f"{self.vista.api_base_url}/marcaciones/plantillas-examen"
        params = {"id_examen": self.id_examen} if self.id_examen else {}
        headers = {"X-App-Key": self.app_key}

        def pedir():
            respuesta = requests.get(url, params=params, headers=headers, timeout=15)
            if respuesta.status_code != 200:
                raise RuntimeError(respuesta.text or "error del servidor")
            return respuesta.json()

        self._pendiente_red = True
        self._entrega = _ejecutar_en_hilo(pedir, self._descarga_lista)

    def _descarga_lista(self, datos, error):
        self._pendiente_red = False
        if self._cancelado or not self._activo:
            return
        if error is not None:
            log.error("Error descargando las huellas del examen: %s", error)
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

        # Descodificar miles de plantillas es trabajo inútil si ya se hizo
        # para estos mismos datos: se reutiliza el resultado.
        procesado = getattr(self.vista, "_plantillas_procesadas", None)
        if procesado is not None and procesado[0] is datos:
            _, self._plantillas, self._indices, self._formato = procesado
        else:
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
            self.vista._plantillas_procesadas = (
                datos, self._plantillas, self._indices, self._formato)
        self._posicion = 0
        self._captura_actual = None

        QTimer.singleShot(0, self._conectar)

    def _conectar(self):
        if not self._activo:
            return
        try:
            lector = getattr(self.vista, "_lector_abierto", None)
            if (lector is not None and getattr(lector, "conectado", False)
                    and getattr(lector, "tipo", None) == self._formato):
                # Ya estaba abierto de la vuelta anterior: no se vuelve a
                # escanear el USB ni a inicializar el SDK.
                self.lector = lector
            else:
                self.lector = crear_lector(self._formato)
                self.lector.conectar()
                if getattr(self.lector, "soporta_sondeo", False):
                    self.vista._lector_abierto = self.lector
        except Exception as error:
            log.exception("Error conectando el lector de huella")
            self.lector = None
            self._fallar(str(error))
            return
        QTimer.singleShot(0, self._comparar)

    # ── captura y comparación ──────────────────────────────────────
    def _capturar_si_hay_dedo(self):
        """Devuelve la captura, o ``None`` si todavía no hay dedo."""
        sondeo = getattr(self.lector, "soporta_sondeo", False)
        try:
            if sondeo:
                return self.lector.capturar_plantilla_actual(timeout=0)
            return self.lector.capturar_plantilla_actual()
        except RuntimeError as error:
            if _ERROR_SIN_DEDO in str(error):
                return None
            raise

    def _comparar(self):
        """Espera el dedo sin bloquear y compara con las huellas habilitadas."""
        if not self._activo:
            return
        total = len(self._indices)
        try:
            if hasattr(self.lector, "comparar_captura_con_plantilla"):
                self._paso_con_captura(total)
            else:
                self._paso_por_plantilla(total)
        except RuntimeError as error:
            if _ERROR_SIN_DEDO in str(error):
                self._posicion = 0
                self._captura_actual = None
                QTimer.singleShot(250, self._comparar)
                return
            log.exception("Error comparando con el lector")
            self._fallar(f"Error del lector de huella: {error}")
        except Exception as error:
            log.exception("Error comparando con el lector")
            self._fallar(f"Error del lector de huella: {error}")

    def _paso_con_captura(self, total):
        """Lectores que capturan una sola vez (ZKTeco)."""
        if self._captura_actual is None:
            if not self._aviso_espera:
                self.vista._estado_identificacion("Apoya el dedo en el lector…")
                self._aviso_espera = True
            self._captura_actual = self._capturar_si_hay_dedo()
            if self._captura_actual is None:
                QTimer.singleShot(INTERVALO_SONDEO_MS, self._comparar)
                return
            self._aviso_espera = False

        inicio = time.perf_counter()
        while self._posicion < total:
            indice = self._indices[self._posicion]
            try:
                coincide, score = self.lector.comparar_captura_con_plantilla(
                    self._captura_actual, self._plantillas[indice]
                )
            except FormatoIncompatibleError:
                coincide, score = False, 0.0
            if coincide:
                log.info("Identificación automática: coincidencia con %s",
                         self.candidatos[indice].get("nombre_completo"))
                self._registrar(self.candidatos[indice], self._plantillas[indice], score)
                return
            self._posicion += 1
            gastado_ms = (time.perf_counter() - inicio) * 1000
            if gastado_ms >= PRESUPUESTO_COMPARACION_MS and self._posicion < total:
                self.vista._estado_identificacion(
                    f"Buscando coincidencia ({self._posicion}/{total})…")
                QTimer.singleShot(0, self._comparar)
                return
        self._sin_coincidencia()

    def _paso_por_plantilla(self, total):
        """Lectores que capturan en cada comparación (libfprint): como antes."""
        self.vista._estado_identificacion(
            f"Apoya el dedo en el lector — buscando ({self._posicion + 1}/{total})…"
        )
        indice = self._indices[self._posicion]
        try:
            coincide, score = self._comparar_una(self._plantillas[indice])
        except FormatoIncompatibleError:
            coincide, score = False, 0.0

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
        lector localmente y el servidor confía en su veredicto. La petición
        sale en segundo plano para no congelar la pantalla.
        """
        self._activo = False
        self._cerrar_lector()
        url = f"{self.vista.api_base_url}/marcaciones/verificar-huella"
        headers = {"X-App-Key": self.app_key}
        datos = {
            "id_examen": self.id_examen,
            "id_postulante": candidato["id_postulante"],
            "tipo_dedo": candidato["tipo_dedo"],
            "score_cliente": int(score),
        }

        def enviar():
            respuesta = requests.post(
                url, headers=headers, data=datos,
                files={"file": ("huella.bin", plantilla, "application/octet-stream")},
                timeout=15,
            )
            try:
                return respuesta.json()
            except ValueError:
                return {"mensaje": respuesta.text or "Respuesta inválida del servidor"}

        self._pendiente_red = True
        self._entrega = _ejecutar_en_hilo(
            enviar, lambda payload, error: self._registro_listo(candidato, payload, error))

    def _registro_listo(self, candidato, payload, error):
        self._pendiente_red = False
        if self._cancelado:
            return
        if error is not None:
            log.error("Error registrando el ingreso por huella: %s", error)
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
        # Tras un fallo el lector puede haber quedado en mal estado: se
        # descarta para que la próxima vuelta lo abra de nuevo.
        self._cerrar_lector(descartar=True)
        self.vista._identificacion_error(mensaje)

    def _cerrar_lector(self, descartar=False):
        lector, self.lector = self.lector, None
        if lector is None:
            return
        compartido = getattr(self.vista, "_lector_abierto", None) is lector
        if compartido and not descartar:
            return  # se queda abierto para la siguiente identificación
        if compartido:
            self.vista._lector_abierto = None
        try:
            lector.cerrar()
        except Exception:  # pragma: no cover
            pass


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
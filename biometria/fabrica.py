"""Fachada de la capa biométrica: elige la mejor implementación disponible.

Dos familias de lectores:

- **libfprint** (DigitalPersona U.are.U 4000/4500 y otros): la
  biblioteca se empaqueta con la app (``desktop/biometria/libs``);
  sólo hace falta una regla udev para el acceso USB.
- **ZKTeco** (ZK4500/ZK9500): requiere la ZKFinger SDK oficial
  (``libzkfp.so``), además de la regla udev.

Flujo típico::

    lectores, usb_ok = detectar_lectores()
    lector = crear_lector()                 # o crear_lector("libfprint")
    lector.conectar()
    imagen, plantilla = lector.capturar_imagen(), None
    plantilla = lector.enrolar_dedo(dedo=6)        # 3+ toques
    aceptado, score = lector.verificar_plantilla(guardada)
    lector.cerrar()
"""

import logging
import os

from desktop.biometria.modelos import (
    LectorHuella,
    MODELOS_ZK,
    UMBRAL_CONSISTENCIA,
    UMBRAL_VERIFICACION,
    ErrorLector,
    LectorNoConectadoError,
    SDKNoDisponibleError,
)
from desktop.biometria import usb_zk
from desktop.biometria import zkfp_ctypes
from desktop.biometria import libfprint_backend

log = logging.getLogger(__name__)


def detectar_lectores():
    """Devuelve ``(lectores, usb_ok)`` con todos los lectores soportados.

    ``usb_ok`` indica si el bus USB es accesible. Si hay lectores
    libfprint, el bus USB se considera accesible aunque ``pyusb``
    no esté instalado (libfprint usa su propio acceso USB vía libusb).
    """
    lectores = []
    usb_ok = True

    # 1. Lectores compatibles con libfprint (DigitalPersona …)
    try:
        if libfprint_backend.libfprint_disponible():
            for info in libfprint_backend.detectar_dispositivos():
                lectores.append(
                    LectorHuella(
                        nombre=info["nombre"],
                        tipo="libfprint",
                        vid=info.get("vid", 0),
                        pid=info.get("pid", 0),
                        bus=0,
                        direccion=0,
                        indice_sdk=info["indice"],
                        driver=info["driver"],
                        scan_type=info["scan_type"],
                        modelo=info["nombre"],
                        etapas_enrolamiento=info["etapas_enrolamiento"],
                    )
                )
    except Exception as error:  # pragma: no cover
        log.debug("Error detectando lectores libfprint: %s", error)

    # 2. Lectores ZKTeco por USB
    zk_lectores, zk_usb_ok = usb_zk.detectar_lectores()
    if not zk_usb_ok and zk_lectores:
        # Hay ZKTeco pero pyusb no puede acceder al bus: no bloquear
        # si hay lectores libfprint disponibles.
        if not any(l.tipo == "libfprint" for l in lectores):
            usb_ok = False
    for lector in zk_lectores:
        lector.tipo = "zk"
        lector.modelo = MODELOS_ZK.get(lector.pid, lector.nombre)
        lectores.append(lector)

    return lectores, usb_ok


def libfprint_disponible() -> bool:
    """True si la biblioteca libfprint-2 está cargable."""
    return libfprint_backend.libfprint_disponible()


def sdk_zk_disponible() -> bool:
    """True si la ZKFinger SDK de ZKTeco (libzkfp.so) está instalada."""
    return bool(zkfp_ctypes.buscar_libzkfp())


def ruta_sdk_zk() -> str:
    return zkfp_ctypes.buscar_libzkfp() or ""


def crear_lector(tipo=None, indice=0, info=None):
    """Crea un lector de alto nivel listo para ``conectar()``.

    ``tipo`` puede ser ``"libfprint"``, ``"zk"`` o ``None``
    (elige el primero disponible, preferiendo libfprint porque
    no requiere SDK propietaria). Si se pasa ``info`` (un
    ``LectorHuella`` ya detectado) se evita reescanear el bus USB.
    """
    if info is not None:
        elegido = info
    else:
        log.debug("crear_lector(): llamando a detectar_lectores()...")
        lectores, usb_ok = detectar_lectores()
        log.debug("crear_lector(): detectar_lectores() devolvió %d lectores, usb_ok=%s", len(lectores), usb_ok)
        if not usb_ok:
            raise LectorNoConectadoError(
                "No se pudo acceder al bus USB (falta la regla udev).\n"
                "Ejecuta:  sudo ./setup_lectores_huella.sh"
            )
        if not lectores:
            raise LectorNoConectadoError(
                "No se detectó ningún lector de huella.\n"
                "Conecta el lector por USB."
            )
        if tipo:
            candidatos = [l for l in lectores if l.tipo == tipo]
        else:
            candidatos = [l for l in lectores if l.tipo == "libfprint"]
            if not candidatos:
                candidatos = [l for l in lectores if l.tipo == "zk"]
        if not candidatos:
            raise LectorNoConectadoError(
                f"No hay lectores de tipo «{tipo}» conectados."
            )
        elegido = candidatos[min(indice, len(candidatos) - 1)]
    log.debug("crear_lector(): lector elegido=%s, creando LectorLibfprint...", elegido.modelo)
    if elegido.tipo == "libfprint":
        lector = libfprint_backend.LectorLibfprint(elegido.indice_sdk)
        log.debug("crear_lector(): LectorLibfprint creado OK")
        return lector
    # Se pasa lo ya detectado: conectar() no debe volver a escanear el bus USB
    # (en Windows eso agrega segundos y puede chocar con el driver oficial).
    return LectorZK(elegido.indice_sdk, info=elegido)


class LectorZK:
    """Lector de huella de alto nivel sobre la ZKFinger SDK de ZKTeco."""

    tipo = "zk"
    # Permite consultar «¿hay un dedo?» sin bloquear (ver capturar_plantilla_actual).
    soporta_sondeo = True

    def __init__(self, indice=0, info=None):
        self.indice = getattr(info, "indice_sdk", indice) if info is not None else indice
        self.info = info
        self.sdk = None
        self.conectado = False
        self.ancho = 256
        self.alto = 300
        self.modelo = info.modelo if info is not None else "Lector ZKTeco"
        self._base_huellas_clave = None
        self._base_huellas_lista = False
        self._base_huellas_indices = []
        self._base_huellas_errores = 0
        self._base_1n_fallida = False

    # ------------------------------------------------------------------
    def conectar(self):
        """Inicializa el SDK y abre el primer lector."""
        if not sdk_zk_disponible():
            raise SDKNoDisponibleError(
                "La ZKFinger SDK de ZKTeco no está instalada.\n"
                "Ejecuta:  ./setup_lectores_huella.sh"
            )
        info = self.info
        if info is None:
            lectores, usb_ok = detectar_lectores()
            zk_lectores = [l for l in lectores if l.tipo == "zk"]
            if not zk_lectores:
                raise LectorNoConectadoError(
                    "No se detectó ningún lector ZKTeco.\n"
                    "Conecta el ZK4500 o ZK9500 por USB."
                )
            info = zk_lectores[min(self.indice, len(zk_lectores) - 1)]
        else:
            # Ya viene detectado por crear_lector(): no reescanear el USB.
            usb_ok = True
        if not usb_ok:
            raise LectorNoConectadoError(
                "No se pudo acceder al bus USB (falta la regla udev).\n"
                "Ejecuta:  sudo ./setup_lectores_huella.sh"
            )
        # En Windows el driver oficial ZKTeco impide que PyUSB reclame la
        # interfaz, pero la SDK ya confirmó el acceso al abrir el dispositivo.
        if os.name != "nt" and not info.accesible:
            raise LectorNoConectadoError(
                f"El lector {info.modelo} está "
                "conectado, pero este usuario no tiene permiso para "
                "usarlo.\nEjecuta:  sudo ./setup_lectores_huella.sh"
            )
        self.modelo = info.modelo
        self.sdk = zkfp_ctypes.ZKFingerSDK()
        self.sdk.inicializar()
        if self.sdk.cantidad_dispositivos() == 0:
            self.sdk.terminar()
            raise LectorNoConectadoError(
                "La SDK no encontró el lector. "
                "Verifica que el ZK4500/ZK9500 esté conectado."
            )
        self.sdk.abrir_dispositivo(self.indice)
        self.ancho = self.sdk.ancho
        self.alto = self.sdk.alto
        self.conectado = True
        self._base_huellas_clave = None
        self._base_huellas_lista = False
        self._base_huellas_indices = []
        self._base_huellas_errores = 0
        self._base_1n_fallida = False
        log.info(
            "Lector ZKTeco conectado: %s (%dx%d)",
            self.modelo, self.ancho, self.alto,
        )
        return self

    def cerrar(self):
        if self.sdk:
            try:
                self.sdk.cerrar_dispositivo()
                self.sdk.terminar()
            except Exception as error:  # pragma: no cover
                log.debug("Error cerrando el SDK: %s", error)
            self.sdk = None
        self.conectado = False
        self._base_huellas_clave = None
        self._base_huellas_lista = False
        self._base_huellas_indices = []

    def __enter__(self):
        return self.conectar()

    def __exit__(self, *args):
        self.cerrar()

    # ── identificación 1:N nativa ──────────────────────────────────
    def base_huellas_disponible(self):
        """False si la SDK no pudo cargar la base 1:N en este lector."""
        return not self._base_1n_fallida

    def iniciar_base_huellas(self):
        """Vacía la caché 1:N y la deja lista para recibir plantillas."""
        self._requerido()
        if self._base_1n_fallida:
            raise ErrorLector("La base 1:N no está disponible en este lector")
        self.sdk.limpiar_base()
        self._base_huellas_clave = None
        self._base_huellas_lista = False
        self._base_huellas_indices = []
        self._base_huellas_errores = 0

    def agregar_lote_base_huellas(self, plantillas, indices, desde, hasta):
        """Agrega un tramo de plantillas a la caché 1:N.

        ``indices`` contiene los índices reales de los candidatos compatibles
        con este lector. Devuelve la posición hasta la que se procesó.
        """
        self._requerido()
        if self._base_huellas_lista:
            raise ErrorLector("La base 1:N ya está cargada")
        total = len(indices)
        desde = max(0, int(desde))
        hasta = min(total, int(hasta))
        consecutivos = 0
        for posicion in range(desde, hasta):
            indice = indices[posicion]
            fid = len(self._base_huellas_indices) + 1
            try:
                self.sdk.agregar_a_base(fid, plantillas[indice])
            except Exception as error:
                consecutivos += 1
                self._base_huellas_errores += 1
                if consecutivos >= 20:
                    self.descartar_base_huellas()
                    raise ErrorLector(
                        "No se pudo cargar la base 1:N de huellas: "
                        f"{error}"
                    ) from error
                if self._base_huellas_errores <= 5:
                    log.warning(
                        "Huella omitida al cargar la base 1:N (%s): %s",
                        indice, error,
                    )
                continue
            consecutivos = 0
            self._base_huellas_indices.append(indice)
        return hasta

    def terminar_base_huellas(self, clave=None):
        """Marca la caché 1:N como lista para identificar capturas."""
        if not self._base_huellas_indices:
            raise ErrorLector("La base 1:N quedó vacía")
        self._base_huellas_clave = clave
        self._base_huellas_lista = True

    def base_huellas_lista(self, clave=None):
        """True si la base ya está cargada para la misma versión de plantillas."""
        return (
            self._base_huellas_lista
            and not self._base_1n_fallida
            and self._base_huellas_clave == clave
        )

    def descartar_base_huellas(self):
        """Invalida la caché 1:N y evita reintentos costosos en este lector."""
        self._base_huellas_clave = None
        self._base_huellas_lista = False
        self._base_huellas_indices = []
        self._base_1n_fallida = True
        if self.sdk:
            try:
                self.sdk.limpiar_base()
            except Exception:  # pragma: no cover
                log.debug("Error limpiando la base 1:N", exc_info=True)

    def identificar_captura(self, captura):
        """Identifica una captura contra toda la base 1:N.

        Devuelve ``(indice_candidato, score)`` o ``None`` si no hay una
        coincidencia que supere el umbral.
        """
        self._requerido()
        if not self._base_huellas_lista:
            raise ErrorLector("La base 1:N todavía no está cargada")
        fid, score = self.sdk.identificar_en_base(captura)
        if fid <= 0:
            return None
        try:
            indice = self._base_huellas_indices[fid - 1]
        except IndexError:
            log.warning("La SDK devolvió un identificador de huella inválido: %s", fid)
            return None
        if score < UMBRAL_VERIFICACION:
            return None
        return indice, float(score)

    # ------------------------------------------------------------------
    def capturar_imagen(self):
        """Captura sólo la imagen (para vista previa)."""
        self._requerido()
        return self.sdk.capturar_imagen(), self.ancho, self.alto

    def capturar(self, timeout=4.0):
        """Captura imagen + plantilla. Devuelve ``(imagen, plantilla)``."""
        self._requerido()
        imagen, plantilla = self.sdk.capturar_plantilla(timeout)
        return (imagen, self.ancho, self.alto), plantilla

    def enrolar_dedo(self, dedo, on_avance=None):
        """Enrolamiento: 3 capturas del mismo dedo + DBMerge.

        ``on_avance(completadas, total, imagen)`` se invoca tras
        cada captura válida. Devuelve la plantilla combinada.
        """
        self._requerido()
        capturas = []
        while len(capturas) < 3:
            (imagen, _w, _h), plantilla = self.capturar()
            if capturas:
                # Confirmar que es el mismo dedo que la captura anterior
                score = self.sdk.comparar_plantillas(capturas[-1], plantilla)
                if score < UMBRAL_CONSISTENCIA:
                    raise ErrorLector(
                        "Parece que cambiaste de dedo. Empieza de nuevo "
                        "y usa siempre el MISMO dedo."
                    )
            capturas.append(plantilla)
            if on_avance:
                on_avance(len(capturas), 3, imagen, self.ancho, self.alto)
        return self.sdk.combinar_plantillas(*capturas)

    def verificar_plantilla(self, plantilla_guardada_cruda):
        """Verificación 1:1. Devuelve ``(aceptado, score)``."""
        self._requerido()
        if not plantilla_guardada_cruda:
            return False, 0.0
        (imagen, _w, _h), plantilla = self.capturar()
        score = self.sdk.comparar_plantillas(
            plantilla_guardada_cruda, plantilla)
        if score < 0:
            raise ErrorLector(f"Error comparando plantillas (código {score})")
        return score >= UMBRAL_VERIFICACION, float(score)

    def capturar_plantilla_actual(self, timeout=4.0):
        """Captura una sola vez para comparar contra varias plantillas.

        Con ``timeout=0`` no espera: si no hay dedo lanza ``RuntimeError``
        («No se pudo capturar la huella…») al instante.
        """
        self._requerido()
        (_imagen, _w, _h), plantilla = self.capturar(timeout)
        return plantilla

    def capturar_para_enrolar_no_bloqueante(self):
        """Una sola consulta al lector, sin esperar dedo.

        Devuelve ``(imagen, plantilla, ancho, alto)`` o ``None`` si todavía no
        hay una huella apoyada. Permite enrolar con un QTimer sin congelar la
        interfaz (el enrolamiento bloqueante tardaba segundos).
        """
        self._requerido()
        try:
            imagen, plantilla = self.sdk.capturar_plantilla(0)
        except RuntimeError:
            return None
        if not plantilla:
            return None
        return imagen, plantilla, self.ancho, self.alto

    def comparar_captura_con_plantilla(self, captura, plantilla_guardada_cruda):
        """Compara una captura viva ya tomada sin volver a usar el lector."""
        self._requerido()
        score = self.sdk.comparar_plantillas(plantilla_guardada_cruda, captura)
        if score < 0:
            raise ErrorLector(f"Error comparando plantillas (código {score})")
        return score >= UMBRAL_VERIFICACION, float(score)

    def _requerido(self):
        if not self.conectado:
            raise ErrorLector("El lector no está conectado")
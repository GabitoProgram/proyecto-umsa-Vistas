"""Detección de lectores ZKTeco por USB (pyusb + libusb).

Esta capa NO necesita la ZKFinger SDK: enumera los lectores conectados
usando ``pyusb`` sobre ``libusb-1.0`` (la del sistema o, si no hay,
la empaquetada vía pip ``libusb``, que se instala sin root).

Para capturar imágenes/plantillas hace falta el permiso de acceso al
dispositivo USB, que se configura con una regla udev (ver
``setup_lectores_huella.sh``).
"""

import os
import logging

from desktop.biometria.modelos import (
    LectorHuella,
    VID_ZK,
    VID_DIGITALPERSONA,
    MODELOS_ZK,
    MODELOS_DIGITALPERSONA,
)
log = logging.getLogger(__name__)

_libusb_preloaded = False


def _precargar_libusb():
    """Precarga ``libusb-1.0`` con RTLD_GLOBAL para que pyusb la encuentre.

    Se prefiere la **libusb del sistema** (la misma que usa
    ``libgusb``/libfprint) para no cargar dos builds distintos
    de la misma SONAME en un mismo proceso; sólo si no existe
    se recurre a la copia empaquetada (pip ``libusb``).
    """
    global _libusb_preloaded
    if _libusb_preloaded:
        return
    _libusb_preloaded = True
    try:
        import ctypes
        import ctypes.util

        # 1. La del sistema (compatible con libgusb de libfprint).
        ruta_sistema = ctypes.util.find_library("usb-1.0")
        if ruta_sistema:
            try:
                ctypes.CDLL(ruta_sistema, mode=ctypes.RTLD_GLOBAL)
                log.debug("libusb del sistema precargada: %s", ruta_sistema)
                return
            except OSError as error:
                log.debug("No se pudo precargar %s: %s", ruta_sistema, error)

        # 2. La empaquetada con el paquete pip ``libusb``.
        import libusb as paquete_libusb

        raiz = os.path.join(
            os.path.dirname(paquete_libusb.__file__), "_platform", "linux")
        arquitectura = "x86_64" if os.uname().machine in ("x86_64", "amd64") else "aarch64"
        ruta = os.path.join(raiz, arquitectura, "libusb-1.0.so")
        if os.path.exists(ruta):
            ctypes.CDLL(ruta, mode=ctypes.RTLD_GLOBAL)
            log.debug("libusb empaquetada precargada desde %s", ruta)
    except Exception as error:  # pragma: no cover - depende del entorno
        log.debug("No se pudo precargar libusb: %s", error)


def detectar_lectores():
    """Devuelve la lista de lectores ZKTeco conectados por USB.

    La detección funciona aunque el usuario no tenga permisos de apertura
    (para eso hace falta la regla udev); en ese caso el lector se reporta
    igualmente, con ``accesible=False``.
    """
    _precargar_libusb()
    lectores = []
    try:
        import usb.core
    except ImportError:
        log.debug("pyusb no está instalado")
        return lectores, False

    pyusb_operativo = True
    try:
        dispositivos = []
        for vid in (VID_ZK, VID_DIGITALPERSONA):
            dispositivos.extend(
                usb.core.find(find_all=True, idVendor=vid) or []
            )
        for indice, dispositivo in enumerate(dispositivos):
            try:
                nombre = _leer_cadena(dispositivo, dispositivo.iProduct)
            except Exception:
                nombre = None
            modelo = MODELOS_ZK.get(
                dispositivo.idProduct,
                MODELOS_DIGITALPERSONA.get(
                    dispositivo.idProduct, "Lector de huella USB"
                ),
            )
            if not nombre:
                nombre = modelo
            # Intentar abrir para verificar si tenemos permisos de uso.
            accesible = _verificar_acceso(dispositivo)
            lectores.append(
                LectorHuella(
                    nombre=nombre,
                    tipo="zk",
                    vid=dispositivo.idVendor,
                    pid=dispositivo.idProduct,
                    bus=dispositivo.bus,
                    direccion=dispositivo.address,
                    indice_sdk=indice,
                    modelo=modelo,
                )
            )
            lectores[-1].accesible = accesible
    except Exception as error:  # pragma: no cover - fallos de backend USB
        log.debug("Error enumerando dispositivos USB: %s", error)
        pyusb_operativo = False
    return lectores, pyusb_operativo


def _leer_cadena(dispositivo, indice):
    import usb.util

    if not indice:
        return None
    return usb.util.get_string(dispositivo, indice)


def _verificar_acceso(dispositivo):
    """Comprueba si podemos configurar el dispositivo (permisos udev)."""
    # En Windows el driver oficial de ZKTeco no deja reclamar la interfaz con
    # PyUSB. Hacerlo en cada detección era lento y ensuciaba el bus; la SDK
    # confirmará el acceso al abrir el dispositivo.
    if os.name == "nt":
        return True
    try:
        import usb.util

        dispositivo.set_configuration(1)
        usb.util.claim_interface(dispositivo, 0)
        usb.util.release_interface(dispositivo, 0)
        return True
    except Exception:
        return False

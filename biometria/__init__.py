"""Integración con lectores de huella.

Dos familias soportadas:

- **libfprint** (DigitalPersona U.are.U 4000/4500 y otros):
  biblioteca de código abierto empaquetada con la app.
- **ZKTeco** (ZK4500/ZK9500): vía la ZKFinger SDK oficial.

Capas:
- ``usb_zk``: detección pura por USB de lectores ZKTeco (pyusb).
- ``libfprint_backend``: wrapper ctypes sobre libfprint-2.
- ``zkfp_ctypes``: wrapper ctypes sobre la ZKFinger SDK (libzkfp.so).
- ``fabrica``: fachada que elige el lector disponible.
"""

from desktop.biometria.modelos import (
    LectorHuella,
    DEDO_NOMBRES,
    MODELOS_ZK,
    MAGIC_LIBFPRINT,
    MAGIC_ZK,
    ErrorLector,
    LectorNoConectadoError,
    SDKNoDisponibleError,
    PermisoUSBError,
    CapturaCanceladaError,
    FormatoIncompatibleError,
    detectar_formato_plantilla,
    prefijar_plantilla,
    quitar_prefijo_plantilla,
)
from desktop.biometria.fabrica import (
    detectar_lectores,
    libfprint_disponible,
    sdk_zk_disponible,
    crear_lector,
    LectorZK,
)
from desktop.biometria.libfprint_backend import (
    LectorLibfprint,
    detectar_dispositivos,
)

__all__ = [
    "LectorHuella",
    "DEDO_NOMBRES",
    "MODELOS_ZK",
    "MAGIC_LIBFPRINT",
    "MAGIC_ZK",
    "ErrorLector",
    "LectorNoConectadoError",
    "SDKNoDisponibleError",
    "PermisoUSBError",
    "CapturaCanceladaError",
    "FormatoIncompatibleError",
    "detectar_formato_plantilla",
    "prefijar_plantilla",
    "quitar_prefijo_plantilla",
    "detectar_lectores",
    "libfprint_disponible",
    "sdk_zk_disponible",
    "crear_lector",
    "LectorZK",
    "LectorLibfprint",
    "detectar_dispositivos",
]

"""Modelos y constantes compartidos de la capa biométrica dactilar.

Soporta dos familias de lectores:
- **ZKTeco** (ZK4500/ZK9500): vía la ZKFinger SDK oficial (``libzkfp.so``).
- **DigitalPersona U.are.U** (y otros compatibles con libfprint): vía
  ``libfprint-2`` (código abierto, empaquetada en ``desktop/biometria/libs``).

Las plantillas de cada familia son incompatibles entre sí, por lo que cada
plantilla se guarda con un prefijo mágico que identifica su formato
(:data:`MAGIC_LIBFPRINT` / :data:`MAGIC_ZK`).
"""

from dataclasses import dataclass, field

# VID/PID de los lectores ZKTeco soportados
VID_ZK = 0x1B55
PID_ZK4500 = 0x0840
PID_ZK9500 = 0x0124

MODELOS_ZK = {
    PID_ZK4500: "ZK4500",
    PID_ZK9500: "ZK9500",
}

# Prefijos que identifican el formato de una plantilla guardada.
MAGIC_LIBFPRINT = b"FPRINT2:"
MAGIC_ZK = b"ZKFINGER:"

# Nombres de dedos. Convención del sistema (y de libfprint FpFinger):
# 1-5 mano izquierda, 6-10 mano derecha.
DEDO_NOMBRES = {
    1: "Pulgar izquierdo",
    2: "Índice izquierdo",
    3: "Medio izquierdo",
    4: "Anular izquierdo",
    5: "Meñique izquierdo",
    6: "Pulgar derecho",
    7: "Índice derecho",
    8: "Medio derecho",
    9: "Anular derecho",
    10: "Meñique derecho",
}

# Umbral de similitud (score 0-100) para aceptar una huella en verificación 1:1.
UMBRAL_VERIFICACION = 60
# Umbral más laxo para confirmar que dos capturas seguidas son del MISMO dedo
# durante el enrolamiento.
UMBRAL_CONSISTENCIA = 40

# Tamaño máximo de plantilla ZKFinger V10 (ver MAX_TEMPLATE_SIZE del SDK).
MAX_TEMPLATE_SIZE = 2048


class ErrorLector(Exception):
    """Error base de la capa biométrica."""


class LectorNoConectadoError(ErrorLector):
    """No hay ningún lector conectado (o no tiene permisos)."""


class SDKNoDisponibleError(ErrorLector):
    """No se encontró la SDK del fabricante del lector."""


class PermisoUSBError(ErrorLector):
    """El lector está conectado pero el usuario no tiene permiso de acceso USB."""


class CapturaCanceladaError(ErrorLector):
    """El usuario canceló la captura."""


class FormatoIncompatibleError(ErrorLector):
    """La plantilla guardada corresponde a otro tipo de lector."""


@dataclass
class LectorHuella:
    """Un lector de huella conectado al equipo."""

    nombre: str
    tipo: str = "zk"  # "zk" | "libfprint"
    vid: int = 0
    pid: int = 0
    bus: int = 0
    direccion: int = 0
    indice_sdk: int = 0
    driver: str = ""  # driver libfprint (p. ej. "uru4000")
    scan_type: str = ""  # "press" | "swipe"
    modelo: str = ""
    etapas_enrolamiento: int = 3  # toques necesarios (libfprint)

    # Se asigna dinámicamente tras la detección (no es campo del dataclass).
    accesible: bool = field(default=False, repr=False)

    @property
    def descripcion(self) -> str:
        nombre = self.modelo or self.nombre
        if self.bus or self.direccion:
            return f"{nombre} (bus {self.bus}, dir. {self.direccion})"
        return nombre


def detectar_formato_plantilla(plantilla: bytes) -> str:
    """Devuelve ``"libfprint"`` o ``"zk"`` según el prefijo de la plantilla.

    Las plantillas sin prefijo (registro antiguo) se interpretan como ZKTeco.
    """
    if not plantilla:
        return "zk"
    if plantilla.startswith(MAGIC_LIBFPRINT):
        return "libfprint"
    return "zk"


def prefijar_plantilla(plantilla: bytes, tipo: str) -> bytes:
    """Añade el prefijo de formato a una plantilla cruda."""
    if tipo == "libfprint":
        if plantilla.startswith(MAGIC_LIBFPRINT):
            return plantilla
        return MAGIC_LIBFPRINT + plantilla
    if plantilla.startswith(MAGIC_ZK):
        return plantilla
    return MAGIC_ZK + plantilla


def quitar_prefijo_plantilla(plantilla: bytes) -> bytes:
    """Devuelve la plantilla sin el prefijo de formato."""
    for magia in (MAGIC_LIBFPRINT, MAGIC_ZK):
        if plantilla.startswith(magia):
            return plantilla[len(magia):]
    return plantilla

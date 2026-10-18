"""Wrapper ctypes sobre la ZKFinger SDK de ZKTeco (``libzkfp.so``).

La ZKFinger SDK es el componente oficial de ZKTeco que permite:
- Capturar la imagen de la huella (256×300, escala de grises).
- Extraer la plantilla biométrica (ZKFinger V10, máx. 2048 bytes).
- Combinar 3 capturas del mismo dedo en una plantilla final (``DBMerge``).
- Comparar plantillas 1:1 (``DBMatch``).

Documentación de la C API (incluida en el SDK):
    int  ZKFPM_Init();
    int  ZKFPM_Terminate();
    int  ZKFPM_GetDeviceCount();
    HANDLE ZKFPM_OpenDevice(int index);
    int  ZKFPM_CloseDevice(HANDLE hDevice);
    int  ZKFPM_AcquireFingerprint(HANDLE, unsigned char* fpImage,
                                  unsigned int cbFPImage,
                                  unsigned char* fpTemplate,
                                  unsigned int* cbTemplate);
    int  ZKFPM_AcquireFingerprintImage(HANDLE, unsigned char* fpImage,
                                       unsigned int cbFPImage);
    HANDLE ZKFPM_DBInit();
    int  ZKFPM_DBFree(HANDLE hDBCache);
    int  ZKFPM_DBMerge(HANDLE, temp1, temp2, temp3, regTemp, unsigned int* cb);
    int  ZKFPM_DBMatch(HANDLE, temp1, unsigned int cb1, temp2, unsigned int cb2);
    int  ZKFPM_GetParameters(HANDLE, int nParamCode, unsigned char* pv, unsigned int* cb);

Códigos de parámetro: 1=ancho de imagen, 2=alto de imagen, 3=DPI, 106=tamaño de imagen.
Códigos de error: 0=OK, -2=librería de captura, -3=sin dispositivo, -8=captura,
-9=extracción, -12=ocupado, -18=cancelada, -22=fallo al combinar, etc.
"""

import ctypes
import ctypes.util
import os
import sys
import logging
import time

from desktop.biometria.modelos import (
    MAX_TEMPLATE_SIZE,
    SDKNoDisponibleError,
)

log = logging.getLogger(__name__)

ES_WINDOWS = os.name == "nt"

# Códigos de error de la ZKFinger SDK
ZKFP_ERR_OK = 0
ZKFP_ERR_INITLIB = -1
ZKFP_ERR_INIT = -2
ZKFP_ERR_NO_DEVICE = -3
ZKFP_ERR_INVALID_PARAM = -5
ZKFP_ERR_OPEN = -6
ZKFP_ERR_INVALID_HANDLE = -7
ZKFP_ERR_CAPTURE = -8
ZKFP_ERR_EXTRACT_FP = -9
ZKFP_ERR_BUSY = -12
ZKFP_ERR_CANCEL = -18
ZKFP_ERR_MERGE = -22
ZKFP_ERR_NOT_OPENED = -23
ZKFP_ERR_NOT_INIT = -24

# Códigos de parámetro
PARAM_ANCHO_IMAGEN = 1
PARAM_ALTO_IMAGEN = 2
PARAM_DPI = 3
PARAM_TAMANO_IMAGEN = 106

# Nombres y rutas de la biblioteca según la plataforma.
# Windows: la ZKFinger SDK for Windows instala «zkfp.dll»
# (misma C API ZKFPM_* que la versión Linux).
if ES_WINDOWS:
    NOMBRES_LIB = ("libzkfp.dll", "zkfp.dll", "ZKFinger.dll")
    RUTAS_SDK = [
        os.path.dirname(os.path.abspath(sys.argv[0])) if sys.argv[0] else "",
        os.getcwd(),
        os.path.expanduser("~/zkfinger"),
        os.path.expanduser("~/ZKFingerSDK"),
        r"C:\Program Files\ZKTeco",
        r"C:\Program Files (x86)\ZKTeco",
        r"C:\Windows\System32",
        r"C:\Windows\SysWOW64",
    ]
else:
    NOMBRES_LIB = ("libzkfp.so", "libzkfp.so.1", "libzkfp.so.5.3")
    RUTAS_SDK = [
        os.path.expanduser("~/zkfinger"),
        os.path.expanduser("~/ZKFingerSDK"),
        "/opt/zkfinger",
        "/opt/ZKFingerSDK",
        "/usr/local/zkfinger",
        "/usr/local/lib",
        "/usr/lib",
    ]


def _buscar_recursivo_acotado(carpeta, nombres, profundidad_max=3,
                               limite_archivos=400):
    """Busca ``nombres`` bajo ``carpeta`` con profundidad acotada."""
    visitados = 0
    for raiz, dirs, archivos in os.walk(carpeta):
        profundidad = raiz[len(carpeta):].count(os.sep)
        if profundidad >= profundidad_max:
            dirs[:] = []
        for nombre in archivos:
            visitados += 1
            if nombre.lower() in nombres:
                return os.path.join(raiz, nombre)
            if visitados > limite_archivos:
                dirs[:] = []
                break
        if visitados > limite_archivos:
            break
    return None


def buscar_libzkfp():
    """Busca la biblioteca de la ZKFinger SDK. Devuelve la ruta o None.

    - Linux: ``libzkfp.so`` en las carpetas del SDK (búsqueda
      acotada, sin recorrido recursivo de directorios del sistema).
    - Windows: ``zkfp.dll`` (busca también bajo «C:\\Program Files\\ZKTeco»,
      acotado a 3 niveles).
    """
    nombres_minus = {n.lower() for n in NOMBRES_LIB}
    # 1. Rutas exactas y un nivel de profundidad en las carpetas del SDK
    for carpeta in RUTAS_SDK:
        if not carpeta or not os.path.isdir(carpeta):
            continue
        for nombre in NOMBRES_LIB:
            candidato = os.path.join(carpeta, nombre)
            if os.path.exists(candidato):
                return candidato
        # Solo un nivel de profundidad (p. ej. ~/zkfinger/lib/libzkfp.so)
        for sub in ("lib", "libs", "x64", "lib/x64", "x86_64", "bin"):
            for nombre in NOMBRES_LIB:
                candidato = os.path.join(carpeta, sub, nombre)
                if os.path.exists(candidato):
                    return candidato
    # 2. En Windows, búsqueda recursiva acotada bajo las carpetas
    #    de Program Files (la DLL suele ir en ...\ZKFinger SDK\bin\x64)
    if ES_WINDOWS:
        for carpeta in RUTAS_SDK:
            if not carpeta or not os.path.isdir(carpeta):
                continue
            hallado = _buscar_recursivo_acotado(carpeta, nombres_minus)
            if hallado:
                return hallado
    # 3. Búsqueda del cargador del sistema (ldconfig en Linux)
    if not ES_WINDOWS:
        for nombre in NOMBRES_LIB:
            try:
                ruta = ctypes.util.find_library(nombre)
            except Exception:
                ruta = None
            if ruta and os.path.exists(ruta):
                return ruta
    return None


class ZKFingerSDK:
    """Acceso a la ZKFinger SDK mediante ctypes."""

    def __init__(self, ruta_lib=None):
        self.ruta_lib = ruta_lib or buscar_libzkfp()
        if not self.ruta_lib:
            if ES_WINDOWS:
                detalle = (
                    "No se encontró la ZKFinger SDK de ZKTeco (zkfp.dll).\n"
                    "Instala la «ZKFinger SDK for Windows» en este equipo "
                    "(la app la detecta en C:\\Program Files\\ZKTeco)."
                )
            else:
                detalle = (
                    "No se encontró la ZKFinger SDK de ZKTeco (libzkfp.so). "
                    "Ejecuta setup_lectores_huella.sh para instalarla."
                )
            raise SDKNoDisponibleError(detalle)
        self._lib = ctypes.CDLL(self.ruta_lib)
        self._configurar_prototipos()
        self._inicializada = False
        self.hdispositivo = None
        self.hdbcache = None
        self.ancho = 256
        self.alto = 300

    # ------------------------------------------------------------------
    def _configurar_prototipos(self):
        lib = self._lib
        lib.ZKFPM_Init.restype = ctypes.c_int
        lib.ZKFPM_Terminate.restype = ctypes.c_int
        lib.ZKFPM_GetDeviceCount.restype = ctypes.c_int

        lib.ZKFPM_OpenDevice.restype = ctypes.c_void_p
        lib.ZKFPM_OpenDevice.argtypes = [ctypes.c_int]
        lib.ZKFPM_CloseDevice.restype = ctypes.c_int
        lib.ZKFPM_CloseDevice.argtypes = [ctypes.c_void_p]

        lib.ZKFPM_AcquireFingerprint.restype = ctypes.c_int
        lib.ZKFPM_AcquireFingerprint.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint,
            ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint),
        ]
        lib.ZKFPM_AcquireFingerprintImage.restype = ctypes.c_int
        lib.ZKFPM_AcquireFingerprintImage.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint,
        ]

        lib.ZKFPM_DBInit.restype = ctypes.c_void_p
        lib.ZKFPM_DBFree.restype = ctypes.c_int
        lib.ZKFPM_DBFree.argtypes = [ctypes.c_void_p]

        lib.ZKFPM_DBMerge.restype = ctypes.c_int
        lib.ZKFPM_DBMerge.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p,
            ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint),
        ]
        lib.ZKFPM_DBMatch.restype = ctypes.c_int
        lib.ZKFPM_DBMatch.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p, ctypes.c_uint,
            ctypes.c_char_p, ctypes.c_uint,
        ]

        lib.ZKFPM_GetParameters.restype = ctypes.c_int
        lib.ZKFPM_GetParameters.argtypes = [
            ctypes.c_void_p, ctypes.c_int,
            ctypes.c_char_p, ctypes.POINTER(ctypes.c_uint),
        ]

    # ------------------------------------------------------------------
    @property
    def disponible(self) -> bool:
        return self.ruta_lib is not None

    def inicializar(self):
        """Inicializa las librerías de captura y algoritmo."""
        ret = self._lib.ZKFPM_Init()
        if ret not in (ZKFP_ERR_OK, 1):  # 1 = ya inicializada
            raise SDKNoDisponibleError(
                f"No se pudo inicializar la ZKFinger SDK (error {ret}). "
                "Verifica que la versión de libzkfp.so corresponda a tu lector."
            )
        self._inicializada = True

    def terminar(self):
        if self.hdispositivo:
            self.cerrar_dispositivo()
        if self._inicializada:
            self._lib.ZKFPM_Terminate()
            self._inicializada = False

    # ------------------------------------------------------------------
    def cantidad_dispositivos(self) -> int:
        return self._lib.ZKFPM_GetDeviceCount()

    def abrir_dispositivo(self, indice=0):
        """Abre el lector por su índice y lee el tamaño de imagen."""
        self.hdispositivo = self._lib.ZKFPM_OpenDevice(indice)
        if not self.hdispositivo:
            raise RuntimeError("No se pudo abrir el lector de huella")
        self.hdbcache = self._lib.ZKFPM_DBInit()
        if not self.hdbcache:
            self._lib.ZKFPM_CloseDevice(self.hdispositivo)
            self.hdispositivo = None
            raise RuntimeError("No se pudo crear la caché de plantillas")
        # Tamaño real de la imagen del sensor
        self.ancho = self._leer_parametro_entero(PARAM_ANCHO_IMAGEN, self.ancho)
        self.alto = self._leer_parametro_entero(PARAM_ALTO_IMAGEN, self.alto)
        return self.hdispositivo

    def cerrar_dispositivo(self):
        if self.hdbcache:
            self._lib.ZKFPM_DBFree(self.hdbcache)
            self.hdbcache = None
        if self.hdispositivo:
            self._lib.ZKFPM_CloseDevice(self.hdispositivo)
            self.hdispositivo = None

    def _leer_parametro_entero(self, codigo, valor_default):
        buffer = ctypes.c_int(valor_default)
        tamaño = ctypes.c_uint(ctypes.sizeof(ctypes.c_int))
        ret = self._lib.ZKFPM_GetParameters(
            self.hdispositivo, codigo,
            ctypes.cast(ctypes.byref(buffer), ctypes.c_char_p),
            ctypes.byref(tamaño),
        )
        if ret == ZKFP_ERR_OK:
            return buffer.value
        return valor_default

    # ------------------------------------------------------------------
    def capturar_plantilla(self):
        """Captura imagen + plantilla. Bloquea hasta que se coloque un dedo.

        Devuelve ``(imagen_bytes, plantilla_bytes)``.
        """
        tamaño_imagen = self.ancho * self.alto
        buffer_imagen = ctypes.create_string_buffer(tamaño_imagen)
        buffer_plantilla = ctypes.create_string_buffer(MAX_TEMPLATE_SIZE)
        limite = time.monotonic() + 4
        ultimo_ret = ZKFP_ERR_CAPTURE
        while time.monotonic() < limite:
            tamaño_plantilla = ctypes.c_uint(MAX_TEMPLATE_SIZE)
            ret = self._lib.ZKFPM_AcquireFingerprint(
                self.hdispositivo, buffer_imagen, tamaño_imagen,
                buffer_plantilla, ctypes.byref(tamaño_plantilla),
            )
            if ret == ZKFP_ERR_OK:
                return (
                    buffer_imagen.raw[:tamaño_imagen],
                    buffer_plantilla.raw[:tamaño_plantilla.value],
                )
            ultimo_ret = ret
            if ret not in (ZKFP_ERR_CAPTURE, ZKFP_ERR_BUSY):
                break
            time.sleep(0.1)
        raise RuntimeError(
            "No se pudo capturar la huella en 15 segundos "
            f"(código {ultimo_ret}). Coloca el dedo sobre el lector."
        )

    def capturar_imagen(self):
        """Captura sólo la imagen (sin extraer plantilla)."""
        tamaño_imagen = self.ancho * self.alto
        buffer_imagen = ctypes.create_string_buffer(tamaño_imagen)
        ret = self._lib.ZKFPM_AcquireFingerprintImage(
            self.hdispositivo, buffer_imagen, tamaño_imagen,
        )
        if ret != ZKFP_ERR_OK:
            raise RuntimeError(f"Error capturando la imagen (código {ret})")
        return buffer_imagen.raw[:tamaño_imagen]

    # ------------------------------------------------------------------
    def combinar_plantillas(self, temp1, temp2, temp3):
        """Combina 3 capturas del mismo dedo en la plantilla final (DBMerge)."""
        buffer_salida = ctypes.create_string_buffer(MAX_TEMPLATE_SIZE)
        tamaño_salida = ctypes.c_uint(MAX_TEMPLATE_SIZE)
        ret = self._lib.ZKFPM_DBMerge(
            self.hdbcache,
            ctypes.create_string_buffer(temp1, len(temp1)),
            ctypes.create_string_buffer(temp2, len(temp2)),
            ctypes.create_string_buffer(temp3, len(temp3)),
            buffer_salida,
            ctypes.byref(tamaño_salida),
        )
        if ret != ZKFP_ERR_OK:
            raise RuntimeError(
                "No se pudieron combinar las 3 capturas. "
                "Asegúrate de usar el MISMO dedo y coloca el dedo con la misma posición. "
                f"(código {ret})"
            )
        return buffer_salida.raw[:tamaño_salida.value]

    def comparar_plantillas(self, plantilla_a, plantilla_b):
        """Compara dos plantillas 1:1 (DBMatch). Devuelve el score (0-100, negativo=error)."""
        return self._lib.ZKFPM_DBMatch(
            self.hdbcache,
            ctypes.create_string_buffer(plantilla_a, len(plantilla_a)), len(plantilla_a),
            ctypes.create_string_buffer(plantilla_b, len(plantilla_b)), len(plantilla_b),
        )


def crear_sdk():
    """Crea e inicializa el SDK si está disponible. Devuelve None si no lo está."""
    ruta = buscar_libzkfp()
    if not ruta:
        return None
    sdk = ZKFingerSDK(ruta)
    try:
        sdk.inicializar()
    except SDKNoDisponibleError:
        return None
    return sdk

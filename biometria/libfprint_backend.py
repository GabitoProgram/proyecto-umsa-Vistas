"""Backend para lectores compatibles con **libfprint-2** (código abierto).

Soporta, entre otros:
- DigitalPersona U.are.U 4000/4000B/4500 (USB 05ba:0007/0008/000a)
- y el resto de lectores de la lista oficial de libfprint.

La biblioteca ``libfprint-2.so.2`` se busca primero en el sistema y,
si no está, en la copia empaquetada con la app
(``desktop/biometria/libs/``). Sus dependencias (libglib, libgusb,
libgio…) son del sistema.

API C enlazada (libfprint-2):
    FpContext *fp_context_new(void);
    void       fp_context_enumerate(FpContext *);          // asíncrono
    GPtrArray *fp_context_get_devices(FpContext *);
    gboolean   fp_device_open_sync(FpDevice *, GCancellable *, GError **);
    gboolean   fp_device_close_sync(FpDevice *, GCancellable *, GError **);
    FpPrint   *fp_device_enroll_sync(FpDevice *, FpPrint *, GCancellable *,
                                     FpEnrollProgress, gpointer, GError **);
    FpImage   *fp_device_capture_sync(FpDevice *, gboolean, GCancellable *,
                                      GError **);
    gboolean   fp_device_verify_sync(FpDevice *, FpPrint *, GCancellable *,
                                     FpMatchCb, gpointer, gboolean *,
                                     FpPrint **, GError **);
    FpPrint   *fp_print_new(FpDevice *);
    void       fp_print_set_finger(FpPrint *, FpFinger);
    gboolean   fp_print_serialize(FpPrint *, guchar **, gsize *, GError **);
    FpPrint   *fp_print_deserialize(const guchar *, gsize, GError **);
    FpImage   *fp_print_get_image(FpPrint *);
    guint      fp_image_get_width(FpImage *);
    guint      fp_image_get_height(FpImage *);
    guchar    *fp_image_get_data(FpImage *, gsize *);
"""

import ctypes
import ctypes.util
import logging
import os
import sys
import time

from desktop.biometria.modelos import (
    LectorHuella,
    ErrorLector,
    LectorNoConectadoError,
    PermisoUSBError,
    SDKNoDisponibleError,
)

log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Carga de la biblioteca
# ──────────────────────────────────────────────────────────────────────
def _cargar_libfprint():
    """Carga ``libfprint-2.so.2`` (del sistema o la copia empaquetada)."""
    if sys.platform != "linux":
        return None
    candidatos = []
    del_sistema = ctypes.util.find_library("fprint-2")
    if del_sistema:
        candidatos.append(del_sistema)
    carpeta_libs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "libs")
    candidatos.extend([
        os.path.join(carpeta_libs, "libfprint-2.so.2"),
        os.path.join(carpeta_libs, "libfprint-2.so.2.0.0"),
    ])
    for ruta in candidatos:
        if not ruta or not os.path.exists(ruta):
            continue
        try:
            return ctypes.CDLL(ruta)
        except OSError as error:
            log.debug("No se pudo cargar %s: %s", ruta, error)
    return None


def _cargar_glib():
    """Carga libglib-2.0 (para bombear el main context de la enumeración)."""
    for nombre in ("libglib-2.0.so.0",):
        ruta = ctypes.util.find_library(nombre)
        if ruta:
            try:
                return ctypes.CDLL(ruta)
            except OSError:
                pass
        candidato = f"/lib/x86_64-linux-gnu/{nombre}"
        if os.path.exists(candidato):
            return ctypes.CDLL(candidato)
    return None


_lib = None
_glib = None
_lib_cargado = False


def _librerias():
    """Devuelve ``(libfprint, glib)`` cargadas (singleton perezoso)."""
    global _lib, _glib, _lib_cargado
    if _lib_cargado:
        return _lib, _glib
    _lib_cargado = True
    # Garantizar que libgusb (dependencia de libfprint) use el
    # **libusb del sistema**: si antes se precargó la copia
    # empaquetada del pip ``libusb``, las transferencias de
    # gusb se quedan colgadas (el dispositivo responde, pero
    # el callback nunca se despacha). Con el libusb del sistema
    # todo funciona.
    try:
        ruta_libusb = ctypes.util.find_library("usb-1.0")
        if ruta_libusb:
            ctypes.CDLL(ruta_libusb, mode=ctypes.RTLD_GLOBAL)
    except Exception as error:  # pragma: no cover
        log.debug("No se pudo precargar el libusb del sistema: %s", error)
    _lib = _cargar_libfprint()
    if _lib is None:
        return None, None
    _glib = _cargar_glib()
    if _glib is None:
        log.debug("libglib no disponible: la enumeración puede ser incompleta")
    _configurar_prototipos(_lib)
    return _lib, _glib


class _GError(ctypes.Structure):
    _fields_ = [
        ("domain", ctypes.c_uint32),
        ("code", ctypes.c_int32),
        ("message", ctypes.c_char_p),
    ]


class _GPtrArray(ctypes.Structure):
    # struct _GPtrArray { gpointer *pdata; guint len; }  (guint = 4 bytes)
    _fields_ = [("pdata", ctypes.c_void_p), ("len", ctypes.c_uint)]


# Callbacks de libfprint
FP_ENROLL_PROGRESS = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p,
)
FP_MATCH_CB = ctypes.CFUNCTYPE(
    None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p,
)

# libfprint: FpFinger. 0xFFF = "no se sabe qué dedo es". Se usa al
# identificar para que el lector no rechace la captura por ser un dedo
# distinto al que declara la plantilla.
FP_FINGER_UNKNOWN = 0xFFF


def _configurar_prototipos(lib):
    # Contexto
    lib.fp_context_new.restype = ctypes.c_void_p
    lib.fp_context_enumerate.argtypes = [ctypes.c_void_p]
    lib.fp_context_get_devices.argtypes = [ctypes.c_void_p]
    lib.fp_context_get_devices.restype = ctypes.POINTER(_GPtrArray)
    # Dispositivo
    lib.fp_device_open_sync.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_device_open_sync.restype = ctypes.c_int
    lib.fp_device_close_sync.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_device_close_sync.restype = ctypes.c_int
    lib.fp_device_get_name.argtypes = [ctypes.c_void_p]
    lib.fp_device_get_name.restype = ctypes.c_char_p
    lib.fp_device_get_driver.argtypes = [ctypes.c_void_p]
    lib.fp_device_get_driver.restype = ctypes.c_char_p
    lib.fp_device_get_device_id.argtypes = [ctypes.c_void_p]
    lib.fp_device_get_device_id.restype = ctypes.c_char_p
    lib.fp_device_get_nr_enroll_stages.argtypes = [ctypes.c_void_p]
    lib.fp_device_get_nr_enroll_stages.restype = ctypes.c_int
    lib.fp_device_get_scan_type.argtypes = [ctypes.c_void_p]
    lib.fp_device_get_scan_type.restype = ctypes.c_int
    # Enrolamiento / captura / verificación
    lib.fp_device_enroll_sync.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        FP_ENROLL_PROGRESS, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_device_enroll_sync.restype = ctypes.c_void_p
    lib.fp_device_capture_sync.argtypes = [
        ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_device_capture_sync.restype = ctypes.c_void_p
    lib.fp_device_verify_sync.argtypes = [
        ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
        FP_MATCH_CB, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int),
        ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_device_verify_sync.restype = ctypes.c_int
    # Plantillas
    lib.fp_print_new.argtypes = [ctypes.c_void_p]
    lib.fp_print_new.restype = ctypes.c_void_p
    lib.fp_print_set_finger.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.fp_print_serialize.argtypes = [
        ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p),
        ctypes.POINTER(ctypes.c_size_t), ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_print_serialize.restype = ctypes.c_int
    lib.fp_print_deserialize.argtypes = [
        ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p)]
    lib.fp_print_deserialize.restype = ctypes.c_void_p
    lib.fp_print_get_image.argtypes = [ctypes.c_void_p]
    lib.fp_print_get_image.restype = ctypes.c_void_p
    # Imagen
    lib.fp_image_get_width.argtypes = [ctypes.c_void_p]
    lib.fp_image_get_width.restype = ctypes.c_uint
    lib.fp_image_get_height.argtypes = [ctypes.c_void_p]
    lib.fp_image_get_height.restype = ctypes.c_uint
    lib.fp_image_get_data.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_size_t)]
    lib.fp_image_get_data.restype = ctypes.c_void_p
    # GLib
    if _glib:
        _glib.g_main_context_default.restype = ctypes.c_void_p
        _glib.g_main_context_iteration.argtypes = [ctypes.c_void_p, ctypes.c_int]
        _glib.g_main_context_iteration.restype = ctypes.c_int
        _glib.g_free.argtypes = [ctypes.c_void_p]


def _mensaje_error(err_ptr):
    """Extrae el mensaje de un ``GError *``."""
    if not err_ptr:
        return "error desconocido"
    try:
        err = ctypes.cast(err_ptr, ctypes.POINTER(_GError)).contents
        if err.message:
            return err.message.decode("utf-8", "replace")
    except Exception:  # pragma: no cover
        pass
    return "error desconocido"


def libfprint_disponible() -> bool:
    """True si se pudo cargar la biblioteca libfprint-2."""
    lib, _ = _librerias()
    return lib is not None


# ──────────────────────────────────────────────────────────────────────
# Detección de dispositivos
# ──────────────────────────────────────────────────────────────────────
def detectar_dispositivos():
    """Enumera los lectores compatibles con libfprint.

    Devuelve una lista de diccionarios con la información de cada
    lector. La enumeración es asíncrona: se bombea el main context
    de GLib hasta que la lista se estabiliza.
    """
    lib, glib = _librerias()
    if lib is None:
        return []
    ctx = lib.fp_context_new()
    if not ctx:
        return []
    try:
        lib.fp_context_enumerate(ctx)
        # Bombear el main context hasta que la enumeración se estabilice
        if glib:
            defctx = glib.g_main_context_default()
            estable = 0
            inicio = time.time()
            while time.time() - inicio < 3.0:
                glib.g_main_context_iteration(defctx, False)
                n = _contar_dispositivos(lib, ctx)
                if n != estable:
                    estable = n
                    ultima_cambios = time.time()
                elif time.time() - ultima_cambios > 0.4:
                    break
                time.sleep(0.02)
        dispositivos = []
        arr = lib.fp_context_get_devices(ctx)
        if arr and arr.contents.len:
            cantidad = min(arr.contents.len, 64)  # tope de seguridad
            punteros = ctypes.cast(
                arr.contents.pdata, ctypes.POINTER(ctypes.c_void_p))
            for i in range(cantidad):
                dev = punteros[i]
                if not dev:
                    continue
                info = _info_dispositivo(lib, dev, i)
                if info:
                    dispositivos.append(info)
        return dispositivos
    finally:
        # El contexto es un GObject: liberarlo con g_object_unref
        _g_object_unref(ctx)


_gobject = None


def _g_object_unref(obj):
    """Libera un GObject (fp_context) si es posible."""
    global _gobject
    if obj is None:
        return
    try:
        if _gobject is None:
            ruta = ctypes.util.find_library("gobject-2.0")
            if not ruta:
                return
            _gobject = ctypes.CDLL(ruta)
        _gobject.g_object_unref(obj)
    except Exception:  # pragma: no cover
        pass


def _contar_dispositivos(lib, ctx):
    arr = lib.fp_context_get_devices(ctx)
    return min(arr.contents.len, 64) if arr else 0


def _info_dispositivo(lib, dev, indice):
    try:
        nombre = lib.fp_device_get_name(dev)
        driver = lib.fp_device_get_driver(dev)
        device_id = lib.fp_device_get_device_id(dev)
        scan_type = lib.fp_device_get_scan_type(dev)
        etapas = lib.fp_device_get_nr_enroll_stages(dev)
    except Exception as error:  # pragma: no cover
        log.debug("Error leyendo dispositivo libfprint: %s", error)
        return None
    nombre = (nombre or b"Lector de huella").decode("utf-8", "replace")
    driver = (driver or b"").decode("utf-8", "replace")
    device_id = (device_id or b"").decode("utf-8", "replace")
    # Intentar VID:PID desde el device_id (formato "usb:VID:PID")
    vid = pid = 0
    if device_id.startswith("usb:"):
        try:
            _, vid_s, pid_s = device_id.split(":")
            vid, pid = int(vid_s, 16), int(pid_s, 16)
        except ValueError:
            pass
    return {
        "indice": indice,
        "nombre": nombre,
        "driver": driver,
        "device_id": device_id,
        "vid": vid,
        "pid": pid,
        "scan_type": "swipe" if scan_type == 0 else "press",
        "etapas_enrolamiento": etapas if etapas > 0 else 1,
    }


# ──────────────────────────────────────────────────────────────────────
# Lector de alto nivel
# ──────────────────────────────────────────────────────────────────────
class LectorLibfprint:
    """Lector de huella sobre libfprint-2 (DigitalPersona U.are.U …)."""

    tipo = "libfprint"

    def __init__(self, indice=0):
        self.indice = indice
        self._lib = None
        self._glib = None
        self._ctx = None
        self._dev = None
        self.modelo = "Lector libfprint"
        self.nombre = ""
        self.driver = ""
        self.scan_type = "press"
        self.etapas_enrolamiento = 1
        self.ancho = 0
        self.alto = 0
        self.conectado = False
        self._cb_enrolamiento = None
        self._cb_match = None

    # ── ciclo de vida ──────────────────────────────────────────────
    def conectar(self):
        lib, glib = _librerias()
        if lib is None:
            raise SDKNoDisponibleError(
                "No se pudo cargar libfprint-2. "
                "Verifica que la biblioteca esté instalada."
            )
        self._lib, self._glib = lib, glib
        dispositivos = detectar_dispositivos()
        log.debug("conectar(): detectar_dispositivos() devolvió %d dispositivos", len(dispositivos))
        if not dispositivos:
            raise LectorNoConectadoError(
                "No se detectó ningún lector compatible con libfprint.\n"
                "Conecta el lector por USB."
            )
        if self.indice >= len(dispositivos):
            self.indice = 0
        info = dispositivos[self.indice]
        self.modelo = info["nombre"]
        self.nombre = info["nombre"]
        self.driver = info["driver"]
        self.scan_type = info["scan_type"]
        self.etapas_enrolamiento = info["etapas_enrolamiento"]

        self._ctx = lib.fp_context_new()
        if not self._ctx:
            raise ErrorLector("No se pudo crear el contexto libfprint")
        # El dispositivo que abre open_sync se elige por posición en la
        # lista que devuelve get_devices (el mismo orden de detección).
        err = ctypes.c_void_p(0)
        lib.fp_context_enumerate(self._ctx)
        if self._glib:
            defctx = self._glib.g_main_context_default()
            for _ in range(150):
                self._glib.g_main_context_iteration(defctx, False)
                arr = lib.fp_context_get_devices(self._ctx)
                if arr and arr.contents.len:
                    break
                time.sleep(0.01)
        arr = lib.fp_context_get_devices(self._ctx)
        if not arr or not arr.contents.len:
            raise LectorNoConectadoError("El lector desapareció de la lista")
        punteros = ctypes.cast(arr.contents.pdata, ctypes.POINTER(ctypes.c_void_p))
        dev = punteros[self.indice]
        if not dev:
            raise LectorNoConectadoError("El lector no está disponible")

        ok = lib.fp_device_open_sync(dev, None, ctypes.byref(err))
        if not ok:
            mensaje = _mensaje_error(err.value)
            raise self._error_apertura(mensaje)
        self._dev = dev
        self.conectado = True
        log.info("Lector libfprint conectado: %s (driver %s)", self.modelo, self.driver)
        return self

    def _error_apertura(self, mensaje):
        """Clasifica el error de apertura (permisos vs. otros)."""
        bajo = mensaje.lower()
        if any(p in bajo for p in ("access", "denied", "permission")):
            return PermisoUSBError(
                f"El lector está conectado pero este usuario no tiene "
                f"permiso para usarlo.\n"
                f"Ejecuta:  sudo ./setup_lectores_huella.sh\n"
                f"(detalle: {mensaje})"
            )
        return LectorNoConectadoError(
            f"No se pudo abrir el lector: {mensaje}"
        )

    def cerrar(self):
        if self._lib and self._dev:
            try:
                err = ctypes.c_void_p(0)
                self._lib.fp_device_close_sync(
                    self._dev, None, ctypes.byref(err))
            except Exception as error:  # pragma: no cover
                log.debug("Error cerrando el lector: %s", error)
        self._dev = None
        self._ctx = None
        self.conectado = False

    def __enter__(self):
        return self.conectar()

    def __exit__(self, *args):
        self.cerrar()

    # ── captura de imagen (vista previa) ───────────────────────────
    def capturar_imagen(self):
        """Captura una imagen (espera el dedo). Devuelve ``(bytes, w, h)``."""
        self._requerido()
        err = ctypes.c_void_p(0)
        img = self._lib.fp_device_capture_sync(
            self._dev, True, None, ctypes.byref(err))
        if not img:
            raise ErrorLector(f"No se pudo capturar la imagen: {_mensaje_error(err.value)}")
        return self._imagen_bytes(img)

    def _imagen_bytes(self, img):
        w = self._lib.fp_image_get_width(img)
        h = self._lib.fp_image_get_height(img)
        self.ancho, self.alto = w, h
        length = ctypes.c_size_t(0)
        data = self._lib.fp_image_get_data(img, ctypes.byref(length))
        if not data or length.value == 0:
            return b"", w, h
        tamaño = min(length.value, w * h * 4)
        raw = ctypes.string_at(data, tamaño)
        return raw[: w * h], w, h

    # ── enrolamiento ───────────────────────────────────────────────
    def enrolar_dedo(self, dedo, on_avance=None):
        """Enrolamiento completo (todas las etapas, bloqueante).

        ``on_avance(completadas, total, imagen_bytes)`` se invoca en
        cada etapa superada. Devuelve la plantilla cruda (sin prefijo).
        """
        self._requerido()
        plantilla = self._lib.fp_print_new(self._dev)
        if not plantilla:
            raise ErrorLector("No se pudo crear la plantilla")
        self._lib.fp_print_set_finger(plantilla, int(dedo))

        self._cb_enrolamiento = FP_ENROLL_PROGRESS(
            self._cb_progreso_enrolamiento)
        self._on_avance = on_avance
        err = ctypes.c_void_p(0)
        resultado = self._lib.fp_device_enroll_sync(
            self._dev, plantilla, None,
            self._cb_enrolamiento, None, ctypes.byref(err))
        if not resultado:
            raise ErrorLector(
                f"No se completó el enrolamiento: {_mensaje_error(err.value)}"
            )
        return self._serializar(resultado)

    def _cb_progreso_enrolamiento(self, device, completadas, print_ptr,
                                  user_data, error):
        try:
            imagen = b""
            ancho = alto = 0
            if print_ptr:
                img = self._lib.fp_print_get_image(print_ptr)
                if img:
                    imagen, ancho, alto = self._imagen_bytes(img)
            if self._on_avance:
                self._on_avance(
                    completadas, self.etapas_enrolamiento,
                    imagen, ancho, alto)
        except Exception as error_cb:  # pragma: no cover
            log.debug("Error en el callback de progreso: %s", error_cb)

    def _serializar(self, print_ptr):
        data = ctypes.c_void_p(0)
        length = ctypes.c_size_t(0)
        err = ctypes.c_void_p(0)
        ok = self._lib.fp_print_serialize(
            print_ptr, ctypes.byref(data), ctypes.byref(length),
            ctypes.byref(err))
        if not ok:
            raise ErrorLector(f"No se pudo serializar la plantilla: {_mensaje_error(err.value)}")
        try:
            if not data or length.value == 0:
                return b""
            return bytes(ctypes.string_at(data, length.value))
        finally:
            if data and self._glib:
                self._glib.g_free(data)

    # ── verificación 1:1 ───────────────────────────────────────────
    def verificar_plantilla(self, plantilla_guardada_cruda):
        """Compara una captura en vivo con la plantilla guardada.

        Devuelve ``(aceptado, score)``. El score es 100.0 si hay
        coincidencia (libfprint devuelve booleano de match).
        """
        return self.comparar_con_plantilla(plantilla_guardada_cruda)

    def comparar_con_plantilla(self, plantilla_guardada_cruda,
                                forzar_dedo_desconocido=False):
        """Compara la captura viva con UNA plantilla concreta.

        La identificación automática 1:N prueba las huellas una por una,
        así que quien la llama necesita saber cuál comparó. Si la plantilla
        no pertenece a este lector se devuelve ``(False, 0.0)`` en vez de
        fallar, para que un único registro mal formado no corte la
        identificación del resto.

        ``forzar_dedo_desconocido`` borra el dedo declarado en la plantilla.
        Hace falta al identificar: si se conserva, libfprint rechaza la
        captura cuando el dedo apoyado no es el que dice la plantilla y se
        queda esperando a un dedo que no va a aparecer.
        """
        self._requerido()
        if not plantilla_guardada_cruda:
            return False, 0.0
        err = ctypes.c_void_p(0)
        guardada = self._lib.fp_print_deserialize(
            plantilla_guardada_cruda, len(plantilla_guardada_cruda),
            ctypes.byref(err))
        if not guardada:
            log.warning(
                "Plantilla no deserializable con este lector "
                "(registrada con otro modelo): se omite")
            return False, 0.0
        if forzar_dedo_desconocido:
            self._lib.fp_print_set_finger(guardada, FP_FINGER_UNKNOWN)
        match = ctypes.c_int(0)
        capturada = ctypes.c_void_p(0)
        self._cb_match = FP_MATCH_CB(self._cb_match_dummy)
        err = ctypes.c_void_p(0)
        ok = self._lib.fp_device_verify_sync(
            self._dev, guardada, None,
            self._cb_match, None,
            ctypes.byref(match), ctypes.byref(capturada),
            ctypes.byref(err))
        if not ok:
            raise ErrorLector(
                f"La verificación no se pudo completar: {_mensaje_error(err.value)}"
            )
        return bool(match.value), (100.0 if match.value else 0.0)

    def _cb_match_dummy(self, *args):
        pass

    def _requerido(self):
        if not self.conectado or not self._dev:
            raise ErrorLector("El lector no está conectado")

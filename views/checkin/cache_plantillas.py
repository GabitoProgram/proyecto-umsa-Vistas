import json
import os
import tempfile
from datetime import date


def _carpeta_cache():
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if not base:
        base = os.path.expanduser("~")
    carpeta = os.path.join(base, "SistemaAdmision", "cache", "plantillas")
    os.makedirs(carpeta, exist_ok=True)
    return carpeta


def _ruta_cache(id_examen):
    nombre = f"plantillas_examen_{id_examen if id_examen is not None else 'todos'}.json"
    return os.path.join(_carpeta_cache(), nombre)


def cargar(id_examen, version=None):
    ruta = _ruta_cache(id_examen)
    try:
        with open(ruta, "r", encoding="utf-8") as archivo:
            contenido = json.load(archivo)
    except (OSError, ValueError):
        return None

    if not isinstance(contenido, dict):
        return None
    if contenido.get("id_examen") != id_examen:
        return None
    if contenido.get("fecha") != date.today().isoformat():
        return None
    if version is not None and contenido.get("version") != version:
        return None

    datos = contenido.get("datos")
    return datos if isinstance(datos, dict) else None


def guardar(id_examen, datos, version):
    carpeta = _carpeta_cache()
    ruta = _ruta_cache(id_examen)
    contenido = {
        "id_examen": id_examen,
        "version": version,
        "fecha": date.today().isoformat(),
        "datos": datos,
    }

    descriptor, temporal = tempfile.mkstemp(
        dir=carpeta,
        prefix="plantillas_",
        suffix=".tmp",
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as archivo:
            json.dump(contenido, archivo, ensure_ascii=False, separators=(",", ":"))
        os.replace(temporal, ruta)
    except Exception:
        try:
            os.remove(temporal)
        except OSError:
            pass
        raise

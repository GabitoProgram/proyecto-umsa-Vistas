import json
import os
import sys
from typing import Optional


def _config_file():
    if getattr(sys, "frozen", False):
        return os.path.join(
            os.path.dirname(sys.executable), "config", "app_config.json"
        )
    return os.path.join(os.path.dirname(__file__), "app_config.json")


CONFIG_FILE = _config_file()
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


class AppConfig:
    @staticmethod
    def get_api_base_url() -> str:
        """Devuelve la URL configurada, priorizando el JSON externo."""
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                valor = json.load(file).get("api_base_url")
                if valor:
                    return str(valor).rstrip("/")
        except (OSError, ValueError):
            pass
        valor = os.getenv("API_BASE_URL")
        if valor:
            return valor.rstrip("/")
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if line.startswith("API_BASE_URL="):
                        return line.split("=", 1)[1].strip().strip('"\'').rstrip("/")
        except OSError:
            pass
        return "http://localhost:8000/api/v1"

    @staticmethod
    def get_app_key() -> Optional[str]:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return json.load(file).get("app_client_key")
        except (OSError, ValueError):
            return None

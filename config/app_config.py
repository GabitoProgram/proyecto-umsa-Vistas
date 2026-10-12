import json
import os
from typing import Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "app_config.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")


class AppConfig:
    @staticmethod
    def get_api_base_url() -> str:
        """Devuelve la URL de la API desde el entorno o el archivo .env."""
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

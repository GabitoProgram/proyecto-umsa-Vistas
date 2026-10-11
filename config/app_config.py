import json
import os
from typing import Optional

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "app_config.json")


class AppConfig:
    @staticmethod
    def get_app_key() -> Optional[str]:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as file:
                return json.load(file).get("app_client_key")
        except (OSError, ValueError):
            return None

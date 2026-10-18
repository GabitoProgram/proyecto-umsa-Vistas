import os
import json
import requests
from typing import Optional, Dict, Any

from desktop.config.app_config import AppConfig

class APIClient:
    BASE_URL = AppConfig.get_api_base_url()

    def __init__(self):
        self.jwt_token: Optional[str] = None
        self.app_key: Optional[str] = AppConfig.get_app_key()
        self.current_user: Optional[Dict[str, Any]] = None

    def _headers(self, require_jwt: bool = False) -> Dict[str, str]:
        headers = {}
        if self.app_key:
            headers['X-App-Key'] = self.app_key
        if self.jwt_token:
            headers['Authorization'] = f'Bearer {self.jwt_token}'
        return headers

    def consultar_examen_activo(self) -> Dict[str, Any]:
        url = f'{self.BASE_URL}/examenes/activos-ahora'
        try:
            resp = requests.get(url, headers=self._headers(), timeout=4)
            if resp.status_code == 200:
                activos = resp.json().get('activos', [])
                return activos[0] if activos else {'activo': False}
            return {'activo': False, 'error': f'HTTP {resp.status_code}'}
        except requests.RequestException as e:
            return {'activo': False, 'error': str(e)}

    def login(self, username: str, password: str) -> bool:
        url = f'{self.BASE_URL}/auth/login'
        payload = {'username': username, 'password': password}
        try:
            resp = requests.post(url, data=payload, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                self.jwt_token = data.get('access_token')
                self.current_user = self.get_me()
                return True
            return False
        except requests.RequestException:
            return False

    def get_me(self) -> Optional[Dict[str, Any]]:
        url = f'{self.BASE_URL}/auth/me'
        try:
            resp = requests.get(url, headers=self._headers(require_jwt=True), timeout=4)
            return resp.json() if resp.status_code == 200 else None
        except requests.RequestException:
            return None

    def marcar_rostro(self, id_examen: int, id_postulante: int, image_bytes: bytes):
        url = f'{self.BASE_URL}/marcaciones/verificar-rostro'
        files = {'file': ('captura.jpg', image_bytes, 'image/jpeg')}
        data = {
            'id_examen': id_examen,
            'id_postulante': id_postulante,
        }
        resp = requests.post(url, headers=self._headers(), data=data, files=files, timeout=8)
        return resp.json(), resp.status_code

    def marcar_huella(self, id_examen: int, id_postulante: int, tipo_dedo: int, template_bytes: bytes):
        url = f'{self.BASE_URL}/marcaciones/verificar-huella'
        data = {
            'id_examen': id_examen,
            'id_postulante': id_postulante,
            'tipo_dedo': tipo_dedo,
        }
        files = {'file': ('huella.bin', template_bytes, 'application/octet-stream')}
        resp = requests.post(url, headers=self._headers(), data=data, files=files, timeout=5)
        return resp.json(), resp.status_code

    def get_contador(self, id_examen: int):
        url = f'{self.BASE_URL}/examenes/{id_examen}/contador'
        try:
            resp = requests.get(url, headers=self._headers(), timeout=4)
            return resp.json() if resp.status_code == 200 else None
        except requests.RequestException:
            return None

    def ajustar_tolerancia(self, id_examen: int, minutos: int):
        url = f'{self.BASE_URL}/examenes/{id_examen}/tolerancia'
        resp = requests.patch(url, headers=self._headers(require_jwt=True), json={'tolerancia_minutos': minutos}, timeout=5)
        return resp.json(), resp.status_code


    def listar_postulantes(self, skip: int = 0, limit: int = 1000):
        url = f"{self.BASE_URL}/postulantes?skip={skip}&limit={limit}"
        try:
            resp = requests.get(url, headers=self._headers(require_jwt=True), timeout=6)
            return resp.json() if resp.status_code == 200 else []
        except requests.RequestException:
            return []

    def crear_postulante(self, datos: dict):
        url = f"{self.BASE_URL}/postulantes/"
        try:
            resp = requests.post(url, headers=self._headers(require_jwt=True), json=datos, timeout=6)
            return resp.json(), resp.status_code
        except requests.RequestException as e:
            return {"error": str(e)}, 500

    def importar_excel_postulantes(self, file_path: str):
        url = f"{self.BASE_URL}/postulantes/importar-excel"
        try:
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                resp = requests.post(url, headers=self._headers(require_jwt=True), files=files, timeout=30)
                return resp.json(), resp.status_code
        except requests.RequestException as e:
            return {"error": str(e)}, 500


    def listar_carreras(self):
        url = f"{self.BASE_URL}/admin/carreras"
        try:
            resp = requests.get(url, headers=self._headers(require_jwt=True), timeout=4)
            return resp.json() if resp.status_code == 200 else []
        except requests.RequestException:
            return []

api = APIClient()

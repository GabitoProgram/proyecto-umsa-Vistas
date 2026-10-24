# Frontend UMSA

Aplicación de escritorio PySide6 para administración, registro de
postulantes, biometría facial y marcación por huella del sistema UMSA.

El frontend y el backend son repositorios independientes. El frontend se
ejecuta en una terminal y el backend en otra.

## Requisitos

- Windows 10/11.
- Python 3.13 recomendado para la interfaz actual.
- Backend UMSA ejecutándose.
- PostgreSQL funcionando en la máquina del backend.
- Git.
- Para huellas: lector ZKTeco ZK9500 y la SDK oficial instalada en la
  máquina donde se ejecuta el frontend.

## Crear el entorno virtual

Desde la carpeta del frontend:

```powershell
py -3.13 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install PySide6 requests pandas openpyxl opencv-python pyusb libusb
```

En Git Bash:

```bash
source venv/Scripts/activate
```

El frontend no incluye actualmente un `requirements.txt`; por eso las
dependencias principales se instalan con el comando anterior.

## Configurar la URL del backend

En la raíz del frontend crea o edita `.env`:

```dotenv
API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Si el backend utiliza otro equipo de la red:

```dotenv
API_BASE_URL=http://IP_DEL_SERVIDOR:8000/api/v1
```

Si el backend utiliza otro puerto, reemplaza `8000`.

## Configurar la clave de aplicación

Edita `config/app_config.json`:

```json
{
  "app_client_key": "LA_MISMA_APP_CLIENT_KEY_DEL_BACKEND"
}
```

El valor debe ser exactamente el mismo que `APP_CLIENT_KEY` del `.env` del
backend. No publiques esta clave en repositorios públicos.

## Ejecutar el frontend

Con el entorno virtual activo:

```powershell
python main.py
```

También puedes usar:

```powershell
py -3.13 main.py
```

El backend debe estar ejecutándose antes de iniciar la aplicación si deseas
usar login, dashboard, postulantes o marcación biométrica.

## Orden recomendado para iniciar el sistema

### Terminal 1: backend

```powershell
cd "E:\INFORMATICA 8\Taller 1\Vistas\proyecto-umsa-Backend"
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Terminal 2: frontend

```powershell
cd "E:\INFORMATICA 8\Taller 1\Vistas\proyecto-umsa-Vistas"
.\venv\Scripts\Activate.ps1
python main.py
```

## Configuración del ZK9500

Para usar huellas en Windows:

1. Conecta el ZK9500 por USB.
2. Instala la SDK oficial de ZKTeco.
3. Comprueba que el archivo `zkfp.dll` esté en una ruta disponible para la
   aplicación, como la carpeta del proyecto, la carpeta de la SDK o una ruta
   del sistema.
4. Registra las huellas desde el panel administrativo.
5. Habilita la huella para el postulante y el examen correspondiente.
6. Entra al registro biométrico y apoya el dedo en el lector.

La aplicación inicia la lectura automáticamente; no es necesario pulsar un
botón para identificar la huella.

Si el lector aparece detectado pero no captura, comprueba que:

- La SDK sea compatible con el modelo ZK9500.
- No haya otro programa usando el lector.
- La DLL coincida con la arquitectura de Python instalada.
- La huella esté habilitada para el examen activo.
- La clave de aplicación coincida con la del backend.

## Flujo inicial de uso

1. Inicia PostgreSQL.
2. Inicia el backend.
3. Inicia el frontend.
4. Entra con el usuario `admin` creado por el backend.
5. Crea gestiones y carreras.
6. Registra o importa postulantes.
7. Registra y habilita rostro o huellas.
8. Programa el examen y asigna aulas/asientos si corresponde.
9. Abre el registro biométrico durante la ventana del examen.

## Solución de problemas

### No conecta con la API

Comprueba que el backend responda en:

```text
http://127.0.0.1:8000/health
```

Después revisa `API_BASE_URL` en `.env`.

### Error de puerto ocupado

El backend puede estar ejecutándose ya. Comprueba el proceso que usa el
puerto 8000 o inicia el backend en otro puerto y actualiza `.env`.

### No aparece el examen activo

Comprueba que la fecha y hora del examen estén dentro de la ventana
permitida y que el backend tenga acceso a PostgreSQL.

### No reconoce la huella

Comprueba que la huella esté registrada, habilitada y asociada al examen.
Mantén el dedo apoyado hasta que termine la captura.

## Seguridad

No publiques:

- `.env`.
- `config/app_config.json` con una clave real.
- Contraseñas.
- Logs con datos personales.
- Capturas o plantillas biométricas.


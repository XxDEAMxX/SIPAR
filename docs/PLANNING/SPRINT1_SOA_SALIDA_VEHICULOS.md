# Sprint 1 - Servicio SOA de salida de vehiculos

## Objetivo
Implementar un microservicio FastAPI independiente que:
1. Reciba eventos de salida por endpoint HTTP.
2. Detecte automaticamente placas desde camara (OpenCV + fast-alpr).
3. Reenvie cada salida al backend principal de SIPAR.

## Arquitectura
- Servicio: `src/vehicle-exit-service`
- Protocolo: HTTP REST
- Integracion SOA: comunicacion entre servicios por `X-API-Key`.
- Ejecucion: contenedor dedicado en `src/docker-compose.yml`.

## Endpoint del microservicio
### POST /api/v1/vehicle-exits
Registra una salida de vehiculo y reenvia el evento al backend principal.

Request de ejemplo:
```json
{
  "plate": "ABC123",
  "exit_time": "2026-04-08T18:10:00Z",
  "source": "manual",
  "confidence": 0.98,
  "camera_id": "cam-salida-1"
}
```

Response de ejemplo:
```json
{
  "accepted": true,
  "duplicate": false,
  "forwarded": true,
  "message": "Salida registrada y enviada al backend principal",
  "plate": "ABC123",
  "exit_time": "2026-04-08T18:10:00Z"
}
```

## Worker de camara
- Se activa con `AUTO_DETECTION_ENABLED=true`.
- Lee continuamente frames de la camara (`CAMERA_INDEX`).
- Usa detector configurable:
  - `DETECTOR_PROVIDER=fast-alpr` para deteccion real.
  - `DETECTOR_PROVIDER=mock` para pruebas.
- Aplica umbral de confianza (`CAMERA_MIN_CONFIDENCE`).
- Evita duplicados por ventana temporal (`DUPLICATE_WINDOW_SECONDS`).

## Variables de entorno clave
- `BACKEND_EXIT_URL`: endpoint del backend principal para recibir salida.
- `SERVICE_API_KEY`: clave compartida entre servicios.
- `AUTO_DETECTION_ENABLED`: habilita worker automatico.
- `DETECTOR_PROVIDER`: `mock` o `fast-alpr`.

## Pruebas unitarias implementadas
- `tests/test_service.py`
  - Reenvio correcto del primer evento.
  - Bloqueo de duplicados en ventana de tiempo.
- `tests/test_api.py`
  - Health check.
  - Registro manual exitoso.
  - Manejo de error del backend principal (502).

## Ejecucion local
Desde `src/vehicle-exit-service`:
```bash
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8010
```

Con docker compose (desde `src`):
```bash
docker compose up --build
```

## Nota de integracion
Este microservicio envia eventos al endpoint configurado en `BACKEND_EXIT_URL`.
El backend principal debe exponer esa ruta para persistir la salida en tickets/vehiculos.

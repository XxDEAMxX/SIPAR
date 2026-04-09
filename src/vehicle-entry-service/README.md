# vehicle-entry-service

Servicio basico de deteccion de placas para camara de entrada.

## Que hace
- Lee frames desde una camara (`CAMERA_INDEX`).
- Detecta placas con `fast_alpr`.
- Imprime en consola: placa y confianza de deteccion.
- Evita repetir la misma placa por unos segundos (`PLATE_COOLDOWN_SECONDS`).
- Si defines `BACKEND_ENDPOINT`, envia un `POST` simple por cada deteccion.

## Variables de entorno
Puedes copiar `.env.example` y ajustar valores.

Variables clave:
- `BACKEND_ENDPOINT`: URL donde se enviara cada deteccion via `POST`.
- `CAMERA_INDEX`: indice de camara de OpenCV.
- `CAMERA_ID`: identificador logico de la camara.
- `MIN_DETECTION_CONFIDENCE`: confianza minima para aceptar detecciones.

## Ejecutar
Desde la carpeta del servicio:
```bash
pip install -r requirements.txt
uvicorn main:app --host 127.0.0.1 --port 8001
```

Desde la raiz del workspace:
```bash
python -m uvicorn main:app --app-dir src/vehicle-entry-service --host 127.0.0.1 --port 8001
```

## Endpoints locales
- `GET /health`: estado del worker.

## Ejemplo de impresion en consola
```text
Placa detectada: ABC123 | confianza=0.873
```

## Payload enviado al backend (si BACKEND_ENDPOINT existe)
```json
{
  "plate": "ABC123",
  "detection_confidence": 0.88,
  "camera_id": "entry-cam-1",
  "detected_at": "2026-04-08T15:42:19.391501+00:00"
}
```

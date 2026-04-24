# vehicle-exit-service

Servicio basico de deteccion de placas para camara de salida.

## Que hace
- Lee frames desde una camara (`CAMERA_INDEX`).
- Detecta placas con `fast_alpr`.
- Imprime en consola: placa y confianza de deteccion.
- Evita repetir la misma placa por unos segundos (`PLATE_COOLDOWN_SECONDS`).
- Si defines `BACKEND_ENDPOINT`, envia un `POST` simple por cada deteccion al backend central.

## Variables de entorno
Puedes copiar `.env.example` y ajustar valores.

Variables clave:
- `BACKEND_ENDPOINT`: URL donde se enviara cada deteccion via `POST`.
- `SERVICE_API_KEY`: API key para autenticar el microservicio contra el backend.
- `DETECTION_DIRECTION`: debe ser `exit` para este servicio.
- `CAMERA_INDEX`: indice de camara de OpenCV.
- `CAMERA_ID`: identificador logico de la camara.
- `CONSENSUS_WINDOW_SECONDS`: ventana corta para agrupar varias lecturas de la misma placa.
- `CONSENSUS_MIN_OBSERVATIONS`: lecturas minimas antes de enviar la placa consolidada.
- `CONSENSUS_MIN_SUPPORT`: cantidad minima total de lecturas compatibles dentro del consenso.
- `CONSENSUS_MIN_CONFIDENCE`: confianza minima requerida para emitir una placa consolidada.
- `MIN_PLATE_CONFIDENCE`: confianza minima del OCR de placa para considerar una lectura.
- `IMMEDIATE_EMIT_PLATE_CONFIDENCE`: si una lectura individual supera este umbral, se envia sin esperar a cerrar la ventana.
- `IMMEDIATE_EMIT_MIN_HITS`: cantidad de lecturas consecutivas iguales y de alta confianza para emitir de inmediato.
- `POST_EMIT_LOCK_SECONDS`: tiempo durante el cual se ignoran nuevas lecturas tras emitir un evento.
- `PRESENCE_RESET_SECONDS`: tiempo sin ver la placa antes de permitir otro evento del mismo vehiculo.
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
Placa inmediata: ABC123 | confianza=0.971 | observaciones=2
```

## Payload enviado al backend (si BACKEND_ENDPOINT existe)
```json
{
  "plate": "ABC123",
  "direction": "exit",
  "detection_confidence": 0.88,
  "camera_id": "exit-cam-1",
  "source": "vehicle-exit-service",
  "detected_at": "2026-04-08T15:42:19.391501+00:00"
}
```

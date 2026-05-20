# Servicio de cupos

Este servicio detecta ocupacion de espacios usando dos datos:

- `SLOT_CAMERA_SOURCE`: de donde sale la imagen, por ejemplo OBS Virtual Camera.
- `SLOTS_CONFIG_PATH`: donde estan los poligonos de los cupos marcados.

## OBS Virtual Camera

Si usas OBS, no necesitas registrar `cupos` en `stream-service`. Puedes leer la camara virtual directamente:

```env
SLOT_CAMERA_SOURCE=1
SLOTS_CONFIG_PATH=../test-deteccion/cupos.json
SLOT_FRAME_WIDTH=800
SLOT_FRAME_HEIGHT=600
SLOT_OCCUPIED_STD_THRESHOLD=20
SLOT_DETECTION_FPS=6
SLOT_STREAM_FPS=12
```

El numero de `SLOT_CAMERA_SOURCE` depende de Windows. Prueba `0`, `1`, `2`, `3` hasta encontrar OBS.

## Stream service

Si prefieres pasar por `stream-service`, registra una camara `cupos`:

```env
CAMERAS_JSON={"entrada":0,"salida":3,"cupos":1}
```

Y en este servicio usa:

```env
SLOT_CAMERA_SOURCE=http://127.0.0.1:8010/cameras/cupos/stream
```

Si no registras `cupos`, `stream-service` respondera `404 Not Found`.

## Imagen estatica

Para probar sin OBS:

```env
SLOT_CAMERA_SOURCE=../test-deteccion/park3.png
SLOTS_CONFIG_PATH=../test-deteccion/cupos.json
```

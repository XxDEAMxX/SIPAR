import cv2
import json
import numpy as np
import os
import urllib.request

SOURCE = os.getenv("MARKER_SOURCE", "http://127.0.0.1:8010/cameras/cupos/snapshot")
OUTPUT = os.getenv("MARKER_OUTPUT", "cupos.json")
FRAME_WIDTH = int(os.getenv("MARKER_FRAME_WIDTH", "800"))
FRAME_HEIGHT = int(os.getenv("MARKER_FRAME_HEIGHT", "600"))


def cargar_imagen(source):
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=8) as response:
            data = np.asarray(bytearray(response.read()), dtype=np.uint8)
        frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
    else:
        frame = cv2.imread(source)

    if frame is None:
        raise RuntimeError(f"No se pudo cargar la imagen base desde {source}")
    return cv2.resize(frame, (FRAME_WIDTH, FRAME_HEIGHT))


imagen = cargar_imagen(SOURCE)

puntos_actuales = []
cupos = []
id_cupo = 1


def ordenar_puntos(puntos):
    centro = np.mean(np.array(puntos), axis=0)
    return sorted(puntos, key=lambda p: np.arctan2(p[1] - centro[1], p[0] - centro[0]))


def dibujar():
    copia = imagen.copy()
    
    for cupo in cupos:
        pts = np.array(cupo["polygon"], np.int32)
        cv2.polylines(copia, [pts], True, (0, 255, 0), 2)
        cx = int(np.mean([p[0] for p in cupo["polygon"]]))
        cy = int(np.mean([p[1] for p in cupo["polygon"]]))
        cv2.putText(copia, f"#{cupo['id']}", (cx-10, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
    
    for p in puntos_actuales:
        cv2.circle(copia, tuple(p), 5, (0, 0, 255), -1)
    
    if len(puntos_actuales) > 1:
        pts = np.array(puntos_actuales, np.int32)
        cv2.polylines(copia, [pts], False, (0, 0, 255), 1)
    
    cv2.putText(copia, f"Cupo #{id_cupo} | Clics: {len(puntos_actuales)}/4 | ENTER=guardar C=cancelar Q=salir",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1,
                cv2.LINE_AA)
    
    cv2.imshow("Marcar cupos", copia)

def click(event, x, y, flags, param):
    global puntos_actuales
    if event == cv2.EVENT_LBUTTONDOWN:
        if len(puntos_actuales) < 4:
            puntos_actuales.append([x, y])
            dibujar()

cv2.namedWindow("Marcar cupos")
cv2.setMouseCallback("Marcar cupos", click)
dibujar()

while True:
    key = cv2.waitKey(0) & 0xFF

    if key == 13:  # ENTER
        if len(puntos_actuales) == 4:
            cupos.append({"id": id_cupo, "polygon": ordenar_puntos(puntos_actuales.copy())})
            print(f"Cupo #{id_cupo} guardado")
            id_cupo += 1
            puntos_actuales = []
            dibujar()

    elif key == ord('c'):
        puntos_actuales = []
        dibujar()

    elif key == ord('q'):
        break

with open(OUTPUT, "w") as f:
    json.dump(
        {
            "frame": {
                "width": FRAME_WIDTH,
                "height": FRAME_HEIGHT,
                "source": SOURCE,
            },
            "spots": cupos,
        },
        f,
        indent=2,
    )

print(f"Guardados {len(cupos)} cupos en {OUTPUT}")
cv2.destroyAllWindows()

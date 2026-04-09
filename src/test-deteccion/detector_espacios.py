import cv2
import json
import numpy as np

def cargar_cupos(path):
    with open(path) as f:
        data = json.load(f)
    return data["spots"]

def clasificar_cupo(gray, polygon):
    mask = np.zeros(gray.shape, np.uint8)
    pts = np.array(polygon, np.int32)
    cv2.fillPoly(mask, [pts], 255)
    region = cv2.bitwise_and(gray, gray, mask=mask)
    pixeles = region[mask == 255]
    desviacion = np.std(pixeles)
    return desviacion > 20

def dibujar_cupos(frame, cupos, estados):
    overlay = frame.copy()

    for cupo, ocupado in zip(cupos, estados):
        pts = np.array(cupo["polygon"], np.int32)
        color = (0, 0, 220) if ocupado else (0, 200, 0)
        cv2.fillPoly(overlay, [pts], color)

    frame = cv2.addWeighted(frame, 0.6, overlay, 0.4, 0)

    for cupo, ocupado in zip(cupos, estados):
        pts = np.array(cupo["polygon"], np.int32)
        color = (0, 0, 220) if ocupado else (0, 200, 0)
        cv2.polylines(frame, [pts], True, color, 2)

    libres = estados.count(False)
    ocupados = estados.count(True)
    cv2.putText(frame, f"Libres: {libres}  Ocupados: {ocupados}",
                (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    return frame

cupos = cargar_cupos("cupos.json")

frame = cv2.imread("park3.png")
frame = cv2.resize(frame, (800, 600))

gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
estados = [clasificar_cupo(gray, c["polygon"]) for c in cupos]

frame = dibujar_cupos(frame, cupos, estados)

cv2.imshow("Parqueadero", frame)
cv2.waitKey(0)
cv2.destroyAllWindows()
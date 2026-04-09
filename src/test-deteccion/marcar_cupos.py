import cv2
import json
import numpy as np

imagen = cv2.imread("park1.png")
imagen = cv2.resize(imagen, (800, 600))

puntos_actuales = []
cupos = []
id_cupo = 1

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
            cupos.append({"id": id_cupo, "polygon": puntos_actuales.copy()})
            print(f"Cupo #{id_cupo} guardado")
            id_cupo += 1
            puntos_actuales = []
            dibujar()

    elif key == ord('c'):
        puntos_actuales = []
        dibujar()

    elif key == ord('q'):
        break

with open("cupos.json", "w") as f:
    json.dump({"spots": cupos}, f, indent=2)

print(f"Guardados {len(cupos)} cupos en cupos.json")
cv2.destroyAllWindows()
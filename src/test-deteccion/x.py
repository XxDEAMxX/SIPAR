import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from fast_alpr import ALPR

# Detecta automáticamente si hay GPU disponible
providers_disponibles = ort.get_available_providers()

if "CUDAExecutionProvider" in providers_disponibles:
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    print("Usando GPU (CUDA)")
else:
    providers = ["CPUExecutionProvider"]
    print("Usando CPU")

# Inicializa el lector de placas
alpr = ALPR(
    detector_model="yolo-v9-t-384-license-plate-end2end",
    ocr_model="cct-xs-v1-global-model",
    detector_providers=providers,
    ocr_providers=providers,
)

# Abre la cámara (0 = cámara por defecto)
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: No se pudo abrir la cámara")
    exit()

print("Cámara abierta. Presiona 'q' para salir.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: No se pudo leer el frame")
        break

    # Detecta y dibuja las placas
    resultado = alpr.draw_predictions(frame)

    # Extraer la imagen del objeto resultado
    imagen = resultado.image

    if isinstance(imagen, Image.Image):
        frame_anotado = cv2.cvtColor(np.array(imagen, dtype=np.uint8), cv2.COLOR_RGB2BGR)
    elif isinstance(imagen, np.ndarray):
        frame_anotado = imagen.astype(np.uint8)
    else:
        frame_anotado = np.array(imagen, dtype=np.uint8)

    cv2.imshow("Parqueadero - Detección de placas", frame_anotado)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
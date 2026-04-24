import cv2

cap = cv2.VideoCapture(3)

while True:
    ret, frame = cap.read()

    if not ret:
        print("No se pudo abrir la cámara")
        break

    cv2.imshow("Cámara", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
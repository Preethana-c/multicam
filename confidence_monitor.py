import cv2
import numpy as np
from ultralytics import YOLO

H = np.array([
    [0.176138,  0.647589, -63.412272],
    [-0.180912, 0.622446,  -0.125533],
    [-0.000002, 0.001756,   0.102316]
])

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(r"C:\Preethi\multi_cam\camera_vid\4p-c0.avi")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, classes=[0], verbose=False)

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        conf = float(box.conf[0])
        foot_x = (x1 + x2) // 2
        foot_y = y2

        pt = np.array([[[foot_x, foot_y]]], dtype=np.float32)
        floor_pt = cv2.perspectiveTransform(pt, H)
        fx, fy = floor_pt[0][0]

        # color by confidence: red = low, green = high
        color = (0, int(255 * conf), int(255 * (1 - conf)))

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        # confidence bar
        bar_width = int((x2 - x1) * conf)
        cv2.rectangle(frame, (x1, y2 + 5), (x1 + bar_width, y2 + 12), color, -1)

        cv2.putText(frame, f"conf:{conf:.2f} ({fx:.0f},{fy:.0f})", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        print(f"Floor ({fx:.0f}, {fy:.0f}) — confidence: {conf:.2f}")

    cv2.imshow("Confidence Monitor", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
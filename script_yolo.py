import cv2
import numpy as np
from ultralytics import YOLO

H = np.array([
    [0.176138,  0.647589, -63.412272],
    [-0.180912, 0.622446,  -0.125533],
    [-0.000002, 0.001756,   0.102316]
])

model = YOLO("yolov8n.pt")  # downloads automatically first time

cap = cv2.VideoCapture(r"C:\Preethi\multi_cam\camera_vid\4p-c0.avi")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, classes=[0], verbose=False)  # class 0 = person

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        
        # foot point = bottom center of bounding box
        foot_x = (x1 + x2) // 2
        foot_y = y2

        # project to floor
        pt = np.array([[[foot_x, foot_y]]], dtype=np.float32)
        floor_pt = cv2.perspectiveTransform(pt, H)
        fx, fy = floor_pt[0][0]

        # draw on frame
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.circle(frame, (foot_x, foot_y), 5, (0, 0, 255), -1)
        cv2.putText(frame, f"({fx:.0f}, {fy:.0f})", (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

    cv2.imshow("Camera 0 - Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
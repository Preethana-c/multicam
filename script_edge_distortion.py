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

    cx, cy = frame.shape[1] // 2, frame.shape[0] // 2  # move this OUTSIDE the box loop
    results = model(frame, classes=[0], verbose=False)

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        foot_x = (x1 + x2) // 2
        foot_y = y2

        pt = np.array([[[foot_x, foot_y]]], dtype=np.float32)
        floor_pt = cv2.perspectiveTransform(pt, H)
        fx, fy = floor_pt[0][0]

        dist_from_center = np.sqrt((foot_x - cx)**2 + (foot_y - cy)**2)
        max_dist = np.sqrt(cx**2 + cy**2)
        ratio = dist_from_center / max_dist

        color = (0, int(255 * (1 - ratio)), int(255 * ratio))

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"({fx:.0f},{fy:.0f}) edge:{ratio:.2f}", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # crosshair drawn once per frame, after the box loop
    cv2.line(frame, (cx-20, cy), (cx+20, cy), (255,255,255), 1)
    cv2.line(frame, (cx, cy-20), (cx, cy+20), (255,255,255), 1)

    cv2.imshow("Edge Distortion", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
import cv2
import numpy as np
from ultralytics import YOLO

H = np.array([
    [0.176138,  0.647589, -63.412272],
    [-0.180912, 0.622446,  -0.125533],
    [-0.000002, 0.001756,   0.102316]
])

# define zones — adjust these numbers based on what coordinates you saw
ZONES = {
    "ZONE A": (0,   0,   200, 200),   # x_min, y_min, x_max, y_max
    "ZONE B": (200, 0,   400, 200),
    "ZONE C": (0,   200, 200, 400),
    "ZONE D": (200, 200, 400, 400),
}

ZONE_COLORS = {
    "ZONE A": (255, 0,   0),
    "ZONE B": (0,   255, 0),
    "ZONE C": (0,   0,   255),
    "ZONE D": (255, 255, 0),
}

def get_zone(fx, fy):
    for name, (xmin, ymin, xmax, ymax) in ZONES.items():
        if xmin <= fx <= xmax and ymin <= fy <= ymax:
            return name
    return "UNKNOWN"

model = YOLO("yolov8n.pt")
cap = cv2.VideoCapture(r"C:\Preethi\multi_cam\camera_vid\4p-c0.avi")

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, classes=[0], verbose=False)

    # track which zones are occupied this frame
    occupied_zones = set()

    for box in results[0].boxes:
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        foot_x = (x1 + x2) // 2
        foot_y = y2

        pt = np.array([[[foot_x, foot_y]]], dtype=np.float32)
        floor_pt = cv2.perspectiveTransform(pt, H)
        fx, fy = floor_pt[0][0]

        zone = get_zone(fx, fy)
        occupied_zones.add(zone)
        color = ZONE_COLORS.get(zone, (255, 255, 255))

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{zone} ({fx:.0f},{fy:.0f})", (x1, y1-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

    # simulate light control
    print("--- Frame ---")
    for zone in ZONES:
        status = "ON  💡" if zone in occupied_zones else "OFF 🌑"
        print(f"  Light {zone}: {status}")

    cv2.imshow("Zone Detection", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
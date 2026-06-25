import cv2
import numpy as np
import json
import paho.mqtt.client as mqtt
from ultralytics import YOLO

TILE_SIZE = 28
LIGHT_ROWS = [3, 7, 11, 15, 19, 23, 27]
LIGHT_COLS = [2, 7, 11, 15, 19]

USER = "admin"
PASS = "admin123"
CHANNEL = "1"  # 101 = cam1 main stream, 102 = cam1 substream
PORT ="554"
SUBTYPE=0

CAM1_IP = "192.168.0.203"
CAM2_IP = "192.168.0.204"
CAM3_IP = "192.168.0.210"
CAM4_IP = "192.168.0.211"

CAM1_URL = f"rtsp://{USER}:{PASS}@{CAM1_IP}:{PORT}/cam/realmonitor?channel={CHANNEL}&subtype={SUBTYPE}"
CAM2_URL = f"rtsp://{USER}:{PASS}@{CAM2_IP}:{PORT}/cam/realmonitor?channel={CHANNEL}&subtype={SUBTYPE}"
CAM3_URL = f"rtsp://{USER}:{PASS}@{CAM3_IP}:{PORT}/cam/realmonitor?channel={CHANNEL}&subtype={SUBTYPE}"
CAM4_URL = f"rtsp://{USER}:{PASS}@{CAM4_IP}:{PORT}/cam/realmonitor?channel={CHANNEL}&subtype={SUBTYPE}"

URLS = [CAM1_URL, CAM2_URL, CAM3_URL, CAM4_URL]
CAM_NAMES = ["cam1", "cam2", "cam3", "cam4"]

FRAME_W = 640
FRAME_H = 360

# load homographies
with open("homographies.json") as f:
    homographies = {cam: np.array(H) for cam, H in json.load(f).items()}

# mqtt
mqttclient = mqtt.Client()
mqttclient.connect("localhost", 1883)
mqttclient.loop_start()

# yolo
model = YOLO("yolov8n.pt")

# open all streams
caps = {cam: cv2.VideoCapture(url) for cam, url in zip(CAM_NAMES, URLS)}

# track which lights are currently ON so we can turn off old ones
active_lights = {}  # cam_name → set of (ri, ci)

def find_nearest_light(tile_col, tile_row):
    best_ri, best_ci, best_dist = 0, 0, float('inf')
    for ri, lr in enumerate(LIGHT_ROWS):
        for ci, lc in enumerate(LIGHT_COLS):
            dist = (tile_row - lr)**2 + (tile_col - lc)**2
            if dist < best_dist:
                best_dist = dist
                best_ri, best_ci = ri, ci
    return best_ri, best_ci

def pixel_to_tile(cam_name, px, py):
    H = homographies[cam_name]
    pt = np.array([[[px, py]]], dtype=np.float32)
    result = cv2.perspectiveTransform(pt, H)
    floor_px = result[0][0][0]
    floor_py = result[0][0][1]
    tile_col = int(floor_px / TILE_SIZE)
    tile_row = int(floor_py / TILE_SIZE)
    return tile_col, tile_row

def build_grid(frames_dict):
    ordered = []
    for cam in CAM_NAMES:
        f = frames_dict.get(cam)
        if f is None:
            f = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
            cv2.putText(f, f"{cam} no feed", (FRAME_W//2-60, FRAME_H//2),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
        ordered.append(cv2.resize(f, (FRAME_W, FRAME_H)))
    top = np.hstack([ordered[0], ordered[1]])
    bot = np.hstack([ordered[2], ordered[3]])
    return np.vstack([top, bot])

print("running — press q to quit")

while True:
    frames_dict = {}

    for cam_name, cap in caps.items():
        ret, frame = cap.read()
        if not ret:
            frames_dict[cam_name] = None
            continue

        H = homographies.get(cam_name)
        if H is None:
            frames_dict[cam_name] = frame
            continue

        results = model(frame, classes=[0], verbose=False)
        detected_lights = set()

        for box in results[0].boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            foot_x = (x1 + x2) // 2
            foot_y = y2

            tile_col, tile_row = pixel_to_tile(cam_name, foot_x, foot_y)

            # clamp to grid bounds
            tile_col = max(0, min(tile_col, 21))
            tile_row = max(0, min(tile_row, 27))

            ri, ci = find_nearest_light(tile_col, tile_row)
            detected_lights.add((ri, ci))

            # draw on frame
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.circle(frame, (foot_x, foot_y), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"tile({tile_col},{tile_row}) light({ri},{ci})",
                        (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)

        # turn off lights no longer needed
        prev_lights = active_lights.get(cam_name, set())
        for ri, ci in prev_lights - detected_lights:
            mqttclient.publish(f"lights/{ri}/{ci}", "OFF")

        # turn on new lights
        for ri, ci in detected_lights - prev_lights:
            mqttclient.publish(f"lights/{ri}/{ci}", "ON")

        active_lights[cam_name] = detected_lights
        frames_dict[cam_name] = frame

    grid = build_grid(frames_dict)
    cv2.imshow("detection", grid)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        # turn off all lights on exit
        for cam_lights in active_lights.values():
            for ri, ci in cam_lights:
                mqttclient.publish(f"lights/{ri}/{ci}", "OFF")
        break

for cap in caps.values():
    cap.release()
mqttclient.loop_stop()
cv2.destroyAllWindows()
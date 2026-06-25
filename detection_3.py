import cv2
import numpy as np
import json
import threading
import time
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
 
# ── tunable constants ─────────────────────────────────────
TARGET_FPS   = 10       # cap display loop to this FPS
YOLO_EVERY   = 3        # run YOLO every N frames
LIGHT_HOLD   = 10.0     # seconds to keep light ON after last detection
 
# ─────────────────────────────────────────────────────────
 
with open("homographies.json") as f:
    homographies = {cam: np.array(H) for cam, H in json.load(f).items()}
 
mqttclient = mqtt.Client()
mqttclient.connect("localhost", 1883)
mqttclient.loop_start()
 
model = YOLO("yolov8n.pt")
 
# ── per-camera latest frame store ────────────────────────
latest_frames = {cam: None for cam in CAM_NAMES}
frame_locks   = {cam: threading.Lock() for cam in CAM_NAMES}
 
def camera_reader(cam_name, url):
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        with frame_locks[cam_name]:
            latest_frames[cam_name] = frame
 
for cam, url in zip(CAM_NAMES, URLS):
    t = threading.Thread(target=camera_reader, args=(cam, url), daemon=True)
    t.start()
 
# ── light hold tracking ───────────────────────────────────
# last_seen[(ri, ci)] = timestamp of last detection for that light
last_seen = {}   # (ri, ci) → float (time.time())
light_on  = {}   # (ri, ci) → bool  (current published state)
 
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
    tile_col = int(result[0][0][0] / TILE_SIZE)
    tile_row = int(result[0][0][1] / TILE_SIZE)
    return tile_col, tile_row
 
def set_light(ri, ci, state):
    """Publish only if state actually changed."""
    key = (ri, ci)
    if light_on.get(key) != state:
        mqttclient.publish(f"lights/{ri}/{ci}", "ON" if state else "OFF")
        light_on[key] = state
 
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
 
frame_counter  = 0
fps_timer      = time.time()
fps_display    = 0
frame_interval = 1.0 / TARGET_FPS  # seconds per frame
 
all_person_positions = []  # published to browser each YOLO cycle
 
while True:
    loop_start = time.time()
    frame_counter += 1
    run_yolo = (frame_counter % YOLO_EVERY == 0)
 
    frames_dict = {}
    person_positions = []  # collect across all cams this cycle
 
    for cam_name in CAM_NAMES:
        with frame_locks[cam_name]:
            frame = latest_frames[cam_name]
 
        if frame is None:
            frames_dict[cam_name] = None
            continue
 
        frame = frame.copy()
 
        if run_yolo:
            H = homographies.get(cam_name)
            if H is None:
                frames_dict[cam_name] = frame
                continue
 
            results = model(frame, classes=[0], verbose=False)
            now = time.time()
 
            for box in results[0].boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                foot_x = (x1 + x2) // 2
                foot_y = y2
 
                tile_col, tile_row = pixel_to_tile(cam_name, foot_x, foot_y)
                tile_col = max(0, min(tile_col, 21))
                tile_row = max(0, min(tile_row, 27))
 
                ri, ci = find_nearest_light(tile_col, tile_row)
 
                # update last seen timestamp for this light
                last_seen[(ri, ci)] = now
 
                # collect for UI dots
                person_positions.append({
                    "tile_col": tile_col,
                    "tile_row": tile_row,
                    "cam": cam_name
                })
 
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.circle(frame, (foot_x, foot_y), 5, (0, 0, 255), -1)
                cv2.putText(frame, f"tile({tile_col},{tile_row}) L({ri},{ci})",
                            (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,255,0), 1)
 
            # publish person positions to browser
            mqttclient.publish("persons/positions", json.dumps(person_positions))
 
            # ── apply LIGHT_HOLD: turn on/off based on last_seen ──
            now = time.time()
            for ri in range(len(LIGHT_ROWS)):
                for ci in range(len(LIGHT_COLS)):
                    key = (ri, ci)
                    last = last_seen.get(key, 0)
                    should_be_on = (now - last) < LIGHT_HOLD
                    set_light(ri, ci, should_be_on)
 
        frames_dict[cam_name] = frame
 
    # ── FPS display ───────────────────────────────────────
    elapsed_fps = time.time() - fps_timer
    if elapsed_fps >= 1.0:
        fps_display = frame_counter / elapsed_fps
        frame_counter = 0
        fps_timer = time.time()
 
    grid = build_grid(frames_dict)
    cv2.putText(grid, f"FPS: {fps_display:.1f}  HOLD: {LIGHT_HOLD}s",
                (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 180), 2)
    cv2.imshow("detection", grid)
 
    if cv2.waitKey(1) & 0xFF == ord('q'):
        # turn off all lights on exit
        for key in light_on:
            if light_on[key]:
                mqttclient.publish(f"lights/{key[0]}/{key[1]}", "OFF")
        break
 
    # ── FPS cap: sleep to hit TARGET_FPS ─────────────────
    elapsed = time.time() - loop_start
    sleep_time = frame_interval - elapsed
    if sleep_time > 0:
        time.sleep(sleep_time)
 
mqttclient.loop_stop()
cv2.destroyAllWindows()
 
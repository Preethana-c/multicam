# Multi-Camera Smart Lighting System — Complete Project Explainer

---

## What This System Does (The Big Picture)

You have 4 IP cameras mounted at the corners of a room (or floor). When a person walks under a light, that light automatically turns ON. When they walk away, the light turns OFF. A browser dashboard shows a top-down map of the room with 35 lights, and you can watch them blink on/off in real time as people move.

**The chain is:**
```
Camera feeds → Python detects people → maps their position to floor tiles → 
publishes MQTT message → Node.js server receives it → pushes to browser via Socket.io → 
canvas redraws with light ON/OFF
```

---

## Folder Structure (what each file is for)

```
multi_cam/
│
├── camera_stream.py       ← test file: connect to ONE camera and view feed
├── camera_stream2.py      ← test file: Hikvision camera URL format
├── camera_stream3.py      ← test file: CP Plus camera URL format
│
├── camera_marking.py      ← SETUP STEP 1: mark points on live camera feeds
│                             (older version, runs all 4 cams one by one)
│
├── light-ui/homography.py ← SETUP STEP 1+2+3: full calibration tool
│                             (newer all-in-one version — use this one)
│
├── python_compute.py      ← SETUP STEP 2: compute homography matrices from points
│
├── apply_homography.py    ← SETUP STEP 3: test file — verify homography works
│
├── detection.py           ← RUNTIME: the main program that runs live
│
├── cam_points.json        ← OUTPUT of setup: pixel coords you clicked on cameras
├── floor_points.json      ← OUTPUT of setup: tile coords you clicked on floor map
├── homographies.json      ← OUTPUT of setup: 4 computed 3×3 matrices
│
├── camera_vid/            ← sample/test video files (not live cameras)
│   ├── 4p-c0.avi  4p-c1.avi  4p-c2.avi  4p-c3.avi
│   └── calibration-4p.txt  ← reference homography matrices from EPFL dataset
│
└── light-ui/              ← the web dashboard
    ├── server.js           ← Node.js server (Express + Socket.io + MQTT client)
    ├── index.html          ← the floor map UI (canvas-based)
    ├── package.json        ← Node dependencies
    └── oldserver.js / oldindex.html  ← earlier versions (ignore these)
```

---

## Part 1 — The Hardware

### Cameras

You have 4 **IP cameras** (CP Plus brand, RTSP protocol).

- Camera 1: `192.168.0.203`
- Camera 2: `192.168.0.204`
- Camera 3: `192.168.0.210`
- Camera 4: `192.168.0.211`

They all share the same login: `admin` / `admin123`.

Each camera streams over **RTSP** (Real-Time Streaming Protocol). The URL looks like:

```
rtsp://admin:admin123@192.168.0.203:554/cam/realmonitor?channel=1&subtype=0
```

- `channel=1` → camera channel 1
- `subtype=0` → main stream (high quality); `subtype=1` would be substream (lower quality, faster)

OpenCV's `cv2.VideoCapture(url)` can open RTSP streams just like a local video file.

### The Room Layout

The room is modeled as a **22 columns × 28 rows grid of tiles**. Each tile is **28 pixels** wide and tall on the floor map canvas.

So the floor map canvas is: `22 × 28 = 616 px wide` and `28 × 28 = 784 px tall`.

There are **35 light fixtures** at fixed tile positions:

```
LIGHT_ROWS = [3, 7, 11, 15, 19, 23, 27]   ← 7 rows of lights
LIGHT_COLS = [2, 7, 11, 15, 19]            ← 5 columns of lights
7 × 5 = 35 lights total
```

The 4 cameras sit in the corners of this grid:
```
Camera positions on grid:
  cam1 → tile (row=0,  col=0)   ← top-left
  cam2 → tile (row=0,  col=21)  ← top-right
  cam3 → tile (row=27, col=0)   ← bottom-left
  cam4 → tile (row=27, col=21)  ← bottom-right
```

---

## Part 2 — The Core Concept: Homography

### The Problem

Each camera sees the room from a different angle. A person standing at the far-left corner looks like they're at pixel `(50, 200)` in camera 1's view. But in camera 3's view that same person might be at pixel `(750, 100)`. They're at the same real-world position, but the pixel coordinates are totally different in each camera.

We need a way to take **any pixel from any camera** and find out **which tile on the floor plan** that pixel corresponds to.

### What is a Homography?

A **homography** is a 3×3 matrix that transforms one 2D plane to another 2D plane. It handles the perspective distortion — the fact that far things look small, near things look big, and the camera is looking at an angle.

Given a homography matrix `H`, you can transform any point `(px, py)` in the camera image to `(fx, fy)` on the floor map:

```
[fx']       [H00 H01 H02]   [px]
[fy']  =    [H10 H11 H12] × [py]
[w' ]       [H20 H21 H22]   [1 ]

fx = fx'/w'
fy = fy'/w'
```

This is projective geometry / perspective transform mathematics.

### How to Compute a Homography

You need **at least 4 point correspondences** — meaning: you need to know that "this pixel in the camera" corresponds to "this tile on the floor map."

The more points you give (5, 6, 7...), the more accurate the result.

OpenCV's `cv2.findHomography(src_points, dst_points, cv2.RANSAC)` computes this matrix automatically. RANSAC is an algorithm that automatically ignores any bad/mismatched points you might have accidentally given it.

---

## Part 3 — The Setup Process (Calibration)

This is the one-time setup you do before the system can work. You run either `camera_marking.py` or `light-ui/homography.py` (they do the same thing, the second one is a newer cleaner version).

### Step 1: Mark Points on Camera Feeds

The script opens a live camera feed window. You click on a recognizable real-world feature — like the corner of a tile, a door frame, a marking on the floor — and type a label (like `p1`, `p2`, etc.).

```python
def click_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        label = input(f"label for ({x},{y})? ").strip()
        if label:
            cam_points[cam_name][label] = (x, y)
```

This saves: **"on cam1, I clicked on feature 'p1' at pixel (580, 113)"**

You do this for 5–7 points per camera, then press `n` to move to the next camera.

After doing all 4 cameras, `cam_points.json` looks like:

```json
{
  "cam1": { "p1": [580, 113], "p2": [548, 77], "p3": [700, 284], ... },
  "cam2": { "p1": [21, 87],   "p2": [216, 98], ... },
  "cam3": { ... },
  "cam4": { ... }
}
```

### Step 2: Mark the Same Points on the Floor Map

After marking each camera, the script opens your browser to `http://localhost:3000?cam=cam1`. The Node server is running and the floor map grid is displayed.

You click on the same real-world features — but now on the top-down floor grid. The browser asks you to type the same label (`p1`, etc.) and sends the tile coordinates back to the Node server via a POST request to `/click`.

```javascript
// in index.html — when you click the canvas
canvas.addEventListener('click', (e) => {
    const tile_col = Math.floor((e.clientX - rect.left) / TILE_SIZE);
    const tile_row = Math.floor((e.clientY - rect.top) / TILE_SIZE);
    const label = prompt(`tile (${tile_col}, ${tile_row}) — label?`);
    
    fetch('/click', {
        method: 'POST',
        body: JSON.stringify({ label, cam: currentCam, tile_col, tile_row })
    });
});
```

The Python script waits for you to press Enter in the terminal. Then it calls `GET /clicks` to retrieve the data from the server.

```python
resp = requests.get("http://localhost:3000/clicks")
clicked = resp.json()
for item in clicked:
    floor_points[cam_name][item["label"]] = (item["tile_col"], item["tile_row"])
```

This saves: **"feature 'p1' is at tile column 18, tile row 6 on the floor map"**

After all cameras, `floor_points.json` looks like:

```json
{
  "cam1": { "p1": [18, 6], "p2": [17, 8], "p3": [17, 4], ... },
  "cam2": { "p1": [0, 27],  "p2": [6, 19], ... },
  ...
}
```

### Step 3: Compute the Homography Matrices

`python_compute.py` reads both JSON files and computes the homography for each camera.

```python
TILE_SIZE = 28  # pixels per tile on the floor map canvas

for cam_name in ["cam1", "cam2", "cam3", "cam4"]:
    cp = cam_points[cam_name]   # pixel coords
    fp = floor_points[cam_name] # tile coords

    # source: pixel coordinates on camera image
    src = np.float32([cp[l] for l in common])

    # destination: pixel coordinates on floor map
    # tile coord × 28 converts tile number to pixel on canvas
    dst = np.float32([
        [fp[l][0] * TILE_SIZE, fp[l][1] * TILE_SIZE]
        for l in common
    ])

    H, status = cv2.findHomography(src, dst, cv2.RANSAC)
    homographies[cam_name] = H.tolist()
```

**Why multiply by TILE_SIZE?**
The floor map canvas uses pixels. Tile column 18 = pixel column `18 × 28 = 504`. So the dst array uses canvas pixel coordinates, not tile numbers directly.

After this, `homographies.json` stores four 3×3 matrices:

```json
{
  "cam1": [[-1.65, 7.06, 681.14], [-0.28, 0.89, 238.18], [-0.002, 0.012, 1.0]],
  "cam2": [...],
  "cam3": [...],
  "cam4": [...]
}
```

These matrices are the core of the whole system. You only compute them once. They don't change unless you move the cameras.

---

## Part 4 — Using the Homography (apply_homography.py)

This is a test/verification script. It shows you how to use the matrix.

```python
def pixel_to_tile(cam_name, px, py):
    H = homographies[cam_name]
    
    # wrap the point in the shape OpenCV expects: [[[px, py]]]
    pt = np.array([[[px, py]]], dtype=np.float32)
    
    # apply the perspective transform
    result = cv2.perspectiveTransform(pt, H)
    
    # result is a canvas pixel on the floor map
    floor_px = result[0][0][0]
    floor_py = result[0][0][1]
    
    # convert canvas pixels back to tile number
    tile_col = int(floor_px / TILE_SIZE)
    tile_row = int(floor_py / TILE_SIZE)
    
    return tile_col, tile_row
```

Test cases — these should produce roughly correct tile numbers:
```python
pixel_to_tile("cam1", 580, 113)  # should be near tile (18, 6)
pixel_to_tile("cam2", 21, 87)    # should be near tile (0, 27)
pixel_to_tile("cam3", 313, 315)  # should be near tile (5, 3)
pixel_to_tile("cam4", 293, 224)  # should be near tile (5, 19)
```

These test inputs are the same `p1` points you clicked during setup, so they should map back to the `p1` tile coordinates you marked on the floor map. If they do, your calibration is correct.

---

## Part 5 — Person Detection (YOLO)

`detection.py` uses **YOLOv8** (a real-time object detection model) to find people in each frame.

```python
model = YOLO("yolov8n.pt")   # 'n' = nano, the smallest/fastest version
```

For each camera frame:
```python
results = model(frame, classes=[0], verbose=False)
# classes=[0] means "only detect class 0" — class 0 in COCO dataset is 'person'
```

For each detected person, YOLO gives you a **bounding box**: `(x1, y1, x2, y2)` — the top-left and bottom-right corner of the rectangle around the person.

To find where the person's **feet** are (which matters for locating them on the floor):
```python
foot_x = (x1 + x2) // 2   # horizontal center of the box
foot_y = y2                 # BOTTOM of the box (where the feet would be)
```

Then convert feet pixel to floor tile:
```python
tile_col, tile_row = pixel_to_tile(cam_name, foot_x, foot_y)
```

Then clamp to valid tile range (don't go outside the 22×28 grid):
```python
tile_col = max(0, min(tile_col, 21))
tile_row = max(0, min(tile_row, 27))
```

---

## Part 6 — Finding the Nearest Light

Not every tile has a light. The lights are only at the 35 specific positions defined by `LIGHT_ROWS` and `LIGHT_COLS`. So once we know which tile a person is on, we find the closest light.

```python
LIGHT_ROWS = [3, 7, 11, 15, 19, 23, 27]
LIGHT_COLS = [2, 7, 11, 15, 19]

def find_nearest_light(tile_col, tile_row):
    best_ri, best_ci, best_dist = 0, 0, float('inf')
    for ri, lr in enumerate(LIGHT_ROWS):
        for ci, lc in enumerate(LIGHT_COLS):
            # squared Euclidean distance (no sqrt needed, just comparing)
            dist = (tile_row - lr)**2 + (tile_col - lc)**2
            if dist < best_dist:
                best_dist = dist
                best_ri, best_ci = ri, ci
    return best_ri, best_ci  # index into LIGHT_ROWS and LIGHT_COLS arrays
```

`ri` = which row of lights (0–6), `ci` = which column of lights (0–4).

---

## Part 7 — MQTT Messaging

**MQTT** is a lightweight publish/subscribe messaging protocol. Think of it like a chat system where:
- **Publishers** send messages to a "topic"
- **Subscribers** listen to topics and receive those messages

You need **Mosquitto** running as the MQTT broker (the message router). Start it with: `mosquitto` or as a service.

### Python side (publisher)

```python
import paho.mqtt.client as mqtt

mqttclient = mqtt.Client()
mqttclient.connect("localhost", 1883)  # 1883 is the default MQTT port
mqttclient.loop_start()               # runs MQTT in background thread
```

When a light should turn on:
```python
mqttclient.publish(f"lights/{ri}/{ci}", "ON")
# e.g. topic = "lights/2/3", payload = "ON"
```

When a light should turn off:
```python
mqttclient.publish(f"lights/{ri}/{ci}", "OFF")
```

### Smart ON/OFF tracking

The system only publishes changes. It tracks which lights were ON last frame and compares to current frame:

```python
active_lights = {}  # cam_name → set of (ri, ci) tuples

prev_lights = active_lights.get(cam_name, set())

# lights that disappeared → turn OFF
for ri, ci in prev_lights - detected_lights:
    mqttclient.publish(f"lights/{ri}/{ci}", "OFF")

# new lights → turn ON
for ri, ci in detected_lights - prev_lights:
    mqttclient.publish(f"lights/{ri}/{ci}", "ON")

active_lights[cam_name] = detected_lights
```

This prevents flooding the broker with redundant messages every frame.

---

## Part 8 — The Node.js Server (server.js)

The server does two jobs:

**Job 1 — During setup:** It's a REST API for collecting floor-map point clicks.

```
POST /click    ← browser sends tile coords + label + cam name
GET  /clicks   ← Python reads back what was clicked
DELETE /clicks ← Python clears the list before each camera's turn
```

**Job 2 — During runtime:** It bridges MQTT → browser in real time.

```javascript
const mqttClient = mqtt.connect('mqtt://localhost:1883');

mqttClient.on('connect', () => {
    mqttClient.subscribe('lights/#');   // subscribe to ALL light topics
});

mqttClient.on('message', (topic, payload) => {
    const parts = topic.split('/');     // "lights/2/3" → ["lights","2","3"]
    const row = parseInt(parts[1]);
    const col = parseInt(parts[2]);
    const state = payload.toString() === 'ON';
    
    io.emit('light_update', { row, col, state });  // push to ALL browser clients
});
```

`socket.io` (io) is a WebSocket library. `io.emit(...)` sends a real-time message to every browser that has the page open. The browser doesn't need to refresh — it updates instantly.

---

## Part 9 — The Browser Dashboard (index.html)

The browser draws a top-down floor map using the HTML5 **Canvas API** (2D drawing in JavaScript).

### Canvas Setup

```javascript
const TILE_COLS = 22;
const TILE_ROWS = 28;
const TILE_SIZE = 28;  // pixels per tile

canvas.width  = TILE_COLS * TILE_SIZE;   // 616px
canvas.height = TILE_ROWS * TILE_SIZE;   // 784px
```

### Light State Storage

```javascript
const lightStates = [];
// lightStates[ri][ci] = true (ON) or false (OFF)
// ri goes 0–6, ci goes 0–4
```

### Drawing

`drawRoom()` is called every time a light changes. It:

1. Fills the background dark blue
2. Colors each non-light tile with a zone color (which light "zone" it belongs to, based on nearest light)
3. Draws a grid of thin lines
4. Draws each light square — yellow+glow if ON, dark green if OFF
5. Draws 4 camera icons at the corners
6. Updates the count display ("3 ACTIVE")

```javascript
if (on) {
    // radial gradient glow effect
    const grd = ctx.createRadialGradient(...);
    grd.addColorStop(0, 'rgba(255,235,80,0.5)');  // yellow center
    grd.addColorStop(1, 'rgba(255,235,80,0)');     // transparent edge
    ctx.fillStyle = grd;
    // fill the glow area
    ctx.fillStyle = '#ffe844';   // solid yellow for the bulb
    ctx.shadowColor = '#ffe844';
    ctx.shadowBlur = 14;         // CSS-style blur glow
    // draw the square
}
```

### Receiving Real-Time Updates

```javascript
const socket = io();  // connects to the Socket.io server automatically

socket.on('light_update', ({ row, col, state }) => {
    lightStates[row][col] = state;  // update state
    drawRoom();                      // redraw everything
});
```

### Floor Point Collection Mode

When the URL has `?cam=cam1`, the canvas switches into calibration mode — you can click on it to mark tile positions. This is only active during setup.

```javascript
const params = new URLSearchParams(window.location.search);
const currentCam = params.get('cam') || null;

if (currentCam) {
    canvas.addEventListener('click', (e) => {
        // ... send tile coords to server
    });
}
```

---

## Part 10 — The Earlier Experiments (camera_stream files)

Before building the full system, you tested connecting to cameras:

- **camera_stream.py** — plain RTSP viewer, one camera, Dahua URL format
- **camera_stream2.py** — Hikvision format: `rtsp://user:pass@ip/Streaming/Channels/101`
- **camera_stream3.py** — CP Plus format: `rtsp://user:pass@ip/cam/realmonitor?channel=1&subtype=0`

These taught you the different RTSP URL formats for different brands. The actual cameras in this project are CP Plus, so that format is what ended up in the final code.

Also: `os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"` — this forces OpenCV to use TCP instead of UDP for the RTSP stream. TCP is more reliable (fewer dropped packets) but slightly slower.

---

## Part 11 — The Sample Dataset (camera_vid/)

The `4p-c0.avi` through `4p-c3.avi` files and `calibration-4p.txt` are from the **EPFL CVLAB multi-camera pedestrian dataset** (a research dataset from 2008). These were used for testing the code before the real cameras were set up. The `.txt` file has pre-computed homography matrices for that dataset, showing the expected format.

---

## How to Run the Full System

### Prerequisites (install once)

```bash
# Python packages
pip install opencv-python numpy paho-mqtt ultralytics requests

# Node packages (inside light-ui/)
cd light-ui
npm install

# Mosquitto MQTT broker (download from mosquitto.org, or)
# On Windows: install as a service
```

### Step A — One-time calibration (only needed once, or after moving cameras)

```bash
# Terminal 1 — start the Node server
cd light-ui
node server.js

# Terminal 2 — run the calibration tool
python light-ui/homography.py
# For each camera:
#   1. Click 5–7 points on the camera feed window
#   2. Browser opens with floor map — click the same points there
#   3. Press Enter in terminal → repeat for next camera

# After all 4 cameras, compute homographies:
python python_compute.py
# → creates homographies.json
```

### Step B — Run the live system

```bash
# Terminal 1 — start Mosquitto broker
mosquitto

# Terminal 2 — start Node server
cd light-ui
node server.js

# Terminal 3 — start Python detection
python detection.py

# Open browser: http://localhost:3000
# Watch lights turn on as people walk under them
```

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SETUP (one-time)                            │
│                                                                     │
│  camera_marking.py / homography.py                                  │
│    │                                                                │
│    ├─ shows live camera feeds                                       │
│    ├─ you click features → saves cam_points.json                   │
│    ├─ opens browser floor map → you click same features             │
│    │  browser → POST /click → server.js → stores clicks            │
│    ├─ Python → GET /clicks → saves floor_points.json               │
│    └─ python_compute.py reads both files → homographies.json       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        RUNTIME (live)                               │
│                                                                     │
│  4 IP Cameras (RTSP)                                                │
│       │                                                             │
│       ▼                                                             │
│  detection.py                                                       │
│   ├─ reads frame from each camera                                   │
│   ├─ runs YOLOv8 → gets bounding boxes                             │
│   ├─ takes foot point (bottom-center of each box)                  │
│   ├─ applies homography matrix → gets tile (col, row)              │
│   ├─ finds nearest light (ri, ci)                                  │
│   └─ publishes MQTT: topic="lights/ri/ci" payload="ON"/"OFF"       │
│                │                                                    │
│                ▼                                                    │
│  Mosquitto MQTT Broker (localhost:1883)                             │
│                │                                                    │
│                ▼                                                    │
│  server.js (subscribes to "lights/#")                               │
│   └─ on message → io.emit('light_update', {row, col, state})       │
│                │                                                    │
│                ▼                                                    │
│  Browser (Socket.io)                                                │
│   └─ socket.on('light_update') → lightStates[row][col] = state     │
│                                → drawRoom() → canvas redraws       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Concepts to Understand

### Why homography and not just a simple scale formula?

Because cameras look at an angle (perspective distortion). Things close to the camera look bigger than things far away. A simple `tile = pixel / scale` would only work if the camera was pointing straight down. The homography matrix captures all of this — rotation, translation, and perspective — in one 3×3 matrix.

### Why RANSAC in findHomography?

When you click points during calibration, you might accidentally click slightly off. RANSAC (Random Sample Consensus) tests many random subsets of your points and finds the homography that works for the most points, ignoring the outliers. `status` is a boolean array — `1` means that point was used (inlier), `0` means it was ignored (outlier).

### Why foot point and not center of bounding box?

The bounding box center would be at chest height. To know where a person is standing on the floor, you want their feet. The homography maps camera pixels to floor positions assuming the point is ON THE FLOOR (ground plane). The bottom-center of the bounding box is the best approximation of the person's foot position.

### Why TILE_SIZE = 28?

It's the number of pixels each tile takes up on the canvas in the browser. The floor map is displayed at 28px per tile. When converting tile coordinates to canvas pixels (for the homography dst points), you multiply by 28. When converting back from canvas pixels to tiles after the transform, you divide by 28.

### Why Socket.io instead of just polling?

Polling (browser repeatedly asks "any updates?") adds latency and is wasteful. Socket.io uses WebSockets — a persistent two-way connection. When a light changes, the server instantly pushes the update to all browsers. No delay, no extra requests.

---

## Files You Would Need to Recreate This Project

1. `detection.py` — the main runtime loop
2. `light-ui/server.js` — Node server
3. `light-ui/index.html` — browser UI
4. `light-ui/package.json` — Node dependencies
5. Either `camera_marking.py` or `light-ui/homography.py` — calibration tool
6. `python_compute.py` — homography computation

After calibration, you also need:
- `cam_points.json`
- `floor_points.json`
- `homographies.json`

And these are installed/downloaded automatically:
- `yolov8n.pt` — YOLO model (downloads on first run)
- Mosquitto broker
- npm packages (`express`, `socket.io`, `mqtt`)
- pip packages (`opencv-python`, `ultralytics`, `paho-mqtt`, `numpy`)

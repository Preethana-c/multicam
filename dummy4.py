import paho.mqtt.client as mqtt
import cv2
import numpy as np

# room config — must match index.html
TILE_COLS = 22
TILE_ROWS = 28
TILE_SIZE = 28   # pixels per tile on the click map

CANVAS_W = TILE_COLS * TILE_SIZE
CANVAS_H = TILE_ROWS * TILE_SIZE

# exact light tile positions
LIGHT_COLS = [2, 7, 11, 15, 19]
LIGHT_ROWS = [3, 7, 11, 15, 19, 23, 27]

# camera tile positions
CAMERAS = [(0, 0), (0, 21), (27, 0), (27, 21)]

# mqtt
client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()

person_lights = {}
current_person = 1

colors = {1: (0, 255, 255), 2: (255, 0, 255), 3: (0, 165, 255), 4: (255, 255, 0)}

def find_nearest_light(tile_c, tile_r):
    # find closest light row and col
    nearest_ri = min(range(len(LIGHT_ROWS)), key=lambda i: abs(LIGHT_ROWS[i] - tile_r))
    nearest_ci = min(range(len(LIGHT_COLS)), key=lambda i: abs(LIGHT_COLS[i] - tile_c))
    return nearest_ri, nearest_ci

def draw_map(person_positions):
    canvas = np.zeros((CANVAS_H, CANVAS_W, 3), dtype=np.uint8)

    # tile background
    for r in range(TILE_ROWS):
        for c in range(TILE_COLS):
            x = c * TILE_SIZE
            y = r * TILE_SIZE
            is_light = r in LIGHT_ROWS and c in LIGHT_COLS
            color = (30, 30, 30) if not is_light else (40, 40, 0)
            cv2.rectangle(canvas, (x+1, y+1),
                         (x+TILE_SIZE-1, y+TILE_SIZE-1), color, -1)

    # grid lines
    for r in range(TILE_ROWS + 1):
        cv2.line(canvas, (0, r*TILE_SIZE), (CANVAS_W, r*TILE_SIZE), (45, 35, 0), 1)
    for c in range(TILE_COLS + 1):
        cv2.line(canvas, (c*TILE_SIZE, 0), (c*TILE_SIZE, CANVAS_H), (45, 35, 0), 1)

    # lights
    for r in LIGHT_ROWS:
        for c in LIGHT_COLS:
            x = c * TILE_SIZE
            y = r * TILE_SIZE
            pad = 3
            cv2.rectangle(canvas, (x+pad, y+pad),
                         (x+TILE_SIZE-pad, y+TILE_SIZE-pad), (0, 200, 200), -1)

    # cameras
    for (cr, cc) in CAMERAS:
        x = cc * TILE_SIZE + TILE_SIZE // 2
        y = cr * TILE_SIZE + TILE_SIZE // 2
        cv2.circle(canvas, (x, y), TILE_SIZE//2 - 2, (255, 100, 50), -1)

    # persons
    for pid, (pr, pc) in person_positions.items():
        x = pc * TILE_SIZE + TILE_SIZE // 2
        y = pr * TILE_SIZE + TILE_SIZE // 2
        color = colors.get(pid, (255, 255, 255))
        cv2.circle(canvas, (x, y), TILE_SIZE//2 - 2, color, -1)
        cv2.putText(canvas, f"P{pid}", (x-8, y+4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 0), 1)

    # current person label
    cv2.putText(canvas, f"Person {current_person} active (1-4 switch, c clear, q quit)",
                (5, CANVAS_H - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)

    return canvas

person_positions = {}

def click_callback(event, x, y, flags, param):
    global current_person
    if event == cv2.EVENT_LBUTTONDOWN:
        # convert pixel to tile
        tile_c = x // TILE_SIZE
        tile_r = y // TILE_SIZE

        # find nearest light
        ri, ci = find_nearest_light(tile_c, tile_r)

        # turn off previous
        if current_person in person_lights:
            pr, pc = person_lights[current_person]
            client.publish(f"lights/{pr}/{pc}", "OFF")

        # turn on new
        client.publish(f"lights/{ri}/{ci}", "ON")
        person_lights[current_person] = (ri, ci)
        person_positions[current_person] = (tile_r, tile_c)

        print(f"Person {current_person} → Light grid ({ri},{ci}) ON")

cv2.namedWindow("Floor Map")
cv2.setMouseCallback("Floor Map", click_callback)

print("Click anywhere on the map — snaps to nearest light")
print("Press 1-4 to switch person, c to clear, q to quit")

while True:
    frame = draw_map(person_positions)
    cv2.imshow("Floor Map", frame)
    key = cv2.waitKey(100) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('1'):
        current_person = 1
    elif key == ord('2'):
        current_person = 2
    elif key == ord('3'):
        current_person = 3
    elif key == ord('4'):
        current_person = 4
    elif key == ord('c'):
        for r in range(len(LIGHT_ROWS)):
            for c in range(len(LIGHT_COLS)):
                client.publish(f"lights/{r}/{c}", "OFF")
        person_lights.clear()
        person_positions.clear()

client.loop_stop()
cv2.destroyAllWindows()
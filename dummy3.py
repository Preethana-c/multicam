import paho.mqtt.client as mqtt
import cv2
import numpy as np

ROWS = 6
COLS = 6
ROOM_W = 600
ROOM_H = 600
CELL_W = ROOM_W / COLS
CELL_H = ROOM_H / ROWS
CELL_PIXELS = 100

person_lights = {}
current_person = 1

client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()

def get_light(x, y):
    col = int(x // CELL_W)
    row = int(y // CELL_H)
    col = min(col, COLS - 1)
    row = min(row, ROWS - 1)
    return row, col

def draw_floor(person_positions):
    h = ROWS * CELL_PIXELS
    w = COLS * CELL_PIXELS
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    for r in range(ROWS + 1):
        cv2.line(canvas, (0, r * CELL_PIXELS), (w, r * CELL_PIXELS), (50, 50, 50), 1)
    for c in range(COLS + 1):
        cv2.line(canvas, (c * CELL_PIXELS, 0), (c * CELL_PIXELS, h), (50, 50, 50), 1)

    for r in range(ROWS):
        for c in range(COLS):
            cx = c * CELL_PIXELS + CELL_PIXELS // 2
            cy = r * CELL_PIXELS + CELL_PIXELS // 2
            cv2.putText(canvas, f"{r},{c}", (cx - 15, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 80, 80), 1)

    colors = {1: (0, 255, 255), 2: (255, 0, 255), 3: (0, 165, 255), 4: (255, 255, 0)}
    for pid, (px, py) in person_positions.items():
        color = colors.get(pid, (255, 255, 255))
        screen_x = int(px / ROOM_W * (COLS * CELL_PIXELS))
        screen_y = int(py / ROOM_H * (ROWS * CELL_PIXELS))
        cv2.circle(canvas, (screen_x, screen_y), 12, color, -1)
        cv2.putText(canvas, f"P{pid}", (screen_x - 8, screen_y + 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    cv2.putText(canvas, f"Person {current_person} active (press 1-4 to switch)",
                (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)
    return canvas

person_positions = {}

def click_callback(event, x, y, flags, param):
    global current_person
    if event == cv2.EVENT_LBUTTONDOWN:
        room_x = x / (COLS * CELL_PIXELS) * ROOM_W
        room_y = y / (ROWS * CELL_PIXELS) * ROOM_H

        if current_person in person_lights:
            pr, pc = person_lights[current_person]
            client.publish(f"lights/{pr}/{pc}", "OFF")

        row, col = get_light(room_x, room_y)
        client.publish(f"lights/{row}/{col}", "ON")
        person_lights[current_person] = (row, col)
        person_positions[current_person] = (room_x, room_y)
        print(f"Person {current_person} → Light ({row},{col}) ON")

cv2.namedWindow("Floor Map - Click to place person")
cv2.setMouseCallback("Floor Map - Click to place person", click_callback)

print("Click floor map to place person")
print("Press 1-4 to switch person, c to clear, q to quit")

while True:
    frame = draw_floor(person_positions)
    cv2.imshow("Floor Map - Click to place person", frame)
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
        for r in range(ROWS):
            for c in range(COLS):
                client.publish(f"lights/{r}/{c}", "OFF")
        person_lights.clear()
        person_positions.clear()

client.loop_stop()
cv2.destroyAllWindows()
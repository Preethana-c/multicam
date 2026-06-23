import paho.mqtt.client as mqtt
import cv2
import numpy as np

ROWS = 6
COLS = 6
CELL = 100
LIGHT_SIZE = 40

light_states = [[False] * COLS for _ in range(ROWS)]

def draw_grid(states):
    h = ROWS * CELL
    w = COLS * CELL
    canvas = np.zeros((h, w, 3), dtype=np.uint8)

    for r in range(ROWS):
        for c in range(COLS):
            cx = c * CELL + CELL // 2
            cy = r * CELL + CELL // 2
            color = (0, 255, 0) if states[r][c] else (0, 80, 80)
            top_left = (cx - LIGHT_SIZE//2, cy - LIGHT_SIZE//2)
            bot_right = (cx + LIGHT_SIZE//2, cy + LIGHT_SIZE//2)
            cv2.rectangle(canvas, top_left, bot_right, color, -1)
            cv2.putText(canvas, f"{r},{c}", (cx - 15, cy + 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255,255,255), 1)
    return canvas

def on_connect(client, userdata, flags, rc):
    print("Connected to broker")
    client.subscribe("lights/#")

def on_message(client, userdata, msg):
    parts = msg.topic.split("/")
    row = int(parts[1])
    col = int(parts[2])
    state = msg.payload.decode() == "ON"
    light_states[row][col] = state
    print(f"Light ({row},{col}) → {'ON' if state else 'OFF'}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect("localhost", 1883)
client.loop_start()

while True:
    frame = draw_grid(light_states)
    cv2.imshow("Light Grid", frame)
    if cv2.waitKey(100) & 0xFF == ord('q'):
        break

client.loop_stop()
cv2.destroyAllWindows()
import paho.mqtt.client as mqtt

# --- Grid config (must match light_ui.py) ---
ROWS = 6
COLS = 6

# Real room dimensions in cm
ROOM_W = 600   # adjust to your room width
ROOM_H = 600   # adjust to your room height

CELL_W = ROOM_W / COLS   # 100cm per cell
CELL_H = ROOM_H / ROWS   # 100cm per cell

def get_light(person_x, person_y):
    col = int(person_x // CELL_W)
    row = int(person_y // CELL_H)
    col = min(col, COLS - 1)
    row = min(row, ROWS - 1)
    return row, col

# --- MQTT setup ---
client = mqtt.Client()
client.connect("localhost", 1883)
client.loop_start()

print("Enter person position as: x y")
print("Example: 150 300")
print("Type 'clear' to turn all lights off")
print("Type 'q' to quit")

prev_light = None

while True:
    user_input = input("> ")

    if user_input == 'q':
        break

    if user_input == 'clear':
        for r in range(ROWS):
            for c in range(COLS):
                client.publish(f"lights/{r}/{c}", "OFF")
        print("All lights off")
        continue

    try:
        x, y = map(float, user_input.split())

        # turn off previous light
        if prev_light:
            pr, pc = prev_light
            client.publish(f"lights/{pr}/{pc}", "OFF")

        # find which light this position maps to
        row, col = get_light(x, y)

        # turn on new light
        client.publish(f"lights/{row}/{col}", "ON")
        print(f"Person at ({x}, {y}) → Light ({row}, {col}) ON")

        prev_light = (row, col)

    except:
        print("Invalid input. Try: 150 300")

client.loop_stop()
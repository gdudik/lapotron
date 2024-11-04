import RPi.GPIO as GPIO
import requests
import json
import time
import os
import socket


# Define your server IP address and port
SERVER_IP = '192.168.1.44'
SERVER_PORT_PIN21 = 5201
SERVER_PORT_PIN23 = 5201
ACTION_LIGHT = 11

# Define keypad layout
KEYPAD = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
    ['*', 0, '#']
]

# Define GPIO pins for rows and columns
ROWS = [16, 18, 22, 24]
COLS = [32, 36, 38]

# Function to check for network connectivity
def is_connected():
    try:
        # Try to connect to a reliable external server (Google DNS)
        socket.create_connection(("192.168.1.1", 53))
        return True
    except OSError:
        return False

# Wait until the network is up
print("Waiting for network connection...")
while not is_connected():
    time.sleep(1)
print("Network connection established.")

# Initialize GPIO
GPIO.setmode(GPIO.BOARD)

# Set up pin 3 as output
GPIO.setup(ACTION_LIGHT, GPIO.OUT)

# Set up pin 21 as input
GPIO.setup(21, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up pin 23 as input
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_UP)

for row_pin in ROWS:
    GPIO.setup(row_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Set up column pins as outputs
for col_pin in COLS:
    GPIO.setup(col_pin, GPIO.OUT)
    GPIO.output(col_pin, GPIO.HIGH)


def get_key():
    key = None

    # Scan each column
    for col_num, col_pin in enumerate(COLS):
        GPIO.output(col_pin, GPIO.LOW)

        # Check each row
        for row_num, row_pin in enumerate(ROWS):
            if GPIO.input(row_pin) == GPIO.LOW:
                key = KEYPAD[row_num][col_num]

                # Wait for key release
                while GPIO.input(row_pin) == GPIO.LOW:
                    time.sleep(0.05)

        GPIO.output(col_pin, GPIO.HIGH)
    return key

def send_http_request(pin, command):
    url = f"http://{SERVER_IP}:{pin}"
    headers = {'Content-Type': 'application/json'}
    data = command
    json_data = json.dumps(data)  # Convert data to JSON string
    try:
        response = requests.post(url, headers=headers, data=json_data)
        print(f"HTTP request sent to {url}, response: {response.status_code}")
    except requests.RequestException as e:
        print(f"Request failed: {e}")

def handle_pin21(channel):
    blink_high(ACTION_LIGHT)
    print("handle_pin21 triggered")
    send_http_request(SERVER_PORT_PIN21, {"action": "activate_grid_cell", "grid": "grid", "cell": [11, 2]})
    print("Pin 21 pulled LOW")

def handle_pin23(channel):
    blink_high(ACTION_LIGHT)
    print("handle_pin23 triggered")
    send_http_request(SERVER_PORT_PIN23, {"action": "activate_grid_cell", "grid": "grid", "cell": [11, 1]})
    print("Pin 23 pulled LOW")

def blink_high(pin):
    GPIO.output(pin, GPIO.HIGH)
    time.sleep(0.15)
    GPIO.output(pin, GPIO.LOW)


def send_TCP(message, retries=3, delay=2):
    attempt = 0
    while attempt < retries:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('192.168.1.44', 3636))
            s.send(message)
            return
        except socket.error as e:
            attempt += 1
            for _ in range(2):
                          blink_high(ACTION_LIGHT)
                          time.sleep(.10)
            time.sleep(delay)
        finally:
            s.close()

    
    

try:
    # Add event detection for both pins with debounce
    GPIO.add_event_detect(21, GPIO.FALLING, callback=handle_pin21, bouncetime=500)
    GPIO.add_event_detect(23, GPIO.FALLING, callback=handle_pin23, bouncetime=500)
    
    recording = False
    recorded_keys = []
    key_sequence = ''

    while True:
        pressed_key = get_key()

        if pressed_key is not None:
            blink_high(ACTION_LIGHT)
            if pressed_key == '*':
                recording = True
                recorded_keys = []
                key_sequence = ''
            elif pressed_key == '#':
                if recording:
                    key_sequence = ''.join(map(str, recorded_keys))
                    print("Recorded keys:", key_sequence)
                    recording = False
                    if key_sequence == '9999':
                        for _ in range(5):
                          blink_high(ACTION_LIGHT)
                          time.sleep(.10)
                        print("Magic sequence detected! Shutting down...")
                        os.system("sudo shutdown -h now")
                    else: 
                        send_TCP((f'Lap_Count={key_sequence}\n'.encode()))

            elif recording:
                recorded_keys.append(pressed_key)
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Script interrupted by user")
finally:
    GPIO.cleanup()  # Ensure GPIO cleanup on exit
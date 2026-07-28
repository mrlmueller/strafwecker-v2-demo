"""
This MicroPython script runs on the ESP32.

It listens for HTTP POSTs to /trigger, which should include JSON like:
{
    "duration": 300,
    "alarm_id": 123,
    "log_id": 45
}

Then it starts a timer and uses an RGB LED to indicate states:
- Cyan while waiting for button press
- If button is pressed, it sends status to Pi: {status="button_pressed", alarm_id, log_id, time_to_button_sec=...}
- If user never presses the button before time expires, it sends {status="no_press", alarm_id, log_id} to Pi,
  calls the Cloud Function, and lights red for 10 minutes (which can still be interrupted by button press).
"""

import network
import uasyncio as asyncio
import ujson
import urequests
import time
from machine import Pin, PWM
import config
import _thread

# ------------------------------------------------------------
# Configuration Constants
# ------------------------------------------------------------
PI_URL = config.PI_URL  # e.g. "http://192.168.0.10:5000/esp_callback"
CLOUD_RUN_URL = config.CLOUD_RUN_URL
API_KEY = config.API_KEY
SECRET_KEY = config.SECRET_KEY

# ------------------------------------------------------------
# RGB LED Setup using PWM
# ------------------------------------------------------------
RED_PIN = 2
GREEN_PIN = 0
BLUE_PIN = 1

COLOR_OFF = (0, 0, 0)
COLOR_CYAN = (0, 1023, 1023)
COLOR_YELLOW = (1023, 1023, 0)
COLOR_GREEN = (0, 1023, 0)
COLOR_MAGENTA = (1023, 0, 1023)
COLOR_RED = (1023, 0, 0)


class RGBLED:
    def __init__(self, red_pin, green_pin, blue_pin, freq=1000):
        self.red = PWM(Pin(red_pin), freq=freq, duty=0)
        self.green = PWM(Pin(green_pin), freq=freq, duty=0)
        self.blue = PWM(Pin(blue_pin), freq=freq, duty=0)

    def set_color(self, r, g, b):
        self.red.duty(r)
        self.green.duty(g)
        self.blue.duty(b)

    def off(self):
        self.set_color(*COLOR_OFF)


rgb = RGBLED(RED_PIN, GREEN_PIN, BLUE_PIN)

# ------------------------------------------------------------
# Button Setup (pin 19)
# ------------------------------------------------------------
BUTTON = Pin(3, Pin.IN, Pin.PULL_UP)
button_pressed = False


def button_callback(pin):
    global button_pressed
    button_pressed = True


BUTTON.irq(trigger=Pin.IRQ_FALLING, handler=button_callback)


# ------------------------------------------------------------
# Network Connection
# ------------------------------------------------------------
def connect_to_network(ssid, password):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)
    max_wait = 15
    wait_time = 0
    while not wlan.isconnected() and wait_time < max_wait:
        print("Connecting to WLAN...")
        time.sleep(1)
        wait_time += 1
    if wlan.isconnected():
        print("Connected! IP Address:", wlan.ifconfig()[0])
    else:
        print("Failed to connect to WLAN.")
    return wlan


# ------------------------------------------------------------
# Global variables to store alarm_id/log_id from /trigger
# ------------------------------------------------------------
alarm_id_global = None
log_id_global = None


# ------------------------------------------------------------
# External Requests to Pi
# ------------------------------------------------------------
def send_status_to_pi(payload, retry=3):
    """
    Sends a JSON payload to the Pi's esp_callback endpoint
    (PI_URL) with the given API_KEY. Returns True if success, else False.
    """
    for attempt in range(retry):
        try:
            print(
                "Attempt {}: Sending payload {} to {}".format(
                    attempt + 1, payload, PI_URL
                )
            )
            headers = {
                "Content-Type": "application/json", 
                "X-API-KEY": API_KEY,
                # Make sure the connection is clearly from a proper client
                "User-Agent": "ESP32-MicroPython/1.0"
            }
            # Explicitly stringify the JSON to ensure proper formatting
            data = ujson.dumps(payload)
            print(f"Sending data: {data}")
            response = urequests.post(
                PI_URL, data=data, headers=headers
            )
            # Print both status code and response body
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            response.close()
            print("Payload sent successfully.")
            return True
        except Exception as e:
            print("Error sending to Pi: {}".format(e))
            if attempt < retry - 1:
                print("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("Max retries reached. Aborting.")
                return False


def call_cloud_function(retry=3):
    """
    Calls your Cloud Function if the user does not press the button.
    Returns True if success, else False.
    """
    for attempt in range(retry):
        try:
            print(
                "Sending request to Cloud Function (Attempt {})...".format(attempt + 1)
            )
            headers = {
                "X-Secret-Key": SECRET_KEY,
                "Content-Type": "application/json",
                "Content-Length": "0",  # Avoid 411 errors
            }
            response = urequests.post(CLOUD_RUN_URL, headers=headers)
            raw_text = response.text
            print("Cloud Function Response:", raw_text)
            response.close()
            return True
        except Exception as e:
            print("Cloud Function request failed: {}".format(e))
            if attempt < retry - 1:
                print("Retrying in 2 seconds...")
                time.sleep(2)
            else:
                print("Max retries reached. Request failed.")
                return False


# ------------------------------------------------------------
# Async LED Blinking Helpers
# ------------------------------------------------------------
async def blink_led(color, on_time, off_time, stop_event):
    """
    Repeatedly blink an LED color until stop_event is set.
    """
    while not stop_event.is_set():
        rgb.set_color(*color)
        await asyncio.sleep(on_time)
        rgb.off()
        await asyncio.sleep(off_time)


# ------------------------------------------------------------
# Main Timer Flow
# ------------------------------------------------------------
async def start_timer(duration=300):
    """
    The main timer flow after /trigger is called.
    - Sets LED to Cyan
    - Waits for button press or time expiry
    - If pressed, we notify the Pi: {status="button_pressed", alarm_id, log_id, time_to_button_sec=...}
    - If not pressed, we call Pi {status="no_press"}, call the Cloud Function, then show RED for 10 min
      (still can be interrupted by button press).
    """
    global button_pressed, alarm_id_global, log_id_global

    button_pressed = False
    rgb.set_color(*COLOR_CYAN)
    print("Timer started ({} seconds)...".format(duration))
    start_time = time.time()
    
    # Send confirmation that ESP32 received the trigger and button timer started
    if alarm_id_global is not None and log_id_global is not None:
        confirmation_payload = {
            "status": "timer_started",
            "alarm_id": alarm_id_global,
            "log_id": log_id_global,
            "start_time": start_time
        }
        _thread.start_new_thread(send_status_to_pi, (confirmation_payload,))

    # 1) Wait up to 'duration' seconds for the button press
    for sec in range(duration):
        if button_pressed:
            elapsed = int(time.time() - start_time)
            print(
                "Button pressed! Timer is stopping. Elapsed time: {} seconds".format(
                    elapsed
                )
            )

            # Send "button_pressed" to Pi with alarm_id/log_id/time
            if alarm_id_global is not None and log_id_global is not None:
                payload = {
                    "status": "button_pressed",
                    "alarm_id": alarm_id_global,
                    "log_id": log_id_global,
                    "time_to_button_sec": elapsed,
                }
                _thread.start_new_thread(
                    send_status_to_pi, (payload,)
                )  # Send in background

            rgb.set_color(*COLOR_GREEN)  # Indicate success
            await asyncio.sleep(2)
            rgb.off()
            return "Button pressed -> Timer stopped"

        remaining = duration - sec
        print("Time remaining: {} s".format(remaining))
        await asyncio.sleep(1)

    # 2) No button press
    print("Timer expired! No button press detected.")

    # Send "no_press" to Pi, call Cloud Function
    if alarm_id_global is not None and log_id_global is not None:
        payload = {
            "status": "no_press",
            "alarm_id": alarm_id_global,
            "log_id": log_id_global,
        }
        # Blink Red fast while we send
        stop_blink = asyncio.Event()
        blink_task = asyncio.create_task(blink_led(COLOR_RED, 0.2, 0.2, stop_blink))

        # We'll do both calls in a separate thread for no-press scenario
        def no_press_requests():
            send_status_to_pi(payload)
            call_cloud_function()

        _thread.start_new_thread(no_press_requests, ())

        # Wait for a bit (2-3 seconds) to let the requests finish
        await asyncio.sleep(3)
        stop_blink.set()
        await blink_task

    # 3) Turn on solid Red for 10 minutes (unless button pressed again)
    rgb.set_color(*COLOR_RED)
    print("Solid Red LED for 10 minutes. Press button to deactivate.")
    red_start = time.time()
    while time.time() - red_start < 600:
        if button_pressed:
            print("Button pressed during red LED phase! Turning off.")
            rgb.off()
            # Optionally send Pi "button_pressed_during_red" or something if needed
            return "Button pressed -> Red phase stopped"
        await asyncio.sleep(1)

    # 4) Time up, turn off LED
    print("10 minutes expired. Red LED turning off automatically.")
    rgb.off()
    return "Red LED turned off after timeout."


# ------------------------------------------------------------
# HTTP Server Handlers
# ------------------------------------------------------------
async def handle_request(reader, writer):
    global alarm_id_global, log_id_global

    try:
        request = await reader.read(1024)
        req_str = request.decode("utf-8")
        print("HTTP Request received:")
        print(req_str)

        if "POST /trigger" in req_str:
            # Parse JSON body to get duration, alarm_id, log_id
            duration = 300
            parts = req_str.split("\r\n\r\n", 1)
            if len(parts) > 1:
                try:
                    data = ujson.loads(parts[1])
                    duration = data.get("duration", 300)
                    alarm_id_global = data.get("alarm_id")
                    log_id_global = data.get("log_id")
                except Exception as e:
                    print("Failed to parse JSON body: {}".format(e))

            # Send immediate HTTP response
            response_body = ujson.dumps({"message": "ESP32 received trigger"})
            response_headers = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                f"Content-Length: {len(response_body)}\r\n"
                "Connection: close\r\n\r\n"
            )
            await writer.awrite(response_headers + response_body)
            await writer.aclose()

            # Start the timer in the background
            asyncio.create_task(start_timer(duration))
        else:
            # Not a recognized endpoint
            resp = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n"
                "Connection: close\r\n\r\n"
                "Page not found."
            )
            await writer.awrite(resp)
            await writer.aclose()

    except Exception as e:
        print("Exception in handle_request: {}".format(e))
        try:
            error_resp = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 17\r\n"
                "Connection: close\r\n\r\n"
                "Error occurred."
            )
            await writer.awrite(error_resp)
            await writer.aclose()
        except:
            pass


async def start_server():
    server = await asyncio.start_server(handle_request, "0.0.0.0", 80)
    print("HTTP Server is running...")
    while True:
        await asyncio.sleep(1)


# ------------------------------------------------------------
# Main Function
# ------------------------------------------------------------
def main():
    from machine import WDT
    wdt = WDT(timeout=30000)  # 30 second watchdog

    ssid = config.SSID
    password = config.WLAN_PASSWORD
    connect_to_network(ssid, password)
    wdt.feed()

    async def run_with_watchdog():
        server_task = asyncio.create_task(start_server())
        while True:
            wdt.feed()
            await asyncio.sleep(10)

    try:
        asyncio.run(run_with_watchdog())
    except Exception as e:
        print("Exception in main server loop: {}".format(e))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Program terminated by user.")


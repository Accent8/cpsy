import time

from gpiozero import Device, Motor, Button
from gpiozero.pins.pigpio import PiGPIOFactory
import board
import adafruit_tcs34725
import adafruit_ssd1306
from PIL import Image, ImageDraw

Device.pin_factory = PiGPIOFactory()

motor_a = Motor(forward=12, backward=18)
motor_b = Motor(forward=13, backward=25)

button = Button(17, pull_up=True)

i2c = board.I2C()
color_sensor = adafruit_tcs34725.TCS34725(i2c)
color_sensor.integration_time = 24
color_sensor.gain = 16

oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

SPEED = 0.15
MIN_RATIO = 0.15
MAX_RATIO = 0.85
running = False

def show(line1, line2="", line3=""):
    oled.fill(0)
    image = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), line1, fill=255)
    draw.text((0, 20), line2, fill=255)
    draw.text((0, 40), line3, fill=255)
    oled.image(image)
    oled.show()

def read_rgb():
    return color_sensor.color_rgb_bytes

def wait_for_press():
    button.wait_for_press()
    time.sleep(0.3)

def toggle_running():
    global running
    running = not running
    if not running:
        motor_a.stop()
        motor_b.stop()
        show("Paused", "Press to resume")
    else:
        show("Running...")

# --- Calibration ---
show("CALIBRATION", "Place on WHITE", "Press button")
wait_for_press()
white_r, white_g, white_b = 0, 0, 0
for i in range(10):
    r, g, b = read_rgb()
    white_r += r
    white_g += g
    white_b += b
    time.sleep(0.05)
white_r //= 10
white_g //= 10
white_b //= 10

show("W: {},{},{}".format(white_r, white_g, white_b),
     "Place on BLACK", "Press button")

wait_for_press()

black_r, black_g, black_b = 0, 0, 0
for i in range(10):
    r, g, b = read_rgb()
    black_r += r
    black_g += g
    black_b += b
    time.sleep(0.05)
black_r //= 10
black_g //= 10
black_b //= 10

black_avg = (black_r + black_g + black_b) // 3
white_avg = (white_r + white_g + white_b) // 3
threshold = (black_avg + white_avg) // 2

show("B:{} W:{}".format(black_avg, white_avg),
     "Thr: {}".format(threshold),
     "Press to start")
wait_for_press()

turning_left = True
on_line = False

button.when_pressed = lambda: toggle_running()
running = True
show("Running...")

try:
    while True:
        if not running:
            time.sleep(0.1)
            continue

        r, g, b = read_rgb()
        avg = (r + g + b) // 3
        was_on_line = on_line
        on_line = avg < threshold

        if was_on_line and not on_line:
            turning_left = not turning_left

        if white_avg > black_avg:
            error = abs(avg - threshold) / (white_avg - black_avg)
        else:
            error = 1.0
        error = min(error, 1.0)

        ratio = MAX_RATIO - error * (MAX_RATIO - MIN_RATIO)

        if turning_left:
            motor_a.forward(SPEED * ratio)
            motor_b.forward(SPEED)
        else:
            motor_a.forward(SPEED)
            motor_b.forward(SPEED * ratio)

except KeyboardInterrupt:
    motor_a.stop()
    motor_b.stop()
    show("Stopped")
    print("Stopped")

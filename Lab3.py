from gpiozero import LED
from time import sleep
import time
import math
import board
import adafruit_icm20x

# Change these two numbers to whatever GPIO pins your two LEDs are wired to
north_led = LED(17)
level_led = LED(27)

i2c = board.I2C()
icm = adafruit_icm20x.ICM20948(i2c)

# Give north and level a little wiggle room
NORTH_TOLERANCE = 15
LEVEL_TOLERANCE = 10

# Calibrate the compass by spinning it and record the smallest
# and largest readings, without this the compass just jumps
# around randomly

print("Rotate the sensor in a circle now")

mx, my, mz = icm.magnetic
mag_min = [mx, my, mz]
mag_max = [mx, my, mz]

calibrate_start = time.time()
while time.time() - calibrate_start < 8:
    mx, my, mz = icm.magnetic
    reading = [mx, my, mz]
    for i in range(3):
        if reading[i] < mag_min[i]:
            mag_min[i] = reading[i]
        if reading[i] > mag_max[i]:
            mag_max[i] = reading[i]
    sleep(0.05)

print("Compass calibrated\n")

# This is to calibrate the level, so just start by keeping
# the sensor level on the table and then base the rest
# of the level of this number

print("Hold the sensor flat")

sum_x = sum_y = sum_z = 0
num_samples = 20
for i in range(num_samples):
    ax, ay, az = icm.acceleration
    sum_x += ax
    sum_y += ay
    sum_z += az
    sleep(0.05)

level_x = sum_x / num_samples
level_y = sum_y / num_samples
level_z = sum_z / num_samples

print("Calibration Complete\n")
# ---- Step 3: main loop ----

print("Running. Ctrl+C to stop\n")

while True:
    # --- Compass heading ---
    mx, my, mz = icm.magnetic
    reading = [mx, my, mz]
    calibrated = [0, 0, 0]
    for i in range(3):
        span = mag_max[i] - mag_min[i]
        if span == 0:
            calibrated[i] = 0
        else:
            calibrated[i] = (reading[i] - mag_min[i]) / span - 0.5

    heading = math.degrees(math.atan2(calibrated[1], calibrated[0]))
    if heading < 0:
        heading += 360

    facing_north = heading <= NORTH_TOLERANCE or heading >= (360 - NORTH_TOLERANCE)

    ax, ay, az = icm.acceleration

    dot_product = (ax * level_x) + (ay * level_y) + (az * level_z)
    current_size = math.sqrt(ax**2 + ay**2 + az**2)
    reference_size = math.sqrt(level_x**2 + level_y**2 + level_z**2)

    cos_of_angle = dot_product / (current_size * reference_size)
    cos_of_angle = max(-1, min(1, cos_of_angle))
    tilt = math.degrees(math.acos(cos_of_angle))

    is_level = tilt <= LEVEL_TOLERANCE

    # --- LEDs ---
    north_led.value = facing_north
    level_led.value = is_level

    print(f"Heading: {heading:6.1f} (north={facing_north})   Tilt: {tilt:5.1f} (level={is_level})")

    sleep(0.2)
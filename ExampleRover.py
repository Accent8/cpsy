import time
import board
import adafruit_tcs34725
from simple_pid import PID
from gpiozero import Robot, Motor, DigitalOutputDevice
from encoder import Encoders

# ---------------------------------------------------------------
# Settings
# ---------------------------------------------------------------
SPEED = 400        # Target wheel speed in encoder steps per second (692 = 1 rotation)
TH = 3000          # Threshold for finding the line, c
KP = 0.0008        # Wheel PID gains
KI = 0.002
KD = 0.0

# ---------------------------------------------------------------
# Hardware setup
# ---------------------------------------------------------------
sensor = adafruit_tcs34725.TCS34725(board.I2C())
sensor.integration_time = 24   # ms, short = faster loop
sensor.gain = 4

slp = DigitalOutputDevice('GPIO26')
slp.on()
robot = Robot(right=Motor('GPIO12', 'GPIO18'), left=Motor('GPIO19', 'GPIO13'))
enc = Encoders(left_pins=(5, 6), right_pins=(27, 17))

# One PID per wheel: input = measured speed, output = motor power 0..1
pid_left = PID(KP, KI, KD, setpoint=SPEED, sample_time=None, output_limits=(0, 1))
pid_right = PID(KP, KI, KD, setpoint=SPEED, sample_time=None, output_limits=(0, 1))

try:
    left_prev, right_prev = enc.read()
    t_prev = time.perf_counter()

    while True:
        # 1. SENSE: line or floor?
        r, g, b, c = sensor.color_raw

        # 2. MEASURE: wheel speeds in steps per second
        left, right = enc.read()
        t_now = time.perf_counter()
        dt = t_now - t_prev
        left_speed = (left - left_prev) / dt
        right_speed = (right - right_prev) / dt
        left_prev, right_prev, t_prev = left, right, t_now

        # 3. DECIDE + 4. CALCULATE
        if c < TH:                         # dark = on line -> turn left
            left_cmd = -0.1                # left wheel slightly backwards = tighter turn
            right_cmd = pid_right(right_speed)
            pid_left.reset()               # stopped wheel starts fresh next time
        else:                              # bright = floor -> turn right
            left_cmd = pid_left(left_speed)
            right_cmd = 0
            pid_right.reset()

        # 5. ACT
        robot.value = (left_cmd, right_cmd)

        # print(c, "line" if c < TH else "floor", f"L={left_speed:4.0f} R={right_speed:4.0f}")

finally:
    robot.stop()
    slp.off()
    enc.close()
import pygame
import time

from gpiozero import Device, Motor, MCP3008
from gpiozero.pins.pigpio import PiGPIOFactory
from simple_pid import PID

import board
import busio
import adafruit_ssd1306
from PIL import Image, ImageDraw

sensor = MCP3008(channel=0)

def voltage(sensor):
    return sensor.value * 3.3

def distance_cm(v):
    if v <= 0:
        return float('inf')
    return 60.5 * v ** -1.1

Device.pin_factory = PiGPIOFactory()

motor_a = Motor(forward=12, backward=18)
motor_b = Motor(forward=13, backward=25)

# Settings
MAX_SPEED = 0.2
THRESHOLD = 30 # cm
TURN_TIME = 0.5

pid = PID(0.03, 0.15, 0.001, setpoint=0)
pid.output_limits = (-0.1, 0.1)

TRIM = 0.0
forward = True

def clamp(val, lo, hi):
    return max(lo, min(hi, val))

def drive(fwd):
    correction = pid(0) + TRIM
    speed_a = clamp(MAX_SPEED + correction, 0, 1)
    speed_b = clamp(MAX_SPEED - correction, 0, 1)
    if fwd:
        motor_a.forward(speed_a)
        motor_b.forward(speed_b)
    else:
        motor_a.backward(speed_a)
        motor_b.backward(speed_b)

def turn_around():
    motor_a.forward(MAX_SPEED)
    motor_b.backward(MAX_SPEED)
    time.sleep(TURN_TIME)

try:
    while True:
        v = voltage(sensor)
        dist = distance_cm(v)
        print(f"{v:.2f} V  ->  {dist:.1f} cm")

        if dist < THRESHOLD:
            motor_a.stop()
            motor_b.stop()
            time.sleep(0.2)

            turn_around()
            pid.reset()

        drive(forward)
        time.sleep(0.1)

except KeyboardInterrupt:
    motor_a.stop()
    motor_b.stop()
    print("Stopped")

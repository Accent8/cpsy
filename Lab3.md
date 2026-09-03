Me:
hey so i have a ICM-29048 sensor and i want to make it into a compass and i have to translate the coordinates into real world readings can you help me with that python code
Claude:
Quick note: I couldn't find a real part called "ICM-29048" — that's almost certainly the **ICM-20948**, TDK/InvenSense's 9-axis IMU (accel + gyro + AK09916 magnetometer) that's popular for compass projects on Raspberry Pi and similar boards. I'll build the code for that; let me know if you actually meant a different chip.

Before I write it, I need to know how it's wired up, since that changes the code quite a bit.This uses the `icm20948` Python library (Pimoroni's driver, works fine with generic ICM-20948 breakouts too) since hand-rolling the raw I2C register sequence for the auxiliary magnetometer is fiddly and easy to get subtly wrong.

Setup on the Pi:

```bash
sudo raspi-config nonint do_i2c 0
python3 -m venv --system-site-packages ~/.venvs/pimoroni
source ~/.venvs/pimoroni/bin/activate
pip install icm20948
i2cdetect -y 1   # confirm the sensor shows up (0x68 or 0x69)
```

How the "translation" works: `imu.read_magnetometer_data()` gives you raw X/Y/Z magnetic field values. On their own those are noisy and offset-biased, so the script tracks a running min/max on each axis and rescales into a -0.5..0.5 range — that's the hard-iron calibration step, and it's why the script asks you to spin the sensor through a full circle right after starting it. From there, `atan2` on two of the axes gives you heading in radians, which gets converted to degrees (0–360, clockwise from magnetic north) and then to a 16-point compass label (N, NNE, NE, …).

Two things worth knowing since you went with the simple/no-tilt-compensation option: this reports heading relative to *magnetic* north, not true north (that gap is called declination and depends on your location), and it assumes the board is held roughly flat — tilting it will skew the reading. Both are one-line additions later if you want them (declination is just an offset you add; tilt compensation folds in the accelerometer). Happy to add either if you find you need it once you're testing with real hardware.
```python
#!/usr/bin/env python3
"""
Turn an ICM-20948 9-axis IMU into a simple digital compass on a Raspberry Pi (I2C).

Hardware:
    ICM-20948 SDA -> Pi SDA (GPIO2 / pin 3)
    ICM-20948 SCL -> Pi SCL (GPIO3 / pin 5)
    ICM-20948 VCC -> 3.3V, GND -> GND

Setup (one-time):
    sudo raspi-config nonint do_i2c 0        # enable I2C
    python3 -m venv --system-site-packages ~/.venvs/pimoroni
    source ~/.venvs/pimoroni/bin/activate
    pip install icm20948

    Confirm the sensor shows up on the bus (usually address 0x68 or 0x69):
        i2cdetect -y 1

Why calibration is needed:
    The magnetometer's raw X/Y/Z readings are offset by "hard iron" bias from
    the board itself and anything metal nearby, so the raw numbers don't
    center on zero. If you skip this step the heading will be wrong/jumpy.
    This script calibrates live: rotate the sensor through a full 360 degrees
    (flat, X-axis facing up) right after starting it, and the min/max seen on
    each axis is used to re-center and rescale future readings.

    This version assumes the sensor is held roughly flat/level. It does NOT
    correct for tilt (pitch/roll) or for magnetic declination (the offset
    between magnetic north and true north at your location) - it reports
    heading relative to MAGNETIC north. If you ever want true north, look up
    your local declination and add it to `heading_deg` before wrapping to 0-360.
"""

import math
import time

from icm20948 import ICM20948

# Which two raw axes correspond to your compass' "flat" plane depends on how
# the board is physically oriented. With the chip flat on a table and the
# X-axis arrow pointing away from you, Y and Z are the pair that works with
# this library's axis convention (this matches the sensor's own example).
X, Y, Z = 0, 1, 2
HEADING_AXES = (Y, Z)


class Compass:
    def __init__(self):
        self.imu = ICM20948()
        # Seed the calibration bounds with two real readings so min/max
        # start somewhere sane instead of +/-infinity.
        first = list(self.imu.read_magnetometer_data())
        self._min = list(first)
        self._max = list(first)

    def _calibrated_xyz(self):
        raw = list(self.imu.read_magnetometer_data())  # (x, y, z) in microtesla/Gauss
        calibrated = [0.0, 0.0, 0.0]

        for i in range(3):
            v = raw[i]
            if v < self._min[i]:
                self._min[i] = v
            if v > self._max[i]:
                self._max[i] = v

            span = self._max[i] - self._min[i]
            if span == 0:
                calibrated[i] = 0.0
            else:
                # Rescale into 0..1, then shift to -0.5..0.5 so atan2 sees a
                # value centered on zero like a "real" reading would be.
                calibrated[i] = (v - self._min[i]) / span - 0.5

        return calibrated

    def heading_degrees(self) -> float:
        """Return compass heading in degrees, 0 = magnetic north, clockwise."""
        mag = self._calibrated_xyz()
        heading_rad = math.atan2(mag[HEADING_AXES[0]], mag[HEADING_AXES[1]])
        if heading_rad < 0:
            heading_rad += 2 * math.pi
        return math.degrees(heading_rad)


COMPASS_POINTS = [
    "N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
    "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW",
]


def heading_to_compass_point(heading_deg: float) -> str:
    index = round(heading_deg / 22.5) % 16
    return COMPASS_POINTS[index]


def main():
    compass = Compass()
    print("Rotate the sensor through a full 360 degrees (flat) to calibrate.")
    print("Press Ctrl+C to stop.\n")

    try:
        while True:
            heading = compass.heading_degrees()
            point = heading_to_compass_point(heading)
            print(f"Heading: {heading:6.1f} deg  ({point})")
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
```
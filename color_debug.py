import time

import board
import adafruit_tcs34725
import adafruit_ssd1306
from PIL import Image, ImageDraw

i2c = board.I2C()
color_sensor = adafruit_tcs34725.TCS34725(i2c)
color_sensor.integration_time = 150
color_sensor.gain = 16

oled = adafruit_ssd1306.SSD1306_I2C(128, 64, i2c)

def show(line1, line2="", line3=""):
    oled.fill(0)
    image = Image.new("1", (128, 64))
    draw = ImageDraw.Draw(image)
    draw.text((0, 0), line1, fill=255)
    draw.text((0, 20), line2, fill=255)
    draw.text((0, 40), line3, fill=255)
    oled.image(image)
    oled.show()

try:
    while True:
        r, g, b = color_sensor.color_rgb_bytes
        avg = (r + g + b) // 3
        show("R:{} G:{} B:{}".format(r, g, b),
             "Avg: {}".format(avg),
             "Lux: {:.0f}".format(color_sensor.lux))
        time.sleep(0.3)

except KeyboardInterrupt:
    oled.fill(0)
    oled.show()
    print("Done")

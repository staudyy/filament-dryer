from machine import I2C, Pin
from neopixel import NeoPixel
import asyncio
import time

from lib.ssd1306 import SSD1306_I2C
from components import Mosfet, Knob, DS18B20, SHT40
from application import Application
from settings import Settings

# RGB Led
rgb_led=NeoPixel(Pin(16), 1)

# OLED Display
OLED_WIDTH = 128
OLED_HEIGHT = 64
i2c_display = I2C(1, scl=Pin(15), sda=Pin(14), freq=400_000)
try:
    oled = SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c_display)
except:
    rgb_led[0] = (255//10, 0, 0)
    rgb_led.write()
    raise Exception("Display init error.")

# SHT40
i2c_sht40 = I2C(0, scl=Pin(5), sda=Pin(4), freq=400_000)
sht40 = SHT40(i2c_sht40, measure_delay=50)

# Temperature sensor
try:
    temp_sensor = DS18B20(0)
except:
    rgb_led[0] = (255//10, 0, 0)
    rgb_led.write()
    oled.text("ERROR", 0, 0)
    oled.text("Temp sensor", 0, 10)
    oled.text("init error", 0, 20)
    oled.show()
    raise Exception("Temperature sensor init error.")

# Rotary encoder
knob = Knob(1, 2, 3, half_step=True)

# MOSFET Controllers
fan_mosfet = Mosfet(6)
heater_mosfet = Mosfet(7)


app = Application(
    display=oled,
    temp_sensor=temp_sensor,
    hum_sensor=sht40,
    knob=knob,
    fan=fan_mosfet,
    heater=heater_mosfet,
    rgb_led=rgb_led,
    settings=Settings()
    )

asyncio.run(app.run())

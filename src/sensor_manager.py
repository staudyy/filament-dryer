from neopixel import NeoPixel
import asyncio
import time

from components import Mosfet, Knob, DS18B20, SHT40
from settings import Settings

# TODO Calculate heat on/off thresholds automatically

class SensorManager:
    def __init__(
            self,
            temp_sensor: DS18B20,
            hum_sensor: SHT40,
            knob: Knob,
            fan: Mosfet,
            heater: Mosfet,
            rgb_led: NeoPixel,
            settings: Settings
            ):

        self._temp_sensor = temp_sensor
        self._hum_sensor = hum_sensor
        self._knob = knob
        self.rgb_led = rgb_led
        self.fan = fan
        self.heater = heater
        self.settings = settings

        # Inside box logic setup
        self._heat_stop_event = asyncio.Event()
        self._heat_start_event = asyncio.Event()

        # Temperature sensor setup
        self._temp_sensor_temp = 999

        # Humidity sensor setup
        self._humidity = 100
        self._hum_sensor_temp = 999
        self._humidity_disable_timer = time.ticks_ms()

        # Knob setup
        self._knob_event = asyncio.Event()
        self._knob.add_listener(self._knob_change_callback)
        self._knob.button.on_click(self._knob_click)
        self._knob_last_value = 0

        # RGB Led setup
        self.rgb_led_off()

        # Listeners
        self._knob_click_listeners = []
        self._knob_change_listeners = []
        self._error_listeners = []
        self._display_update_listeners = []

    def _knob_click(self):
        for listener in self._knob_click_listeners:
            listener()

    def _knob_change_callback(self):
        self._knob_event.set()

    async def _knob_change_loop(self):
        while self.settings.enabled >= 1:
            await self._knob_event.wait()
            self._knob_change()
            self._knob_event.clear()
    
    def _knob_change(self):
        if self._knob.value() > self._knob_last_value:
            for listener in self._knob_change_listeners:
                listener(True)
        else:
            for listener in self._knob_change_listeners:
                listener(False)
        self._knob_last_value = self._knob.value()

    def _error(self, status="-"):
        if not self._error_listeners:
            raise Exception(status)
        for listener in self._error_listeners:
            listener(status)
    
    async def _read_temp_loop(self):
        while self.settings.enabled >= 2:
            try:
                self._temp_sensor_temp = await self._temp_sensor.read_temp()
                self.temp_update()
                await asyncio.sleep_ms(max(round(self.settings.temp_update_delay*1000) - self._temp_sensor.measure_delay, 0))
            except:
                self._error(status="Temp sensor err")
                await asyncio.sleep_ms(1000)
    
    async def _read_hum_loop(self):
        try:
            await self._hum_sensor.soft_reset()
            while self.settings.enabled >= 2:
                    self._hum_sensor_temp, self._humidity = await self._hum_sensor.measure()
                    self.hum_update()
                    await asyncio.sleep_ms(max(round(self.settings.hum_update_delay*1000) - self._hum_sensor.measure_delay, 0))
        except:
            self._error(status="Hum sensor err")
            await asyncio.sleep_ms(1000)
    
    async def _screen_update_loop(self):
        while self.settings.enabled >= 1:
            for listener in self._display_update_listeners:
                listener()
            await asyncio.sleep_ms(1000//self.settings.display_refresh_rate)

    def hum_update(self):
        if self.settings.enabled < 3 or self._humidity >= self.settings.target_humidity:
            self._humidity_disable_timer = time.ticks_ms()
        elif self.settings.enabled >= 3 and time.ticks_diff(time.ticks_ms(), self._humidity_disable_timer) >= self.settings.humidity_disable_time * 1000 * 60:
            self.settings.enabled = 2
        
        # If any of the sensor reach target turn heat off (or), Both sensors have to be low enough for heat to turn on (checked in temp_update)
        if self._hum_sensor_temp >= self.settings.target_temp + self.settings.heat_stop_treshold:
            if not self._heat_stop_event.is_set():
                self._heat_stop_event.set()

    def temp_update(self):
        # Check deviation
        if abs(self._temp_sensor_temp - self._hum_sensor_temp) >= self.settings.temp_deviation and self._temp_sensor_temp != 999 and self._hum_sensor_temp != 999:
            self._error(status="Temp deviation")

        if self._temp_sensor_temp >= self.settings.target_temp + self.settings.heat_stop_treshold:
            if not self._heat_stop_event.is_set():
                self._heat_stop_event.set()
        
        elif self._temp_sensor_temp <= self.settings.target_temp + self.settings.heat_start_treshold and self._hum_sensor_temp <= self.settings.target_temp + self.settings.heat_start_treshold:
            if not self._heat_start_event.is_set():
                self._heat_start_event.set()
            elif not self.heater._is_on and self.settings.enabled >= 3:
                self.heater.on()
                self.rgb_led_color(0, 255, 0)

    async def _box_logic_loop(self):
        if self.settings.enabled >= 3:
            self.fan.on()
        else:
            self.fan.off()
        self.heater.off()

        # Loop is on sensor level, loop stays running while fan + heater is disabled
        while self.settings.enabled >= 2:
            self._heat_start_event.clear()
            await self._heat_start_event.wait()
            if self.settings.enabled >= 3:
                self.heater.on()
                self.rgb_led_color(0, 255, 0)
                print("ON")

            self._heat_stop_event.clear()
            await self._heat_stop_event.wait()
            self.heater.off()
            self.rgb_led_off()
            print("OFF")
    
    def rgb_led_color(self, r, g, b):
        self.rgb_led[0] = (r//10, g//10, b//10)
        self.rgb_led.write()
    
    def rgb_led_off(self):
        self.rgb_led_color(0, 0, 0)
    
    def on_enable_change(self, last_state):
        if self.settings.enabled > last_state:
            if last_state <= 0:  # New state >= 1
                asyncio.create_task(self._knob_change_loop())
                asyncio.create_task(self._screen_update_loop())

            if last_state <= 1:  # New state >= 2
                asyncio.create_task(self._read_temp_loop())
                asyncio.create_task(self._read_hum_loop())
                asyncio.create_task(self._box_logic_loop())

            if last_state == 2: # New state >= 3, only if sensors were previously enabled
                self.fan.on()
                self.hum_update()
                self.temp_update()

        elif self.settings.enabled < 3:
            self.fan.off()
            self.heater.off()
            self.rgb_led_off()

    def add_knob_click_listener(self, listener):
        self._knob_click_listeners.append(listener)

    def add_knob_change_listener(self, listener):
        self._knob_change_listeners.append(listener)
    
    def add_error_listener(self, listener):
        self._error_listeners.append(listener)
    
    def add_display_update_listener(self, listener):
        self._display_update_listeners.append(listener)
    
    def get_current_temp(self):
        return self._temp_sensor_temp

    def get_current_humidity(self):
        return self._humidity
    
    def get_current_temp2(self):
        return self._hum_sensor_temp

    def run(self):
        self.on_enable_change(0)
        # asyncio.create_task(self._knob_change_loop())
        # asyncio.create_task(self._screen_update_loop())
        # asyncio.create_task(self._read_temp_loop())
        # asyncio.create_task(self._read_hum_loop())
        # asyncio.create_task(self._box_logic_loop())

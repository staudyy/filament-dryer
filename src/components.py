from machine import Pin
import asyncio
import time
import onewire, ds18x20

from lib.rotary_irq_rp2 import RotaryIRQ, Rotary

class SHT40:
    # Measurement commands (Precision levels)
    MEASURE_HIGH = 0xFD
    MEASURE_MED  = 0xF6
    MEASURE_LOW  = 0xE0

    # Soft Reset command
    SOFT_RESET   = 0x94

    def __init__(self, i2c, address=0x44, measure_delay=10):
        # Call soft_reset after init.
        self.i2c = i2c
        self.address = address
        self.measure_delay = measure_delay

    def _verify_crc(self, data):
        crc = 0xFF
        for byte in data[:2]:
            crc ^= byte
            for _ in range(8):
                if crc & 0x80:
                    crc = (crc << 1) ^ 0x31
                else:
                    crc = crc << 1
        return (crc & 0xFF) == data[2]

    # Call before starting measurements.
    async def soft_reset(self):
        self.i2c.writeto(self.address, bytes([self.SOFT_RESET]))
        await asyncio.sleep_ms(2)

    async def _read_measurement(self, command):
        self.i2c.writeto(self.address, bytes([command]))

        await asyncio.sleep_ms(self.measure_delay) 
        
        data = self.i2c.readfrom(self.address, 6)
        
        if not self._verify_crc(data[0:3]) or not self._verify_crc(data[3:6]):
            raise RuntimeError("CRC error during measurement")
            
        t_ticks = (data[0] << 8) | data[1]
        rh_ticks = (data[3] << 8) | data[4]
        
        t_celsius = -45 + (175 * t_ticks / 65535.0)
        rh_percent = -6 + (125 * rh_ticks / 65535.0)
        
        rh_percent = max(0.0, min(100.0, rh_percent))
        
        return t_celsius, rh_percent

    async def measure(self, precision=MEASURE_HIGH):
        if precision not in (self.MEASURE_LOW, self.MEASURE_MED, self.MEASURE_HIGH):
            raise ValueError("Invalid precision command")
        
        return await self._read_measurement(precision)

    async def measure_heater(self, heater_cmd):
        print("Not implemented, dont use")


class DS18B20:
    def __init__(self, pin, measure_delay=750) -> None:
        self.sensor = ds18x20.DS18X20(onewire.OneWire(Pin(pin)))
        self.measure_delay = measure_delay
        roms = self.sensor.scan()
        if not roms:
            raise RuntimeError("No DS18B20 found")
        self.address = roms[0]
    
    async def read_temp(self):
        self.sensor.convert_temp()
        await asyncio.sleep_ms(self.measure_delay)  # wait for conversion
        return self.sensor.read_temp(self.address)


class Mosfet:
    def __init__(self, pin_id) -> None:
        self.pin = Pin(pin_id, Pin.OUT)
        self._is_on = False
        self.off()
    
    @property
    def is_on(self):
        return self._is_on
    
    def on(self):
        self._is_on = True
        self.pin.on()
    
    def off(self):
        self._is_on = False
        self.pin.off()
    
    def toggle(self):
        if self._is_on:
            self._is_on = False
            self.pin.off()
        else:
            self._is_on = True
            self.pin.on()


class Knob(RotaryIRQ):
    def __init__(
        self,
        clock_pin,
        data_pin,
        button_pin,
        min_val=0,
        max_val=10,
        incr=1,
        reverse=False,
        range_mode=Rotary.RANGE_UNBOUNDED,
        pull_up=False,
        half_step=False,
        invert=False
    ):
        super().__init__(clock_pin, data_pin, min_val, max_val, incr, reverse, range_mode, pull_up, half_step, invert)
        self.button  = Button(button_pin)


class Button:
    def __init__(self, pin_id, debounce=50):
        self.button = Pin(pin_id, Pin.IN, Pin.PULL_UP)
        self.debounce = debounce

        self.click_listeners = []
        self.click_listeners_async = []
        self.presses = 0

        self._toggled = False
        self._last_pressed = time.ticks_ms()
        self.button.irq(trigger=Pin.IRQ_FALLING | Pin.IRQ_RISING, handler=self.button_press_handler)

    def button_press_handler(self, pin=None):
        if not self.is_pressed():
            self._last_pressed = time.ticks_ms()
            self._toggled = False

        if not self._toggled and self.is_pressed() and time.ticks_diff(time.ticks_ms(), self._last_pressed) >= self.debounce:
            self._last_pressed = time.ticks_ms()
            self._toggled = True
            self._click_fire()

                    
    def _click_fire(self):
        for listener in self.click_listeners:
            listener()

        for listener in self.click_listeners_async:
            asyncio.create_task(listener())
        

    def on_click(self, *listeners):
        for listener in listeners:
            self.click_listeners.append(listener)
    
    def on_release(self, *listeners):
        # TODO
        pass

    # USE ONLY WITH EVENT LOOP
    def on_click_async(self, *listeners):
        for listener in listeners:
            self.click_listeners_async.append(listener)

    def is_pressed(self):
        return self.button.value() == 0
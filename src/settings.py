try:
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from sensor_manager import SensorManager
except ImportError:
    pass

class Settings:
    def __init__(
            self,
            humidity_disable_time=30.0,  # min
            heat_stop_treshold=-0.5,  # °C
            heat_start_treshold=-0.8,  # °C
            settings_timeout=10,  # sec
            min_temp=10,  # °C
            max_temp=80,  # °C
            display_refresh_rate=20,  # Hz
            target_temp=50,  # °C
            target_humidity=5,  # %
            temp_deviation=5,  # °C
            hum_update_delay=1.0,  #s
            temp_update_delay=1.0,  #s
            enabled=2,  # -1: Kill event loop, 0: All disabled, 1: UI enabled, 2: Sensors enabled, 3: Heater + fan enabled,  !!! states -1, 0 not working yet, state 1 unstable, possible double asyncio loops
            ) -> None:
        
        self.humidity_disable_time = humidity_disable_time
        # stop > start
        self.heat_stop_treshold = heat_stop_treshold
        self.heat_start_treshold = heat_start_treshold
        self.settings_timeout = settings_timeout
        self.min_temp = min_temp
        self.max_temp = max_temp
        self.display_refresh_rate = display_refresh_rate
        self.temp_deviation = temp_deviation
        self.hum_update_delay = hum_update_delay
        self.temp_update_delay = temp_update_delay
        self.error_status = "-"

        self._target_temp = target_temp
        self._target_humidity = target_humidity
        self._enabled = enabled

        self._sensor_manager: SensorManager = None

    @property
    def target_temp(self):
        return self._target_temp

    @target_temp.setter
    def target_temp(self, val):
        self._target_temp = val
        if self._sensor_manager:
            self._sensor_manager.temp_update()

    @property
    def target_humidity(self):
        return self._target_humidity

    @target_humidity.setter
    def target_humidity(self, val):
        self._target_humidity = val
        if self._sensor_manager:
            self._sensor_manager.hum_update()
    
    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, val):
        old = self._enabled
        self._enabled = val
        if self._sensor_manager:
            self._sensor_manager.on_enable_change(old)
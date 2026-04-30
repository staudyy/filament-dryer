from neopixel import NeoPixel
import asyncio
import gc
import time

from lib.ssd1306 import SSD1306_I2C
from lib.writer import Writer
from views import StatusView, ErrorView, OptionsView, EditorView, WriterWrapper
from presenters import StatusPresenter, ErrorPresenter, EditorPresenter, OptionsPresenter
from components import Mosfet, Knob, DS18B20, SHT40
from fonts import RobotoMono_Regular15, RobotoMono_Regular40
from settings import Settings
from sensor_manager import SensorManager

# TODO Better error handling, dont crash entire app

class ViewWrapper:
    # For type hints, add all screens
    status: StatusView
    error: ErrorView
    editor: EditorView

    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def __getitem__(self, key):
        return getattr(self, key)
    
    def add(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def delete(self, key):
        delattr(self, key)
    
    def get_items(self):
        return self.__dict__


class Application:
    def __init__(
            self,
            display: SSD1306_I2C,
            temp_sensor: DS18B20,
            hum_sensor: SHT40,
            knob: Knob,
            fan: Mosfet,
            heater: Mosfet,
            rgb_led: NeoPixel,
            settings: Settings,
            ):
        
        self.display = display
        self._last_input = time.ticks_ms()
        self.settings = settings

        self._sensor_manager = SensorManager(
            temp_sensor=temp_sensor,
            hum_sensor=hum_sensor,
            knob=knob,
            fan=fan,
            heater=heater,
            rgb_led=rgb_led,
            settings=settings
            )
        
        # Add reference to settings
        self.settings._sensor_manager = self._sensor_manager

        # Views
        writers = {
            # 8: Writer(self.display, RobotoMono_Regular8, verbose=False),  # unused
            15: Writer(self.display, RobotoMono_Regular15, verbose=False),
            40: Writer(self.display, RobotoMono_Regular40, verbose=False)
        }
        self.text_writer = WriterWrapper(self.display, writers)
        
        self._persistent_views = ViewWrapper(
            status=StatusView(self.display, self.text_writer, error_listener=self.error),
            error=ErrorView(self.display, self.text_writer, error_listener=self.error),
            editor=EditorView(self.display, self.text_writer, error_listener=self.error)
        )

        # Presenters
        self.ui_stack = [StatusPresenter(self._persistent_views.status, self.settings, self._sensor_manager, self.create_options_presenter(options_getter=self.ui_get_options_list))]  # type: list[StatusPresenter | ErrorPresenter | EditorPresenter | OptionsPresenter]

        # Listeners
        self._sensor_manager.add_display_update_listener(self.display_update)
        self._sensor_manager.add_knob_click_listener(self.knob_click)
        self._sensor_manager.add_knob_change_listener(self.knob_change)
        self._sensor_manager.add_error_listener(self.error)

    @property
    def active_presenter(self):
        return self.ui_stack[-1]

    def ui_home(self):
        self.ui_stack = [self.ui_stack[0]]
        gc.collect()
    
    def ui_back(self):
        self.ui_stack.pop()
        gc.collect()
    
    def ui_toggle_enable(self):
        if self.settings.enabled >= 3:
            self.settings.enabled = 2
        else:
            self.settings.enabled = 3
        # Really bad implementation, works only when settings is active, when state changes while settings are open (ui is not in home), label doesnt get updated TODO
        # Basically needs full redo, also goes for ui_get_options_list, it is just a dirty patch
        try:
            for i, label in enumerate(self.active_presenter.view.options):  # type: ignore
                if label in ("Disable", "Enable", "Force enable"):
                    if self.settings.enabled >= 3:
                        self.active_presenter.view.options[i] = "Disable"  # type: ignore
                    elif self.settings.enabled == 2:
                        self.active_presenter.view.options[i] = "Enable"  # type: ignore
                    else:
                        self.active_presenter.view.options[i] = "Force enable"  # type: ignore
        except:
            pass
    
    def ui_get_options_list(self):
        # TODO to all, some kind of extremes (enabled, disabled, for example humidity disable time when >60, dont ever disable)
        if self.settings.enabled >= 3:
            enable_str = "Disable"
        elif self.settings.enabled == 2:
            enable_str = "Enable"
        else:
            enable_str = "Force enable"

        return [
                ("Home", self.ui_home),
                (enable_str, self.ui_toggle_enable),
                ("Temperature", self.create_editor_presenter(self.ui_back, "Temperature", "target_temp", "%val°C", self.settings.min_temp, self.settings.max_temp)),
                ("Humidity goal", self.create_editor_presenter(self.ui_back, "Humidity goal", "target_humidity", "<%val%", 0, 101)),
                ("Humidity timer", self.create_editor_presenter(self.ui_back, "Humidity timer", "humidity_disable_time", "%valm", 0, 1440, increment=5)),
                ("Advanced", self.create_options_presenter(options_getter=self.ui_get_advanced_options_list)),
            ]

    def ui_get_advanced_options_list(self):
        # TODO Overrides
        return [
            ("BACK", self.ui_back),
            ("Temp deviation", self.create_editor_presenter(self.ui_back, "Temp deviation", "temp_deviation", "%val°C", 0, 100, increment=0.5)),
            ("Heater stop", self.create_editor_presenter(self.ui_back, "Heater stop (C)", "heat_stop_treshold", "%val", -10, 10, increment=0.05)),
            ("Heater start", self.create_editor_presenter(self.ui_back, "Heater start (C)", "heat_start_treshold", "%val", -10, 10, increment=0.05)),
            ("Min temp", self.create_editor_presenter(self.ui_home, "Min temp", "min_temp", "%val°C", -999, 999)),
            ("Max temp", self.create_editor_presenter(self.ui_home, "Max temp", "max_temp", "%val°C", -999, 999)),
            ("Temp upd freq", self.create_editor_presenter(self.ui_back, "Temp upd freq", "temp_update_delay", "%vals", .7, 1000, increment=0.1)),
            ("Hum upd freq", self.create_editor_presenter(self.ui_back, "Hum upd freq", "hum_update_delay", "%vals", .1, 1000, increment=0.1)),
            ("UI Timeout", self.create_editor_presenter(self.ui_back, "UI Timeout", "settings_timeout", "%vals", 1, 999)),
            ("Fan override", lambda: 0),
            ("Heater override",lambda: 0),
            ("LED override",lambda: 0),
            ("Vent override",lambda: 0)
            ]
    
    def create_error_presenter(self):
        def append_error():
            presenter = ErrorPresenter(
                view=self._persistent_views.error,
                settings=self.settings
            )
            self.ui_stack.append(presenter)
        return append_error

    def create_editor_presenter(self, click_callback, label, key, value_string="%val", min_val=0.0, max_val=100.0, increment=1.0):
        def append_editor():
            presenter = EditorPresenter(
                view=self._persistent_views.editor,
                settings=self.settings,
                click_callback=click_callback,
                label=label,
                key=key,
                value_string=value_string,
                min_val=min_val,
                max_val=max_val,
                increment=increment
            )
            self.ui_stack.append(presenter)
        return append_editor
    
    def create_options_presenter(self, *, options_list=[], options_getter=None):
        def append_options():
            if options_getter is not None:
                options = options_getter()
            else:
                options = options_list
            presenter = OptionsPresenter(
                view=OptionsView(
                    display=self.display,
                    text_writer=self.text_writer,
                    options=[option[0] for option in options],
                    error_listener=self.error
                ),
                settings=self.settings,
                options=options
            )
            self.ui_stack.append(presenter)
        return append_options

    def _check_timeout(self):
        if type(self.active_presenter) in (StatusPresenter, ErrorPresenter):
            return
        if time.ticks_diff(time.ticks_ms(), self._last_input) > self.settings.settings_timeout * 1000:
            self.ui_home()

    def display_update(self): 
        self._check_timeout()
        self.active_presenter.display_update()

    def knob_click(self):
        self._last_input = time.ticks_ms()
        self.active_presenter.on_click()

    def knob_change(self, clockwise):
        self._last_input = time.ticks_ms()
        self.active_presenter.on_scroll(clockwise)

    def error(self, status="-"):
        if self.settings.error_status == "-" or self.settings.error_status != status:
            self.settings.error_status = status
        else:
            print("Multiple errors:", status)
        self.settings.enabled = 1
        # asyncio.create_task(self.testing_disable())
        self._sensor_manager.rgb_led_color(255, 0, 0)
        if type(self.active_presenter) != ErrorPresenter:
            self.ui_stack.append(ErrorPresenter(self._persistent_views.error, self.settings, self.ui_home))
    
    # async def testing_disable(self):
    #     self.settings.enabled = 0
    #     print("full disable")
    #     await asyncio.sleep(2)
    #     self.settings.enabled = 1
    #     print("ui enable")
        

    async def run(self):
        self._sensor_manager.run()
        while self.settings.enabled >= 0:
            await asyncio.sleep_ms(10)

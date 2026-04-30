from views import *
from settings import Settings
from sensor_manager import SensorManager

class Presenter:
    def on_scroll(self, clockwise):
        pass

    def on_click(self):
        pass

    def display_update(self):
        pass
        

class StatusPresenter(Presenter):
    def __init__(self, view: StatusView, settings: Settings, sensor_manager: SensorManager, action_callback) -> None:
        self.view = view
        self.settings = settings
        self.sensor_manager = sensor_manager
        self.action_callback = action_callback
    
    def on_click(self):
        self.action_callback()
    
    def on_scroll(self, clockwise):
        self.action_callback()
    
    def display_update(self):
        self.view.show(
            self.settings.target_temp,
            self.sensor_manager.get_current_temp(),
            self.sensor_manager.get_current_temp2(),
            self.sensor_manager.get_current_humidity(),
            self.settings.enabled >= 3,
            self.sensor_manager.fan._is_on,
            self.sensor_manager.heater._is_on
        )


class ErrorPresenter(Presenter):
    def __init__(self, view: ErrorView, settings: Settings, click_callback=None) -> None:
        self.view = view
        self.settings = settings
        self.click_callback = click_callback
    
    def display_update(self):
        self.view.show(self.settings.error_status)

    def on_click(self):
        if self.click_callback is not None:
            self.click_callback()


class EditorPresenter(Presenter):
    def __init__(self, view: EditorView, settings: Settings, click_callback, label, key, value_string="%val", min_val=0.0, max_val=100.0, increment=1.0, font_height=40) -> None:
        self.view = view
        self.settings = settings
        self.click_callback = click_callback
        self.label = label
        self.key = key
        self.value_string = value_string
        self.min_val = min_val
        self.max_val = max_val
        self.increment = increment
        self.font_height = font_height
    
    def on_click(self):
        self.click_callback()
    
    def on_scroll(self, clockwise):
        if clockwise:
            increment = self.increment
        else:
            increment = -self.increment
        
        current_val = getattr(self.settings, self.key)
        if current_val >= 1 and self.increment <= 0.01:
            increment *=10
        if current_val >= 10 and self.increment <= 0.1:
            increment *=10
        if current_val >= 100 and self.increment <= 1:
            increment *=10
        new_val = max(min(current_val + increment, self.max_val), self.min_val)
        setattr(self.settings, self.key, new_val)
    
    def display_update(self):
        value = getattr(self.settings, self.key)
        if value >= 100 or value % 1 <= 10**-5 or value % 1 >= 1 - 10**-5:
            value = round(value)
        elif value >= 10 or value*10 % 1 <= 10**-5 or value*10 % 1 >= 1 - 10**-5:
            value = round(value, 2)
        else:
            value = round(value, 2)
        self.view.show(self.label, self.value_string.replace("%val", str(value)), font_height=self.font_height)


# Always create new view
class OptionsPresenter(Presenter):
    def __init__(self, view: OptionsView, settings: Settings, options) -> None:
        self.view = view
        self.settings = settings  # maybe not needed
        self.options = options  # [(label, callback)]
    
    def on_click(self):
        self.options[self.view.get_selected_i()][1]()
    
    def on_scroll(self, clockwise):
        if clockwise:
            self.view.scroll_down()
        else:
            self.view.scroll_up()
    
    def display_update(self):
        self.view.show()
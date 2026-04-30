from lib.ssd1306 import SSD1306_I2C

# Split into Logic and Views
# Implement a stack (which screen is active, better than current)
# [\/] Create a Settings class that holds all variable settings (better for implementing parameters, necesary for scalable LogicScreen implementation)
# Go back should be a callback to a manager
# Manager should always create new instance of LogicScreen instead of using and editing one instance. Research garbage collection

class WriterWrapper:
    def __init__(self, display: SSD1306_I2C, writers) -> None:
        self.display = display
        self.writers = writers
        
        self.font_sizes = sorted(list(self.writers.keys()), reverse=True)
    
    def _get_writer(self, font_size):
        if font_size in self.writers:
            return self.writers[font_size]
        else:
            raise Exception(f"Font size {font_size} not defined.")

    def text(self, string, x, y, color=1, font_size=8):
        if x < 0 or x > self.display.width or y < 0 or y > self.display.height:
            raise Exception("Invalid coordinates of text.")
        writer = self._get_writer(font_size)
        writer.set_textpos(self.display, y, x)

        if color == 1:
            writer.printstring(string, invert=False)
        else:
            writer.printstring(string, invert=True)


class View:
    def __init__(self, display: SSD1306_I2C, text_writer: WriterWrapper, error_listener=None) -> None:
        self.display = display
        self.text_writer = text_writer
        self.error_listener = error_listener

    def _write(self):
        try:
            self.display.show()
        except:
            if self.error_listener is not None:
                self.error_listener("Display err")
                print("Display write error.")

    def _setup(self):
        self.display.fill(0)
    
    def show(self):
        self._setup()
        self._write()


    def checkmark_icon(self, x, y, size=10):
        self.display.line(x, y + 2*size//3, x + size//3, y + size, 1)
        self.display.line(x + size//3, y + size, x + size, y, 1)

    def cross_icon(self, x, y, size=10):
        self.display.line(x, y, x+size, y+size, 1)
        self.display.line(x, y+size, x+size, y, 1)
    
    def heat_icon(self, x, y, size=10):
        for i in range(3):
            self.display.ellipse(x + size//6 + i*size//3, y + size//4, size//6, size//4, 1, False, 0b0110)  # type: ignore
            self.display.ellipse(x + size//6 + i*size//3, y + 3*size//4, size//6, size//4, 1, False, 0b1001)  # type: ignore

    def fan_icon(self, x, y, size=10):
        self.display.ellipse(x + size//2, y + size//2, size//6, size//6, 1, True)
        
        self.display.line(x + size//2, y + size//2, x + size//2, y + size//6, 1)
        self.display.ellipse(x + 3*size//4, y + size//6, size//4, size//6, 1, False, 0b0010)
        self.display.line(x + size//2, y + size //2, x + 3*size//4, y, 1)

        self.display.line(x + size//2, y + size//2, x + size//2, y + 5*size//6, 1)
        self.display.ellipse(x + size//4, y + 5*size//6, size//4, size//6, 1, False, 0b1000)
        self.display.line(x + size//2, y + size //2, x + size//4, y + size, 1)

        self.display.line(x + size//2, y + size//2, x + size//6, y + size//2, 1)
        self.display.ellipse(x + size//6, y + size//4, size//6, size//4, 1, False, 0b0100)
        self.display.line(x + size//2, y + size //2, x, y + size//4, 1)

        self.display.line(x + size//2, y + size//2, x + 5*size//6, y + size//2, 1)
        self.display.ellipse(x + 5*size//6, y + 3*size//4, size//6, size//4, 1, False, 0b0001)
        self.display.line(x + size//2, y + size //2, x + size, y + 3*size//4, 1)


class StatusView(View):
    def _setup(self, target_t, current_t, current_t2, current_h, enabled=False, fan_enabled=False, heat_enabled=False):
        super()._setup()
        if enabled:
            self.checkmark_icon(100, 1, size=18)
        else:
            self.cross_icon(100, 1, size=18)

        if fan_enabled:
            self.fan_icon(100, 22, size=18)

        if heat_enabled:
            self.heat_icon(100, 43, size=18)

        # self.display.text(f"T: {target_t:1} C", 5, 10, 1)
        # self.display.text(f"C: {current_t:0.1f} C", 5, 23, 1)
        # self.display.text(f"H1: {0:0.1f} C", 5, 36, 1)
        # self.display.text(f"H2: {0:0.1f} C", 5, 49, 1)
        self.text_writer.text(f"Goal {target_t:1}°C", 0, 1, font_size=15)
        self.text_writer.text(f"Ts {current_t:0.1f}°C", 0, 17, font_size=15)
        self.text_writer.text(f"Hs {current_t2:0.1f}°C", 0, 33, font_size=15)
        self.text_writer.text(f"Hu {current_h:0.1f}%", 0, 49, font_size=15)
    
    def show(self, target_t, current_t, current_t2, current_h, enabled=False, fan_enabled=False, heat_enabled=False):
        self._setup(target_t, current_t, current_t2, current_h, enabled, fan_enabled, heat_enabled)
        self._write()


class ErrorView(View):
    def _setup(self, status):
        super()._setup()
        self.display.text("ERROR", 5, 10, 1)
        self.display.text(status, 5, 20, 1)
    
    def show(self, status="-"):
        self._setup(status)
        self._write()


class EditorView(View):
    def _setup(self, label, value_string, font_height):
        super()._setup()
        MARGIN = 5
        self.display.text(label, (self.display.width - len(label)*8)//2, MARGIN, 1)
        if type(value_string) is not str:
            value_string = str(value_string)
        str_len = self.text_writer.writers[font_height].stringlen(value_string)
        self.text_writer.text(value_string, max((self.display.width - str_len)//2, 0), max((self.display.height - font_height) // 2 + MARGIN//2 + 4, 0), font_size=font_height)
    
    def show(self, name, value_string, font_height=40):
        self._setup(name, value_string, font_height)
        self._write()


class OptionsView(View):
    def __init__(self, display: SSD1306_I2C, text_writer: WriterWrapper, options, font_size=8, spacing=2, error_listener=None) -> None:
        super().__init__(display, text_writer, error_listener=error_listener)
        self.options = options  # Labels only
        self.selected = 0
        self.font_size = font_size
        self.spacing = spacing
        self._visible = [0, self.get_max_items()] # [inclusive, exclusive]

    def _setup_scrollbar(self, width=2, min_height=20, increment=8):
        invisible_count = len(self.options) - self.get_max_items()
        if invisible_count == 0:
            return
        height = self.display.height - invisible_count * increment
        if height < min_height:
            increment = (self.display.height - min_height) / invisible_count
            height = min_height
        self.display.rect(0, round(self._visible[0]*increment), width, height, 1, True)  # type: ignore

    def _setup(self, selected=None, start_x=4):
        if selected is not None:
            self.select_i(selected)

        super()._setup()
        self._setup_scrollbar()
        for i, option_i in enumerate(range(self._visible[0], self._visible[1])):
            start_y = self.spacing + i*(self.spacing + self.font_size)
            if start_y + self.font_size - 1 > self.display.height:
                break
            
            if option_i == self.selected:
                self.display.rect(start_x, start_y - 1, self.display.width, self.font_size + 2, 1, True)  # Not an error, fill  # type: ignore
                self.display.text(self.options[option_i], start_x + 1, start_y, 0)
                # self.text_writer.text(self.options[option_i], start_x + 1, start_y, 0, font_size=self.font_size)
            else:
                self.display.text(self.options[option_i], start_x + 1, start_y, 1)
                # self.text_writer.text(self.options[option_i], start_x + 1, start_y, 1, font_size=self.font_size)
    
    def show(self, selected=None):
        self._setup(selected)
        self._write()
    
    def get_max_items(self):
        # Equation:  self.spacing + (N+1)*(self.spacing + self.font_size) < self.display.height
        return min(len(self.options), (self.display.height - self.spacing) // (self.spacing + self.font_size))  # no -1 because floored

    def select_i(self, index):
        if index < 0 or index >= len(self.options):
            raise Exception("Selection index out of range.")
        max_c = self.get_max_items()
        half = max_c // 2
        if index < half:
            self._visible = [0, max_c]
        elif len(self.options) - index - 1 < max_c - half:
            self._visible = [len(self.options) - max_c, len(self.options)]
        else:
            self._visible = [index - half, index + max_c - half]
        self.selected = index
    
    def select(self, option):
        for i, option_check in enumerate(self.options):
            if option == option_check:
                self.select_i(i)
                return
        raise Exception("No such option.")
    
    def scroll_up(self):
        if self.selected - 1 >= 0:
            self.selected -= 1
            if self.selected < self._visible[0]:
                self._visible[0] -= 1
                self._visible[1] -= 1
    
    def scroll_down(self):
        if self.selected + 1 < len(self.options):
            self.selected += 1
            if self.selected >= self._visible[1]:
                self._visible[0] += 1
                self._visible[1] += 1
    
    def get_selected(self):
        return self.options[self.selected]

    def get_selected_i(self):
        return self.selected

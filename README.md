# Filament Dryer
Software for my DIY filament dryer project written in micropython. Features interfacing with all components of the dryer, feature-rich UI controlled by a rotary encoder, sensor error detection and handling and lots of other advanced settings.

The entire project is powered by a RP2040-Zero MCU running Micropython firmware. Any other MCU supported by Micropython should work (Tested on ESP32 C3 SuperMini, needs a different version of [micropyton-rotary](https://github.com/MikeTeachman/micropython-rotary))

## Showcase video
Keep in mind that this project is a WIP  
[YouTube](https://youtu.be/yA8oI_Ru9zQ)

## Features
#### What you need to know
- Display current status on screen
    - Target temperature
    - Current temperature and humidity
    - Enabled/disabled icon
    - Fan status icon
    - Heater status icon
- Turn dryer on/off
- Set target temperature (up to 80C)
- Set target humidity and turn dryer off after it has been reached for set time
- Automatically detect if a component fails and disable the dryer  
- Intuitive simple UI

#### Other features
- Automatically maintains target temperature using the 2 sensors
- Monitors deviation between sensors and disables the dryer if it gets too high (failure indicator)
- All parameters are able to be changed in the Advanced settings in the UI
    - Change maximum deviation
    - Change minimum and maximum target temperature
    - Change heater enable/disable tresholds
    - Change UI timeout
    - And more!
- Indicates dryer state using the rp2040 onboard RGB Led:
    - Green: Heater is enabled
    - Red: Error (useful when display fails and is unable to display the error message)  

A lot of other features and improvements are in the making!

## 3D Printable models
- Fan + Heater mounting bracket: [MakerWorld](https://makerworld.com/en/models/2739180-filament-dryer-fan-and-heater-bracket), [Printables](https://www.printables.com/model/1706165-filament-dryer-fan-and-heater-bracket)
- Case (TODO)

## Used parts
- RP2040-Zero
- Rotary encoder
- SSD1306 Display
- DS18B20 Temperature sensor
- SHT40 Humidity + temperature sensor
- PTC Heater
- 80x80x10 Fan
- 100C Thermal fuse
- 10.6l airtight container
- Mosfet modules, transistor, resistors in wiring
- Old 90W 20V laptop PSU
- Buck converter (to power the RP2040)
- Cables, screw terminals (for connecting wires)
- Screws, nuts and bolts

## How to install
1. Flash Micropython firmware on the MCU
2. Copy all files inside the ```src``` folder to the MCU

---

*Detailed build guide and parts list comming soon!*  

Other projects used:  
- [font-to-py](https://github.com/peterhinch/micropython-font-to-py) and Writer class for fonts  
- [micropyton-rotary](https://github.com/MikeTeachman/micropython-rotary) Rotary encoder driver  
- [ssd1306](https://github.com/micropython/micropython-lib/blob/master/micropython/drivers/display/ssd1306/ssd1306.py) Display driver  


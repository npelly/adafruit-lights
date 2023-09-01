# Nick Pelly August 19, 2023

from adafruit_irremote import GenericDecode
from adafruit_irremote import NECRepeatIRMessage
from adafruit_irremote import FailedToDecode
from adafruit_irremote import IRDecodeException
from board import D10
from board import D5
from board import NeoPixel as BuiltinNeoPixel
from neopixel  import NeoPixel
from pulseio import PulseIn
import time
import gc

# Board Constants
IR_INPUT_PIN = D10
LED_OUTPUT_PIN = D5
LED_COUNT = 16

# Defaults and Settings
AUTO_POWER_OFF_DURATION = 30 * 60  # seconds
DEFAULT_COLOR = (252, 3, 194)  # Lucy's Pink
DEFAULT_BRIGHTNESS = 0.2
FLASH_TIME_ON = 0.2
FLASH_TIME_OFF = 0.1
FADE_STEP_DURATION = 0.05
RAINBOW_STEP_DURATION = 0.03

# MODE constants
OFF= 0
ON = 1
BRIGHTNESS_UP = 2
BRIGHTNESS_DOWN = 3
FLASH = 4
STROBE = 5
FADE = 6
SMOOTH = 7

# IR Remote and Color Constants
IR_CODE_TABLE = {
    # Generic IR remote, 5x purchased on amazon August 2023
    (255, 8, 191, 64):  (None, OFF),             # OFF
    (255, 8, 63, 192):  (None, ON),              # ON
    (255, 8, 255, 0):   (None, BRIGHTNESS_UP),   # BRIGHTNESS_UP
    (255, 8, 127, 128): (None, BRIGHTNESS_DOWN), # BRIGHTNESS_DOWN
    (255, 8, 47, 208):  (None, FLASH),           # FLASH
    (255, 8, 15, 240):  (None, STROBE),          # STROBE
    (255, 8, 55, 200):  (None, FADE),            # FADE
    (255, 8, 23, 232):  (None, SMOOTH),          # SMOOTH
    (255, 8, 223, 32):  ((255, 0, 0), None),            # RED
    (255, 8, 239, 16):  ((252, 94, 3), None),           # RED_2: Lucy's Orange
    (255, 8, 207, 48):  ((255, 69, 0), None),           # RED_3
    (255, 8, 247, 8):   ((255, 99, 71), None),          # RED_4
    (255, 8, 215, 40):  ((255, 200, 0), None),          # RED_5: Lucy's Yellow
    (255, 8, 95, 160):  ((0, 255, 0), None),            # GREEN
    (255, 8, 111, 144): ((0, 128, 0), None),            # GREEN_2
    (255, 8, 79, 176):  ((3, 157, 252), None),          # GREEN_3: Lucy's Light Blue
    (255, 8, 119, 136): ((173, 255, 47), None),         # GREEN_4
    (255, 8, 87, 168):  ((0, 255, 127), None),          # GREEN_5
    (255, 8, 159, 96):  ((0, 0, 255), None),            # BLUE
    (255, 8, 175, 80):  ((0, 0, 128), None),            # BLUE_2
    (255, 8, 143, 112): ((30, 144, 255), None),         # BLUE_3
    (255, 8, 183, 72):  ((252, 3, 215), None),          # BLUE_4: Lucy's Purple
    (255, 8, 151, 104): ((252, 3, 194), None),          # BLUE_5: Lucy's Pink
    (255, 8, 31, 224):  ((255, 255, 255), None),        # WHITE
}

# State
power_on = True
power_off_time = time.monotonic() + AUTO_POWER_OFF_DURATION
selected_mode = ON
selected_color = DEFAULT_COLOR
selected_brightness = DEFAULT_BRIGHTNESS
next_timestamp = 0
flash_state_on = False
rainbow_colorwheel = 0
rainbow_led_index = 0

# Start execution...
builtin_pixel = NeoPixel(BuiltinNeoPixel, 1)
pixels = NeoPixel(LED_OUTPUT_PIN, LED_COUNT, brightness=DEFAULT_BRIGHTNESS)
ir_pulse_decoder = GenericDecode()

gc.collect()
print("Free:", gc.mem_free())
print("Allocated:", gc.mem_alloc())

def fill_all_leds(color):
    builtin_pixel.fill(color)
    pixels.fill(color)

def increment_or_skip_timestamp(timestamp, increment):
    timestamp += increment
    if timestamp < time.monotonic():
        print(".")
        # skip ahead
        timestamp = time.monotonic() + increment
    return timestamp

def colorwheel(pos):
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (int(255 - pos * 3), int(pos * 3), 0)
    elif pos < 170:
        pos -= 85
        return (0, int(255 - pos * 3), int(pos * 3))
    else:
        pos -= 170
        return (int(pos * 3), 0, int(255 - pos * 3))

def select_color(color):
    global selected_color
    selected_color = color
    fill_all_leds(color)

def handle_button(button):
    global power_on
    global selected_mode
    global selected_brightness
    global pixels

    if button == OFF:
        power_on = False
        fill_all_leds((0, 0, 0))
    elif button == ON:
        power_on = True
        pixels.brightness = selected_brightness
        fill_all_leds(selected_color)    
    elif button == BRIGHTNESS_UP:
        selected_brightness += 0.05
        if selected_brightness > 0.4:
            selected_brightness = 0.4
        pixels.brightness = selected_brightness
    elif button == BRIGHTNESS_DOWN:
        selected_brightness -= 0.05
        if selected_brightness <= 0.0:
            selected_brightness = 0.05
        pixels.brightness = selected_brightness
    elif button == FLASH or button == FADE or button == SMOOTH or button == STROBE:
        if selected_mode == button:
            selected_mode = ON
            if power_on:
                pixels.brightness = selected_brightness
                fill_all_leds(selected_color)
        else:
            selected_mode = button

def run_mode_task():
    global next_timestamp
    global power_on

    if not power_on:
        return
    
    timestamp = time.monotonic()

    if timestamp > power_off_time:

        power_on = False
        fill_all_leds((0, 0, 0))
        return

    if selected_mode == ON:
        return
    
    if timestamp > next_timestamp:
        if selected_mode == FLASH:
            global flash_state_on
            flash_state_on = not flash_state_on
            if flash_state_on:
                fill_all_leds(selected_color)
                next_timestamp = increment_or_skip_timestamp(next_timestamp, FLASH_TIME_ON)
            else:
                fill_all_leds((0, 0, 0))
                next_timestamp = increment_or_skip_timestamp(next_timestamp, FLASH_TIME_OFF)
        elif selected_mode == FADE:
            global pixels
            pixels.brightness -= 0.02
            if pixels.brightness <= 0:
                pixels.brightness = 0.4
            next_timestamp = increment_or_skip_timestamp(next_timestamp, FADE_STEP_DURATION)
        elif selected_mode == SMOOTH:
            global rainbow_colorwheel
            rainbow_colorwheel += 1
            rainbow_colorwheel %= 256
            fill_all_leds(colorwheel(rainbow_colorwheel))
            next_timestamp = increment_or_skip_timestamp(next_timestamp, RAINBOW_STEP_DURATION)
        elif selected_mode == STROBE:
            global rainbow_colorwheel
            global rainbow_led_index

            pixel_colorwheel = (rainbow_colorwheel + rainbow_led_index * 256 // LED_COUNT) % 256
            pixels[rainbow_led_index] = colorwheel(pixel_colorwheel)
            rainbow_colorwheel += 1
            rainbow_colorwheel %= 256
            rainbow_led_index += 1
            rainbow_led_index %= LED_COUNT

            next_timestamp = increment_or_skip_timestamp(next_timestamp, 0.02)
        
def run_ir_task(ir_pulse_in):
    global selected_color
    global power_off_time

    pulses = ir_pulse_decoder.read_pulses(ir_pulse_in, blocking=False, max_pulse=100)
    gc.collect()

    if not pulses:
        return
    try:
        code = ir_pulse_decoder.decode_bits(pulses)

        print("Received IR code:", code)
        (color, button) = IR_CODE_TABLE[code]
        print("...color:", color, "button:", button)

        power_off_time = time.monotonic() + AUTO_POWER_OFF_DURATION  # Extend deadline

        if color:
            select_color(color)
        if button is not None:
            handle_button(button)
        print("Free:", gc.mem_free())
        print("Allocated:", gc.mem_alloc())
    except NECRepeatIRMessage:  # unusual short code!
        print("NEC repeat!")
    except IRDecodeException as e:     # failed to decode
        print("Failed to decode: ", e.args)
    except FailedToDecode:
        print("Failed")
    except KeyError:
        print("...unknown code")
    ir_pulse_in.clear()
    gc.collect()
    print("Free:", gc.mem_free())
    print("Allocated:", gc.mem_alloc())

with PulseIn(IR_INPUT_PIN, maxlen=50, idle_state=True) as ir_pulse_in:
    gc.collect()
    print("Free:", gc.mem_free())
    print("Allocated:", gc.mem_alloc())
    
    fill_all_leds(selected_color)

    while True:
        run_ir_task(ir_pulse_in)
        if power_on:
            run_mode_task()

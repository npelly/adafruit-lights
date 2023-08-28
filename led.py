# Nick Pelly August 19, 2023

import adafruit_irremote
import board
import neopixel
import pulseio
import time
import gc


# Board Constants
IR_INPUT_PIN = board.D10
LED_OUTPUT_PIN = board.D5
LED_COUNT = 20

def action_off():
    global power_on
    
    power_on = False
    fill_all_leds((0, 0, 0))

def action_on():
    global power_on

    power_on = True
    fill_all_leds(selected_color)

def action_brightness_up():
    global brightness
    global pixels

    brightness = brightness + 0.05
    if brightness > 0.4:
        brightness = 0.4
    pixels.brightness = brightness

def action_brightness_down():
    global brightness
    global pixels

    brightness = brightness - 0.05
    if brightness <= 0:
        brightness = 0.05
    pixels.brightness = brightness

def action_flash():
    global flash_active
    global fade_active
    
    flash_active = not flash_active
    fade_active = False


def action_fade():
    global fade_active
    global flash_active

    fade_active = not fade_active
    flash_active = False

DEFAULT_COLOR = (252, 3, 194)  # Lucy's Pink
DEFAULT_BRIGHTNESS = 0.2


IR_CODE_TABLE = {
    # Generic IR remote, 5x purchased on amazon August 2023
    (255, 8, 191, 64):  (None, action_off),        # OFF (Black)
    (255, 8, 63, 192):  (None, action_on),     # ON (White)
    (255, 8, 255, 0):   (None, action_brightness_up),   # BRIGHTNESS_UP
    (255, 8, 127, 128): (None, action_brightness_down), # BRIGHTNESS_DOWN
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
    (255, 8, 47, 208):  (None, action_flash),           # FLASH
    (255, 8, 15, 240):  (None, None),          # STROBE
    (255, 8, 55, 200):  (None, action_fade),            # FADE
    (255, 8, 23, 232):  (None, None)           # SMOOTH
}


print(time.monotonic(), "Starting LED controller...")

builtin_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1)
pixels = neopixel.NeoPixel(LED_OUTPUT_PIN, LED_COUNT, brightness=DEFAULT_BRIGHTNESS)
ir_pulse_decoder = adafruit_irremote.GenericDecode()

selected_color = DEFAULT_COLOR
brightness = DEFAULT_BRIGHTNESS
pixels.brightness = brightness

def fill_all_leds(color):
    builtin_pixel.fill(color)
    pixels.fill(color)

def increment_or_skip_timestamp(timestamp, increment):
    timestamp += increment
    if timestamp < time.monotonic():
        # skip ahead
        timestamp = time.monotonic() + increment
    return timestamp

# --- Power ---
power_on = True

# --- Flash ---
FLASH_TIME_ON = 0.2
FLASH_TIME_OFF = 0.1
flash_active = False
flash_state_on = False
flash_next_timestamp = 0

def maybe_run_flash():
    global flash_next_timestamp
    global flash_state_on

    if not flash_active:
        return
    timestamp = time.monotonic()
    if timestamp > flash_next_timestamp:
        flash_state_on = not flash_state_on
        if flash_state_on:
            fill_all_leds(selected_color)
            flash_next_timestamp = increment_or_skip_timestamp(flash_next_timestamp, FLASH_TIME_ON)
        else:
            fill_all_leds((0, 0, 0))
            flash_next_timestamp = increment_or_skip_timestamp(flash_next_timestamp, FLASH_TIME_OFF)

# --- Fade ---
FADE_STEP_DURATION = 0.05
fade_active = False
fade_next_timestamp = 0


def maybe_run_fade():
    global fade_next_timestamp

    if not fade_active:
        return
    timestamp = time.monotonic()
    if timestamp > fade_next_timestamp:
        pixels.brightness -= 0.02
        if pixels.brightness <= 0:
            pixels.brightness = 0.4

        fade_next_timestamp = increment_or_skip_timestamp(fade_next_timestamp, FADE_STEP_DURATION)

def run_tasks(ir_pulse_in):
    run_ir_task(ir_pulse_in)
    if not power_on:
        return
    maybe_run_flash()
    maybe_run_fade()
    #maybe_run_rainbow()


def run_ir_task(ir_pulse_in):
    global selected_color
    global brightness
    global power_on
    
    pulses = ir_pulse_decoder.read_pulses(ir_pulse_in, blocking=False)
    if not pulses:
        return
    try:
        code = ir_pulse_decoder.decode_bits(pulses)
        print("Received IR code:", code)
        (color, action) = IR_CODE_TABLE[code]
        print("...color:", color, "action:", action)

        if color:
            selected_color = color
            fill_all_leds(color)
        if action:
            action()
    except adafruit_irremote.IRNECRepeatException:  # unusual short code!
        print("NEC repeat!")
    except adafruit_irremote.IRDecodeException as e:     # failed to decode
        print("Failed to decode: ", e.args)
    except adafruit_irremote.FailedToDecode:
        print("Failed")
    except KeyError:
        print("...unknown code")
    ir_pulse_in.clear()

with pulseio.PulseIn(IR_INPUT_PIN, maxlen=300, idle_state=True) as ir_pulse_in:
    gc.collect()
    print("Free:", gc.mem_free())
    print("Allocated:", gc.mem_alloc())
    if power_on:
        action_on()
    while True:
        timestamp = time.monotonic()

        run_tasks(ir_pulse_in)


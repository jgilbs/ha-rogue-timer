"""Constants for the Rogue Gym Timer integration.

Protocol confirmed via PacketLogger capture 2026-08-11:
frames are  55 AA 01 <key>  — header, keypress opcode, key code.
No length byte, no checksum, no handshake. Write Command (no response).
"""
from __future__ import annotations

from enum import IntEnum

DOMAIN = "rogue_timer"

SERVICE_UUID = "0000ffe0-0000-1000-8000-00805f9b34fb"
# Confirmed against the physical timer 2026-08-11: FFE1 (write-without-response)
# is the working write target. GATT also exposes FFE2 (write), FFE3 (notify),
# and an FFF1/FFF2 pair — roles unknown, not needed for keypresses.
WRITE_CHAR_UUID = "0000ffe1-0000-1000-8000-00805f9b34fb"

FRAME_HEADER = bytes([0x55, 0xAA])
OP_KEYPRESS = 0x01

# Notifications (RX on FFE1), decoded on hardware 2026-08-11. TBT (Tabata)
# mode ONLY — every other mode is silent; likely built for an app
# Tabata-follow feature. Frame:  01 02 50 <event>  — reading: 01 = report
# opcode, 02 = payload length, 0x50 = payload class (constant so far),
# <event> = code below. Fired by physical keypresses too, so HA can track
# externally-driven state, but only while the timer is in TBT mode.
NOTIFY_HEADER = bytes([0x01, 0x02, 0x50])


class NotifyEvent(IntEnum):
    """Status event codes observed from the timer (last frame byte)."""

    TICK = 0x00   # every second while running
    START = 0x03  # run started
    STOP = 0x05   # run stopped/paused
    EXIT = 0x07   # returned to clock display


class KeyCode(IntEnum):
    """Key codes confirmed from app captures."""

    POWER = 0x00
    MUTE = 0x01
    MODE_INTERVAL = 0x02
    MODE_COUNT = 0x03       # count-up
    MODE_TIMER = 0x04       # countdown timer
    BRIGHTNESS = 0x05       # cycle display brightness
    MODE_FGB = 0x06         # Fight Gone Bad
    MODE_TBT = 0x07         # Tabata
    MODE_CLOCK = 0x08       # clock display
    CLOCK_12_24 = 0x09      # 12/24 hr clock format toggle
    RESET = 0x0A
    PLUS_10 = 0x0B          # +10 quick-add
    START_STOP = 0x0C       # single toggle key
    DOWN = 0x0D
    UP = 0x0E
    RIGHT = 0x0F
    LEFT = 0x10
    EXIT = 0x11
    SET = 0x12              # enter/confirm
    DIGIT_0 = 0x13          # digit N = 0x13 + N
    DIGIT_1 = 0x14
    DIGIT_2 = 0x15
    DIGIT_3 = 0x16
    DIGIT_4 = 0x17
    DIGIT_5 = 0x18
    DIGIT_6 = 0x19
    DIGIT_7 = 0x1A
    DIGIT_8 = 0x1B
    DIGIT_9 = 0x1C
    VOL_UP = 0x1D
    VOL_DOWN = 0x1E
    WARMUP = 0x20
    MODE_EMOM = 0x21


# Command names accepted by the remote entity's send_command service.
COMMANDS: dict[str, KeyCode] = {
    "power": KeyCode.POWER,
    "mute": KeyCode.MUTE,
    "interval": KeyCode.MODE_INTERVAL,
    "count": KeyCode.MODE_COUNT,
    "timer": KeyCode.MODE_TIMER,
    "brightness": KeyCode.BRIGHTNESS,
    "clock": KeyCode.MODE_CLOCK,
    "12_24_hr": KeyCode.CLOCK_12_24,
    "reset": KeyCode.RESET,
    "plus_10": KeyCode.PLUS_10,
    "start_stop": KeyCode.START_STOP,
    "set": KeyCode.SET,
    "enter": KeyCode.SET,
    "up": KeyCode.UP,
    "down": KeyCode.DOWN,
    "left": KeyCode.LEFT,
    "right": KeyCode.RIGHT,
    "vol_up": KeyCode.VOL_UP,
    "vol_down": KeyCode.VOL_DOWN,
    **{f"digit_{n}": KeyCode(0x13 + n) for n in range(10)},
    "warmup": KeyCode.WARMUP,
    "emom": KeyCode.MODE_EMOM,
    "fgb": KeyCode.MODE_FGB,
    "tbt": KeyCode.MODE_TBT,
    "exit": KeyCode.EXIT,
}

CONNECT_ATTEMPTS = 3


# ---------------------------------------------------------------------------
# Macros — named key sequences sent with an inter-key delay.
#
# Countdown presets use Interval mode with 0 sets and 0 rest, which behaves
# as a true countdown (Timer mode only counts up). Field order confirmed on
# hardware 2026-08-11: INTERVAL, SET, sets (2 digits), SET, work (MMSS),
# SET, rest (MMSS), SET. The presets only program the countdown, then EXIT
# back to the clock display — start the program with start_interval (or
# the Start/Stop key). Tune here only — buttons pick these up by name.
# ---------------------------------------------------------------------------


def _digits(value: str) -> tuple[KeyCode, ...]:
    return tuple(KeyCode(0x13 + int(c)) for c in value)


def _countdown(work_mmss: str) -> tuple[KeyCode, ...]:
    return (
        KeyCode.MODE_INTERVAL, KeyCode.SET,
        *_digits("00"), KeyCode.SET,          # sets = 0
        *_digits(work_mmss), KeyCode.SET,     # work = countdown length
        *_digits("0000"), KeyCode.SET,        # rest = 0
        KeyCode.EXIT,                         # back to clock — clears display
    )


MACROS: dict[str, tuple[KeyCode, ...]] = {
    "start_interval": (KeyCode.MODE_INTERVAL, KeyCode.START_STOP),
    "timer_1min": _countdown("0100"),
    "timer_2min": _countdown("0200"),
    "timer_5min": _countdown("0500"),
    "timer_10min": _countdown("1000"),
}

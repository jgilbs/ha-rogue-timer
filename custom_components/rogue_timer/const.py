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
# Sequence confirmed on hardware 2026-08-11: Timer mode, MMSS digits,
# Start — no SET confirm needed. Note: Timer mode counts UP to the set
# target, not down. Tune here only — buttons pick these up by name.
# ---------------------------------------------------------------------------

MACROS: dict[str, tuple[KeyCode, ...]] = {
    "timer_2min": (
        KeyCode.MODE_TIMER,
        KeyCode.DIGIT_2, KeyCode.DIGIT_0, KeyCode.DIGIT_0,
        KeyCode.START_STOP,
    ),
    "timer_5min": (
        KeyCode.MODE_TIMER,
        KeyCode.DIGIT_5, KeyCode.DIGIT_0, KeyCode.DIGIT_0,
        KeyCode.START_STOP,
    ),
    "timer_10min": (
        KeyCode.MODE_TIMER,
        KeyCode.DIGIT_1, KeyCode.DIGIT_0, KeyCode.DIGIT_0, KeyCode.DIGIT_0,
        KeyCode.START_STOP,
    ),
}

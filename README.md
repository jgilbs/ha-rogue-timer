# Rogue Gym Timer for Home Assistant

Command-only BLE "virtual remote" for a Rogue gym timer, using Home Assistant's
Bluetooth stack — works transparently through ESPHome Bluetooth proxies.

## Protocol (confirmed via PacketLogger capture)

FFE0-style UART bridge. Keypress frames, Write Command, no response:

    55 AA 01 <key>

Complete key map (reversed from app captures):

| Code | Key | Code | Key | Code | Key |
|------|-----|------|-----|------|-----|
| 0x00 | Power | 0x0B | +10 | 0x14-0x1C | Digits 1-9 |
| 0x01 | Mute | 0x0C | Start/Stop | 0x1D | Vol Up |
| 0x02 | Interval | 0x0D | Down | 0x1E | Vol Down |
| 0x03 | Count | 0x0E | Up | 0x20 | Warmup |
| 0x04 | Timer | 0x0F | Right | 0x21 | EMOM |
| 0x05 | Brightness | 0x10 | Left | | |
| 0x06 | FGB | 0x11 | Exit | | |
| 0x07 | TBT | 0x12 | Set | | |
| 0x08 | Clock | 0x13 | Digit 0 | | |
| 0x09 | 12/24 Hr | | | | |
| 0x0A | Reset | | | | |

Write characteristic **FFE1 confirmed on hardware** (write-without-response).
Full GATT layout of the timer:

| Char | Handle | Properties | Role |
|------|--------|-----------|------|
| FFF2 | 0x0009 | write | unknown |
| FFF1 | 0x000B | notify | unknown |
| FFE2 | 0x000F | write, write-no-rsp | unknown (unused) |
| FFE1 | 0x0011 | read, write, write-no-rsp, notify | **keypress TX** |
| FFE3 | 0x0014 | notify | unknown |

The timer sends `01 02 50 07` notifications after Exit; meaning not yet
decoded. Timer mode counts **up** to the set target, not down.

## Entities

- Buttons: one per key in the confirmed map — Start/Stop, Power, Mute, Reset,
  every mode (Interval, Count, Timer, FGB, Tabata, Clock, EMOM, Warmup),
  navigation (Up/Down/Left/Right, Set, Exit), Brightness, 12/24 hr, +10, and
  Volume up/down.
- Macro buttons: 2/5/10-minute timer presets (verified on hardware — note the
  timer counts up to the target; sequences live in `MACROS` in `const.py`).
- Remote: `remote.send_command` accepts every named command from `COMMANDS`
  in `const.py` **or raw key codes** (`"0x12"`, `"18"`) — so you can probe
  for new codes from Developer Tools → Actions without touching code.
  `num_repeats` and `delay_secs` are honored.

No state entities: the timer's `01 02 50 07` notification is not yet decoded,
so the integration is transmit-only.

## Adding new keys later

1. Probe with the remote entity: `remote.send_command` with `command: "0x03"`
   etc., watching the timer display.
2. Add the code to `KeyCode` and `COMMANDS` in `const.py`; add a button in
   `button.py` if you want a dedicated dashboard control.

## Install

Copy `custom_components/rogue_timer/` into `config/custom_components/`, restart
HA, then add the integration (Settings → Devices & Services). Keep the Rogue
phone app closed while HA is connected — the timer accepts one central at a time.

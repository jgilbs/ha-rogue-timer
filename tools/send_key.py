#!/usr/bin/env python3
"""Hardware verification tool for the Rogue gym timer.

Interactive keypress sender that talks straight to the timer over your
laptop's Bluetooth — no Home Assistant needed. Verifies the three open
protocol questions:

  1. Write characteristic: is it FFE1 or FFE2?  (`char ffe2` to switch live)
  2. Macro sequences: does mode -> digits -> start actually set a timer?
  3. Notifications: every notify char is subscribed, so any state frames
     the timer sends are printed with their source characteristic.

Usage:
    pip install bleak
    python tools/discover_gatt.py          # find the timer's address first
    python tools/send_key.py <address>

Keep the Rogue phone app closed — the timer accepts one central at a time.

REPL commands:
    power, mute, start_stop, digit_5, ...   any name from const.COMMANDS
    0x12  /  18                             raw key code (hex or decimal)
    macro timer_2min                        run a sequence from const.MACROS
    char ffe2                               switch write target (ffe1 / ffe2 / full UUID)
    resp                                    toggle write-with-response
    list                                    show all names, macros, settings
    quit
"""
import asyncio
import importlib.util
import pathlib
import sys

from bleak import BleakClient

# Load const.py directly from its file so we don't execute the integration's
# __init__.py (which imports homeassistant, not installed on a laptop).
_CONST_PATH = (
    pathlib.Path(__file__).resolve().parent.parent
    / "custom_components"
    / "rogue_timer"
    / "const.py"
)
_spec = importlib.util.spec_from_file_location("rogue_const", _CONST_PATH)
const = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(const)

INTER_KEY_DELAY = 0.15


def _expand_uuid(short: str) -> str:
    """ffe1 -> 0000ffe1-0000-1000-8000-00805f9b34fb; full UUIDs pass through."""
    short = short.strip().lower()
    if len(short) == 4:
        return f"0000{short}-0000-1000-8000-00805f9b34fb"
    return short


def _resolve(token: str) -> int | None:
    token = token.strip().lower()
    if token in const.COMMANDS:
        return int(const.COMMANDS[token])
    try:
        return int(token, 16) if token.startswith("0x") else int(token)
    except ValueError:
        return None


async def repl(address: str) -> None:
    write_uuid = const.WRITE_CHAR_UUID
    with_response = False

    def on_notify(char, data: bytearray) -> None:
        print(f"\n[NOTIFY] {char.uuid} ({char.handle}): {data.hex(' ')}")

    async with BleakClient(address) as client:
        print(f"Connected to {address}")

        # Show write-capable chars so FFE1-vs-FFE2 is answerable at a glance,
        # and subscribe to everything that notifies.
        for service in client.services:
            for char in service.characteristics:
                props = set(char.properties)
                if props & {"write", "write-without-response"}:
                    print(
                        f"  writable: {char.uuid}  handle=0x{char.handle:04x}"
                        f"  [{','.join(sorted(props))}]"
                    )
                if props & {"notify", "indicate"}:
                    try:
                        await client.start_notify(char, on_notify)
                        print(f"  notifying: {char.uuid}  handle=0x{char.handle:04x}")
                    except Exception as err:
                        print(f"  subscribe failed on {char.uuid}: {err}")

        async def send(code: int) -> None:
            frame = const.FRAME_HEADER + bytes([const.OP_KEYPRESS, code])
            print(f"TX {frame.hex(' ')} -> {write_uuid[4:8]}")
            await client.write_gatt_char(write_uuid, frame, response=with_response)

        print(f"\nWrite target {write_uuid[4:8]}, response={with_response}.")
        print("Type a key name / raw code, 'list' for help, 'quit' to exit.\n")

        loop = asyncio.get_running_loop()
        while True:
            try:
                line = (await loop.run_in_executor(None, input, "> ")).strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not line:
                continue
            cmd, _, arg = line.partition(" ")
            cmd = cmd.lower()

            if cmd in ("quit", "exit", "q"):
                break
            if cmd == "list":
                print("Keys:", ", ".join(sorted(const.COMMANDS)))
                print("Macros:", ", ".join(sorted(const.MACROS)))
                print(f"Write target: {write_uuid}, response={with_response}")
                continue
            if cmd == "char":
                write_uuid = _expand_uuid(arg or "ffe1")
                print(f"Write target now {write_uuid}")
                continue
            if cmd == "resp":
                with_response = not with_response
                print(f"Write with response: {with_response}")
                continue
            if cmd == "macro":
                keys = const.MACROS.get(arg.strip().lower())
                if keys is None:
                    print(f"Unknown macro. Have: {', '.join(sorted(const.MACROS))}")
                    continue
                for i, key in enumerate(keys):
                    if i:
                        await asyncio.sleep(INTER_KEY_DELAY)
                    await send(int(key))
                continue

            code = _resolve(cmd)
            if code is None or not 0 <= code <= 0xFF:
                print("Unknown command — 'list' shows key names, or use 0xNN.")
                continue
            await send(code)

        print("Disconnecting.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(repl(sys.argv[1]))

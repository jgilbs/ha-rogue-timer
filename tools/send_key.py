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
    macro timer_2min 0.5                    ...with a custom inter-key delay (s)
    note pressed physical start button      annotate the log (for decoding)
    char ffe2                               switch write target (ffe1 / ffe2 / full UUID)
    resp                                    toggle write-with-response
    list                                    show all names, macros, settings
    quit

Everything (TX, notifications, notes) is appended to tools/notify.log with
wall-clock timestamps for offline frame decoding.
"""
import asyncio
import datetime
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
LOG_PATH = pathlib.Path(__file__).resolve().parent / "notify.log"


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
    last_tx: str = "(none)"
    log_file = LOG_PATH.open("a")

    def log(kind: str, detail: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_file.write(f"{stamp} {kind:<8} {detail}\n")
        log_file.flush()

    def on_notify(char, data: bytearray) -> None:
        short = char.uuid[4:8]
        print(f"\n[NOTIFY] {short} h=0x{char.handle:04x}: {data.hex(' ')}"
              f"   (last TX: {last_tx})")
        log("NOTIFY", f"{short} {data.hex(' ')}  last_tx={last_tx}")

    async with BleakClient(address) as client:
        print(f"Connected to {address}")
        print(f"Logging to {LOG_PATH}")
        log("SESSION", f"connected {address}")

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

        async def send(code: int, label: str | None = None) -> None:
            nonlocal last_tx
            frame = const.FRAME_HEADER + bytes([const.OP_KEYPRESS, code])
            last_tx = label or f"0x{code:02x}"
            print(f"TX {frame.hex(' ')} -> {write_uuid[4:8]}")
            log("TX", f"{frame.hex(' ')}  key={last_tx}")
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
            if cmd == "note":
                log("NOTE", arg)
                print("noted.")
                continue
            if cmd == "macro":
                name, _, delay_arg = arg.strip().lower().partition(" ")
                keys = const.MACROS.get(name)
                if keys is None:
                    print(f"Unknown macro. Have: {', '.join(sorted(const.MACROS))}")
                    continue
                try:
                    delay = float(delay_arg) if delay_arg else INTER_KEY_DELAY
                except ValueError:
                    print(f"Bad delay {delay_arg!r} — use seconds, e.g. 0.5")
                    continue
                log("NOTE", f"macro {name} delay={delay}")
                for i, key in enumerate(keys):
                    if i:
                        await asyncio.sleep(delay)
                    await send(int(key), label=key.name.lower())
                continue

            code = _resolve(cmd)
            if code is None or not 0 <= code <= 0xFF:
                print("Unknown command — 'list' shows key names, or use 0xNN.")
                continue
            await send(code, label=cmd if cmd in const.COMMANDS else None)

        log("SESSION", "disconnect")
        log_file.close()
        print("Disconnecting.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    asyncio.run(repl(sys.argv[1]))

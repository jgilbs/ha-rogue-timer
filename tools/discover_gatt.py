#!/usr/bin/env python3
"""Protocol bring-up helper for the Rogue gym timer.

Run this on any machine with a Bluetooth adapter (laptop is fine — it doesn't
need to go through HA/the proxy for this step):

    pip install bleak
    python discover_gatt.py            # scan and list candidates
    python discover_gatt.py AA:BB:CC:DD:EE:FF   # connect + dump GATT + log notifications

While connected, press buttons on the physical remote / timer keypad. Every
characteristic that supports notify/indicate is subscribed, so state frames
show up here with their source characteristic. That plus an Android
btsnoop_hci.log of the Rogue app gives you everything const.py needs.
"""
import asyncio
import sys

from bleak import BleakClient, BleakScanner


async def scan() -> None:
    print("Scanning 10s for BLE devices...")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    for device, adv in sorted(
        devices.values(), key=lambda d: d[1].rssi, reverse=True
    ):
        marker = "  <-- ?" if "rogue" in (device.name or "").lower() else ""
        print(
            f"{device.address}  rssi={adv.rssi:>4}  "
            f"name={device.name!r}  uuids={adv.service_uuids}{marker}"
        )


async def dump(address: str) -> None:
    def on_notify(char, data: bytearray) -> None:
        print(f"[NOTIFY] {char.uuid} ({char.handle}): {data.hex(' ')}")

    async with BleakClient(address) as client:
        print(f"Connected to {address}\n")
        for service in client.services:
            print(f"Service {service.uuid}  ({service.description})")
            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  Char {char.uuid}  handle={char.handle}  [{props}]")
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char)
                        print(f"    value: {value.hex(' ')}")
                    except Exception as err:
                        print(f"    read failed: {err}")
                if "notify" in char.properties or "indicate" in char.properties:
                    try:
                        await client.start_notify(char, on_notify)
                        print("    subscribed to notifications")
                    except Exception as err:
                        print(f"    subscribe failed: {err}")
        print(
            "\nListening for notifications — press buttons on the timer/remote."
            "\nCtrl-C to exit.\n"
        )
        await asyncio.Event().wait()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(dump(sys.argv[1]))
    else:
        asyncio.run(scan())

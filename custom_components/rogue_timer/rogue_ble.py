"""BLE client for the Rogue gym timer — command-only (virtual remote).

The timer speaks a keypress protocol over an FFE0-style UART bridge:
    55 AA 01 <key>
sent as Write Command. No state is read back; this client only transmits.
Connections route through HA's Bluetooth stack (adapters or ESPHome
proxies) via bleak-retry-connector.
"""
from __future__ import annotations

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

from .const import CONNECT_ATTEMPTS, FRAME_HEADER, OP_KEYPRESS, WRITE_CHAR_UUID, KeyCode

_LOGGER = logging.getLogger(__name__)

DISCONNECT_DELAY = 90  # keep the link up briefly between commands
INTER_KEY_DELAY = 0.15  # verified on hardware — 16-key macros land cleanly


class RogueTimerClient:
    """Owns the BLE connection and sends keypress frames."""

    def __init__(self, ble_device: BLEDevice) -> None:
        self._ble_device = ble_device
        self._client: BleakClientWithServiceCache | None = None
        self._connect_lock = asyncio.Lock()
        self._disconnect_timer: asyncio.TimerHandle | None = None
        self._disconnect_task: asyncio.Task | None = None
        self._loop = asyncio.get_running_loop()

    @property
    def address(self) -> str:
        return self._ble_device.address

    @property
    def name(self) -> str:
        return self._ble_device.name or self._ble_device.address

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Track the freshest BLEDevice (best adapter/proxy path)."""
        self._ble_device = ble_device

    async def _ensure_connected(self) -> BleakClientWithServiceCache:
        if self._client is not None and self._client.is_connected:
            self._reset_disconnect_timer()
            return self._client
        async with self._connect_lock:
            if self._client is not None and self._client.is_connected:
                self._reset_disconnect_timer()
                return self._client
            _LOGGER.debug("%s: connecting", self.name)
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self.name,
                disconnected_callback=self._on_disconnect,
                max_attempts=CONNECT_ATTEMPTS,
                use_services_cache=True,
            )
            self._reset_disconnect_timer()
            return self._client

    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("%s: disconnected", self.name)
        self._client = None

    def _reset_disconnect_timer(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
        self._disconnect_timer = self._loop.call_later(
            DISCONNECT_DELAY, self._start_idle_disconnect
        )

    def _start_idle_disconnect(self) -> None:
        # Hold a reference so the task isn't garbage-collected mid-disconnect.
        self._disconnect_task = asyncio.create_task(self.disconnect())

    async def disconnect(self) -> None:
        if self._disconnect_timer:
            self._disconnect_timer.cancel()
            self._disconnect_timer = None
        if self._client is not None and self._client.is_connected:
            await self._client.disconnect()
        self._client = None

    async def async_test_connection(self) -> bool:
        """Used by the config flow to validate the selected device."""
        try:
            await self._ensure_connected()
        except (BleakError, TimeoutError, OSError) as err:
            _LOGGER.debug("%s: test connection failed: %s", self.name, err)
            return False
        return True

    async def send_key(self, key: KeyCode | int, repeats: int = 1) -> None:
        """Send one keypress frame (optionally repeated)."""
        client = await self._ensure_connected()
        frame = FRAME_HEADER + bytes([OP_KEYPRESS, int(key)])
        for i in range(repeats):
            if i:
                await asyncio.sleep(INTER_KEY_DELAY)
            _LOGGER.debug("%s: TX %s", self.name, frame.hex(" "))
            await client.write_gatt_char(WRITE_CHAR_UUID, frame, response=False)

    async def send_keys(self, keys: list[KeyCode | int]) -> None:
        """Send a sequence of keypresses with a human-like inter-key delay."""
        for i, key in enumerate(keys):
            if i:
                await asyncio.sleep(INTER_KEY_DELAY)
            await self.send_key(key)

"""Remote entity — send named or raw key commands to the timer.

remote.send_command accepts every name in const.COMMANDS (the full
confirmed key map) plus raw codes as hex ("0x12") or decimal ("18"), which
makes probing for unknown key codes possible straight from Developer Tools
without code changes. num_repeats and delay_secs are honored.
"""
from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RogueTimerConfigEntry
from .const import COMMANDS, DOMAIN, KeyCode
from .rogue_ble import RogueTimerClient

_LOGGER = logging.getLogger(__name__)


def _resolve(command: str) -> int:
    name = command.strip().lower()
    if name in COMMANDS:
        return int(COMMANDS[name])
    try:
        code = int(name, 16) if name.startswith("0x") else int(name)
    except ValueError:
        raise ServiceValidationError(
            f"Unknown command '{command}'. Use one of {sorted(COMMANDS)} "
            "or a raw code like '0x12'."
        ) from None
    if not 0 <= code <= 0xFF:
        raise ServiceValidationError(f"Key code {command} out of range 0-255.")
    return code


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RogueTimerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([RogueTimerRemote(entry.runtime_data)])


class RogueTimerRemote(RemoteEntity):
    _attr_has_entity_name = True
    _attr_name = None  # take the device name
    _attr_should_poll = False
    _attr_assumed_state = True

    def __init__(self, client: RogueTimerClient) -> None:
        self._client = client
        self._attr_unique_id = f"{client.address}_remote"
        self._attr_is_on = True
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, client.address)},
            identifiers={(DOMAIN, client.address)},
            name=client.name,
            manufacturer="Rogue Fitness",
            model="Gym Timer",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Power key. The timer has a single power toggle; state is assumed."""
        await self._client.send_key(KeyCode.POWER)
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._client.send_key(KeyCode.POWER)
        self._attr_is_on = False
        self.async_write_ha_state()

    async def async_send_command(
        self, command: Iterable[str], **kwargs: Any
    ) -> None:
        repeats: int = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay: float = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        codes = [_resolve(cmd) for cmd in command]
        for r in range(repeats):
            for i, code in enumerate(codes):
                if r or i:
                    await asyncio.sleep(delay)
                await self._client.send_key(code)

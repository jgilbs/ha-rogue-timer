"""Rogue Gym Timer — BLE virtual remote via HA Bluetooth (adapters + proxies)."""
from __future__ import annotations

import logging

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .rogue_ble import RogueTimerClient

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.REMOTE]

type RogueTimerConfigEntry = ConfigEntry[RogueTimerClient]


async def async_setup_entry(
    hass: HomeAssistant, entry: RogueTimerConfigEntry
) -> bool:
    address: str = entry.data[CONF_ADDRESS]

    ble_device = bluetooth.async_ble_device_from_address(
        hass, address.upper(), connectable=True
    )
    if ble_device is None:
        raise ConfigEntryNotReady(
            f"Rogue timer {address} not currently reachable via any Bluetooth "
            "adapter or proxy"
        )

    client = RogueTimerClient(ble_device)
    entry.runtime_data = client

    @callback
    def _async_device_seen(
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        client.set_ble_device(service_info.device)

    entry.async_on_unload(
        bluetooth.async_register_callback(
            hass,
            _async_device_seen,
            bluetooth.BluetoothCallbackMatcher(
                address=address.upper(), connectable=True
            ),
            bluetooth.BluetoothScanningMode.ACTIVE,
        )
    )

    async def _async_shutdown(_event: Event | None = None) -> None:
        await client.disconnect()

    entry.async_on_unload(
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _async_shutdown)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: RogueTimerConfigEntry
) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.disconnect()
    return unload_ok

"""Config flow: auto-discovery via advertisements plus a manual scan/pick step.

Two entry paths:
  * async_step_bluetooth — HA saw an advertisement matching manifest.json's
    matchers (via a local adapter or an ESPHome Bluetooth proxy) and offers
    the device proactively.
  * async_step_user — the user adds the integration manually and picks the
    timer from a live list of every connectable BLE device currently visible.
    This works even before the real advertised name is known.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import DOMAIN
from .rogue_ble import RogueTimerClient

_LOGGER = logging.getLogger(__name__)


def _format_title(service_info: BluetoothServiceInfoBleak) -> str:
    return service_info.name or service_info.address


class RogueTimerConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Rogue timer."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovery_info: BluetoothServiceInfoBleak | None = None
        self._discovered: dict[str, BluetoothServiceInfoBleak] = {}

    # ------------------------------------------------- automatic discovery

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a device discovered from advertisements."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovery_info = discovery_info
        self.context["title_placeholders"] = {"name": _format_title(discovery_info)}
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm a discovered device."""
        assert self._discovery_info is not None
        info = self._discovery_info
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_validate_and_create(info)
            if result is not None:
                return result
            errors["base"] = "cannot_connect"
        self._set_confirm_only()
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={"name": _format_title(info)},
            errors=errors,
        )

    # ----------------------------------------------------- manual selection

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick from currently-visible connectable devices."""
        errors: dict[str, str] = {}

        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            info = self._discovered[address]
            await self.async_set_unique_id(address, raise_on_progress=False)
            self._abort_if_unique_id_configured()
            result = await self._async_validate_and_create(info)
            if result is not None:
                return result
            errors["base"] = "cannot_connect"

        current_addresses = self._async_current_ids(include_ignore=False)
        for info in bluetooth.async_discovered_service_info(
            self.hass, connectable=True
        ):
            if info.address in current_addresses:
                continue
            self._discovered[info.address] = info

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        # Rogue-looking names first, everything else after, so the timer is
        # findable even if its advertised name turns out not to match "Rogue*".
        def _sort_key(item: tuple[str, BluetoothServiceInfoBleak]) -> tuple[int, str]:
            name = (item[1].name or "").lower()
            return (0 if "rogue" in name else 1, name or item[0])

        options = {
            address: f"{_format_title(info)} ({address})"
            for address, info in sorted(self._discovered.items(), key=_sort_key)
        }

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(options)}
            ),
            errors=errors,
        )

    # ------------------------------------------------------------- creation

    async def _async_validate_and_create(
        self, info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult | None:
        """Try connecting once, then create the entry."""
        client = RogueTimerClient(info.device)
        if not await client.async_test_connection():
            return None
        await client.disconnect()
        return self.async_create_entry(
            title=_format_title(info),
            data={CONF_ADDRESS: info.address},
        )

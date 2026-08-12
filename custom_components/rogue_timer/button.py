"""Button entities — one per confirmed remote key."""
from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import RogueTimerConfigEntry
from .const import DOMAIN, MACROS, KeyCode
from .rogue_ble import RogueTimerClient


@dataclass(frozen=True, kw_only=True)
class RogueButtonDescription(ButtonEntityDescription):
    key_code: KeyCode


@dataclass(frozen=True, kw_only=True)
class RogueMacroDescription(ButtonEntityDescription):
    macro: str  # key into MACROS


BUTTONS: tuple[RogueButtonDescription, ...] = (
    RogueButtonDescription(
        key="start_stop",
        translation_key="start_stop",
        icon="mdi:play-pause",
        key_code=KeyCode.START_STOP,
    ),
    RogueButtonDescription(
        key="power", translation_key="power", icon="mdi:power", key_code=KeyCode.POWER
    ),
    RogueButtonDescription(
        key="mute", translation_key="mute", icon="mdi:volume-off", key_code=KeyCode.MUTE
    ),
    RogueButtonDescription(
        key="interval",
        translation_key="interval",
        icon="mdi:timer-outline",
        key_code=KeyCode.MODE_INTERVAL,
    ),
    RogueButtonDescription(
        key="count",
        translation_key="count",
        icon="mdi:sort-ascending",
        key_code=KeyCode.MODE_COUNT,
    ),
    RogueButtonDescription(
        key="timer",
        translation_key="timer",
        icon="mdi:timer-sand",
        key_code=KeyCode.MODE_TIMER,
    ),
    RogueButtonDescription(
        key="fgb",
        translation_key="fgb",
        icon="mdi:boxing-glove",
        key_code=KeyCode.MODE_FGB,
    ),
    RogueButtonDescription(
        key="tbt",
        translation_key="tbt",
        icon="mdi:timer-refresh-outline",
        key_code=KeyCode.MODE_TBT,
    ),
    RogueButtonDescription(
        key="clock",
        translation_key="clock",
        icon="mdi:clock-outline",
        key_code=KeyCode.MODE_CLOCK,
    ),
    RogueButtonDescription(
        key="reset",
        translation_key="reset",
        icon="mdi:restart",
        key_code=KeyCode.RESET,
    ),
    RogueButtonDescription(
        key="warmup",
        translation_key="warmup",
        icon="mdi:run-fast",
        key_code=KeyCode.WARMUP,
    ),
    RogueButtonDescription(
        key="brightness",
        translation_key="brightness",
        icon="mdi:brightness-6",
        key_code=KeyCode.BRIGHTNESS,
    ),
    RogueButtonDescription(
        key="clock_12_24",
        translation_key="clock_12_24",
        icon="mdi:hours-24",
        key_code=KeyCode.CLOCK_12_24,
    ),
    RogueButtonDescription(
        key="plus_10",
        translation_key="plus_10",
        icon="mdi:numeric-positive-1",
        key_code=KeyCode.PLUS_10,
    ),
    RogueButtonDescription(
        key="emom",
        translation_key="emom",
        icon="mdi:timer-sync-outline",
        key_code=KeyCode.MODE_EMOM,
    ),
    RogueButtonDescription(
        key="vol_up",
        translation_key="vol_up",
        icon="mdi:volume-plus",
        key_code=KeyCode.VOL_UP,
    ),
    RogueButtonDescription(
        key="vol_down",
        translation_key="vol_down",
        icon="mdi:volume-minus",
        key_code=KeyCode.VOL_DOWN,
    ),
    RogueButtonDescription(
        key="up",
        translation_key="up",
        icon="mdi:chevron-up",
        key_code=KeyCode.UP,
    ),
    RogueButtonDescription(
        key="down",
        translation_key="down",
        icon="mdi:chevron-down",
        key_code=KeyCode.DOWN,
    ),
    RogueButtonDescription(
        key="left",
        translation_key="left",
        icon="mdi:chevron-left",
        key_code=KeyCode.LEFT,
    ),
    RogueButtonDescription(
        key="right",
        translation_key="right",
        icon="mdi:chevron-right",
        key_code=KeyCode.RIGHT,
    ),
    RogueButtonDescription(
        key="set",
        translation_key="set",
        icon="mdi:check",
        key_code=KeyCode.SET,
    ),
    RogueButtonDescription(
        key="exit",
        translation_key="exit",
        icon="mdi:keyboard-return",
        key_code=KeyCode.EXIT,
    ),
)


MACRO_BUTTONS: tuple[RogueMacroDescription, ...] = (
    RogueMacroDescription(
        key="start_interval",
        translation_key="start_interval",
        icon="mdi:play",
        macro="start_interval",
    ),
    RogueMacroDescription(
        key="timer_1min",
        translation_key="timer_1min",
        icon="mdi:timer-outline",
        macro="timer_1min",
    ),
    RogueMacroDescription(
        key="timer_2min",
        translation_key="timer_2min",
        icon="mdi:timer-outline",
        macro="timer_2min",
    ),
    RogueMacroDescription(
        key="timer_5min",
        translation_key="timer_5min",
        icon="mdi:timer-outline",
        macro="timer_5min",
    ),
    RogueMacroDescription(
        key="timer_10min",
        translation_key="timer_10min",
        icon="mdi:timer-outline",
        macro="timer_10min",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RogueTimerConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    client = entry.runtime_data
    entities: list[ButtonEntity] = [
        RogueTimerButton(client, description) for description in BUTTONS
    ]
    entities.extend(
        RogueTimerMacroButton(client, description)
        for description in MACRO_BUTTONS
    )
    async_add_entities(entities)


class RogueTimerButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: RogueButtonDescription

    def __init__(
        self, client: RogueTimerClient, description: RogueButtonDescription
    ) -> None:
        self._client = client
        self.entity_description = description
        self._attr_unique_id = f"{client.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, client.address)},
            identifiers={(DOMAIN, client.address)},
            name=client.name,
            manufacturer="Rogue Fitness",
            model="Gym Timer",
        )

    async def async_press(self) -> None:
        await self._client.send_key(self.entity_description.key_code)


class RogueTimerMacroButton(ButtonEntity):
    """Fires a named key sequence from MACROS."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: RogueMacroDescription

    def __init__(
        self, client: RogueTimerClient, description: RogueMacroDescription
    ) -> None:
        self._client = client
        self.entity_description = description
        self._attr_unique_id = f"{client.address}_{description.key}"
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, client.address)},
            identifiers={(DOMAIN, client.address)},
            name=client.name,
            manufacturer="Rogue Fitness",
            model="Gym Timer",
        )

    async def async_press(self) -> None:
        await self._client.send_keys(list(MACROS[self.entity_description.macro]))

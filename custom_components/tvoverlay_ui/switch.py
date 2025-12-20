"""Switch platform for TvOverlay."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TvOverlayApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlaySwitchEntityDescription(SwitchEntityDescription):
    """Describes TvOverlay switch entity."""

    api_key: str
    endpoint: str  # "notifications" or "settings"


SWITCH_DESCRIPTIONS: tuple[TvOverlaySwitchEntityDescription, ...] = (
    TvOverlaySwitchEntityDescription(
        key="display_clock",
        translation_key="display_clock",
        name="Display Clock",
        icon="mdi:clock-outline",
        device_class=SwitchDeviceClass.SWITCH,
        api_key="clockOverlayVisibility",
        endpoint="overlay",
    ),
    TvOverlaySwitchEntityDescription(
        key="display_notifications",
        translation_key="display_notifications",
        name="Display Notifications",
        icon="mdi:message-badge-outline",
        device_class=SwitchDeviceClass.SWITCH,
        api_key="displayNotifications",
        endpoint="notifications",
    ),
    TvOverlaySwitchEntityDescription(
        key="display_fixed_notifications",
        translation_key="display_fixed_notifications",
        name="Display Fixed Notifications",
        icon="mdi:pin-outline",
        device_class=SwitchDeviceClass.SWITCH,
        api_key="displayFixedNotifications",
        endpoint="notifications",
    ),
    TvOverlaySwitchEntityDescription(
        key="pixel_shift",
        translation_key="pixel_shift",
        name="Pixel Shift",
        icon="mdi:television-shimmer",
        device_class=SwitchDeviceClass.SWITCH,
        api_key="pixelShift",
        endpoint="settings",
    ),
    TvOverlaySwitchEntityDescription(
        key="debug_mode",
        translation_key="debug_mode",
        name="Debug Mode",
        icon="mdi:bug-outline",
        device_class=SwitchDeviceClass.SWITCH,
        api_key="displayDebug",
        endpoint="settings",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TvOverlay switches."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: TvOverlayApiClient = data["client"]
    device_name: str = data["name"]

    entities = [
        TvOverlaySwitch(
            client=client,
            entry_id=entry.entry_id,
            device_name=device_name,
            description=description,
        )
        for description in SWITCH_DESCRIPTIONS
    ]

    async_add_entities(entities)


class TvOverlaySwitch(SwitchEntity):
    """Representation of a TvOverlay switch."""

    entity_description: TvOverlaySwitchEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        client: TvOverlayApiClient,
        entry_id: str,
        device_name: str,
        description: TvOverlaySwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        self.entity_description = description
        self._client = client
        self._entry_id = entry_id
        self._device_name = device_name
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_is_on = True  # Assume on by default

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._device_name,
            manufacturer="TvOverlay",
            model="Android TV Overlay",
        )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        await self._set_state(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        await self._set_state(False)

    async def _set_state(self, state: bool) -> None:
        """Set the switch state."""
        # Clock visibility uses 0-95 range instead of boolean
        if self.entity_description.key == "display_clock":
            value = 95 if state else 0
        else:
            value = state

        data = {self.entity_description.api_key: value}

        if self.entity_description.endpoint == "notifications":
            success = await self._client.set_notifications(data)
        elif self.entity_description.endpoint == "overlay":
            success = await self._client.set_overlay(data)
        else:  # settings
            success = await self._client.set_settings(data)

        if success:
            self._attr_is_on = state
            self.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to set %s to %s",
                self.entity_description.key,
                state,
            )

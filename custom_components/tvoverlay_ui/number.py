"""Number platform for TvOverlay."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TvOverlayApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class TvOverlayNumberEntityDescription(NumberEntityDescription):
    """Describes TvOverlay number entity."""

    api_key: str
    endpoint: str  # "overlay" or "notifications"


NUMBER_DESCRIPTIONS: tuple[TvOverlayNumberEntityDescription, ...] = (
    TvOverlayNumberEntityDescription(
        key="clock_visibility",
        translation_key="clock_visibility",
        name="Clock Visibility",
        icon="mdi:clock-digital",
        native_min_value=0,
        native_max_value=95,
        native_step=1,
        mode=NumberMode.SLIDER,
        api_key="clockOverlayVisibility",
        endpoint="overlay",
    ),
    TvOverlayNumberEntityDescription(
        key="overlay_visibility",
        translation_key="overlay_visibility",
        name="Overlay Visibility",
        icon="mdi:layers-outline",
        native_min_value=0,
        native_max_value=95,
        native_step=1,
        mode=NumberMode.SLIDER,
        api_key="overlayVisibility",
        endpoint="overlay",
    ),
    TvOverlayNumberEntityDescription(
        key="fixed_notifications_visibility",
        translation_key="fixed_notifications_visibility",
        name="Fixed Notifications Visibility",
        icon="mdi:pin-outline",
        native_min_value=-1,
        native_max_value=95,
        native_step=1,
        mode=NumberMode.SLIDER,
        api_key="fixedNotificationsVisibility",
        endpoint="notifications",
    ),
    TvOverlayNumberEntityDescription(
        key="notification_duration",
        translation_key="notification_duration",
        name="Notification Duration",
        icon="mdi:timer-sand",
        native_min_value=1,
        native_max_value=60,
        native_step=1,
        native_unit_of_measurement="s",
        mode=NumberMode.SLIDER,
        api_key="notificationDuration",
        endpoint="notifications",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TvOverlay number entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: TvOverlayApiClient = data["client"]
    device_name: str = data["name"]

    entities = [
        TvOverlayNumber(
            client=client,
            entry_id=entry.entry_id,
            device_name=device_name,
            description=description,
        )
        for description in NUMBER_DESCRIPTIONS
    ]

    async_add_entities(entities)


class TvOverlayNumber(NumberEntity):
    """Representation of a TvOverlay number entity."""

    entity_description: TvOverlayNumberEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        client: TvOverlayApiClient,
        entry_id: str,
        device_name: str,
        description: TvOverlayNumberEntityDescription,
    ) -> None:
        """Initialize the number entity."""
        self.entity_description = description
        self._client = client
        self._entry_id = entry_id
        self._device_name = device_name
        self._attr_unique_id = f"{entry_id}_{description.key}"
        # Set default values
        if description.key == "notification_duration":
            self._attr_native_value = 5.0
        elif description.key == "fixed_notifications_visibility":
            self._attr_native_value = -1.0
        else:
            self._attr_native_value = 0.0

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._device_name,
            manufacturer="TvOverlay",
            model="Android TV Overlay",
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        int_value = int(value)
        data = {self.entity_description.api_key: int_value}

        if self.entity_description.endpoint == "overlay":
            success = await self._client.set_overlay(data)
        else:  # notifications
            success = await self._client.set_notifications(data)

        if success:
            self._attr_native_value = value
            self.async_write_ha_state()
        else:
            _LOGGER.error(
                "Failed to set %s to %s",
                self.entity_description.key,
                value,
            )

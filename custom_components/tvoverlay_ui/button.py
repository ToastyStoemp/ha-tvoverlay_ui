"""Button platform for TvOverlay."""
from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TvOverlayApiClient
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


BUTTON_DESCRIPTIONS: tuple[ButtonEntityDescription, ...] = (
    ButtonEntityDescription(
        key="clear_notifications",
        translation_key="clear_notifications",
        name="Clear Notifications",
        icon="mdi:notification-clear-all",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TvOverlay buttons."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: TvOverlayApiClient = data["client"]
    device_name: str = data["name"]

    entities = [
        TvOverlayButton(
            client=client,
            entry_id=entry.entry_id,
            device_name=device_name,
            description=description,
        )
        for description in BUTTON_DESCRIPTIONS
    ]

    async_add_entities(entities)


class TvOverlayButton(ButtonEntity):
    """Representation of a TvOverlay button."""

    _attr_has_entity_name = True

    def __init__(
        self,
        client: TvOverlayApiClient,
        entry_id: str,
        device_name: str,
        description: ButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        self.entity_description = description
        self._client = client
        self._entry_id = entry_id
        self._device_name = device_name
        self._attr_unique_id = f"{entry_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._device_name,
            manufacturer="TvOverlay",
            model="Android TV Overlay",
        )

    async def async_press(self) -> None:
        """Handle the button press."""
        if self.entity_description.key == "clear_notifications":
            # Send an empty notification to clear the display
            success = await self._client.send_notification({})
            if not success:
                _LOGGER.error("Failed to clear notifications")

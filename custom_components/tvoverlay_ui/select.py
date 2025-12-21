"""Select platform for TvOverlay."""
from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import TvOverlayApiClient
from .const import (
    DOMAIN,
    VALID_CORNERS,
    VALID_SHAPES,
)

_LOGGER = logging.getLogger(__name__)

# Notification layout options
VALID_LAYOUTS = ["Default", "Minimalist", "Icon Only"]


@dataclass(frozen=True, kw_only=True)
class TvOverlaySelectEntityDescription(SelectEntityDescription):
    """Describes TvOverlay select entity."""

    options_list: list[str]
    storage_key: str
    api_key: str | None = None
    endpoint: str | None = None


SELECT_DESCRIPTIONS: tuple[TvOverlaySelectEntityDescription, ...] = (
    TvOverlaySelectEntityDescription(
        key="notification_layout",
        translation_key="notification_layout",
        name="Notification Layout",
        icon="mdi:page-layout-body",
        options_list=VALID_LAYOUTS,
        storage_key="notification_layout",
        api_key="notificationLayoutName",
        endpoint="notifications",
    ),
    TvOverlaySelectEntityDescription(
        key="default_corner",
        translation_key="default_corner",
        name="Default Corner",
        icon="mdi:page-layout-header-footer",
        options_list=VALID_CORNERS,
        storage_key="default_corner",
    ),
    TvOverlaySelectEntityDescription(
        key="default_shape",
        translation_key="default_shape",
        name="Default Shape",
        icon="mdi:shape-outline",
        options_list=VALID_SHAPES,
        storage_key="default_shape",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TvOverlay select entities."""
    data = hass.data[DOMAIN][entry.entry_id]
    client: TvOverlayApiClient = data["client"]
    device_name: str = data["name"]

    entities = [
        TvOverlaySelect(
            client=client,
            entry_id=entry.entry_id,
            device_name=device_name,
            description=description,
            entry_data=data,
        )
        for description in SELECT_DESCRIPTIONS
    ]

    async_add_entities(entities)


class TvOverlaySelect(SelectEntity):
    """Representation of a TvOverlay select entity."""

    entity_description: TvOverlaySelectEntityDescription
    _attr_has_entity_name = True

    def __init__(
        self,
        client: TvOverlayApiClient,
        entry_id: str,
        device_name: str,
        description: TvOverlaySelectEntityDescription,
        entry_data: dict,
    ) -> None:
        """Initialize the select entity."""
        self.entity_description = description
        self._client = client
        self._entry_id = entry_id
        self._device_name = device_name
        self._entry_data = entry_data
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_options = description.options_list

        # Set default value
        if description.key == "notification_layout":
            self._attr_current_option = entry_data.get("notification_layout", "Default")
        elif description.key == "default_corner":
            self._attr_current_option = entry_data.get("default_corner", "top_end")
        elif description.key == "default_shape":
            self._attr_current_option = entry_data.get("default_shape", "rounded")

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=self._device_name,
            manufacturer="TvOverlay",
            model="Android TV Overlay",
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        # If this entity has an API endpoint, call it
        if self.entity_description.api_key and self.entity_description.endpoint:
            data = {self.entity_description.api_key: option}

            if self.entity_description.endpoint == "notifications":
                success = await self._client.set_notifications(data)
            else:
                success = False

            if not success:
                _LOGGER.error(
                    "Failed to set %s to %s",
                    self.entity_description.key,
                    option,
                )
                return

        self._attr_current_option = option
        self._entry_data[self.entity_description.storage_key] = option
        self.async_write_ha_state()

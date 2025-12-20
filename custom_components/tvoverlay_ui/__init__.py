"""The TvOverlay integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

from .api import TvOverlayApiClient
from .const import (
    ATTR_BACKGROUND_COLOR,
    ATTR_BACKGROUND_OPACITY,
    ATTR_BORDER_COLOR,
    ATTR_CORNER,
    ATTR_DEVICE_ID,
    ATTR_DURATION,
    ATTR_EXPIRATION,
    ATTR_HOST,
    ATTR_ICON,
    ATTR_ICON_COLOR,
    ATTR_ID,
    ATTR_LARGE_ICON,
    ATTR_MEDIA_TYPE,
    ATTR_MEDIA_URL,
    ATTR_MESSAGE,
    ATTR_MESSAGE_COLOR,
    ATTR_SHAPE,
    ATTR_SMALL_ICON,
    ATTR_SMALL_ICON_COLOR,
    ATTR_SOURCE,
    ATTR_TITLE,
    ATTR_VISIBLE,
    DEFAULT_PORT,
    DOMAIN,
    PLATFORMS,
    SERVICE_CLEAR_FIXED,
    SERVICE_NOTIFY,
    SERVICE_NOTIFY_FIXED,
    STORAGE_KEY,
    STORAGE_VERSION,
    VALID_CORNERS,
    VALID_SHAPES,
)

_LOGGER = logging.getLogger(__name__)


# Common color names to hex mapping
COLOR_NAMES: dict[str, str] = {
    "red": "#FF0000",
    "green": "#00FF00",
    "blue": "#0000FF",
    "white": "#FFFFFF",
    "black": "#000000",
    "yellow": "#FFFF00",
    "orange": "#FFA500",
    "purple": "#800080",
    "pink": "#FFC0CB",
    "cyan": "#00FFFF",
    "magenta": "#FF00FF",
    "gray": "#808080",
    "grey": "#808080",
    "brown": "#A52A2A",
    "lime": "#00FF00",
    "navy": "#000080",
    "teal": "#008080",
    "maroon": "#800000",
    "olive": "#808000",
    "silver": "#C0C0C0",
    "aqua": "#00FFFF",
    "gold": "#FFD700",
    "coral": "#FF7F50",
    "salmon": "#FA8072",
    "violet": "#EE82EE",
    "indigo": "#4B0082",
    "turquoise": "#40E0D0",
}


def _normalize_hex_color(color: str | None) -> str | None:
    """Normalize color to hex string (accepts hex or color names)."""
    if color is None or not color:
        return None
    color = color.strip().lower()
    # Check if it's a color name
    if color in COLOR_NAMES:
        return COLOR_NAMES[color]
    # Handle hex format
    if not color.startswith("#"):
        color = f"#{color}"
    return color.upper()


def _hex_with_alpha(color: str | None, opacity: int | None) -> str | None:
    """Add alpha channel to hex color string (#RRGGBB -> #AARRGGBB)."""
    if color is None or not color:
        return None
    color = _normalize_hex_color(color)
    if color is None:
        return None
    # Remove # prefix, get RGB part
    rgb = color.lstrip("#")
    if len(rgb) == 6:
        # Convert opacity 0-100 to alpha 0-255
        alpha = int((opacity if opacity is not None else 40) * 255 / 100)
        return f"#{alpha:02X}{rgb}"
    return color


# Service schemas - device_id or host required
NOTIFY_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(ATTR_DEVICE_ID): cv.string,
            vol.Optional(ATTR_HOST): cv.string,
            vol.Optional(ATTR_ID): cv.string,
            vol.Optional(ATTR_TITLE): cv.string,
            vol.Optional(ATTR_MESSAGE): cv.string,
            vol.Optional(ATTR_SOURCE): cv.string,
            vol.Optional(ATTR_SMALL_ICON): cv.string,
            vol.Optional(ATTR_SMALL_ICON_COLOR): cv.string,
            vol.Optional(ATTR_LARGE_ICON): cv.string,
            vol.Optional(ATTR_MEDIA_TYPE): vol.In(["none", "image", "video"]),
            vol.Optional(ATTR_MEDIA_URL): cv.string,
            vol.Optional(ATTR_CORNER): vol.In(VALID_CORNERS),
            vol.Optional(ATTR_DURATION): cv.positive_int,
        },
        cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_HOST),
    )
)

NOTIFY_FIXED_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(ATTR_DEVICE_ID): cv.string,
            vol.Optional(ATTR_HOST): cv.string,
            vol.Optional(ATTR_ID): cv.string,
            vol.Optional(ATTR_VISIBLE, default=True): cv.boolean,
            vol.Optional(ATTR_ICON): cv.string,
            vol.Optional(ATTR_MESSAGE): cv.string,
            vol.Optional(ATTR_MESSAGE_COLOR): cv.string,
            vol.Optional(ATTR_ICON_COLOR): cv.string,
            vol.Optional(ATTR_BORDER_COLOR): cv.string,
            vol.Optional(ATTR_BACKGROUND_COLOR): cv.string,
            vol.Optional(ATTR_BACKGROUND_OPACITY): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            ),
            vol.Optional(ATTR_SHAPE): vol.In(VALID_SHAPES),
            vol.Optional(ATTR_EXPIRATION): cv.string,
        },
        cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_HOST),
    )
)

CLEAR_FIXED_SCHEMA = vol.Schema(
    vol.All(
        {
            vol.Optional(ATTR_DEVICE_ID): cv.string,
            vol.Optional(ATTR_HOST): cv.string,
            vol.Required(ATTR_ID): cv.string,
        },
        cv.has_at_least_one_key(ATTR_DEVICE_ID, ATTR_HOST),
    )
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TvOverlay from a config entry."""
    host = entry.data[CONF_HOST]
    port = entry.data[CONF_PORT]
    name = entry.data.get(CONF_NAME, host)

    session = async_get_clientsession(hass)
    client = TvOverlayApiClient(host, port, session)

    # Initialize storage for notification IDs
    store = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
    stored_data = await store.async_load()
    notification_ids: list[str] = stored_data.get("ids", []) if stored_data else []

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "name": name,
        "host": host,
        "port": port,
        "store": store,
        "notification_ids": notification_ids,
        "update_listeners": [],
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services if not already registered
    if not hass.services.has_service(DOMAIN, SERVICE_NOTIFY):
        await _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

        # Unregister services if no more entries
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_NOTIFY)
            hass.services.async_remove(DOMAIN, SERVICE_NOTIFY_FIXED)
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_FIXED)

    return unload_ok


def _parse_host_port(host_string: str) -> tuple[str, int]:
    """Parse host:port string into host and port."""
    if ":" in host_string:
        parts = host_string.rsplit(":", 1)
        try:
            return parts[0], int(parts[1])
        except ValueError:
            return host_string, DEFAULT_PORT
    return host_string, DEFAULT_PORT


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register TvOverlay services."""

    def _get_client_from_device_id(device_id: str) -> TvOverlayApiClient | None:
        """Get the API client from a device registry ID."""
        device_registry = dr.async_get(hass)
        device = device_registry.async_get(device_id)

        if device is None:
            return None

        # Find the config entry for this device
        for identifier in device.identifiers:
            if identifier[0] == DOMAIN:
                entry_id = identifier[1]
                if entry_id in hass.data[DOMAIN]:
                    return hass.data[DOMAIN][entry_id]["client"]

        return None

    def _get_client_from_name_or_host(name_or_host: str) -> TvOverlayApiClient | None:
        """Get the API client by name or host."""
        for entry_data in hass.data[DOMAIN].values():
            if entry_data.get("name") == name_or_host or entry_data.get("host") == name_or_host:
                return entry_data["client"]
        return None

    def _get_client(call_data: dict[str, Any]) -> TvOverlayApiClient | None:
        """Get the API client from service call data."""
        device_id = call_data.get(ATTR_DEVICE_ID)
        host = call_data.get(ATTR_HOST)

        # Try device_id first (from device selector)
        if device_id:
            # Try as device registry ID
            client = _get_client_from_device_id(device_id)
            if client:
                return client

            # Try as name or host string
            client = _get_client_from_name_or_host(device_id)
            if client:
                return client

        # Try manual host:port
        if host:
            # Check if it matches a configured device
            parsed_host, parsed_port = _parse_host_port(host)
            for entry_data in hass.data[DOMAIN].values():
                if entry_data.get("host") == parsed_host and entry_data.get("port") == parsed_port:
                    return entry_data["client"]

            # Create a new client for unconfigured device
            session = async_get_clientsession(hass)
            return TvOverlayApiClient(parsed_host, parsed_port, session)

        return None

    async def async_notify(call: ServiceCall) -> None:
        """Send a notification."""
        client = _get_client(call.data)

        if client is None:
            _LOGGER.error(
                "TvOverlay device not found. Provide device_id or host:port"
            )
            return

        data = _build_notification_data(call.data)
        await client.send_notification(data)

    def _get_entry_data_from_client(client: TvOverlayApiClient) -> dict[str, Any] | None:
        """Get the entry data for a client."""
        for entry_data in hass.data[DOMAIN].values():
            if entry_data.get("client") is client:
                return entry_data
        return None

    async def _add_notification_id(entry_data: dict[str, Any], notification_id: str) -> None:
        """Add a notification ID to storage and notify listeners."""
        ids = entry_data["notification_ids"]
        if notification_id not in ids:
            ids.append(notification_id)
            await entry_data["store"].async_save({"ids": ids})
            # Notify listeners (sensors) of the update
            for listener in entry_data["update_listeners"]:
                listener()

    async def _remove_notification_id(entry_data: dict[str, Any], notification_id: str) -> None:
        """Remove a notification ID from storage and notify listeners."""
        ids = entry_data["notification_ids"]
        if notification_id in ids:
            ids.remove(notification_id)
            await entry_data["store"].async_save({"ids": ids})
            # Notify listeners (sensors) of the update
            for listener in entry_data["update_listeners"]:
                listener()

    async def async_notify_fixed(call: ServiceCall) -> None:
        """Send a fixed notification."""
        client = _get_client(call.data)

        if client is None:
            _LOGGER.error(
                "TvOverlay device not found. Provide device_id or host:port"
            )
            return

        data = _build_fixed_notification_data(call.data)
        success = await client.send_fixed_notification(data)

        # Store the notification ID if successful and ID was provided
        if success and data.get("id"):
            entry_data = _get_entry_data_from_client(client)
            if entry_data:
                await _add_notification_id(entry_data, data["id"])

    async def async_clear_fixed(call: ServiceCall) -> None:
        """Clear a fixed notification."""
        client = _get_client(call.data)

        if client is None:
            _LOGGER.error(
                "TvOverlay device not found. Provide device_id or host:port"
            )
            return

        notification_id = call.data[ATTR_ID]
        success = await client.clear_fixed_notification(notification_id)

        # Remove the notification ID from storage if successful
        if success:
            entry_data = _get_entry_data_from_client(client)
            if entry_data:
                await _remove_notification_id(entry_data, notification_id)

    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY, async_notify, schema=NOTIFY_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY_FIXED, async_notify_fixed, schema=NOTIFY_FIXED_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_CLEAR_FIXED, async_clear_fixed, schema=CLEAR_FIXED_SCHEMA
    )


def _build_notification_data(data: dict[str, Any]) -> dict[str, Any]:
    """Build notification payload from service call data."""
    payload: dict[str, Any] = {}

    # Simple string fields
    simple_fields = {
        ATTR_ID: "id",
        ATTR_TITLE: "title",
        ATTR_MESSAGE: "message",
        ATTR_SOURCE: "source",
        ATTR_CORNER: "corner",
        ATTR_DURATION: "duration",
    }

    for attr, api_key in simple_fields.items():
        if attr in data and data[attr] is not None:
            payload[api_key] = data[attr]

    # Small icon
    if ATTR_SMALL_ICON in data and data[ATTR_SMALL_ICON]:
        payload["smallIcon"] = data[ATTR_SMALL_ICON]

    # Small icon color (hex string or color name)
    small_icon_color = _normalize_hex_color(data.get(ATTR_SMALL_ICON_COLOR))
    if small_icon_color:
        payload["smallIconColor"] = small_icon_color

    # Large icon
    if ATTR_LARGE_ICON in data and data[ATTR_LARGE_ICON]:
        payload["largeIcon"] = data[ATTR_LARGE_ICON]

    # Media (image or video based on type)
    media_type = data.get(ATTR_MEDIA_TYPE)
    media_url = data.get(ATTR_MEDIA_URL)
    if media_url and media_type and media_type != "none":
        if media_type == "image":
            payload["image"] = media_url
        elif media_type == "video":
            payload["video"] = media_url

    return payload


def _build_fixed_notification_data(data: dict[str, Any]) -> dict[str, Any]:
    """Build fixed notification payload from service call data."""
    payload: dict[str, Any] = {}

    # Simple fields
    simple_fields = {
        ATTR_ID: "id",
        ATTR_VISIBLE: "visible",
        ATTR_MESSAGE: "message",
        ATTR_SHAPE: "shape",
        ATTR_EXPIRATION: "expiration",
    }

    for attr, api_key in simple_fields.items():
        if attr in data and data[attr] is not None:
            payload[api_key] = data[attr]

    # Icon
    if ATTR_ICON in data and data[ATTR_ICON]:
        payload["icon"] = data[ATTR_ICON]

    # Colors (hex strings)
    message_color = _normalize_hex_color(data.get(ATTR_MESSAGE_COLOR))
    if message_color:
        payload["messageColor"] = message_color

    icon_color = _normalize_hex_color(data.get(ATTR_ICON_COLOR))
    if icon_color:
        payload["iconColor"] = icon_color

    border_color = _normalize_hex_color(data.get(ATTR_BORDER_COLOR))
    if border_color:
        payload["borderColor"] = border_color

    # Background color with opacity (ARGB format)
    bg_color = data.get(ATTR_BACKGROUND_COLOR)
    if bg_color:
        bg_opacity = data.get(ATTR_BACKGROUND_OPACITY)
        payload["backgroundColor"] = _hex_with_alpha(bg_color, bg_opacity)

    return payload

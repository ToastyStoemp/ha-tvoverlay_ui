"""API client for TvOverlay."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import (
    ENDPOINT_NOTIFY,
    ENDPOINT_NOTIFY_FIXED,
    ENDPOINT_SET_NOTIFICATIONS,
    ENDPOINT_SET_OVERLAY,
    ENDPOINT_SET_SETTINGS,
)

_LOGGER = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 10


class TvOverlayApiError(Exception):
    """Exception for TvOverlay API errors."""


class TvOverlayConnectionError(TvOverlayApiError):
    """Exception for connection errors."""


class TvOverlayApiClient:
    """API client for TvOverlay devices."""

    def __init__(
        self,
        host: str,
        port: int,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        """Initialize the API client."""
        self._host = host
        self._port = port
        self._session = session
        self._base_url = f"http://{host}:{port}"

    @property
    def host(self) -> str:
        """Return the host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the port."""
        return self._port

    async def _request(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> bool:
        """Make a POST request to the TvOverlay API."""
        url = f"{self._base_url}{endpoint}"

        try:
            if self._session is None or self._session.closed:
                timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, json=data or {}) as response:
                        if response.status == 200:
                            return True
                        _LOGGER.error(
                            "TvOverlay API error: %s - %s",
                            response.status,
                            await response.text(),
                        )
                        return False
            else:
                async with self._session.post(url, json=data or {}) as response:
                    if response.status == 200:
                        return True
                    _LOGGER.error(
                        "TvOverlay API error: %s - %s",
                        response.status,
                        await response.text(),
                    )
                    return False
        except asyncio.TimeoutError as err:
            raise TvOverlayConnectionError(
                f"Timeout connecting to TvOverlay at {self._host}:{self._port}"
            ) from err
        except aiohttp.ClientError as err:
            raise TvOverlayConnectionError(
                f"Error connecting to TvOverlay at {self._host}:{self._port}: {err}"
            ) from err

    async def test_connection(self) -> bool:
        """Test the connection to the TvOverlay device."""
        try:
            # Send an empty notification request to test connectivity
            # This should succeed even without any payload
            return await self._request(ENDPOINT_NOTIFY, {})
        except TvOverlayConnectionError:
            return False

    async def send_notification(self, data: dict[str, Any]) -> bool:
        """Send a notification to the TvOverlay device."""
        return await self._request(ENDPOINT_NOTIFY, data)

    async def send_fixed_notification(self, data: dict[str, Any]) -> bool:
        """Send a fixed notification to the TvOverlay device."""
        return await self._request(ENDPOINT_NOTIFY_FIXED, data)

    async def clear_fixed_notification(self, notification_id: str) -> bool:
        """Clear a fixed notification by ID."""
        return await self._request(
            ENDPOINT_NOTIFY_FIXED,
            {"id": notification_id, "visible": False},
        )

    async def set_overlay(self, data: dict[str, Any]) -> bool:
        """Set overlay settings."""
        return await self._request(ENDPOINT_SET_OVERLAY, data)

    async def set_notifications(self, data: dict[str, Any]) -> bool:
        """Set notification settings."""
        return await self._request(ENDPOINT_SET_NOTIFICATIONS, data)

    async def set_settings(self, data: dict[str, Any]) -> bool:
        """Set general settings."""
        return await self._request(ENDPOINT_SET_SETTINGS, data)

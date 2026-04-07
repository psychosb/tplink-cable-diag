"""Data update coordinator for TP-Link Cable Diagnostics."""

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .switch_client import TpLinkSwitchClient

_LOGGER = logging.getLogger(__name__)


class TpLinkCableDiagCoordinator(DataUpdateCoordinator):
    """Coordinator to manage cable diagnostic data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TpLinkSwitchClient,
        scan_interval_minutes: int = DEFAULT_SCAN_INTERVAL,
    ):
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_interval_minutes),
        )

    async def _async_update_data(self) -> dict:
        """Fetch cable test data from the switch."""
        try:
            results = await self.client.async_run_test()
        except Exception as err:
            raise UpdateFailed(f"Error communicating with switch: {err}") from err

        if results is None:
            raise UpdateFailed("Failed to get cable test results from switch")

        return results

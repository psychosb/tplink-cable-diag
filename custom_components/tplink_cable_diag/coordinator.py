"""Data update coordinator for TP-Link Cable Diagnostics."""

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN
from .switch_client import TpLinkSwitchClient

_LOGGER = logging.getLogger(__name__)


class TpLinkCableDiagCoordinator(DataUpdateCoordinator):
    """Coordinator to manage cable diagnostic data updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: TpLinkSwitchClient,
    ):
        self.client = client
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,
        )

    async def _async_update_data(self) -> dict:
        """Fetch cable test data from the switch."""
        # Check which ports are safe to test (no active traffic)
        safe_ports = await self._get_safe_ports()

        if not safe_ports:
            _LOGGER.info("All ports have active traffic, skipping cable test")
            if self.data:
                return self.data
            raise UpdateFailed("All ports busy, cannot run cable test")

        _LOGGER.info("Running cable test on safe ports: %s", safe_ports)

        try:
            results = await self.client.async_run_test(safe_ports)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with switch: {err}") from err

        if results is None:
            raise UpdateFailed("Failed to get cable test results from switch")

        # Merge with previous results for skipped ports
        if self.data:
            for port in range(1, self.client.max_ports + 1):
                if port not in safe_ports and port in self.data:
                    results[port] = self.data[port]
                    results[port]["skipped"] = True

        return results

    async def _get_safe_ports(self) -> list[int]:
        """Determine which ports are safe to test by checking link status.

        Uses the tplink_easy_smart binary sensors to check port state.
        If a port is down (off), it's always safe to test.
        If a port is up (on), check if it's actively transferring data.
        """
        safe = []

        for port in range(1, self.client.max_ports + 1):
            port_entity = f"binary_sensor.tp_link_switch_port_{port}_state"
            state = self.hass.states.get(port_entity)

            if state is None:
                # No tplink_easy_smart entity — test all ports
                safe.append(port)
                continue

            if state.state == "off":
                # Port is down — safe to test
                safe.append(port)
            elif state.state == "on":
                # Port is up — check if it's been stable (not flapping)
                # and also check if it's been changing recently
                last_changed = state.last_changed
                if last_changed:
                    from datetime import datetime, timezone
                    now = datetime.now(timezone.utc)
                    seconds_since_change = (now - last_changed).total_seconds()
                    if seconds_since_change > 60:
                        # Port has been stable for >60s, test is brief (~1s)
                        safe.append(port)
                    else:
                        _LOGGER.info(
                            "Skipping port %d — state changed %ds ago",
                            port, int(seconds_since_change),
                        )
                else:
                    safe.append(port)
            else:
                # Unknown/unavailable — safe to test
                safe.append(port)

        return safe

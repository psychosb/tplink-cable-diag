"""TP-Link Cable Diagnostics integration."""

import logging
from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_change

from .const import (
    DOMAIN,
    CONF_SWITCH_IP,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCHEDULE_DAY,
    CONF_SCHEDULE_HOUR,
    DEFAULT_SCHEDULE_DAY,
    DEFAULT_SCHEDULE_HOUR,
)
from .switch_client import TpLinkSwitchClient
from .coordinator import TpLinkCableDiagCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

DAY_MAP = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3,
    "fri": 4, "sat": 5, "sun": 6,
}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up TP-Link Cable Diagnostics from a config entry."""
    client = TpLinkSwitchClient(
        entry.data[CONF_SWITCH_IP],
        entry.data[CONF_USERNAME],
        entry.data[CONF_PASSWORD],
    )

    coordinator = TpLinkCableDiagCoordinator(hass, client)

    # Run first test
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Schedule periodic tests based on day/hour config
    schedule_day = entry.data.get(CONF_SCHEDULE_DAY, DEFAULT_SCHEDULE_DAY)
    schedule_hour = entry.data.get(CONF_SCHEDULE_HOUR, DEFAULT_SCHEDULE_HOUR)

    async def _scheduled_test(now: datetime):
        """Run cable test at scheduled time."""
        if schedule_day != "daily":
            target_weekday = DAY_MAP.get(schedule_day)
            if target_weekday is not None and now.weekday() != target_weekday:
                return
        _LOGGER.info("Running scheduled cable diagnostics test")
        await coordinator.async_request_refresh()

    # Track time change — fires every day at the configured hour
    unsub = async_track_time_change(
        hass, _scheduled_test, hour=schedule_hour, minute=0, second=0,
    )

    # Store unsubscribe callback for cleanup
    hass.data[DOMAIN][f"{entry.entry_id}_unsub"] = unsub

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Cancel scheduled test
    unsub = hass.data[DOMAIN].pop(f"{entry.entry_id}_unsub", None)
    if unsub:
        unsub()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok

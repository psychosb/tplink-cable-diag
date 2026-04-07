"""Sensor platform for TP-Link Cable Diagnostics."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SWITCH_IP
from .coordinator import TpLinkCableDiagCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cable diagnostic sensors."""
    coordinator: TpLinkCableDiagCoordinator = hass.data[DOMAIN][entry.entry_id]
    switch_ip = entry.data[CONF_SWITCH_IP]

    entities = []
    for port in range(1, 9):
        entities.append(CableDiagSensor(coordinator, switch_ip, port))

    async_add_entities(entities)


class CableDiagSensor(CoordinatorEntity, SensorEntity):
    """Sensor showing cable diagnostic result for a specific port."""

    def __init__(
        self,
        coordinator: TpLinkCableDiagCoordinator,
        switch_ip: str,
        port: int,
    ):
        super().__init__(coordinator)
        self._port = port
        self._switch_ip = switch_ip
        self._attr_name = f"TL-SG108E Port {port} Cable"
        self._attr_unique_id = f"tplink_cable_diag_{switch_ip}_port_{port}"
        self._attr_icon = "mdi:ethernet-cable"

    @property
    def native_value(self) -> str | None:
        """Return the cable test result."""
        if self.coordinator.data is None:
            return None
        port_data = self.coordinator.data.get(self._port, {})
        return port_data.get("state_name", "Unknown")

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional attributes."""
        if self.coordinator.data is None:
            return {}
        port_data = self.coordinator.data.get(self._port, {})
        attrs = {
            "port": self._port,
            "state_code": port_data.get("state"),
            "fault": port_data.get("fault", False),
            "switch_ip": self._switch_ip,
        }
        if port_data.get("length_m") is not None:
            attrs["cable_length_m"] = port_data["length_m"]
            attrs["fault_distance_m"] = port_data["length_m"]
        return attrs

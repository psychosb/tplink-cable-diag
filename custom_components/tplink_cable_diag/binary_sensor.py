"""Binary sensor platform for TP-Link Cable Diagnostics."""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_SWITCH_IP, FAULT_STATES
from .coordinator import TpLinkCableDiagCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up cable fault binary sensor."""
    coordinator: TpLinkCableDiagCoordinator = hass.data[DOMAIN][entry.entry_id]
    switch_ip = entry.data[CONF_SWITCH_IP]

    async_add_entities([CableFaultBinarySensor(coordinator, switch_ip)])


class CableFaultBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that is ON when any port has a cable fault."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(
        self,
        coordinator: TpLinkCableDiagCoordinator,
        switch_ip: str,
    ):
        super().__init__(coordinator)
        self._switch_ip = switch_ip
        self._attr_name = "TL-SG108E Cable Fault"
        self._attr_unique_id = f"tplink_cable_diag_{switch_ip}_fault"
        self._attr_icon = "mdi:ethernet-cable-off"

    @property
    def is_on(self) -> bool | None:
        """Return True if any port has a cable fault."""
        if self.coordinator.data is None:
            return None
        return any(
            port_data.get("fault", False)
            for port_data in self.coordinator.data.values()
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Return details about faulted ports."""
        if self.coordinator.data is None:
            return {}

        faults = []
        for port_num, port_data in self.coordinator.data.items():
            if port_data.get("fault"):
                fault_info = {
                    "port": port_num,
                    "status": port_data.get("state_name", "Unknown"),
                }
                if port_data.get("length_m") is not None:
                    fault_info["distance_m"] = port_data["length_m"]
                faults.append(fault_info)

        return {
            "faulted_ports": faults,
            "fault_count": len(faults),
            "switch_ip": self._switch_ip,
        }

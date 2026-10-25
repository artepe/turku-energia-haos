"""Status sensors. Interval and period sums are not cumulative meter readings."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import UnitOfEnergy
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

SENSOR_TYPES = {
    "latest": "Latest interval energy",
    "today": "Energy today (available readings)",
    "month": "Energy this month (available readings)",
}


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([TurkuEnergiaSensor(coordinator, entry, key) for key in SENSOR_TYPES])


class TurkuEnergiaSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_device_class = SensorDeviceClass.ENERGY

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = SENSOR_TYPES[key]
        self._attr_unique_id = f"{entry.unique_id}_{key}"

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(self._key)

    @property
    def extra_state_attributes(self):
        d = self.coordinator.data or {}
        return {
            "resolution": d.get("resolution"),
            "points_in_last_request": d.get("data_points"),
            "external_statistic_id": d.get("statistic_id"),
            "last_measurement_utc": d["latest_time"].isoformat() if d.get("latest_time") else None,
            "note": "Provider data can be delayed; partial periods excluded.",
        }

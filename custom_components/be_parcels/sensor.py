"""Sensor platform: toont de status van één pakje."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CARRIER, CONF_NAME, CONF_TRACKING_NUMBER, DOMAIN, STATUS_UNKNOWN
from .coordinator import ParcelCoordinator

# Volgorde bepaalt hoe "ver" een pakje is; gebruikt voor icon-logica.
_STATUS_ICONS = {
    "label_created": "mdi:package-variant-closed",
    "in_transit": "mdi:truck-delivery-outline",
    "out_for_delivery": "mdi:truck-fast-outline",
    "delivered": "mdi:package-variant-closed-check",
    "exception": "mdi:alert-circle-outline",
    STATUS_UNKNOWN: "mdi:package-variant",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ParcelCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([ParcelSensor(coordinator, entry)])


class ParcelSensor(CoordinatorEntity[ParcelCoordinator], SensorEntity):
    """Eén sensor per getrackt pakje."""

    _attr_has_entity_name = True
    _attr_name = None  # gebruik de device-naam als entity-naam

    def __init__(self, coordinator: ParcelCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = entry.unique_id or entry.entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.data.get(CONF_NAME, entry.title),
            manufacturer=entry.data[CONF_CARRIER],
            model="Pakje",
        )

    @property
    def native_value(self) -> str:
        if self.coordinator.data is None:
            return STATUS_UNKNOWN
        return self.coordinator.data.status

    @property
    def icon(self) -> str:
        return _STATUS_ICONS.get(self.native_value, _STATUS_ICONS[STATUS_UNKNOWN])

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data
        if data is None:
            return {}
        return {
            "vervoerder": data.carrier,
            "trackingnummer": data.tracking_number,
            "status_omschrijving": data.status_description,
            "laatste_update": data.last_update,
            "verwachte_levering": data.expected_delivery,
            **data.extra,
        }

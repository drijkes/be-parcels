"""Sensor platform: één sensor-entiteit per pakje, dynamisch aangemaakt
wanneer be_parcels.add_parcel wordt aangeroepen (dus zonder herstart)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_CARRIER, CONF_NAME, DOMAIN, STATUS_UNKNOWN
from .coordinator import ParcelsCoordinator

_STATUS_ICONS = {
    "label_created": "mdi:package-variant-closed",
    "in_transit": "mdi:truck-delivery-outline",
    "out_for_delivery": "mdi:truck-fast-outline",
    "delivered": "mdi:package-variant-closed-check",
    "exception": "mdi:alert-circle-outline",
    "not_found": "mdi:help-circle-outline",
    STATUS_UNKNOWN: "mdi:package-variant",
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: ParcelsCoordinator = hass.data[DOMAIN][entry.entry_id]

    # Bij opstart: alle reeds bekende pakjes als entiteit toevoegen.
    async_add_entities(
        ParcelSensor(coordinator, entry, parcel_id) for parcel_id in coordinator.parcels
    )

    @callback
    def _async_new_parcel(parcel_id: str) -> None:
        async_add_entities([ParcelSensor(coordinator, entry, parcel_id)])

    entry.async_on_unload(
        async_dispatcher_connect(
            hass, f"{DOMAIN}_{entry.entry_id}_new_parcel", _async_new_parcel
        )
    )


class ParcelSensor(CoordinatorEntity[ParcelsCoordinator], SensorEntity):
    """Eén sensor per getrackt pakje binnen de hub."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: ParcelsCoordinator, entry: ConfigEntry, parcel_id: str
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self.parcel_id = parcel_id
        self._attr_unique_id = f"{entry.entry_id}_{parcel_id}"
        parcel_cfg = coordinator.parcels.get(parcel_id, {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._attr_unique_id)},
            name=parcel_cfg.get(CONF_NAME, parcel_id),
            manufacturer=parcel_cfg.get(CONF_CARRIER, "onbekend"),
            model="Pakje",
        )

    @property
    def available(self) -> bool:
        return self.parcel_id in self.coordinator.data

    @property
    def native_value(self) -> str:
        status = self.coordinator.data.get(self.parcel_id)
        return status.status if status else STATUS_UNKNOWN

    @property
    def icon(self) -> str:
        return _STATUS_ICONS.get(self.native_value, _STATUS_ICONS[STATUS_UNKNOWN])

    @property
    def extra_state_attributes(self) -> dict:
        status = self.coordinator.data.get(self.parcel_id)
        if status is None:
            return {}
        return {
            "vervoerder": status.carrier,
            "trackingnummer": status.tracking_number,
            "status_omschrijving": status.status_description,
            "laatste_update": status.last_update,
            "verwachte_levering": status.expected_delivery,
            **status.extra,
        }

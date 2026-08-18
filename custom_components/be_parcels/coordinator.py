"""Coordinator: beheert alle getrackte pakjes van één hub-entry samen.

Eén polling-cyclus haalt de status van elk pakje op (met een kleine
tussenpauze om vervoerders niet te bestoken) en bewaart het resultaat
per trackingnummer. Bij elke wijziging in status wordt een HA-event
gegooid, zodat je er automations op kan laten reageren (bv. een
melding versturen zodra een pakje "out_for_delivery" wordt).
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .carriers import CARRIERS
from .carriers.base import ParcelNotFoundError, ParcelProviderError, ParcelStatus
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, EVENT_STATUS_CHANGED, STATUS_NOT_FOUND

_LOGGER = logging.getLogger(__name__)


class ParcelsCoordinator(DataUpdateCoordinator[dict[str, ParcelStatus]]):
    """Eén coordinator per hub-entry, houdt alle pakjes van die hub bij."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry_id}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.hass = hass
        self.entry_id = entry_id
        # key = parcel_id (zelf gekozen unieke sleutel, zie __init__.py),
        # value = dict met carrier/tracking_number/postal_code/name
        self.parcels: dict[str, dict] = {}
        self.data: dict[str, ParcelStatus] = {}

    async def async_fetch_one(self, parcel_id: str, parcel_cfg: dict) -> ParcelStatus:
        """Haal de status van één pakje op (genormaliseerd)."""
        carrier_cls = CARRIERS[parcel_cfg["carrier"]]
        session = async_get_clientsession(self.hass)
        carrier = carrier_cls(session)
        try:
            return await carrier.async_get_status(
                parcel_cfg["tracking_number"], parcel_cfg.get("postal_code")
            )
        except ParcelNotFoundError:
            return ParcelStatus(
                status=STATUS_NOT_FOUND,
                status_description="Trackingnummer niet gevonden",
                carrier=carrier_cls.name,
                tracking_number=parcel_cfg["tracking_number"],
            )
        except ParcelProviderError as err:
            _LOGGER.warning("Kon status van %s niet ophalen: %s", parcel_id, err)
            # Geef de vorige gekende status terug i.p.v. de hele entry te
            # laten falen — één trage/foutieve vervoerder mag de andere
            # pakjes niet blokkeren.
            return self.data.get(
                parcel_id,
                ParcelStatus(
                    status=STATUS_NOT_FOUND,
                    status_description=str(err),
                    carrier=carrier_cls.name,
                    tracking_number=parcel_cfg["tracking_number"],
                ),
            )

    async def _async_update_data(self) -> dict[str, ParcelStatus]:
        new_data: dict[str, ParcelStatus] = {}
        for parcel_id, parcel_cfg in self.parcels.items():
            new_data[parcel_id] = await self.async_fetch_one(parcel_id, parcel_cfg)
            # Kleine pauze tussen calls naar dezelfde soort vervoerder-
            # endpoints, uit beleefdheid tegenover niet-officiële APIs.
            await asyncio.sleep(1)

        self._fire_status_change_events(new_data)
        return new_data

    def _fire_status_change_events(self, new_data: dict[str, ParcelStatus]) -> None:
        for parcel_id, status in new_data.items():
            old_status = self.data.get(parcel_id)
            if old_status is None or old_status.status != status.status:
                self.hass.bus.async_fire(
                    EVENT_STATUS_CHANGED,
                    {
                        "parcel_id": parcel_id,
                        "entry_id": self.entry_id,
                        "old_status": old_status.status if old_status else None,
                        **asdict(status),
                    },
                )

    async def async_add_parcel(self, parcel_id: str, parcel_cfg: dict) -> ParcelStatus:
        """Voeg een pakje toe en haal meteen de eerste status op."""
        self.parcels[parcel_id] = parcel_cfg
        status = await self.async_fetch_one(parcel_id, parcel_cfg)
        self.data[parcel_id] = status
        self.async_set_updated_data(self.data)
        return status

    def async_remove_parcel(self, parcel_id: str) -> None:
        self.parcels.pop(parcel_id, None)
        self.data.pop(parcel_id, None)
        self.async_set_updated_data(self.data)

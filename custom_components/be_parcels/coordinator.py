"""Coordinator: haalt periodiek de status van één pakje op."""
from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .carriers import CARRIERS
from .carriers.base import ParcelNotFoundError, ParcelProviderError, ParcelStatus
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ParcelCoordinator(DataUpdateCoordinator[ParcelStatus]):
    """Eén coordinator per config entry, dus per getrackt pakje."""

    def __init__(
        self,
        hass: HomeAssistant,
        carrier_slug: str,
        tracking_number: str,
        postal_code: str | None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{carrier_slug}_{tracking_number}",
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.carrier_slug = carrier_slug
        self.tracking_number = tracking_number
        self.postal_code = postal_code

        carrier_cls = CARRIERS[carrier_slug]
        session = async_get_clientsession(hass)
        self._carrier = carrier_cls(session)

    async def _async_update_data(self) -> ParcelStatus:
        try:
            return await self._carrier.async_get_status(
                self.tracking_number, self.postal_code
            )
        except ParcelNotFoundError as err:
            raise UpdateFailed(
                f"Trackingnummer {self.tracking_number} niet gevonden bij {self.carrier_slug}"
            ) from err
        except ParcelProviderError as err:
            raise UpdateFailed(f"Fout bij ophalen status: {err}") from err

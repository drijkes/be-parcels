"""Belgian Parcels integration.

Elke config entry vertegenwoordigt precies één te tracken pakje
(vervoerder + trackingnummer [+ postcode]). Dat maakt het toevoegen en
verwijderen van pakjes via de UI (Instellingen > Apparaten & diensten)
heel natuurlijk: elk pakje is gewoon een losse integratie-instantie.
"""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_CARRIER, CONF_POSTAL_CODE, CONF_TRACKING_NUMBER, DOMAIN, PLATFORMS
from .coordinator import ParcelCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet een pakje-config-entry op."""
    coordinator = ParcelCoordinator(
        hass,
        carrier_slug=entry.data[CONF_CARRIER],
        tracking_number=entry.data[CONF_TRACKING_NUMBER],
        postal_code=entry.data.get(CONF_POSTAL_CODE),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Verwijder een pakje-config-entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Herlaad wanneer de gebruiker instellingen aanpast (bv. andere naam)."""
    await hass.config_entries.async_reload(entry.entry_id)

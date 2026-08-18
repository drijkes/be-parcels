"""Belgian Parcels integration.

Eén config entry = één "hub". Vanuit die hub voeg je pakjes toe via de
services be_parcels.add_parcel / be_parcels.remove_parcel — bedoeld om
vanaf een dashboard (knop/script) of een automation aan te roepen,
zodat je geen nieuwe integratie via Instellingen hoeft toe te voegen
voor elk pakje.
"""
from __future__ import annotations

import logging
import pathlib
import re

import voluptuous as vol

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .carriers import CARRIERS
from .const import (
    CONF_CARRIER,
    CONF_NAME,
    CONF_PARCELS,
    CONF_POSTAL_CODE,
    CONF_TRACKING_NUMBER,
    DOMAIN,
    PLATFORMS,
    SERVICE_ADD_PARCEL,
    SERVICE_REMOVE_PARCEL,
)
from .coordinator import ParcelsCoordinator

_LOGGER = logging.getLogger(__name__)

ADD_PARCEL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CARRIER): vol.In(list(CARRIERS)),
        vol.Required(CONF_TRACKING_NUMBER): cv.string,
        vol.Optional(CONF_POSTAL_CODE): cv.string,
        vol.Optional(CONF_NAME): cv.string,
    }
)
REMOVE_PARCEL_SCHEMA = vol.Schema({vol.Required("parcel_id"): cv.string})


def _slugify_id(carrier: str, tracking_number: str) -> str:
    raw = f"{carrier}_{tracking_number}".lower()
    return re.sub(r"[^a-z0-9_]", "_", raw)


FRONTEND_URL_PATH = "/be_parcels_static/be-parcels-card.js"


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Registreer de meegeleverde Lovelace-kaart automatisch.

    Zo hoeft de gebruiker geen handmatige Lovelace-resource toe te
    voegen: de kaart is meteen na herstart beschikbaar in de
    kaart-editor onder "Belgian Parcels".
    """
    if hass.data.get(f"{DOMAIN}_frontend_registered"):
        return

    js_path = str(pathlib.Path(__file__).parent / "www" / "be-parcels-card.js")

    if not pathlib.Path(js_path).is_file():
        _LOGGER.error(
            "be_parcels: kaart-bestand niet gevonden op %s — de "
            "installatie is onvolledig (www/ map ontbreekt of is niet "
            "meegekomen bij de HACS-download). Herinstalleer via HACS.",
            js_path,
        )
        return

    try:
        try:
            # Home Assistant >= 2024.7
            from homeassistant.components.http import StaticPathConfig

            await hass.http.async_register_static_paths(
                [StaticPathConfig(FRONTEND_URL_PATH, js_path, False)]
            )
        except ImportError:
            # Oudere Home Assistant-versies
            hass.http.register_static_path(FRONTEND_URL_PATH, js_path, False)

        add_extra_js_url(hass, FRONTEND_URL_PATH)
    except Exception:  # noqa: BLE001 - we willen dit gegarandeerd loggen
        _LOGGER.exception(
            "be_parcels: registreren van de dashboard-kaart is mislukt. "
            "De integratie zelf blijft werken, maar de kaart 'Belgian "
            "Parcels' zal niet verschijnen in de kaart-editor."
        )
        return

    hass.data[f"{DOMAIN}_frontend_registered"] = True
    _LOGGER.debug("be_parcels: dashboard-kaart geregistreerd op %s", FRONTEND_URL_PATH)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Zet de hub op: coordinator + reeds bekende pakjes + services + frontend-kaart."""
    await _async_register_frontend_card(hass)

    coordinator = ParcelsCoordinator(hass, entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Bestaande pakjes (opgeslagen in entry.options) opnieuw inladen na herstart.
    stored_parcels: dict = entry.options.get(CONF_PARCELS, {})
    coordinator.parcels = dict(stored_parcels)

    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    async def _async_handle_add_parcel(call: ServiceCall) -> None:
        data = ADD_PARCEL_SCHEMA(call.data)
        parcel_id = _slugify_id(data[CONF_CARRIER], data[CONF_TRACKING_NUMBER])
        parcel_cfg = {
            CONF_CARRIER: data[CONF_CARRIER],
            CONF_TRACKING_NUMBER: data[CONF_TRACKING_NUMBER],
            CONF_POSTAL_CODE: data.get(CONF_POSTAL_CODE),
            CONF_NAME: data.get(CONF_NAME)
            or f"{CARRIERS[data[CONF_CARRIER]].name} {data[CONF_TRACKING_NUMBER]}",
        }
        await coordinator.async_add_parcel(parcel_id, parcel_cfg)

        new_options = {**entry.options}
        parcels = {**new_options.get(CONF_PARCELS, {}), parcel_id: parcel_cfg}
        new_options[CONF_PARCELS] = parcels
        hass.config_entries.async_update_entry(entry, options=new_options)
        # Nieuwe entiteit laten verschijnen zonder herstart:
        async_dispatcher_send_new_parcel(hass, entry.entry_id, parcel_id)

    async def _async_handle_remove_parcel(call: ServiceCall) -> None:
        parcel_id = REMOVE_PARCEL_SCHEMA(call.data)["parcel_id"]
        coordinator.async_remove_parcel(parcel_id)

        new_options = {**entry.options}
        parcels = {**new_options.get(CONF_PARCELS, {})}
        parcels.pop(parcel_id, None)
        new_options[CONF_PARCELS] = parcels
        hass.config_entries.async_update_entry(entry, options=new_options)

    hass.services.async_register(
        DOMAIN, SERVICE_ADD_PARCEL, _async_handle_add_parcel, schema=ADD_PARCEL_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_REMOVE_PARCEL,
        _async_handle_remove_parcel,
        schema=REMOVE_PARCEL_SCHEMA,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.services.async_remove(DOMAIN, SERVICE_ADD_PARCEL)
        hass.services.async_remove(DOMAIN, SERVICE_REMOVE_PARCEL)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


def async_dispatcher_send_new_parcel(hass: HomeAssistant, entry_id: str, parcel_id: str) -> None:
    from homeassistant.helpers.dispatcher import async_dispatcher_send

    async_dispatcher_send(hass, f"{DOMAIN}_{entry_id}_new_parcel", parcel_id)

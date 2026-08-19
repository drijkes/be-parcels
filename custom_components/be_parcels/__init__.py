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
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

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
# Cache-busting: zonder versienummer in de URL blijven browsers ÉN
# proxies/CDN's het bestand agressief cachen, ook na een update van de
# integratie. Dit handmatig ophogen bij elke wijziging aan de kaart-JS
# dwingt een verse download af, ongeacht caching ergens tussenin.
FRONTEND_JS_CACHE_VERSION = "35"


class _ParcelsCardView(HomeAssistantView):
    """Levert de kaart-JS met een GEGARANDEERD correcte Content-Type.

    De standaard static-file-registratie van Home Assistant laat het
    detecteren van het mimetype over aan het systeem (Python's
    'mimetypes'-module). Op sommige installaties (vooral minimale
    containers zoals Home Assistant OS) levert dat soms geen/verkeerd
    resultaat op, wat een gewone desktopbrowser meestal nog door de
    vingers ziet, maar wat strengere ingebouwde browsers — zoals die in
    de Home Assistant companion-app — kunnen weigeren uit te voeren.
    Deze eigen view zet de header expliciet, ongeacht systeeminstellingen.
    """

    url = FRONTEND_URL_PATH
    name = "be_parcels:card_js"
    requires_auth = False

    def __init__(self, js_path: str) -> None:
        self._js_path = js_path

    async def get(self, request):
        from aiohttp import web

        try:
            content = await request.app["hass"].async_add_executor_job(
                pathlib.Path(self._js_path).read_text, "utf-8"
            )
        except OSError as err:
            return web.Response(status=404, text=f"be_parcels card niet gevonden: {err}")

        return web.Response(
            text=content,
            content_type="application/javascript",
            charset="utf-8",
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )


async def _async_register_frontend_card(hass: HomeAssistant) -> None:
    """Registreer de meegeleverde Lovelace-kaart automatisch.

    Zo hoeft de gebruiker geen handmatige Lovelace-resource toe te
    voegen: de kaart is meteen na herstart beschikbaar in de
    kaart-editor onder "Belgian Parcels".
    """
    if hass.data.get(f"{DOMAIN}_frontend_registered") == FRONTEND_JS_CACHE_VERSION:
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

    # Cache-Control staat hierboven al op "immutable" (mag voor altijd
    # gecachet worden) — dat is precies waarom een uniek versienummer in
    # de URL zelf zo belangrijk is: een nieuwe versie krijgt een nieuwe
    # URL, dus wordt nooit uit een oude cache bediend.
    versioned_url = f"{FRONTEND_URL_PATH}?v={FRONTEND_JS_CACHE_VERSION}"

    try:
        hass.http.register_view(_ParcelsCardView(js_path))
        add_extra_js_url(hass, versioned_url)
    except Exception:  # noqa: BLE001 - we willen dit gegarandeerd loggen
        _LOGGER.exception(
            "be_parcels: registreren van de dashboard-kaart is mislukt. "
            "De integratie zelf blijft werken, maar de kaart 'Belgian "
            "Parcels' zal niet verschijnen in de kaart-editor."
        )
        return

    hass.data[f"{DOMAIN}_frontend_registered"] = FRONTEND_JS_CACHE_VERSION
    _LOGGER.debug("be_parcels: dashboard-kaart geregistreerd op %s", versioned_url)


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
        # call.data is een ReadOnlyDict; voluptuous probeert bij validatie
        # intern hetzelfde dict-type te construeren (dus ook read-only),
        # wat een "Cannot modify ReadOnlyDict"-fout geeft. Eerst omzetten
        # naar een gewone (schrijfbare) dict lost dat op.
        data = ADD_PARCEL_SCHEMA(dict(call.data))
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
        parcel_id = REMOVE_PARCEL_SCHEMA(dict(call.data))["parcel_id"]
        coordinator.async_remove_parcel(parcel_id)

        # Zonder dit blijft er een leeg apparaat/entiteit achter in
        # Instellingen → Apparaten & diensten, want het verwijderen van
        # de coordinator-data alleen verwijdert de HA-entiteit niet.
        unique_id = f"{entry.entry_id}_{parcel_id}"

        ent_reg = er.async_get(hass)
        entity_id = ent_reg.async_get_entity_id("sensor", DOMAIN, unique_id)
        if entity_id:
            ent_reg.async_remove(entity_id)

        dev_reg = dr.async_get(hass)
        device = dev_reg.async_get_device(identifiers={(DOMAIN, unique_id)})
        if device:
            dev_reg.async_remove_device(device.id)

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

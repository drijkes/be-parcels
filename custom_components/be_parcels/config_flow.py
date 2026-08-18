"""Config flow: eenmalig de 'Belgian Parcels'-hub toevoegen.

Pakjes zelf voeg je NIET hier toe, maar via de kaart op je dashboard
(of de service be_parcels.add_parcel). Hier stel je enkel éénmalig in
naar welke notify-doelen (één of meerdere toestellen) een melding moet
gaan wanneer een pakje "out_for_delivery" wordt — je vinkt gewoon aan
welke toestellen je wil, uit de lijst die Home Assistant al kent.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import CONF_NOTIFY_SERVICES, DOMAIN


def _notify_service_options(hass: HomeAssistant, current: list[str]) -> list[selector.SelectOptionDict]:
    """Bouw de lijst met aanvinkbare notify-doelen op."""
    services = hass.services.async_services().get("notify", {})
    known = sorted(services)
    options = [selector.SelectOptionDict(value=name, label=name) for name in known]

    # Opgeslagen doelen die niet meer bestaan (bv. toestel verwijderd) toch
    # tonen zodat de gebruiker ze bewust kan uitvinken i.p.v. dat ze
    # stilzwijgend verdwijnen.
    for name in current:
        if name not in known:
            options.append(selector.SelectOptionDict(value=name, label=f"{name} (niet meer gevonden)"))

    return options


def _notify_services_schema(hass: HomeAssistant, current: list[str]) -> vol.Schema:
    options = _notify_service_options(hass, current)
    return vol.Schema(
        {
            vol.Optional(CONF_NOTIFY_SERVICES, default=current): selector.selector(
                {"select": {"options": options, "multiple": True, "mode": "list"}}
            ),
        }
    )


class BeParcelsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        # Slechts één hub toegestaan.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Belgian Parcels",
                data={},
                options={CONF_NOTIFY_SERVICES: user_input.get(CONF_NOTIFY_SERVICES, [])},
            )

        return self.async_show_form(
            step_id="user", data_schema=_notify_services_schema(self.hass, [])
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BeParcelsOptionsFlow(config_entry)


class BeParcelsOptionsFlow(config_entries.OptionsFlow):
    """Laat toe de notify-doelen achteraf te wijzigen via 'Configureren'."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            # Belangrijk: options bevat ook CONF_PARCELS (de lijst
            # getrackte pakjes) — enkel het notify-veld overschrijven,
            # niet de volledige options-dict vervangen.
            new_options = {**self._config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        current = list(self._config_entry.options.get(CONF_NOTIFY_SERVICES, []))
        return self.async_show_form(
            step_id="init", data_schema=_notify_services_schema(self.hass, current)
        )

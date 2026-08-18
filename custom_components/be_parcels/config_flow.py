"""Config flow: eenmalig de 'Belgian Parcels'-hub toevoegen.

Pakjes zelf voeg je NIET hier toe, maar via de kaart op je dashboard
(of de service be_parcels.add_parcel). Hier stel je enkel éénmalig in
naar welk notify-doel een melding moet gaan wanneer een pakje
"out_for_delivery" wordt — gekozen uit een dropdown met alle notify-
doelen die Home Assistant al kent (dezelfde lijst als in de
automation-editor), zodat je niets zelf hoeft over te typen.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import CONF_NOTIFY_SERVICE, DOMAIN

NOTIFY_DISABLED = ""  # betekent: geen meldingen versturen


def _notify_service_options(hass: HomeAssistant) -> list[selector.SelectOptionDict]:
    """Bouw de dropdown-opties op basis van alle geregistreerde notify-services."""
    options = [
        selector.SelectOptionDict(value=NOTIFY_DISABLED, label="Geen (meldingen uitgeschakeld)")
    ]
    services = hass.services.async_services().get("notify", {})
    for service_name in sorted(services):
        options.append(selector.SelectOptionDict(value=service_name, label=service_name))
    return options


def _notify_service_schema(hass: HomeAssistant, current: str) -> vol.Schema:
    options = _notify_service_options(hass)
    # Als de opgeslagen waarde niet (meer) in de lijst voorkomt (bv. het
    # toestel is verwijderd), toon 'm toch als extra optie zodat de
    # dropdown niet crasht en de gebruiker het kan corrigeren.
    if current and current not in [o["value"] for o in options]:
        options.append(selector.SelectOptionDict(value=current, label=f"{current} (niet meer gevonden)"))

    return vol.Schema(
        {
            vol.Optional(CONF_NOTIFY_SERVICE, default=current or NOTIFY_DISABLED): selector.selector(
                {"select": {"options": options, "mode": "dropdown"}}
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
                options={CONF_NOTIFY_SERVICE: user_input.get(CONF_NOTIFY_SERVICE, "")},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_notify_service_schema(self.hass, NOTIFY_DISABLED),
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BeParcelsOptionsFlow(config_entry)


class BeParcelsOptionsFlow(config_entries.OptionsFlow):
    """Laat toe het notify-doel achteraf te wijzigen via 'Configureren'."""

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

        current = self._config_entry.options.get(CONF_NOTIFY_SERVICE, "")
        return self.async_show_form(
            step_id="init", data_schema=_notify_service_schema(self.hass, current)
        )

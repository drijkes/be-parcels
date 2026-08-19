"""Config flow: eenmalig de 'Belgian Parcels'-hub toevoegen.

Pakjes zelf voeg je NIET hier toe, maar via de kaart op je dashboard
(of de service be_parcels.add_parcel). Hier stel je in:
  - naar welke toestellen een melding moet gaan bij "onderweg";
  - je (gratis) Track123 API-key, nodig voor alle vervoerders behalve
    bpost/PostNL — zie carriers/track123.py.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import CONF_NOTIFY_SERVICES, CONF_TRACK123_API_KEY, DOMAIN


def _notify_service_options(hass: HomeAssistant, current: list[str]) -> list[selector.SelectOptionDict]:
    """Bouw de lijst met aanvinkbare notify-doelen op."""
    services = hass.services.async_services().get("notify", {})
    known = sorted(services)
    options = [selector.SelectOptionDict(value=name, label=name) for name in known]

    for name in current:
        if name not in known:
            options.append(selector.SelectOptionDict(value=name, label=f"{name} (niet meer gevonden)"))

    return options


def _hub_schema(hass: HomeAssistant, current_notify: list[str], current_key: str) -> vol.Schema:
    notify_options = _notify_service_options(hass, current_notify)
    return vol.Schema(
        {
            vol.Optional(CONF_NOTIFY_SERVICES, default=current_notify): selector.selector(
                {"select": {"options": notify_options, "multiple": True, "mode": "list"}}
            ),
            vol.Optional(CONF_TRACK123_API_KEY, default=current_key): selector.selector(
                {"text": {"type": "password"}}
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
                options={
                    CONF_NOTIFY_SERVICES: user_input.get(CONF_NOTIFY_SERVICES, []),
                    CONF_TRACK123_API_KEY: user_input.get(CONF_TRACK123_API_KEY, ""),
                },
            )

        return self.async_show_form(
            step_id="user", data_schema=_hub_schema(self.hass, [], "")
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BeParcelsOptionsFlow(config_entry)


class BeParcelsOptionsFlow(config_entries.OptionsFlow):
    """Laat toe notify-doelen en de Track123-key achteraf te wijzigen."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            new_options = {**self._config_entry.options, **user_input}
            return self.async_create_entry(title="", data=new_options)

        current_notify = list(self._config_entry.options.get(CONF_NOTIFY_SERVICES, []))
        current_key = self._config_entry.options.get(CONF_TRACK123_API_KEY, "")
        return self.async_show_form(
            step_id="init", data_schema=_hub_schema(self.hass, current_notify, current_key)
        )

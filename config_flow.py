"""Config flow: eenmalig de 'Belgian Parcels'-hub toevoegen.

Pakjes zelf voeg je NIET hier toe, maar via de kaart op je dashboard
(of de service be_parcels.add_parcel). Hier stel je enkel éénmalig in
naar welk notify-doel een melding moet gaan wanneer een pakje
"out_for_delivery" wordt — dat maakt meldingen volledig onderdeel van
de integratie, zonder dat je zelf een automation hoeft te schrijven.
"""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import CONF_NOTIFY_SERVICE, DOMAIN


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

        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SERVICE, default=""): selector.selector(
                    {"text": {}}
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders={
                "hint": "bv. mobile_app_iphone_van_jan — leeg laten kan later ook via Configureren."
            },
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
        schema = vol.Schema(
            {
                vol.Optional(CONF_NOTIFY_SERVICE, default=current): selector.selector(
                    {"text": {}}
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

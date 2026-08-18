"""Config flow: eenmalig de 'Belgian Parcels'-hub toevoegen.

Pakjes zelf voeg je NIET hier toe, maar via de service
be_parcels.add_parcel — bedoeld om vanaf een dashboard of automation
aan te roepen. Zie README.md voor een dashboard-voorbeeld.
"""
from __future__ import annotations

from typing import Any

from homeassistant import config_entries

from .const import DOMAIN


class BeParcelsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        # Slechts één hub toegestaan.
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title="Belgian Parcels", data={})

        return self.async_show_form(step_id="user")

"""Config flow: pakje toevoegen via Instellingen > Apparaten & diensten."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .carriers import CARRIERS
from .carriers.base import ParcelNotFoundError, ParcelProviderError
from .const import CONF_CARRIER, CONF_NAME, CONF_POSTAL_CODE, CONF_TRACKING_NUMBER, DOMAIN


class BeParcelsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flow voor het toevoegen van één pakje."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        carrier_options = {slug: cls.name for slug, cls in CARRIERS.items()}

        if user_input is not None:
            carrier_slug = user_input[CONF_CARRIER]
            tracking_number = user_input[CONF_TRACKING_NUMBER].strip()
            postal_code = user_input.get(CONF_POSTAL_CODE, "").strip() or None
            carrier_cls = CARRIERS[carrier_slug]

            if carrier_cls.requires_postal_code and not postal_code:
                errors[CONF_POSTAL_CODE] = "postal_code_required"
            else:
                # Uniek per vervoerder+trackingnummer, zodat je hetzelfde
                # pakje niet twee keer kan toevoegen.
                unique_id = f"{carrier_slug}_{tracking_number}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Meteen één keer testen zodat de gebruiker direct feedback
                # krijgt als het trackingnummer fout is, i.p.v. pas na de
                # eerste polling-cyclus.
                session = async_get_clientsession(self.hass)
                carrier = carrier_cls(session)
                try:
                    await carrier.async_get_status(tracking_number, postal_code)
                except ParcelNotFoundError:
                    errors["base"] = "not_found"
                except ParcelProviderError:
                    errors["base"] = "cannot_connect"
                else:
                    name = user_input.get(CONF_NAME) or f"{carrier_cls.name} {tracking_number}"
                    return self.async_create_entry(
                        title=name,
                        data={
                            CONF_CARRIER: carrier_slug,
                            CONF_TRACKING_NUMBER: tracking_number,
                            CONF_POSTAL_CODE: postal_code,
                            CONF_NAME: name,
                        },
                    )

        schema = vol.Schema(
            {
                vol.Required(CONF_CARRIER, default="bpost"): vol.In(carrier_options),
                vol.Required(CONF_TRACKING_NUMBER): str,
                vol.Optional(CONF_POSTAL_CODE, default=""): str,
                vol.Optional(CONF_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return BeParcelsOptionsFlow(config_entry)


class BeParcelsOptionsFlow(config_entries.OptionsFlow):
    """Laat toe de weergavenaam van een pakje aan te passen."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            new_data = {**self._config_entry.data, CONF_NAME: user_input[CONF_NAME]}
            self.hass.config_entries.async_update_entry(self._config_entry, data=new_data)
            return self.async_create_entry(title="", data={})

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_NAME, default=self._config_entry.data.get(CONF_NAME, "")
                ): str
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)

"""Gedeelde implementatie voor vervoerders via de 17TRACK-aggregator.

In plaats van voor elke vervoerder apart een eigen (breekbare) scraping-
implementatie te schrijven, praten alle vervoerders hieronder — behalve
bpost, dat al gratis rechtstreeks werkt — via 17TRACK's multi-carrier
Tracking API: https://api.17track.net/en/doc

Dit vereist een GRATIS 17TRACK-account + API-key:
  1. Account aanmaken op https://www.17track.net (of https://api.17track.net)
  2. In het dashboard een API-key genereren.
  3. Die key invullen bij Instellingen → Belgian Parcels → Configureren.

Zonder key geven deze vervoerders een duidelijke foutmelding i.p.v. stil
te falen (zie async_get_status hieronder).

BELANGRIJKE CAVEAT: de exacte JSON-structuur van 17TRACK's v2.4
gettrackinfo-respons (veldnamen als 'latest_event', 'latest_status',...)
is gebaseerd op hun officiële documentatie, maar niet getest tegen een
live account/response. Klopt de statusparsing niet helemaal met wat je
account teruggeeft? Pas dan _parse_track_info() hieronder aan a.d.h.v.
een echte response (te bekijken via Ontwikkelhulpmiddelen of logging).

Carrier-codes: https://res.17track.net/asset/carrier/info/apicarrier.all.json
"""
from __future__ import annotations

import logging
from typing import Any

from .base import ParcelCarrier, ParcelNotFoundError, ParcelProviderError, ParcelStatus
from ..const import (
    STATUS_DELIVERED,
    STATUS_EXCEPTION,
    STATUS_IN_TRANSIT,
    STATUS_LABEL_CREATED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_UNKNOWN,
)

_LOGGER = logging.getLogger(__name__)

REGISTER_URL = "https://api.17track.net/track/v2.4/register"
GETTRACKINFO_URL = "https://api.17track.net/track/v2.4/gettrackinfo"

# Mapping van 17TRACK's "latest_status.status" (main status) naar onze
# genormaliseerde status. Zie https://api.17track.net/en/doc voor de
# volledige lijst van 9 hoofdstatussen.
_STATUS_MAP = {
    "NotFound": STATUS_UNKNOWN,
    "InfoReceived": STATUS_LABEL_CREATED,
    "InTransit": STATUS_IN_TRANSIT,
    "OutForDelivery": STATUS_OUT_FOR_DELIVERY,
    "Delivered": STATUS_DELIVERED,
    "AvailableForPickup": STATUS_OUT_FOR_DELIVERY,
    "Exception": STATUS_EXCEPTION,
    "Expired": STATUS_EXCEPTION,
    "FailedAttempt": STATUS_EXCEPTION,
}


class SeventeenTrackCarrier(ParcelCarrier):
    """Basisklasse: subklassen zetten enkel slug/name/carrier_code.

    country_param: sommige vervoerders (bv. PostNL) hebben naast het
    trackingnummer ook een 'param'-veld nodig, opgebouwd als
    "<bestemmingslandcode>-<postcode>". Zet destination_country_iso als
    dat voor jouw vervoerder nodig is (zie 17TRACK-documentatie
    "Special Note 1" voor de volledige lijst).
    """

    carrier_code: int = 0  # in te vullen door subklasse
    destination_country_iso: str | None = None  # bv. "BE", enkel indien nodig
    api_key: str | None = None  # wordt per aanvraag gezet door coordinator.py

    def _build_param(self, postal_code: str | None) -> str | None:
        if self.destination_country_iso and postal_code:
            return f"{self.destination_country_iso}-{postal_code}"
        return None

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        if not self.api_key:
            raise ParcelProviderError(
                "Geen 17TRACK API-key ingesteld. Vul die in bij "
                "Instellingen → Belgian Parcels → Configureren "
                "(gratis account op 17track.net)."
            )

        headers = {"17token": self.api_key, "Content-Type": "application/json"}
        entry: dict[str, Any] = {"number": tracking_number, "carrier": self.carrier_code}
        param = self._build_param(postal_code)
        if param:
            entry["param"] = param
        body = [entry]

        try:
            # Registreren is idempotent: een al gekend nummer opnieuw
            # registreren geeft gewoon terug dat het al bestaat, geen fout.
            async with self._session.post(
                REGISTER_URL, json=body, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    raise ParcelProviderError(
                        f"17TRACK register gaf status {resp.status} terug"
                    )

            async with self._session.post(
                GETTRACKINFO_URL, json=body, headers=headers, timeout=15
            ) as resp:
                if resp.status != 200:
                    raise ParcelProviderError(
                        f"17TRACK gettrackinfo gaf status {resp.status} terug"
                    )
                data: dict[str, Any] = await resp.json()
        except ParcelProviderError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk/parsing fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        accepted = (data.get("data") or {}).get("accepted") or []
        if not accepted:
            raise ParcelNotFoundError(tracking_number)

        return self._parse_track_info(accepted[0], tracking_number)

    def _parse_track_info(self, accepted_entry: dict[str, Any], tracking_number: str) -> ParcelStatus:
        track_info = accepted_entry.get("track_info") or {}
        latest_status_raw = (track_info.get("latest_status") or {}).get("status", "")
        normalized_status = _STATUS_MAP.get(latest_status_raw, STATUS_UNKNOWN)

        latest_event = track_info.get("latest_event") or {}
        description = latest_event.get("description") or latest_status_raw or STATUS_UNKNOWN
        last_update = latest_event.get("time_iso") or latest_event.get("time_utc")

        misc_info = track_info.get("misc_info") or {}
        expected_delivery = misc_info.get("service_type") and None  # geen betrouwbaar ETA-veld bekend

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=expected_delivery,
            extra={"17track_raw_status": latest_status_raw},
        )

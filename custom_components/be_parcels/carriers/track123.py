"""Gedeelde implementatie via de Track123 API (track123.com).

Track123 is een multi-carrier tracking-API met een GRATIS laag die
elke maand opnieuw begint (in tegenstelling tot 17TRACK's eenmalige
200 registraties): 50 zendingen/maand gratis, real-time refresh zonder
extra kosten. Vereist een gratis account + API-key op track123.com.

Documentatie: https://docs.track123.com/reference/request

Twee stappen, zoals door Track123 zelf aanbevolen:
  1. POST /tk/v2/track/import  — pakket registreren (eenmalig nodig,
     idempotent: opnieuw registreren van een gekend nummer is geen fout)
  2. POST /tk/v2/track/query   — actuele status opvragen

De vervoerder wordt automatisch gedetecteerd als je geen courierCode
meegeeft — net als bij het eerder geprobeerde (en gefaalde) 17TRACK-
endpoint, maar deze keer via een officiële, betaalde/freemium API i.p.v.
een anoniem endpoint, dus zonder de botbescherming die we daar
tegenkwamen.

NIET LIVE GETEST vanuit deze omgeving (netwerkbeperking), maar wel
gebaseerd op Track123's eigen, uitgebreide documentatie met een
volledig echt request/response-voorbeeld (niet enkel een schema).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import aiohttp

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

API_BASE = "https://api.track123.com/gateway/open-api/tk/v2"
IMPORT_URL = f"{API_BASE}/track/import"
QUERY_URL = f"{API_BASE}/track/query"

# Track123's transitStatus-waarden (hoofdletters), vertaald naar onze
# genormaliseerde status. Best-effort: de volledige officiële enum-lijst
# (docs.track123.com/reference/package-status) kon niet volledig
# opgehaald worden, dit is gebaseerd op de voorbeelden in hun eigen
# documentatie.
_STATUS_MAP: dict[str, str] = {
    "PENDING": STATUS_LABEL_CREATED,
    "INFO_RECEIVED": STATUS_LABEL_CREATED,
    "IN_TRANSIT": STATUS_IN_TRANSIT,
    "OUT_FOR_DELIVERY": STATUS_OUT_FOR_DELIVERY,
    "DELIVERED": STATUS_DELIVERED,
    "DELIVERY_FAILED": STATUS_EXCEPTION,
    "EXPIRED": STATUS_EXCEPTION,
    "ABNORMAL": STATUS_EXCEPTION,
    "UNDELIVERED": STATUS_EXCEPTION,
}


class Track123Carrier(ParcelCarrier):
    """Basisklasse: subklassen zetten enkel slug/name.

    api_key wordt door coordinator.py gezet vóór gebruik (afkomstig
    uit de integratie-opties). courier_code is optioneel — zonder
    opgave detecteert Track123 de vervoerder zelf.
    """

    requires_postal_code = False
    courier_code: str | None = None
    api_key: str | None = None

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        if not self.api_key:
            raise ParcelProviderError(
                "Geen Track123 API-key ingesteld. Maak een gratis account op "
                "track123.com en vul de key in bij Instellingen → Belgian "
                "Parcels → Configureren."
            )

        headers = {
            "Track123-Api-Secret": self.api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        import_entry: dict[str, Any] = {"trackNo": tracking_number}
        if self.courier_code:
            import_entry["courierCode"] = self.courier_code
        if postal_code:
            # Veldnaam niet 100% bevestigd voor alle vervoerders — zie
            # "Additional Tracking Fields" in Track123's documentatie.
            import_entry["postalCode"] = postal_code

        async with aiohttp.ClientSession() as session:
            # Registreren: idempotent, dus fouten hier negeren we
            # bewust (kan gewoon betekenen dat het al gekend is).
            try:
                async with session.post(
                    IMPORT_URL, json=[import_entry], headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ):
                    pass
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("Track123 import-stap gaf een fout (genegeerd): %s", err)

            try:
                async with session.post(
                    QUERY_URL, json={"trackNos": [tracking_number]}, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 401:
                        raise ParcelProviderError(
                            "Track123 API-key ongeldig — controleer de key bij "
                            "Instellingen → Belgian Parcels → Configureren."
                        )
                    if resp.status != 200:
                        raise ParcelProviderError(
                            f"Track123 gaf status {resp.status} terug"
                        )
                    raw_text = await resp.text()
            except ParcelProviderError:
                raise
            except Exception as err:  # noqa: BLE001
                raise ParcelProviderError(str(err)) from err

        try:
            data: dict[str, Any] = json.loads(raw_text)
        except ValueError as err:
            raise ParcelProviderError(
                f"Track123 gaf geen geldige JSON terug: {err}. Eerste 300 "
                f"tekens: {raw_text[:300]}"
            ) from err

        if data.get("code") not in (None, "00000"):
            raise ParcelProviderError(
                f"Track123 gaf een foutcode terug: {data.get('code')} — "
                f"{data.get('msg')}"
            )

        content = ((data.get("data") or {}).get("accepted") or {}).get("content") or []
        if not content:
            _LOGGER.warning(
                "Track123: geen resultaten voor %s. Ruwe respons (eerste 500 "
                "tekens): %s",
                tracking_number, raw_text[:500],
            )
            raise ParcelNotFoundError(tracking_number)

        return self._parse_entry(content[0], tracking_number)

    def _parse_entry(self, entry: dict, tracking_number: str) -> ParcelStatus:
        transit_status = entry.get("transitStatus", "")
        normalized_status = _STATUS_MAP.get(transit_status, STATUS_UNKNOWN)

        logistics = entry.get("localLogisticsInfo") or {}
        tracking_details = logistics.get("trackingDetails") or []
        latest_event = tracking_details[0] if tracking_details else {}

        description = latest_event.get("eventDetail") or transit_status or STATUS_UNKNOWN
        location = latest_event.get("address")
        raw_timestamp = latest_event.get("eventTime")

        last_update = None
        if raw_timestamp:
            try:
                last_update = datetime.strptime(raw_timestamp, "%Y-%m-%d %H:%M:%S").isoformat()
            except ValueError:
                last_update = raw_timestamp

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=None,
            extra={
                "locatie": location,
                "tracking_url": logistics.get("courierTrackingLink"),
                "track123_status": transit_status,
            },
        )

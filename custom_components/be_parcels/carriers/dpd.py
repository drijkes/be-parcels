"""DPD (België) vervoerder-plugin.

LET OP — hogere onzekerheid dan bpost/PostNL: DPD heeft geen publieke
consumenten-API. Deze module is gebaseerd op een bevestigd werkende
open-source implementatie voor DPD Oostenrijk (mydpd.at, pakket
"dpdtrack" op PyPI, https://kumig.it/kumitterer/dpdtrack), die het
gedeelde "myDPD"-platform gebruikt dat DPD in meerdere landen inzet
(herkenbaar aan het "jws.php"-pad). Hieronder wordt AANGENOMEN dat
mydpd.be dezelfde backend-structuur gebruikt als mydpd.at — dat is per
analogie afgeleid, NIET zelf getest tegen een echt Belgisch pakje.

Werkt dit niet? Open de Chrome DevTools Network-tab op
https://www.mydpd.be/ (of dpdgroup.com/be/mydpd/...) tijdens het
opzoeken van een pakje, en vergelijk de echte request-URL/body met wat
hieronder staat — pas dan SEARCH_URL of de request-vorm aan.
"""
from __future__ import annotations

from datetime import datetime
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

SEARCH_URL = "https://www.mydpd.be/jws.php/parcel/search"

# DPD's "myDPD"-platform geeft geen aparte statuscode terug, enkel een
# vrije tekst per gebeurtenis (state.text). We leiden onze
# genormaliseerde status af via trefwoorden in die (Nederlandstalige)
# tekst — best-effort, geen officiële enum zoals bij bpost.
_KEYWORD_MAP: list[tuple[str, str]] = [
    ("bezorgd", STATUS_DELIVERED),
    ("delivered", STATUS_DELIVERED),
    ("in bezorging", STATUS_OUT_FOR_DELIVERY),
    ("out for delivery", STATUS_OUT_FOR_DELIVERY),
    ("onderweg naar", STATUS_OUT_FOR_DELIVERY),
    ("opgehaald", STATUS_LABEL_CREATED),
    ("aangemeld", STATUS_LABEL_CREATED),
    ("data ontvangen", STATUS_LABEL_CREATED),
    ("probleem", STATUS_EXCEPTION),
    ("exception", STATUS_EXCEPTION),
    ("niet thuis", STATUS_EXCEPTION),
]


def _guess_status(text: str) -> str:
    lowered = (text or "").lower()
    for keyword, status in _KEYWORD_MAP:
        if keyword in lowered:
            return status
    return STATUS_IN_TRANSIT  # standaard: er is al minstens één event, dus "onderweg"


class DpdCarrier(ParcelCarrier):
    slug = "dpd"
    name = "DPD (BE)"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        try:
            async with self._session.post(
                SEARCH_URL, json=tracking_number, timeout=15
            ) as resp:
                if resp.status == 404:
                    raise ParcelNotFoundError(tracking_number)
                if resp.status != 200:
                    raise ParcelProviderError(f"DPD gaf status {resp.status} terug")
                data: dict[str, Any] = await resp.json()
        except ParcelNotFoundError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk/parsing fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        parcels = data.get("data") or []
        if not parcels:
            raise ParcelNotFoundError(tracking_number)

        parcel = parcels[0]
        entries = (parcel.get("lifecycle") or {}).get("entries") or []

        if not entries:
            return ParcelStatus(
                status=STATUS_LABEL_CREATED,
                status_description=STATUS_LABEL_CREATED,
                carrier=self.name,
                tracking_number=tracking_number,
            )

        # Aanname: entries staan chronologisch, laatste event het meest recent.
        latest = entries[-1]
        description = (latest.get("state") or {}).get("text") or STATUS_UNKNOWN
        normalized_status = _guess_status(description)

        last_update = None
        raw_datetime = latest.get("datetime")
        if raw_datetime:
            try:
                last_update = datetime.strptime(raw_datetime, "%Y%m%d%H%M%S").isoformat()
            except ValueError:
                last_update = raw_datetime  # onbekend formaat, ruwe waarde tonen

        depot_data = latest.get("depotData")
        location = ", ".join(depot_data) if depot_data else None

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=None,
            extra={"locatie": location},
        )

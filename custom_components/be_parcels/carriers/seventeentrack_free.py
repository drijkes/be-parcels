"""Gedeelde implementatie via 17TRACK's GRATIS publieke website-endpoint.

Dit is NIET de betaalde ontwikkelaars-API (die een account + API-key +
quota vereist), maar het endpoint dat 17track.net's eigen gratis
publieke trackingpagina (t.17track.net) intern gebruikt zonder in te
loggen. Gebaseerd op de open-source bibliotheek py17track
(https://github.com/bachya/py17track, module track.py):

    POST https://t.17track.net/restapi/track
    body: {"data": [{"num": "<trackingnummer>"}]}

BELANGRIJK: de auteur van py17track had deze functionaliteit zelf
UITGESCHAKELD met de opmerking "disabled until a workaround can be
found" — vermoedelijk dezelfde soort botbescherming die we bij DPD
tegenkwamen. Deze module voegt daarom proactief browser-headers en een
opwarmverzoek toe (dezelfde aanpak als carriers/dpd.py), maar dat is
geen garantie dat het werkt.

De vervoerder wordt door 17TRACK automatisch herkend aan het
trackingnummer — je hoeft dus niet door te geven welke vervoerder het
is. Dat betekent dat ALLE vervoerders die deze klasse gebruiken
hetzelfde endpoint aanroepen; de vervoerder-keuze in de kaart bepaalt
enkel de weergavenaam.

NIET LIVE GETEST vanuit deze omgeving (netwerkbeperking bij het
bouwen). Test dit zelf; als het faalt op dezelfde manier als DPD
(403/blokkade), is de kans groot dat dit endpoint dezelfde
Cloudflare-achtige bescherming heeft als de betaalde API probeert te
omzeilen — en dan is dit, net als DPD rechtstreeks, geen haalbare
gratis weg.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from .base import ParcelCarrier, ParcelNotFoundError, ParcelProviderError, ParcelStatus
from ..const import (
    STATUS_DELIVERED,
    STATUS_EXCEPTION,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_UNKNOWN,
)

TRACK_URL = "https://t.17track.net/restapi/track"
WARMUP_URL = "https://t.17track.net/"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://t.17track.net/",
    "Origin": "https://t.17track.net",
}

# py17track's PACKAGE_STATUS_MAP, vertaald naar onze genormaliseerde statussen.
_STATUS_MAP: dict[int, str] = {
    10: STATUS_IN_TRANSIT,
    20: STATUS_EXCEPTION,  # Expired
    30: STATUS_OUT_FOR_DELIVERY,  # Ready to be Picked Up
    35: STATUS_EXCEPTION,  # Undelivered
    40: STATUS_DELIVERED,
    50: STATUS_EXCEPTION,  # Returned
}


class SeventeenTrackFreeCarrier(ParcelCarrier):
    """Basisklasse: subklassen zetten enkel slug/name.

    Geen carrier-code nodig — 17TRACK herkent de vervoerder zelf.
    """

    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        try:
            # Opwarmverzoek voor cookies, zelfde reden als bij DPD.
            async with self._session.get(
                WARMUP_URL, headers=REQUEST_HEADERS, timeout=15
            ):
                pass

            async with self._session.post(
                TRACK_URL,
                json={"data": [{"num": tracking_number}]},
                headers=REQUEST_HEADERS,
                timeout=15,
            ) as resp:
                if resp.status != 200:
                    raise ParcelProviderError(
                        f"17TRACK (gratis endpoint) gaf status {resp.status} terug — "
                        "vermoedelijk botbescherming, zie caveat in "
                        "carriers/seventeentrack_free.py."
                    )
                data: dict[str, Any] = await resp.json(content_type=None)
        except ParcelProviderError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk/parsing fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        entries = data.get("dat") or []
        if not entries:
            raise ParcelNotFoundError(tracking_number)

        track_info = (entries[0] or {}).get("track") or {}
        status_code = track_info.get("e", 0)
        if not track_info or status_code == 0:
            raise ParcelNotFoundError(tracking_number)

        normalized_status = _STATUS_MAP.get(status_code, STATUS_UNKNOWN)

        latest_event = track_info.get("z0") or {}
        description = latest_event.get("z") or STATUS_UNKNOWN
        location = latest_event.get("c")
        raw_timestamp = latest_event.get("a")

        last_update = None
        if raw_timestamp:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
                try:
                    last_update = datetime.strptime(raw_timestamp, fmt).isoformat()
                    break
                except ValueError:
                    continue
            if last_update is None:
                last_update = raw_timestamp

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=None,
            extra={"locatie": location, "17track_statuscode": status_code},
        )

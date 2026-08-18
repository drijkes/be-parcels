"""DHL vervoerder-plugin — NIET HAALBAAR (gratis, zonder account).

Twee sporen zijn geprobeerd en beide falen, om dezelfde reden: een
botbescherming die verder gaat dan headers/cookies en waarschijnlijk
JavaScript-uitvoering vereist (fingerprinting/uitdaging), wat een
simpel server-side HTTP-verzoek fundamenteel niet kan nabootsen:

  1. Rechtstreeks bij de vervoerder zelf (zoals wél lukte bij bpost en
     PostNL) — voor DPD specifiek bevestigd geblokkeerd door Cloudflare
     (403), ook met volledige browser-headers + opwarmverzoek.
  2. Via 17TRACK's gratis publieke website-endpoint
     (carriers/seventeentrack_free.py, t.17track.net/restapi/track) —
     4 verschillende aanvraagvormen geprobeerd, allemaal identiek
     afgewezen, wat wijst op dezelfde soort blokkade vóór zelfs de
     velden bekeken worden.

CONCLUSIE: DHL is met gratis, server-side middelen niet haalbaar
binnen deze integratie. Enige realistische alternatieven: een betaalde
"unlocker"-/aggregator-dienst, of een headless browser (Playwright) —
beide bewust niet gebruikt. Zie README.md voor het volledige overzicht.
"""
from __future__ import annotations

from .base import ParcelCarrier, ParcelProviderError, ParcelStatus


class DhlCarrier(ParcelCarrier):
    slug = "dhl"
    name = "DHL"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        raise ParcelProviderError(
            "DHL is niet haalbaar gebleken zonder betaalde dienst — "
            "zie de uitleg bovenaan carriers/dhl.py."
        )

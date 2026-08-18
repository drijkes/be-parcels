"""DPD vervoerder-plugin — SKELET.

DPD heeft (net als de meeste vervoerders) geen simpele publieke JSON-API
voor particulieren. Vul dit skelet aan volgens dezelfde methode als
bpost.py:

  1. Open de DPD track&trace-pagina in je browser met een testpakje.
  2. Open de devtools (F12) → tabblad Network → filter op "Fetch/XHR".
  3. Zoek de request die de statusinformatie ophaalt (meestal JSON).
  4. Kopieer de URL-structuur en de velden die je nodig hebt hieronder.

Zodra dit werkt, registreer je de klasse in carriers/__init__.py.
"""
from __future__ import annotations

from .base import ParcelCarrier, ParcelProviderError, ParcelStatus


class DpdCarrier(ParcelCarrier):
    slug = "dpd"
    name = "DPD"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        raise ParcelProviderError(
            "DPD-ondersteuning is nog niet geïmplementeerd — zie de "
            "instructies bovenaan carriers/dpd.py."
        )

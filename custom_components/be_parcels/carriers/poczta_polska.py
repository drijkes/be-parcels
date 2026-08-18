"""Poczta Polska vervoerder-plugin — SKELET (nog niet geïmplementeerd).

Net als bpost.py zal dit uiteindelijk een gratis, eigen implementatie
worden (geen betalende externe dienst nodig). Volg de stappen uit
README.md ("Zelf een vervoerder toevoegen") om dit in te vullen:
devtools Network-tab op de eigen track&trace-pagina van Poczta Polska,
JSON-endpoint vinden, hieronder implementeren — zie bpost.py als
concreet voorbeeld van hoe dat eruitziet.
"""
from __future__ import annotations

from .base import ParcelCarrier, ParcelProviderError, ParcelStatus


class PocztaPolskaCarrier(ParcelCarrier):
    slug = "poczta_polska"
    name = "Poczta Polska"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        raise ParcelProviderError(
            "Poczta Polska-ondersteuning is nog niet geïmplementeerd — zie de "
            "instructies bovenaan carriers/poczta_polska.py."
        )

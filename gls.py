"""GLS vervoerder-plugin — SKELET.

Zelfde aanpak als dpd.py: gebruik de devtools Network-tab op de GLS
track&trace-pagina om het onderliggende (JSON) endpoint te vinden en
implementeer async_get_status() daarmee. Registreer daarna in
carriers/__init__.py.
"""
from __future__ import annotations

from .base import ParcelCarrier, ParcelProviderError, ParcelStatus


class GlsCarrier(ParcelCarrier):
    slug = "gls"
    name = "GLS"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        raise ParcelProviderError(
            "GLS-ondersteuning is nog niet geïmplementeerd — zie de "
            "instructies bovenaan carriers/gls.py."
        )

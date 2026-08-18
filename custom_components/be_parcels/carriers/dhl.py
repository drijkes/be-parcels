"""DHL Paket (DE) vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).

Voor DHL Express internationaal: gebruik carrier_code 100001 i.p.v. 7041.
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class DhlCarrier(SeventeenTrackCarrier):
    slug = "dhl"
    name = "DHL Paket (DE)"
    requires_postal_code = False
    carrier_code = 7041

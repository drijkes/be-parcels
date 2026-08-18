"""DPD (BE) vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).

Belgische DPD-variant. Voor DPD in een ander land: pas carrier_code aan (zie apicarrier.all.json — er is geen generieke pan-EU DPD-code).
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class DpdCarrier(SeventeenTrackCarrier):
    slug = "dpd"
    name = "DPD (BE)"
    requires_postal_code = False
    carrier_code = 100321

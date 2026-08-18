"""An Post vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class AnPostCarrier(SeventeenTrackCarrier):
    slug = "an_post"
    name = "An Post"
    requires_postal_code = False
    carrier_code = 9051

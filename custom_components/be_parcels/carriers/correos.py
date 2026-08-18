"""Correos vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class CorreosCarrier(SeventeenTrackCarrier):
    slug = "correos"
    name = "Correos"
    requires_postal_code = False
    carrier_code = 19181

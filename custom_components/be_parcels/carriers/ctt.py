"""CTT vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).

Voor CTT Express (pakketdienst i.p.v. post): gebruik carrier_code 100114.
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class CttCarrier(SeventeenTrackCarrier):
    slug = "ctt"
    name = "CTT"
    requires_postal_code = False
    carrier_code = 16101

"""PostNord (Zweden) vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).

Dit is de Zweedse variant. Voor Denemarken: carrier_code 4041 -> 4011 (PostNord Danmark). PostNord is niet actief in Noorwegen/Finland — daar zijn Bring resp. Posti de nationale vervoerders.
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class PostNordCarrier(SeventeenTrackCarrier):
    slug = "postnord"
    name = "PostNord (Zweden)"
    requires_postal_code = False
    carrier_code = 19241

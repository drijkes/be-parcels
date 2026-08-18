"""Deutsche Post vervoerder-plugin — via 17TRACK's gratis publieke endpoint.

Zie carriers/seventeentrack_free.py voor de gedeelde implementatie en
belangrijke caveats (o.a. dat dit endpoint door de brondeveloper zelf
was uitgeschakeld wegens vermoedelijke botbescherming — niet live
getest vanuit deze omgeving).
"""
from __future__ import annotations

from .seventeentrack_free import SeventeenTrackFreeCarrier


class DeutschePostCarrier(SeventeenTrackFreeCarrier):
    slug = "deutsche_post"
    name = "Deutsche Post"

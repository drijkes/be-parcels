"""DHL vervoerder-plugin — via 17TRACK's gratis publieke endpoint.

Zie carriers/seventeentrack_free.py voor de gedeelde implementatie en
belangrijke caveats.
"""
from __future__ import annotations

from .seventeentrack_free import SeventeenTrackFreeCarrier


class DhlCarrier(SeventeenTrackFreeCarrier):
    slug = "dhl"
    name = "DHL"

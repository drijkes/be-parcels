"""PostNL vervoerder-plugin — via de 17TRACK-aggregator.

Zie carriers/aggregator.py voor de gedeelde implementatie, caveats en
hoe je een gratis 17TRACK API-key instelt (Instellingen → Belgian
Parcels → Configureren).

PostNL vereist een extra 'param' (bestemmingsland + postcode). destination_country_iso staat op 'BE' — pas aan indien nodig.
"""
from __future__ import annotations

from .aggregator import SeventeenTrackCarrier


class PostNlCarrier(SeventeenTrackCarrier):
    slug = "postnl"
    name = "PostNL"
    requires_postal_code = True
    carrier_code = 14041
    destination_country_iso = "BE"

"""Registry van alle beschikbare vervoerder-plugins.

Nieuwe vervoerder toevoegen:
  1. Maak carriers/<naam>.py aan met een klasse die ParcelCarrier implementeert.
  2. Importeer en registreer de klasse hieronder in CARRIERS.
  3. De config_flow, services en dashboard-kaart pikken 'm automatisch op
     (voor de kaart: voeg ook een <option> toe in www/be-parcels-card.js).
"""
from __future__ import annotations

from .an_post import AnPostCarrier
from .austrian_post import AustrianPostCarrier
from .base import ParcelCarrier
from .bpost import BpostCarrier
from .chronopost import ChronopostCarrier
from .correos import CorreosCarrier
from .ctt import CttCarrier
from .deutsche_post import DeutschePostCarrier
from .dhl import DhlCarrier
from .dpd import DpdCarrier
from .evri import EvriCarrier
from .fedex import FedexCarrier
from .gls import GlsCarrier
from .inpost import InPostCarrier
from .la_poste import LaPosteCarrier
from .mondial_relay import MondialRelayCarrier
from .poczta_polska import PocztaPolskaCarrier
from .postnl import PostNlCarrier
from .postnord import PostNordCarrier
from .poste_italiane import PosteItalianeCarrier
from .royal_mail import RoyalMailCarrier
from .swiss_post import SwissPostCarrier
from .ups import UpsCarrier

# Vervoerders die écht gratis werken (best-effort, zie hun eigen module
# voor caveats). Gebruikt door de dashboard-kaart om "nog niet
# geïmplementeerd" te tonen bij de rest.
IMPLEMENTED_CARRIERS: set[str] = {"bpost", "postnl", "dpd"}

CARRIERS: dict[str, type[ParcelCarrier]] = {
    cls.slug: cls
    for cls in [
        BpostCarrier,
        DpdCarrier,
        GlsCarrier,
        PostNlCarrier,
        DhlCarrier,
        DeutschePostCarrier,
        LaPosteCarrier,
        ChronopostCarrier,
        MondialRelayCarrier,
        UpsCarrier,
        FedexCarrier,
        RoyalMailCarrier,
        EvriCarrier,
        AnPostCarrier,
        PosteItalianeCarrier,
        CorreosCarrier,
        CttCarrier,
        AustrianPostCarrier,
        PostNordCarrier,
        PocztaPolskaCarrier,
        InPostCarrier,
        SwissPostCarrier,
    ]
}

__all__ = ["ParcelCarrier", "CARRIERS", "IMPLEMENTED_CARRIERS"]

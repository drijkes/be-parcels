"""Registry van alle beschikbare vervoerder-plugins.

Nieuwe vervoerder toevoegen:
  1. Maak carriers/<naam>.py aan met een klasse die ParcelCarrier implementeert.
  2. Importeer en registreer de klasse hieronder in CARRIERS.
  3. De config_flow en sensor platform pikken 'm automatisch op.
"""
from __future__ import annotations

from .base import ParcelCarrier
from .bpost import BpostCarrier
from .dpd import DpdCarrier
from .gls import GlsCarrier

CARRIERS: dict[str, type[ParcelCarrier]] = {
    BpostCarrier.slug: BpostCarrier,
    DpdCarrier.slug: DpdCarrier,
    GlsCarrier.slug: GlsCarrier,
}

__all__ = ["ParcelCarrier", "CARRIERS"]

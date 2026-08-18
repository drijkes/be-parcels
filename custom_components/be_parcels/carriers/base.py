"""Gemeenschappelijke interface voor alle pakjesdienst-plugins.

Elke vervoerder (bpost, DPD, GLS, ...) krijgt hier zijn eigen module die
ParcelCarrier implementeert. Zo blijft de rest van de integratie
(coordinator, sensor, config_flow) volledig vervoerder-onafhankelijk:
er hoeft alleen een nieuwe module + registratie in __init__.py bij te
komen om een vervoerder toe te voegen.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import aiohttp


class ParcelNotFoundError(Exception):
    """Trackingnummer is niet (meer) bekend bij de vervoerder."""


class ParcelProviderError(Exception):
    """De vervoerder gaf een onverwachte/foutieve respons terug."""


@dataclass
class ParcelStatus:
    """Genormaliseerd resultaat, ongeacht welke vervoerder het levert."""

    status: str  # één van de STATUS_* constanten uit const.py
    status_description: str  # leesbare tekst, in de eigen taal van de vervoerder
    carrier: str
    tracking_number: str
    last_update: str | None = None
    expected_delivery: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class ParcelCarrier(ABC):
    """Basisklasse die elke vervoerder-plugin implementeert."""

    slug: str = "base"
    name: str = "Basis vervoerder"
    # Zet op True als de gebruiker ook een postcode moet invullen
    # (sommige vervoerders, zoals bpost, vereisen dit om te kunnen tracken).
    requires_postal_code: bool = False

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    @abstractmethod
    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        """Haal de status van één pakje op en normaliseer die.

        Moet ParcelNotFoundError of ParcelProviderError opgooien
        wanneer het ophalen mislukt, zodat de coordinator dit correct
        als 'unavailable' kan tonen in plaats van te crashen.
        """

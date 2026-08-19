"""Poczta Polska vervoerder-plugin — via de Track123 API.

Zie carriers/track123.py voor de gedeelde implementatie. Vervoerder
wordt automatisch gedetecteerd (geen courier_code opgegeven), zoals
Track123 zelf aanraadt wanneer je niet zeker bent van de exacte code.
"""
from __future__ import annotations

from .track123 import Track123Carrier


class PocztaPolskaCarrier(Track123Carrier):
    slug = "poczta_polska"
    name = "Poczta Polska"

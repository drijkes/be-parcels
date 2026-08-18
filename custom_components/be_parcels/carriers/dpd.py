"""DPD (België) vervoerder-plugin.

Gebaseerd op een ECHTE, live opgevraagde pagina (dank aan test door de
gebruiker) van https://www.dpdgroup.com/be/mydpd/my-parcels/incoming —
dus met veel meer vertrouwen dan de vorige twee pogingen (die allebei
fout bleken: eerst een verkeerde mydpd.be/jws.php-aanname, dan een
verkeerd /my-parcels/search-pad).

De pagina toont de status als leesbare HTML (geen JSON-API), met twee
bruikbare signalen:
  1. Een voortgangsbalk-klasse "progressbar progress_N" (N = 1 t/m 5),
     die exact aangeeft hoever het pakket in DPD's 5-stappen-traject zit.
  2. Een tijdlijn (".parcelStatus") met per stap een label + datum
     (dd/mm/jjjj), waarvan de laatst-ingevulde datum de meest recente
     gebeurtenis is.

Geen postcode nodig voor de basisstatus (enkel voor extra details zoals
afzender/ontvanger, die deze module niet opvraagt).

AANNAME (nog niet 100% zeker): elk pakket doorloopt exact deze 5 vaste
stappen in deze volgorde. Bij afwijkende trajecten (bv. rechtstreekse
bezorging zonder parcelshop-stap) kan progress_N een andere betekenis
hebben — de tekstuele fallback-herkenning vangt dat gedeeltelijk op.
"""
from __future__ import annotations

import re
from datetime import datetime

from .base import ParcelCarrier, ParcelNotFoundError, ParcelProviderError, ParcelStatus
from ..const import (
    STATUS_DELIVERED,
    STATUS_IN_TRANSIT,
    STATUS_LABEL_CREATED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_UNKNOWN,
)

URL_TEMPLATE = (
    "https://www.dpdgroup.com/be/mydpd/my-parcels/incoming"
    "?parcelNumber={number}&lang=nl"
)

# progress_N (voortgangsbalk-klasse) -> onze genormaliseerde status.
_PROGRESS_MAP = {
    1: STATUS_LABEL_CREATED,
    2: STATUS_IN_TRANSIT,
    3: STATUS_IN_TRANSIT,
    4: STATUS_OUT_FOR_DELIVERY,
    5: STATUS_DELIVERED,
}

# Fallback als progress_N niet gevonden wordt: trefwoorden in de laatst
# ingevulde stap-tekst uit de tijdlijn.
_KEYWORD_MAP: list[tuple[str, str]] = [
    ("geleverd", STATUS_DELIVERED),
    ("klaar voor afhaling", STATUS_OUT_FOR_DELIVERY),
    ("in bezorging", STATUS_OUT_FOR_DELIVERY),
    ("onderweg", STATUS_IN_TRANSIT),
    ("in het depot", STATUS_IN_TRANSIT),
    ("overgemaakt aan dpd", STATUS_LABEL_CREATED),
]

_ROW_RE = re.compile(
    r'<div class="col-xs-7">\s*<span>([^<]*)</span>\s*</div>\s*'
    r'<div class="col-xs-5">\s*(?:<span class="bolded inlineDate">([^<]*)</span>)?',
    re.DOTALL,
)


def _guess_status_from_text(text: str) -> str:
    lowered = text.lower()
    for keyword, status in _KEYWORD_MAP:
        if keyword in lowered:
            return status
    return STATUS_UNKNOWN


class DpdCarrier(ParcelCarrier):
    slug = "dpd"
    name = "DPD (BE)"
    requires_postal_code = False

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        url = URL_TEMPLATE.format(number=tracking_number)

        try:
            async with self._session.get(url, timeout=15) as resp:
                if resp.status == 404:
                    raise ParcelNotFoundError(tracking_number)
                if resp.status != 200:
                    raise ParcelProviderError(f"DPD gaf status {resp.status} terug")
                html = await resp.text()
        except ParcelNotFoundError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        # Is dit pakketnummer effectief teruggevonden op de pagina? De
        # tracking-URL toont altijd een <li> per gekend pakket met het
        # nummer erin; staat dat er niet, dan is er niets gevonden.
        if f">{tracking_number}<" not in html:
            raise ParcelNotFoundError(tracking_number)

        # 1) Voortgangsbalk: <div class="progressbar progress_N">
        progress_match = re.search(r'progressbar progress_(\d+)', html)
        progress = int(progress_match.group(1)) if progress_match else None

        # 2) Samenvattingstekst: <span class="gray-out"><span>TEKST</span></span>
        summary_match = re.search(
            r'<span class="gray-out">\s*<span>([^<]*)</span>', html, re.DOTALL
        )
        summary_text = summary_match.group(1).strip() if summary_match else None

        # 3) Tijdlijn: alle (stap, datum)-paren, laatst-ingevulde datum wint.
        rows = _ROW_RE.findall(html)
        last_label, last_date = None, None
        for label, date in rows:
            label = label.strip()
            date = date.strip() if date else ""
            if date:
                last_label, last_date = label, date

        if progress is not None and progress in _PROGRESS_MAP:
            normalized_status = _PROGRESS_MAP[progress]
        elif last_label:
            normalized_status = _guess_status_from_text(last_label)
        elif summary_text:
            normalized_status = _guess_status_from_text(summary_text)
        else:
            normalized_status = STATUS_UNKNOWN

        description = last_label or summary_text or normalized_status

        last_update = None
        if last_date:
            try:
                last_update = datetime.strptime(last_date, "%d/%m/%Y").isoformat()
            except ValueError:
                last_update = last_date  # onbekend formaat, ruwe waarde tonen

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=None,
            extra={"voortgangsstap": progress, "samenvatting": summary_text},
        )

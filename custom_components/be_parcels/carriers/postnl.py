"""PostNL vervoerder-plugin.

LET OP: PostNL heeft geen publieke, officieel-gedocumenteerde
consumenten-API zonder account. Deze module gebruikt hetzelfde
niet-officiële JSON-endpoint dat de publieke Track & Trace-pagina van
PostNL (jouw.postnl.nl/track-and-trace) zelf intern aanspreekt — dus
géén login nodig, enkel trackingnummer + postcode, net als op de
website. Community-gereverse-engineerd (zie o.a.
github.com/malosaa/PostNL_DHL_Tracker_HA), niet officieel
gedocumenteerd door PostNL zelf, dus dit endpoint kan zonder
aankondiging wijzigen.

BELANGRIJKE AANNAME: het endpoint verwacht een bestemmingslandcode
("NL" in het voorbeeld dat we terugvonden). Hieronder staat "BE" als
standaard (voor Belgische ontvangers) — pas DESTINATION_COUNTRY_CODE
hieronder aan als je pakjes naar een ander land laat leveren.
"""
from __future__ import annotations

from typing import Any

from .base import ParcelCarrier, ParcelNotFoundError, ParcelProviderError, ParcelStatus
from ..const import (
    STATUS_DELIVERED,
    STATUS_EXCEPTION,
    STATUS_IN_TRANSIT,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_UNKNOWN,
)

API_URL_TEMPLATE = (
    "https://jouw.postnl.nl/track-and-trace/api/trackAndTrace/"
    "{barcode}-{country}-{postal_code}"
)

DESTINATION_COUNTRY_CODE = "BE"


class PostNlCarrier(ParcelCarrier):
    slug = "postnl"
    name = "PostNL"
    requires_postal_code = True

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        if not postal_code:
            raise ParcelProviderError(
                "PostNL heeft de postcode van de ontvanger nodig om te kunnen tracken."
            )

        # Spaties weg (PostNL verwacht bv. "1000AB", geen "1000 AB").
        clean_postal_code = postal_code.replace(" ", "").upper()
        url = API_URL_TEMPLATE.format(
            barcode=tracking_number,
            country=DESTINATION_COUNTRY_CODE,
            postal_code=clean_postal_code,
        )
        params = {"language": "nl", "D": DESTINATION_COUNTRY_CODE}

        try:
            async with self._session.get(url, params=params, timeout=15) as resp:
                if resp.status == 404:
                    raise ParcelNotFoundError(tracking_number)
                if resp.status != 200:
                    raise ParcelProviderError(f"PostNL gaf status {resp.status} terug")
                data: dict[str, Any] = await resp.json()
        except ParcelNotFoundError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk/parsing fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        colli = data.get("colli") or {}
        if not colli:
            raise ParcelNotFoundError(tracking_number)

        # "colli" is keyed op het barcode-nummer; er is er hier maar één.
        item = next(iter(colli.values()))

        is_delivered = bool(item.get("isDelivered"))
        is_return = bool(item.get("isReturnShipment"))
        before_first_attempt = item.get("beforeFirstDeliveryAttempt")
        is_at_retail_location = bool(item.get("isAtRetailLocation"))

        # Best-effort mapping: PostNL geeft geen simpele "status"-enum
        # terug zoals bpost, dus we leiden de genormaliseerde status af
        # uit een combinatie van boolean-velden. Klopt dit niet met wat
        # jij ziet? Pas de mapping hieronder aan.
        if is_delivered:
            normalized_status = STATUS_DELIVERED
        elif is_return:
            normalized_status = STATUS_EXCEPTION
        elif is_at_retail_location:
            # Klaar om afgehaald te worden — dichtst bij "onderweg" van
            # onze bestaande statussen.
            normalized_status = STATUS_OUT_FOR_DELIVERY
        elif before_first_attempt is False:
            # Er is al een bezorgpoging geweest vandaag: waarschijnlijk
            # onderweg of net bezorgd.
            normalized_status = STATUS_OUT_FOR_DELIVERY
        else:
            normalized_status = STATUS_IN_TRANSIT

        status_phase = item.get("statusPhase") or {}
        description = status_phase.get("message") or normalized_status

        eta = item.get("eta") or {}
        expected_delivery = None
        if eta.get("start") and eta.get("end"):
            expected_delivery = f"{eta['start']} - {eta['end']}"

        last_update = item.get("deliveryDate")

        recipient = (item.get("recipient") or {}).get("names", {}).get("personName")
        sender = (item.get("sender") or {}).get("names", {}).get("personName") or (
            item.get("sender") or {}
        ).get("names", {}).get("companyName")

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=expected_delivery,
            extra={
                "sender": sender,
                "ontvanger": recipient,
                "is_at_retail_location": is_at_retail_location,
                "is_return_shipment": is_return,
            },
        )

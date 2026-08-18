"""bpost vervoerder-plugin.

LET OP: bpost heeft geen publieke, officiële consumenten-API. Deze
module gebruikt hetzelfde niet-officiële JSON-endpoint dat de eigen
Track & Trace-website van bpost (track.bpost.cloud) intern aanspreekt.
Dat werkt in de praktijk goed, maar bpost kan dit endpoint op elk
moment zonder aankondiging wijzigen — dan moet deze module aangepast
worden. Gebruik dus niet te agressieve polling (elke 20-30 min is ruim
voldoende) om geen argwaan/rate-limiting te wekken.
"""
from __future__ import annotations

from typing import Any

from .base import ParcelCarrier, ParcelNotFoundError, ParcelProviderError, ParcelStatus
from ..const import (
    STATUS_DELIVERED,
    STATUS_EXCEPTION,
    STATUS_IN_TRANSIT,
    STATUS_LABEL_CREATED,
    STATUS_OUT_FOR_DELIVERY,
    STATUS_UNKNOWN,
)

API_URL = "https://track.bpost.cloud/track/items"

# Mapping van bpost's interne "activeStep.name" naar onze genormaliseerde status.
_STEP_MAP = {
    "labelled": STATUS_LABEL_CREATED,
    "in_transit": STATUS_IN_TRANSIT,
    "on_round": STATUS_OUT_FOR_DELIVERY,
    "delivered": STATUS_DELIVERED,
    "exception": STATUS_EXCEPTION,
}


class BpostCarrier(ParcelCarrier):
    slug = "bpost"
    name = "bpost"
    requires_postal_code = True

    async def async_get_status(
        self, tracking_number: str, postal_code: str | None = None
    ) -> ParcelStatus:
        if not postal_code:
            raise ParcelProviderError(
                "bpost heeft de postcode van de ontvanger nodig om te kunnen tracken."
            )

        params = {"itemIdentifier": tracking_number, "postalCode": postal_code}
        try:
            async with self._session.get(API_URL, params=params, timeout=15) as resp:
                if resp.status == 404:
                    raise ParcelNotFoundError(tracking_number)
                if resp.status != 200:
                    raise ParcelProviderError(f"bpost gaf status {resp.status} terug")
                data: dict[str, Any] = await resp.json()
        except ParcelNotFoundError:
            raise
        except Exception as err:  # noqa: BLE001 - netwerk/parsing fouten normaliseren
            raise ParcelProviderError(str(err)) from err

        items = data.get("items") or []
        if not items:
            raise ParcelNotFoundError(tracking_number)

        item = items[0]
        active_step = (item.get("activeStep") or {}).get("name")
        normalized_status = _STEP_MAP.get(active_step, STATUS_UNKNOWN)

        events = item.get("events") or []
        description = STATUS_UNKNOWN
        last_update = None
        if events:
            latest = events[0]
            last_update = latest.get("time")
            key = latest.get("key") or {}
            # bpost geeft meertalige teksten terug; NL heeft hier de voorkeur.
            description = (
                key.get("NL", {}).get("description")
                or key.get("EN", {}).get("description")
                or normalized_status
            )

        expected_range = item.get("expectedDeliveryTimeRange") or {}
        expected_delivery = None
        if expected_range:
            expected_delivery = f"{expected_range.get('time1', '')} - {expected_range.get('time2', '')}"

        sender = item.get("senderCommercialName") or (item.get("sender") or {}).get("name")

        return ParcelStatus(
            status=normalized_status,
            status_description=description,
            carrier=self.name,
            tracking_number=tracking_number,
            last_update=last_update,
            expected_delivery=expected_delivery,
            extra={"sender": sender, "raw_active_step": active_step},
        )

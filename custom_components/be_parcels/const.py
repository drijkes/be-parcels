"""Constants for the Belgian Parcels integration."""
from datetime import timedelta

DOMAIN = "be_parcels"
PLATFORMS = ["sensor"]

CONF_CARRIER = "carrier"
CONF_TRACKING_NUMBER = "tracking_number"
CONF_POSTAL_CODE = "postal_code"
CONF_NAME = "name"
CONF_PARCELS = "parcels"  # lijst van pakjes, opgeslagen in entry.options
CONF_NOTIFY_SERVICES = "notify_services"  # lijst, bv. ["mobile_app_jan", "mobile_app_marie"]

DEFAULT_SCAN_INTERVAL = timedelta(minutes=20)

# Genormaliseerde statussen, onafhankelijk van vervoerder.
STATUS_UNKNOWN = "unknown"
STATUS_LABEL_CREATED = "label_created"
STATUS_IN_TRANSIT = "in_transit"
STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
STATUS_DELIVERED = "delivered"
STATUS_EXCEPTION = "exception"
STATUS_NOT_FOUND = "not_found"

SERVICE_ADD_PARCEL = "add_parcel"
SERVICE_REMOVE_PARCEL = "remove_parcel"

# Event dat gegooid wordt telkens een pakje van status verandert.
# Automations kunnen hierop triggeren voor meldingen (bv. bij out_for_delivery).
EVENT_STATUS_CHANGED = f"{DOMAIN}_status_changed"

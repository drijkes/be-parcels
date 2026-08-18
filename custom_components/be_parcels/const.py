"""Constants for the Belgian Parcels integration."""
from datetime import timedelta

DOMAIN = "be_parcels"
PLATFORMS = ["sensor"]

CONF_CARRIER = "carrier"
CONF_TRACKING_NUMBER = "tracking_number"
CONF_POSTAL_CODE = "postal_code"
CONF_NAME = "name"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=20)

# Genormaliseerde statussen, onafhangelijk van vervoerder.
STATUS_UNKNOWN = "unknown"
STATUS_LABEL_CREATED = "label_created"
STATUS_IN_TRANSIT = "in_transit"
STATUS_OUT_FOR_DELIVERY = "out_for_delivery"
STATUS_DELIVERED = "delivered"
STATUS_EXCEPTION = "exception"

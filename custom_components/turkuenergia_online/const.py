"""Constants for the unofficial Turku EnergiaOnline integration."""
DOMAIN = "turkuenergia_online"
API_BASE = "https://digiapi.turkuenergia.fi/energiaonline-backend/v1"
CONSUMPTION_PATH = "/ConsumptionAndProductionData/GetConsumptionAndProductionData"
CONF_API_KEY = "api_key"
CONF_CUSTOMER_CODE = "customer_code"
CONF_METERING_POINT = "metering_point_code"
CONF_RELATED_POINT = "related_metering_point_code"
CONF_WEATHER_LOCATION = "weather_location"
CONF_RESOLUTION = "resolution"
RESOLUTION_QUARTER = "PT15M"  # Experimental; not verified against provider.
RESOLUTION_DAILY = "P1D"  # Observed in a redacted, private API capture.
UPDATE_SECONDS = 3600

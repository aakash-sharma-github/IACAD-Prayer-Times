"""Constants for the IACAD Prayer Times integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "iacad_prayer"
PLATFORMS: Final = ("sensor", "binary_sensor")

CONF_LATITUDE: Final = "latitude"
CONF_LONGITUDE: Final = "longitude"
CONF_TIMEZONE: Final = "timezone"
CONF_CALCULATION_METHOD: Final = "calculation_method"
CONF_MADHAB: Final = "madhab"
CONF_HIGH_LATITUDE_RULE: Final = "high_latitude_rule"

API_BASE_URL: Final = "https://api.aakashsharma.com.np"

CALCULATION_METHODS: Final = (
    "muslim_world_league",
    "egyptian",
    "karachi",
    "umm_al_qura",
    "dubai",
    "iacad_dubai",
    "moon_sighting_committee",
    "north_america",
    "kuwait",
    "qatar",
    "singapore",
    "uoif",
)
MADHABS: Final = ("shafi", "hanafi")
HIGH_LATITUDE_RULES: Final = (
    "middle_of_the_night",
    "seventh_of_the_night",
    "twilight_angle",
)

DEFAULT_CALCULATION_METHOD: Final = "iacad_dubai"
DEFAULT_MADHAB: Final = "shafi"
DEFAULT_HIGH_LATITUDE_RULE: Final = "middle_of_the_night"

DATE_CHECK_INTERVAL: Final = timedelta(minutes=15)

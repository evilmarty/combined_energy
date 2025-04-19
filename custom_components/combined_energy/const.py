"""Constants for the Combined Energy integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final[str] = "combined_energy"

LOGGER = logging.getLogger(__package__)

CURRENCY_AUD = "AUD"

# Data for Combined Energy requests.
DATA_API_CLIENT: Final[str] = "api_client"
DATA_COORDINATOR: Final[str] = "coordinator"

# Config for combined energy requests.
CONF_INSTALLATION_ID: Final[str] = "installation_id"
DEFAULT_NAME: Final[str] = "Combined Energy"

CONNECTIVITY_UPDATE_DELAY: Final[timedelta] = timedelta(seconds=30)
LOG_SESSION_REFRESH_DELAY: Final[timedelta] = timedelta(minutes=10)
READINGS_UPDATE_DELAY: Final[timedelta] = timedelta(minutes=1)
TARIFF_DETAILS_UPDATE_DELAY: Final[timedelta] = timedelta(hours=1)

# Base urls for Combined Energy API
BASE_URL_USER_ACCESS: Final[str] = "https://onwatch.combined.energy"
BASE_URL_DATA_ACCESS: Final[str] = "https://ds20.combined.energy/data-service"
BASE_URL_MQTT_ACCESS: Final[str] = "https://dp20.combined.energy"

"""Constants for the Combined Energy integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final[str] = "combined_energy"

LOGGER = logging.getLogger(__package__)

# Runtime data keys.
DATA_BRIDGE_CLIENT: Final[str] = "bridge_client"
DATA_COORDINATOR: Final[str] = "coordinator"

# Config entry keys.
CONF_MQTT_PASSWORD: Final[str] = "mqtt_password"
DEFAULT_NAME: Final[str] = "Combined Energy"

MQTT_RECONNECT_DELAY: Final[timedelta] = timedelta(seconds=10)
MQTT_PORT_WEBSOCKET: Final[int] = 8080
MQTT_USERNAME_SYSTEM: Final[str] = "sys"
MQTT_TOPIC_PREFIX: Final[str] = "cet-ecn"
MQTT_READINGS_TOPIC_FILTER: Final[str] = "dmg/readings/#"
READINGS_COORDINATOR_NAME: Final[str] = "readings"

INSTALLATION_JSON_PATH: Final[str] = (
    "/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f"
    "%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f"
    "var%2fopt%2fcet%2fconfig%2finstallation%2ejson"
)
SYSTEM_KEY_PATH: Final[str] = (
    "/%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f"
    "%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2f"
    "var%2fopt%2fcet%2fconfig%2fsystem%2ekey"
)

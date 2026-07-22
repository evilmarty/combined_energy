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
CONF_STALE_ENTITY_CLEANUP_PENDING: Final[str] = "stale_entity_cleanup_pending"
DEFAULT_NAME: Final[str] = "Combined Energy"

MQTT_RECONNECT_DELAY: Final[timedelta] = timedelta(seconds=10)
MQTT_PORT_WEBSOCKET: Final[int] = 8080
MQTT_USERNAME_SYSTEM: Final[str] = "sys"
MQTT_TOPIC_PREFIX: Final[str] = "cet-ecn"
MQTT_READINGS_TOPIC_FILTER: Final[str] = "dmg/readings/#"
MQTT_COMMAND_LOGGING_START_TOPIC: Final[str] = "dmg/command/logging/start"
READINGS_WATCHDOG_INTERVAL: Final[timedelta] = timedelta(minutes=5)
READINGS_COORDINATOR_NAME: Final[str] = "readings"
ENERGY_ZERO_EPSILON: Final[float] = 1e-9
ENERGY_STATE_ROUNDING_DIGITS: Final[int] = 6

INSTALLATION_DEVICE_TYPE_GATEWAY: Final[str] = "GATEWAY"
INSTALLATION_DEVICE_TYPE_SOLAR_PV: Final[str] = "SOLAR_PV"
INSTALLATION_DEVICE_TYPE_GRID_METER: Final[str] = "GRID_METER"
INSTALLATION_DEVICE_TYPE_GENERIC_CONSUMER: Final[str] = "GENERIC_CONSUMER"
INSTALLATION_DEVICE_TYPE_WATER_HEATER: Final[str] = "WATER_HEATER"
INSTALLATION_DEVICE_TYPE_ENERGY_BALANCE: Final[str] = "ENERGY_BALANCE"
INSTALLATION_DEVICE_TYPE_COMBINER: Final[str] = "COMBINER"

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

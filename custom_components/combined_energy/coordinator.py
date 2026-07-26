"""MQTT-backed coordinators for Combined Energy."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from custom_components.combined_energy.bridge import (
    BridgeConnectionError,
    MqttBridgeClient,
)
from custom_components.combined_energy.const import (
    INTEL_COORDINATOR_NAME,
    LOGGER,
    MQTT_READINGS_TOPIC_FILTER,
    MQTT_RESPONSE_INTEL_TOPIC,
    READINGS_COORDINATOR_NAME,
    READINGS_WATCHDOG_INTERVAL,
)
from custom_components.combined_energy.models import Intel, Readings
from custom_components.combined_energy.storage import ReadingsStore
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import (
    UNDEFINED,
    DataUpdateCoordinator,
    UndefinedType,
    UpdateFailed,
)


class CombinedEnergyReadingsCoordinator(DataUpdateCoordinator[Readings]):
    """Update coordinator for MQTT readings."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MqttBridgeClient,
        readings_store: ReadingsStore,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize readings coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=READINGS_COORDINATOR_NAME,
            update_interval=None,
            update_method=self._async_update,
            always_update=True,
        )
        self.client = client
        self._watchdog_interval = READINGS_WATCHDOG_INTERVAL
        self._last_message_received_at: datetime | None = None
        self._last_watchdog_check_at: datetime | None = None
        self._watchdog_unsub: Callable[[], None] | None = None
        self._readings_store = readings_store
        LOGGER.debug(
            "Subscribing readings coordinator to topic %s", self._readings_topic
        )
        self.client.subscribe(self._readings_topic, self._handle_readings_message)
        self._check_for_stale_messages()

    @callback
    def _schedule_refresh(self) -> None:
        """Engage watchdog when coordinator scheduling starts."""
        super()._schedule_refresh()
        if self._watchdog_unsub is not None:
            return
        self._watchdog_unsub = async_track_time_interval(
            self.hass,
            self._check_for_stale_messages,
            self._watchdog_interval,
        )

    @callback
    def _unschedule_refresh(self) -> None:
        """Disengage watchdog when coordinator scheduling stops."""
        if self._watchdog_unsub is not None:
            self._watchdog_unsub()
            self._watchdog_unsub = None
        super()._unschedule_refresh()

    @property
    def _readings_topic(self) -> str:
        """Topic filter for readings messages."""
        return self.client.topic(MQTT_READINGS_TOPIC_FILTER)

    async def _async_update(self) -> Readings:
        """Return latest reading from MQTT stream."""
        if self.data is not None:
            return self.data
        raise UpdateFailed("No MQTT readings available yet")

    def _check_for_stale_messages(self, now: datetime | None = None) -> None:
        """Check if new messages arrived since last watchdog check."""
        LOGGER.debug("Checking for stale MQTT readings messages")
        check_time = now or datetime.now(UTC)
        last_watchdog_check_at = self._last_watchdog_check_at or check_time

        if (
            self._last_message_received_at is None
            or self._last_message_received_at < last_watchdog_check_at
        ):
            LOGGER.debug(
                "No MQTT readings received since %s, triggering logging start",
                last_watchdog_check_at.isoformat(),
            )
            try:
                self.client.publish_logging_start()
                LOGGER.debug("triggered logging start command")
            except BridgeConnectionError:
                LOGGER.exception("Failed to publish MQTT logging start command")
        self._last_watchdog_check_at = check_time

    def _handle_readings_message(self, topic: str, payload: bytes) -> None:
        """Parse and publish new readings from MQTT payloads."""
        LOGGER.debug(
            "Processing MQTT readings message topic=%s payload_bytes=%s",
            topic,
            len(payload),
        )
        self._last_message_received_at = datetime.now(UTC)
        self.hass.async_create_task(self._async_process_readings_message(payload))

    async def _async_process_readings_message(self, payload: bytes) -> None:
        """Parse, normalize, and publish new MQTT readings."""
        readings = Readings.from_mqtt_message(payload)
        accumulated = await self._readings_store.async_record_readings(readings)
        if accumulated is None:
            return
        self.async_set_updated_data(accumulated)


class CombinedEnergyIntelCoordinator(DataUpdateCoordinator[Intel]):
    """Update coordinator for MQTT intel responses."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: MqttBridgeClient,
        config_entry: ConfigEntry | None | UndefinedType = UNDEFINED,
    ) -> None:
        """Initialize intel coordinator."""
        super().__init__(
            hass=hass,
            logger=LOGGER,
            config_entry=config_entry,
            name=INTEL_COORDINATOR_NAME,
            update_interval=None,
            update_method=self._async_update,
            always_update=True,
        )
        self.client = client
        self._intel_request_sent = False
        LOGGER.debug("Subscribing intel coordinator to topic %s", self._intel_topic)
        self.client.subscribe(self._intel_topic, self._handle_intel_message)

    @callback
    def _schedule_refresh(self) -> None:
        """Trigger intel request when coordinator becomes active."""
        super()._schedule_refresh()
        if self._intel_request_sent:
            return
        if self.request_intel():
            self._intel_request_sent = True

    @property
    def _intel_topic(self) -> str:
        """Topic for intel response messages."""
        return self.client.topic(MQTT_RESPONSE_INTEL_TOPIC)

    async def _async_update(self) -> Intel:
        """Return latest intel payload from MQTT stream."""
        if self.data is not None:
            return self.data
        raise UpdateFailed("No MQTT intel payload available yet")

    def _handle_intel_message(self, topic: str, payload: bytes) -> None:
        """Parse and publish new intel payloads."""
        LOGGER.debug(
            "Processing MQTT intel message topic=%s payload_bytes=%s",
            topic,
            len(payload),
        )
        self.hass.async_create_task(self._async_process_intel_message(payload))

    def request_intel(self) -> bool:
        """Request an intel payload from the bridge."""
        try:
            self.client.publish_request_intel()
        except BridgeConnectionError:
            LOGGER.exception("Failed to publish MQTT intel request command")
            return False
        else:
            return True

    async def _async_process_intel_message(self, payload: bytes) -> None:
        """Parse and publish new intel payload."""
        json_start = payload.find(b"{")
        if json_start < 0:
            raise ValueError("No JSON object found in intel MQTT payload")
        intel = Intel.model_validate_json(payload[json_start:])
        self.async_set_updated_data(intel)

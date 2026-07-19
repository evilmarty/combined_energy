"""Bridge bootstrap and MQTT runtime client."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import contextlib
from dataclasses import dataclass
import json
from typing import Any

from aiohttp import ClientError
from paho.mqtt import client as mqtt_client
from pydantic import ValidationError

from custom_components.combined_energy.const import (
    CONF_MQTT_PASSWORD,
    INSTALLATION_JSON_PATH,
    LOGGER,
    MQTT_PORT_WEBSOCKET,
    MQTT_RECONNECT_DELAY,
    MQTT_TOPIC_PREFIX,
    MQTT_USERNAME_SYSTEM,
    SYSTEM_KEY_PATH,
)
from custom_components.combined_energy.models import Installation
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


class BridgeBootstrapError(Exception):
    """Raised when bridge bootstrap data cannot be loaded."""


class BridgeConnectionError(Exception):
    """Raised when initial MQTT connection to bridge broker fails."""


@dataclass(slots=True)
class BridgeBootstrap:
    """Resolved bridge connection and installation details."""

    bridge_host: str
    mqtt_password: str
    installation: Installation

    def as_config_data(self) -> dict[str, Any]:
        """Serialize config data stored in config entry."""
        return {
            CONF_HOST: self.bridge_host,
            CONF_MQTT_PASSWORD: self.mqtt_password,
        }


async def _get_json(hass: HomeAssistant, host: str, path: str) -> dict[str, Any]:
    """GET JSON payload from host/path."""
    session = async_get_clientsession(hass)
    url = f"http://{host}{path}"
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            body = await response.text()
    except (ClientError, TimeoutError) as err:
        raise BridgeBootstrapError(f"Request failed for {url}") from err

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as err:
        raise BridgeBootstrapError(f"Invalid JSON payload from {url}") from err
    if not isinstance(payload, dict):
        raise BridgeBootstrapError(f"Unexpected JSON payload from {url}")
    return payload


async def _get_text(hass: HomeAssistant, host: str, path: str) -> str:
    """GET text payload from host/path."""
    session = async_get_clientsession(hass)
    url = f"http://{host}{path}"
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            body = await response.text()
    except (ClientError, TimeoutError) as err:
        raise BridgeBootstrapError(f"Request failed for {url}") from err
    value = body.strip()
    if not value:
        raise BridgeBootstrapError(f"Empty payload from {url}")
    return value


async def _load_installation(hass: HomeAssistant, host: str) -> Installation:
    """Load and validate installation payload from bridge."""
    LOGGER.debug("Loading installation payload from bridge host %s", host)
    payload = await _get_json(hass, host, INSTALLATION_JSON_PATH)
    try:
        installation = Installation.model_validate(payload)
        _ = installation.gateway_id
    except (ValueError, ValidationError) as err:
        raise BridgeBootstrapError(str(err)) from err
    LOGGER.debug(
        "Loaded installation id=%s gateway_id=%s name=%s",
        installation.id,
        installation.gateway_id,
        installation.name,
    )
    return installation


async def _create_bootstrap(
    hass: HomeAssistant, host: str, mqtt_password: str
) -> BridgeBootstrap:
    """Create bridge bootstrap data from live bridge installation."""
    installation = await _load_installation(hass, host)
    return BridgeBootstrap(
        bridge_host=host,
        mqtt_password=mqtt_password,
        installation=installation,
    )


async def validate_bridge_host(hass: HomeAssistant, host: str) -> BridgeBootstrap:
    """Validate host and return resolved bridge bootstrap data."""
    system_key = await _get_text(hass, host, SYSTEM_KEY_PATH)
    return await _create_bootstrap(hass, host, system_key)


async def bootstrap_from_entry_data(
    hass: HomeAssistant, data: dict[str, Any]
) -> BridgeBootstrap:
    """Initialize bridge bootstrap by refreshing installation payload on startup."""
    return await _create_bootstrap(hass, data[CONF_HOST], data[CONF_MQTT_PASSWORD])


class MqttBridgeClient:
    """MQTT bridge client using paho-mqtt websockets."""

    def __init__(self, hass: HomeAssistant, bootstrap: BridgeBootstrap) -> None:
        """Initialize bridge client."""
        self.hass = hass
        self.bootstrap = bootstrap
        self._loop = hass.loop
        self._subscriptions: list[
            tuple[str, Callable[[str, bytes], Awaitable[None] | None]]
        ] = []
        self._message_tasks: set[asyncio.Task[None]] = set()
        self._mqtt_client: mqtt_client.Client | None = None
        self._connected_event = asyncio.Event()
        self._startup_error: Exception | None = None

    def subscribe(
        self,
        topic_pattern: str,
        callback: Callable[[str, bytes], Awaitable[None] | None],
    ) -> None:
        """Register a topic subscription callback."""
        self._subscriptions.append((topic_pattern, callback))
        if self._mqtt_client is None:
            return
        result = self._mqtt_client.subscribe(topic_pattern)
        if result[0] != mqtt_client.MQTT_ERR_SUCCESS:
            raise BridgeConnectionError(
                f"Subscription failed for {topic_pattern}: "
                f"{mqtt_client.error_string(result[0])}"
            )

    def topic(self, topic: str) -> str:
        """Build a full MQTT topic from a relative topic path."""
        gateway_id = self.bootstrap.installation.gateway_id
        return f"{MQTT_TOPIC_PREFIX}/{gateway_id}/{topic.lstrip('/')}"

    async def async_start(self) -> None:
        """Start MQTT client and ensure first connection succeeds."""
        if self._mqtt_client is not None:
            LOGGER.debug(
                "MQTT client already started for host %s", self.bootstrap.bridge_host
            )
            return
        LOGGER.debug(
            "Starting MQTT client for host=%s gateway_id=%s",
            self.bootstrap.bridge_host,
            self.bootstrap.installation.gateway_id,
        )
        self._connected_event.clear()
        self._startup_error = None

        client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION2,
            client_id=f"combined-energy-{self.bootstrap.installation.gateway_id}",
            transport="websockets",
            protocol=mqtt_client.MQTTv311,
        )
        client.username_pw_set(
            username=MQTT_USERNAME_SYSTEM,
            password=self.bootstrap.mqtt_password,
        )
        client.reconnect_delay_set(
            min_delay=int(MQTT_RECONNECT_DELAY.total_seconds()),
            max_delay=60,
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        client.on_message = self._on_message

        try:
            client.connect_async(
                self.bootstrap.bridge_host,
                MQTT_PORT_WEBSOCKET,
                keepalive=60,
            )
            client.loop_start()
            LOGGER.debug(
                "MQTT connect initiated host=%s port=%s",
                self.bootstrap.bridge_host,
                MQTT_PORT_WEBSOCKET,
            )
        except Exception as err:
            raise BridgeConnectionError(
                f"Failed to initialize MQTT broker client: {err}"
            ) from err

        self._mqtt_client = client
        await asyncio.wait_for(self._connected_event.wait(), timeout=15)
        if self._startup_error is not None:
            raise BridgeConnectionError(
                f"Failed to connect to MQTT broker: {self._startup_error}"
            ) from self._startup_error

    async def async_stop(self) -> None:
        """Stop MQTT client loop."""
        LOGGER.debug("Stopping MQTT client for host %s", self.bootstrap.bridge_host)
        if self._mqtt_client is not None:
            with contextlib.suppress(Exception):
                self._mqtt_client.disconnect()
            self._mqtt_client.loop_stop()
            self._mqtt_client = None
        for task in tuple(self._message_tasks):
            task.cancel()
        if self._message_tasks:
            await asyncio.gather(*self._message_tasks, return_exceptions=True)
            self._message_tasks.clear()

    def _on_connect(
        self,
        client: mqtt_client.Client,
        _: Any,
        __: Any,
        reason_code: mqtt_client.ReasonCode,
        ___: mqtt_client.Properties | None = None,
    ) -> None:
        """Handle broker connect callback."""
        if reason_code == 0:
            LOGGER.debug(
                "Connected to MQTT broker host=%s; subscribing to %s topic patterns",
                self.bootstrap.bridge_host,
                len(self._subscriptions),
            )
            for topic_pattern, _ in self._subscriptions:
                result = client.subscribe(topic_pattern)
                if result[0] != mqtt_client.MQTT_ERR_SUCCESS:
                    self._startup_error = BridgeConnectionError(
                        f"Subscription failed for {topic_pattern}: "
                        f"{mqtt_client.error_string(result[0])}"
                    )
                    self._loop.call_soon_threadsafe(self._connected_event.set)
                    return
                LOGGER.debug("Subscribed to MQTT topic pattern %s", topic_pattern)
            self._loop.call_soon_threadsafe(self._connected_event.set)
            return
        self._startup_error = BridgeConnectionError(
            f"Connection refused: {reason_code}"
        )
        LOGGER.debug("MQTT broker connection refused: %s", reason_code)
        self._loop.call_soon_threadsafe(self._connected_event.set)

    def _on_disconnect(
        self,
        _: mqtt_client.Client,
        __: Any,
        ___: mqtt_client.DisconnectFlags,
        reason_code: mqtt_client.ReasonCode,
        ____: mqtt_client.Properties | None = None,
    ) -> None:
        """Handle broker disconnect callback."""
        if reason_code != 0:
            LOGGER.warning("MQTT bridge disconnected with code %s", reason_code)
        else:
            LOGGER.debug("MQTT bridge disconnected with code %s", reason_code)

    def _on_message(
        self,
        _: mqtt_client.Client,
        __: Any,
        message: mqtt_client.MQTTMessage,
    ) -> None:
        """Handle broker message callback."""
        topic = message.topic
        if isinstance(topic, bytes):
            topic = topic.decode()
        payload = bytes(message.payload)
        LOGGER.debug(
            "Received MQTT message topic=%s payload_bytes=%s",
            topic,
            len(payload),
        )
        self._loop.call_soon_threadsafe(self._schedule_message, topic, payload)

    def _schedule_message(self, topic: str, payload: bytes) -> None:
        """Schedule topic-based message handling on asyncio loop."""
        task = self.hass.async_create_task(self._handle_message(topic, payload))
        self._message_tasks.add(task)
        task.add_done_callback(self._message_tasks.discard)

    async def _handle_message(self, topic: str, payload: bytes) -> None:
        """Route and handle incoming MQTT payload by topic."""
        matched = 0
        for topic_pattern, callback in tuple(self._subscriptions):
            if not _topic_matches(topic_pattern, topic):
                continue
            matched += 1
            result = callback(topic, payload)
            if asyncio.iscoroutine(result):
                await result
        if matched == 0:
            LOGGER.debug("No MQTT subscription callbacks matched topic=%s", topic)


def _topic_matches(topic_pattern: str, topic: str) -> bool:
    """Check whether a topic matches an MQTT topic filter."""
    pattern_levels = topic_pattern.split("/")
    topic_levels = topic.split("/")

    for index, pattern in enumerate(pattern_levels):
        if pattern == "#":
            return True
        if index >= len(topic_levels):
            return False
        if pattern != "+" and pattern != topic_levels[index]:
            return False
    return len(topic_levels) == len(pattern_levels)


async def get_bridge_client(
    hass: HomeAssistant, data: dict[str, Any]
) -> MqttBridgeClient:
    """Create bridge client from config entry data."""
    bootstrap = await bootstrap_from_entry_data(hass, data)
    return MqttBridgeClient(hass, bootstrap)

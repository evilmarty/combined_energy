"""Tests for bridge bootstrap and installation mapping."""

import asyncio
import json
from unittest.mock import MagicMock, patch

from aiohttp import ClientSession, web
import pytest

from custom_components.combined_energy.bridge import (
    BridgeBootstrap,
    BridgeBootstrapError,
    MqttBridgeClient,
    bootstrap_from_entry_data,
    validate_bridge_host,
)
from custom_components.combined_energy.models import Installation


@pytest.mark.asyncio
async def test_validate_bridge_host_returns_bootstrap(aiohttp_raw_server, fixture_path):
    """Validate host via installation/system key endpoints."""

    installation_payload = (fixture_path / "installation.json").read_text()
    installation_data = json.loads(installation_payload)

    async def handler(request):
        if request.path.endswith("/var/opt/cet/config/installation.json"):
            return web.Response(
                text=installation_payload, content_type="application/json"
            )
        if request.path.endswith("/var/opt/cet/config/system.key"):
            return web.Response(text="bridge-secret")
        return web.Response(status=404)

    server = await aiohttp_raw_server(handler)
    host = f"{server.host}:{server.port}"
    hass = MagicMock()

    async with ClientSession() as session:
        with patch(
            "custom_components.combined_energy.bridge.async_get_clientsession",
            return_value=session,
        ):
            bootstrap = await validate_bridge_host(hass, host)

    assert bootstrap.bridge_host == host
    assert bootstrap.mqtt_password == "bridge-secret"
    assert bootstrap.installation.id == installation_data["id"]


@pytest.mark.asyncio
async def test_validate_bridge_host_raises_when_no_gwid(
    aiohttp_raw_server, fixture_path
):
    """Fail validation when gwId is missing."""

    installation_payload = (fixture_path / "installation.json").read_text()
    payload_without_gwid = json.loads(installation_payload)
    payload_without_gwid.pop("gwId", None)

    async def handler(request):
        if request.path.endswith("/var/opt/cet/config/installation.json"):
            return web.Response(
                text=json.dumps(payload_without_gwid), content_type="application/json"
            )
        if request.path.endswith("/var/opt/cet/config/system.key"):
            return web.Response(text="bridge-secret")
        return web.Response(status=404)

    server = await aiohttp_raw_server(handler)
    host = f"{server.host}:{server.port}"
    hass = MagicMock()

    async with ClientSession() as session:
        with patch(
            "custom_components.combined_energy.bridge.async_get_clientsession",
            return_value=session,
        ):
            with pytest.raises(BridgeBootstrapError):
                await validate_bridge_host(hass, host)


@pytest.mark.asyncio
async def test_bootstrap_from_entry_data_refreshes_installation(
    aiohttp_raw_server,
    fixture_path,
):
    """Initialize bootstrap from stored data and live installation fetch."""

    installation_payload = (fixture_path / "installation.json").read_text()
    installation_data = json.loads(installation_payload)

    async def handler(request):
        if request.path.endswith("/var/opt/cet/config/installation.json"):
            return web.Response(
                text=installation_payload, content_type="application/json"
            )
        return web.Response(status=404)

    server = await aiohttp_raw_server(handler)
    host = f"{server.host}:{server.port}"
    hass = MagicMock()

    async with ClientSession() as session:
        with patch(
            "custom_components.combined_energy.bridge.async_get_clientsession",
            return_value=session,
        ):
            bootstrap = await bootstrap_from_entry_data(
                hass,
                {
                    "host": host,
                    "mqtt_password": "bridge-secret",
                },
            )

    assert bootstrap.bridge_host == host
    assert bootstrap.installation.gateway_id == installation_data["gwId"]
    assert bootstrap.mqtt_password == "bridge-secret"


@pytest.mark.asyncio
async def test_message_handler_routes_readings_topic(fixture_path):
    """Route topic-matched payloads to subscribers."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="127.0.0.1",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    client = MqttBridgeClient(hass, bootstrap)
    readings_payload = (fixture_path / "captured_readings.bin").read_bytes()
    received = []

    def listener(topic, payload):
        received.append((topic, payload))

    topic = client.topic("dmg/readings/stream")
    client.subscribe(client.topic("dmg/readings/#"), listener)
    await client._handle_message(topic, readings_payload)  # noqa: SLF001

    assert received == [(topic, readings_payload)]


@pytest.mark.asyncio
async def test_message_handler_ignores_non_readings_topic(fixture_path):
    """Ignore payloads from non-matching topics."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="127.0.0.1",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    client = MqttBridgeClient(hass, bootstrap)
    readings_payload = (fixture_path / "captured_readings.bin").read_bytes()
    received = []

    def listener(topic, payload):
        received.append((topic, payload))

    client.subscribe(client.topic("dmg/readings/#"), listener)
    await client._handle_message(  # noqa: SLF001
        client.topic("dmg/events/state"),
        readings_payload,
    )

    assert not received


@pytest.mark.asyncio
async def test_topic_helper_prefixes_installation_scope(fixture_path):
    """Build topic paths with prefix and installation gateway id."""
    installation = Installation.model_validate_json(
        (fixture_path / "installation.json").read_text()
    )
    bootstrap = BridgeBootstrap(
        bridge_host="127.0.0.1",
        mqtt_password="bridge-secret",
        installation=installation,
    )
    hass = MagicMock()
    hass.loop = asyncio.get_running_loop()
    client = MqttBridgeClient(hass, bootstrap)

    assert (
        client.topic("dmg/readings/#")
        == f"cet-ecn/{installation.gateway_id}/dmg/readings/#"
    )

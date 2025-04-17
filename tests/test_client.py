"""Test the client module."""

from datetime import UTC, datetime, timedelta

from aiohttp import web
from custom_components.combined_energy.client import Client, ClientAuthError
from freezegun import freeze_time
import pytest


class TestClient:
    """Test the Client class."""

    @pytest.fixture
    def mock_handler(self, fixture_path):
        """Mock handler for aiohttp server."""

        async def handler(request):
            if request.path == "/user/Login":
                return web.FileResponse(fixture_path / "login.json")
            if request.path == "/dataAccess/installation":
                return web.FileResponse(fixture_path / "installation.json")
            if request.path == "/mqtt2/user/LogSessionStart":
                return web.FileResponse(fixture_path / "log-session.json")
            if request.path == "/dataAccess/readings":
                return web.FileResponse(fixture_path / "readings.json")
            if request.path == "/dataAccess/tariff-details":
                return web.FileResponse(fixture_path / "tariff-details.json")
            return web.Response(status=404)

        return handler

    @pytest.fixture
    async def client(self, aiohttp_raw_server, mock_handler):
        server = await aiohttp_raw_server(mock_handler)
        url = f"{server.scheme}://{server.host}:{server.port}"
        client = Client(mobile_or_email="123456789", password="password")
        client.base_url_user_access = url
        client.base_url_data_access = url
        client.base_url_mqtt_access = url
        return client

    async def test_login__ok(self, client: Client):
        """Test the login method."""

        with freeze_time("2025-04-13 06:51:50"):
            assert not client.logged_in
            login = await client.login()
            assert login.status == "ok"
            assert login.jwt == "xxxx"
            assert login.expires == datetime.now(UTC) + timedelta(minutes=180)
            assert client.logged_in
        with freeze_time("2025-05-13 06:51:50"):
            assert not client.logged_in

    async def test_login__error(self, aiohttp_raw_server, fixture_path):
        """Test the login method with an error."""

        async def mock_handler(request):
            return web.FileResponse(fixture_path / "error.json")

        server = await aiohttp_raw_server(mock_handler)
        with freeze_time("2025-04-13 06:51:50"):
            client = Client(mobile_or_email="123456789", password="password")
            client.base_url_user_access = (
                f"{server.scheme}://{server.host}:{server.port}"
            )
            with pytest.raises(ClientAuthError):
                await client.login()

    async def test_installation__ok(self, client: Client):
        """Test the get_installation method."""

        installation = await client.installation()
        assert installation.status == "ACTIVE"
        assert installation.id == 1234

    async def test_start_log_session(self, client: Client):
        """Test the start_log_session method."""

        log_session = await client.start_log_session()
        assert log_session.status == "ok"
        assert log_session.installation_id == 1234

    async def test_readings(self, client: Client):
        """Test the readings method."""

        readings = await client.readings(
            datetime(2025, 4, 13, 6, 51, 50),
            datetime(2025, 4, 13, 6, 51, 50),
            increment=5,
        )
        assert readings.seconds == 5
        assert readings.range_start == datetime(2025, 4, 15, 20, 27, 50, tzinfo=UTC)
        assert readings.range_end == datetime(2025, 4, 15, 20, 27, 55, tzinfo=UTC)

    async def test_tariff_details(self, client: Client):
        """Test the tariff details method."""

        tariff_details = await client.tariff_details()
        assert tariff_details.status == "ok"
        assert tariff_details.plan_id == 12345

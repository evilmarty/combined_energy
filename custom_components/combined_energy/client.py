"""Combined Energy Client."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any

from aiohttp import ClientResponseError, ClientSession
from aiohttp.hdrs import METH_GET, METH_POST
import backoff

from custom_components.combined_energy.const import (
    BASE_URL_DATA_ACCESS,
    BASE_URL_MQTT_ACCESS,
    BASE_URL_USER_ACCESS,
    DOMAIN,
    LOGGER,
)
from custom_components.combined_energy.models import (
    Installation,
    Login,
    LogSession,
    Readings,
    TariffDetails,
)
from homeassistant import loader
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


def async_cache(func):
    """Cache decorator for async functions."""

    @cache
    def wrapper(*args, **kwargs):
        coroutine = func(*args, **kwargs)
        return asyncio.ensure_future(coroutine)

    return wrapper


class ClientAuthError(Exception):
    """Exception for authentication errors."""


@dataclass
class Client:
    """Client for API."""

    mobile_or_email: str
    password: str
    version: str = "0.0.0"

    session: ClientSession | None = None
    auto_close: bool = True
    _login: Login | None = None

    base_url_user_access: str = BASE_URL_USER_ACCESS
    base_url_data_access: str = BASE_URL_DATA_ACCESS
    base_url_mqtt_access: str = BASE_URL_MQTT_ACCESS

    def __hash__(self) -> int:
        """Return the hash of the object."""
        return hash(self.mobile_or_email)

    async def __aenter__(self) -> "Client":
        """Enter the runtime context related to this object."""
        self.auto_close = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context related to this object."""
        self.auto_close = True
        await self.close()

    @backoff.on_exception(
        backoff.expo,
        ClientResponseError,
        giveup=lambda e: e.status != 503,
        logger=LOGGER,
        max_tries=5,
        factor=2,
        base=1,
    )
    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Make a request to the API."""
        if params is not None:
            params = {k: v for k, v in params.items() if v is not None}
        if self.session is None:
            self.session = ClientSession(
                headers={
                    "Accept": "application/json",
                    "User-Agent": f"CombinedEnergyClient/{self.version}",
                }
            )
        try:
            LOGGER.debug(
                "Making %s request to %s with params %s",
                method,
                url,
                params,
            )
            # Post requests must send as data and not as json
            async with self.session.request(
                method, url, data=data, params=params
            ) as response:
                response.raise_for_status()
                return await response.json()
        finally:
            if self.auto_close:
                await self.close()

    async def _make_request_with_reauth(self, *args, **kwargs) -> dict[str, Any]:
        """Make a request to the API with re-authentication."""
        try:
            return await self._make_request(*args, **kwargs)
        except ClientResponseError as err:
            if err.status == 401:
                self._login = None
                await self.login()
                return await self._make_request(*args, **kwargs)
            raise

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None

    @property
    def logged_in(self) -> bool:
        """Check if the client is logged in."""
        return not getattr(self._login, "expired", True)

    async def login(self) -> Login:
        """Login to the API and caches the result, re-authing only if expired."""
        if self.logged_in:
            return self._login
        data = await self._make_request(
            f"{self.base_url_user_access}/user/Login",
            method=METH_POST,
            data={
                "mobileOrEmail": self.mobile_or_email,
                "pass": self.password,
                "store": False,
            },
        )
        if not data or data.get("status") != "ok":
            raise ClientAuthError(data.get("error", "Login failed"))
        self._login = Login.model_validate(data)
        return self._login

    @async_cache
    async def installation(self) -> Installation:
        """Get installation for account."""
        login = await self.login()
        data = await self._make_request_with_reauth(
            f"{self.base_url_data_access}/dataAccess/installation",
            method=METH_GET,
            params={"jwt": login.jwt},
        )
        return Installation.model_validate(data)

    async def start_log_session(self, retry_auth=True) -> LogSession:
        """Start a log session."""
        try:
            return await self._start_log_session()
        except ClientAuthError:
            if retry_auth:
                self._login = None
                return await self.start_log_session(retry_auth=False)
            raise

    async def _start_log_session(self) -> LogSession:
        """Start a log session."""
        login = await self.login()
        installation = await self.installation()
        data = await self._make_request_with_reauth(
            f"{self.base_url_mqtt_access}/mqtt2/user/LogSessionStart",
            method=METH_POST,
            data={
                "i": installation.id,
                "jwt": login.jwt,
            },
        )
        if not data or data.get("status") != "ok":
            raise ClientAuthError(data.get("error", "Log session failed"))
        return LogSession.model_validate(data)

    async def readings(
        self,
        range_start: datetime | None = None,
        range_end: datetime | None = None,
        increment: 5 | 300 | 1800 = 5,
    ) -> Readings:
        """Get readings for the installation."""
        installation = await self.installation()
        login = await self.login()
        if range_end is None:
            range_end = (
                range_start + timedelta(seconds=increment)
                if range_start is not None
                else datetime.now(UTC)
            )
        if range_start is None:
            range_start = range_end - timedelta(seconds=increment)
        data = await self._make_request_with_reauth(
            f"{self.base_url_data_access}/dataAccess/readings",
            params={
                "jwt": login.jwt,
                "i": installation.id,
                "seconds": increment,
                "rangeStart": int(range_start.timestamp()),
                "rangeEnd": int(range_end.timestamp()),
            },
        )
        return Readings.model_validate(data)

    async def tariff_details(self) -> TariffDetails:
        """Get tariff details for the installation."""
        installation = await self.installation()
        login = await self.login()
        params = {
            "jwt": login.jwt,
            "i": installation.id,
            "planId": installation.tariff_plan_id,
            "postcode": installation.postcode,
        }
        data = await self._make_request_with_reauth(
            f"{self.base_url_data_access}/dataAccess/tariff-details",
            params=params,
        )
        return TariffDetails.model_validate(data)


async def get_client(
    hass: HomeAssistant, mobile_or_email: str, password: str
) -> Client:
    """Get a client for the API."""
    integration = await loader.async_get_integration(hass, DOMAIN)
    return Client(
        mobile_or_email=mobile_or_email,
        password=password,
        version=integration.version,
        session=async_get_clientsession(hass),
        auto_close=False,
    )

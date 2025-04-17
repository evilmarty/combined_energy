"""Combined Energy Client."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any

from aiohttp import ClientSession
from aiohttp.hdrs import METH_GET, METH_POST
from custom_components.combined_energy.const import (
    BASE_URL_DATA_ACCESS,
    BASE_URL_MQTT_ACCESS,
    BASE_URL_USER_ACCESS,
)
from custom_components.combined_energy.models import (
    Installation,
    LogSession,
    Login,
    Readings,
    TariffDetails,
)


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
    _login: Login | None = None
    _auto_close: bool = True

    base_url_user_access: str = BASE_URL_USER_ACCESS
    base_url_data_access: str = BASE_URL_DATA_ACCESS
    base_url_mqtt_access: str = BASE_URL_MQTT_ACCESS

    def __hash__(self) -> int:
        """Return the hash of the object."""
        return hash(self.mobile_or_email)

    async def __aenter__(self) -> "Client":
        """Enter the runtime context related to this object."""
        self._auto_close = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the runtime context related to this object."""
        self._auto_close = True
        await self.close()

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
            async with self.session.request(
                method, url, json=data, params=params
            ) as response:
                response.raise_for_status()
                return await response.json()
        finally:
            if self._auto_close:
                await self.close()

    async def close(self) -> None:
        """Close the session."""
        if self.session:
            await self.session.close()
            self.session = None

    @property
    def logged_in(self) -> bool:
        """Check if the client is logged in."""
        return self._login is not None and not self._login.expired

    async def login(self) -> Login:
        """Login to the API and caches the result, re-authing only if expired."""
        login = await self._perform_login()
        if login.expired:
            self._login.cache_clear()
            login = await self._perform_login()
        return login

    @async_cache
    async def _perform_login(self) -> Login:
        """Perform the actual login."""
        data = await self._make_request(
            f"{self.base_url_user_access}/user/Login",
            method=METH_POST,
            data={
                "mobileOrEmail": self.mobile_or_email,
                "password": self.password,
            },
        )
        if data.get("status") != "ok":
            raise ClientAuthError(data.get("error", "Login failed"))
        self._login = Login.parse_obj(data)
        return self._login

    @async_cache
    async def installation(self) -> Installation:
        """Get installation for account."""
        login = await self.login()
        data = await self._make_request(
            f"{self.base_url_user_access}/dataAccess/installation",
            method=METH_GET,
            params={"jwt": login.jwt},
        )
        return Installation.parse_obj(data)

    async def start_log_session(self) -> LogSession:
        """Start a log session."""
        login = await self.login()
        installation = await self.installation()
        data = await self._make_request(
            f"{self.base_url_mqtt_access}/mqtt2/user/LogSessionStart",
            method=METH_POST,
            data={
                "i": installation.id,
                "jwt": login.jwt,
            },
        )
        return LogSession.parse_obj(data)

    async def readings(
        self,
        range_start: datetime | None,
        range_end: datetime | None,
        increment: int,
    ) -> Readings:
        """Get readings for the installation."""
        installation = await self.installation()
        login = await self.login()
        params = {"jwt": login.jwt, "i": installation.id, "seconds": increment}
        if range_start is not None:
            params["rangeStart"] = int(range_start.timestamp())
        if range_end is not None:
            params["rangeEnd"] = int(range_end.timestamp())
        data = await self._make_request(
            f"{self.base_url_data_access}/dataAccess/readings",
            params=params,
        )
        return Readings.parse_obj(data)

    async def tariff_details(self) -> TariffDetails:
        """Get tariff details for the installation."""
        installation = await self.installation()
        login = await self.login()
        params = {"jwt": login.jwt, "i": installation.id}
        data = await self._make_request(
            f"{self.base_url_data_access}/dataAccess/tariff-details",
            params=params,
        )
        return TariffDetails.parse_obj(data)

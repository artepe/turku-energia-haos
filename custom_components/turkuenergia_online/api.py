"""Unofficial EnergiaOnline client. Never log full URLs, headers or responses."""
from __future__ import annotations

import asyncio

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_BASE, CONF_API_KEY, CONF_CUSTOMER_CODE, CONF_METERING_POINT,
    CONF_RELATED_POINT, CONF_WEATHER_LOCATION, CONSUMPTION_PATH,
)


class EnergiaOnlineError(Exception):
    """Redacted, safe error."""


class EnergiaOnlineAuthError(EnergiaOnlineError):
    """Access denied."""


class EnergiaOnlineClient:
    def __init__(self, session: ClientSession, settings: dict) -> None:
        self._session = session
        self._settings = settings

    async def fetch(self, start: str, end: str, resolution: str) -> dict:
        body = {
            "range": {"from": start, "to": end},
            "customerCodes": [self._settings[CONF_CUSTOMER_CODE]],
            "meteringPointCode": self._settings[CONF_METERING_POINT],
            "relatedMeteringPointCode": self._settings.get(CONF_RELATED_POINT, ""),
            "consumptionAndProductionResolution": resolution,
            "exchangeElectricityPriceUnit": "CentPerKWH",
            "includeVat": True,
            "language": "fi",
            "weatherLocation": self._settings.get(CONF_WEATHER_LOCATION, ""),
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json; x-api-version=1",
            "Ocp-Apim-Subscription-Key": self._settings[CONF_API_KEY],
            "Origin": "https://energiaonline.fi",
        }
        try:
            async with asyncio.timeout(35):
                async with self._session.post(
                    API_BASE + CONSUMPTION_PATH, json=body, headers=headers,
                    timeout=ClientTimeout(total=30),
                ) as resp:
                    if resp.status in (401, 403):
                        raise EnergiaOnlineAuthError("Service denied access")
                    if resp.status >= 400:
                        raise EnergiaOnlineError("Service rejected request")
                    try:
                        data = await resp.json(content_type=None)
                    except (ValueError, ClientError):
                        raise EnergiaOnlineError("Invalid JSON response") from None
                    if not isinstance(data, dict):
                        raise EnergiaOnlineError("Unexpected response format")
                    return data
        except (TimeoutError, ClientError):
            raise EnergiaOnlineError("Could not reach EnergiaOnline") from None

"""Local-only HA configuration flow; do not expose user secrets in logs."""
from __future__ import annotations

from datetime import date, timedelta
import hashlib

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnergiaOnlineAuthError, EnergiaOnlineClient, EnergiaOnlineError
from .const import (
    DOMAIN, CONF_API_KEY, CONF_CUSTOMER_CODE, CONF_METERING_POINT,
    CONF_RELATED_POINT, CONF_RESOLUTION, CONF_WEATHER_LOCATION,
    RESOLUTION_QUARTER, RESOLUTION_DAILY,
)


def form_schema(values: dict | None = None) -> vol.Schema:
    values = values or {}
    return vol.Schema({
        vol.Required(CONF_CUSTOMER_CODE, default=values.get(CONF_CUSTOMER_CODE, "")): str,
        vol.Required(CONF_METERING_POINT, default=values.get(CONF_METERING_POINT, "")): str,
        vol.Required(CONF_API_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_RELATED_POINT, default=values.get(CONF_RELATED_POINT, "")): str,
        vol.Optional(CONF_WEATHER_LOCATION, default=values.get(CONF_WEATHER_LOCATION, "")): str,
        vol.Required(CONF_RESOLUTION, default=values.get(CONF_RESOLUTION, RESOLUTION_QUARTER)):
            vol.In([RESOLUTION_QUARTER, RESOLUTION_DAILY]),
    })


class TurkuEnergiaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None):
        errors = {}
        if user_input is not None:
            fingerprint = hashlib.sha256(user_input[CONF_METERING_POINT].encode()).hexdigest()[:20]
            await self.async_set_unique_id(fingerprint)
            self._abort_if_unique_id_configured()
            try:
                api = EnergiaOnlineClient(async_get_clientsession(self.hass), user_input)
                today = date.today()
                # Validate with the only verified resolution, not experimental PT15M.
                await api.fetch((today - timedelta(days=5)).isoformat(), today.isoformat(), RESOLUTION_DAILY)
            except EnergiaOnlineAuthError:
                errors["base"] = "invalid_auth"
            except EnergiaOnlineError:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title="Turku EnergiaOnline", data=user_input)
        return self.async_show_form(step_id="user", data_schema=form_schema(user_input), errors=errors)

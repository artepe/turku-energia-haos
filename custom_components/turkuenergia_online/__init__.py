"""Unofficial Home Assistant importer for EnergiaOnline consumption."""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import logging
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.models import (
    StatisticData, StatisticMeanType, StatisticMetaData,
)
from homeassistant.components.recorder.statistics import (
    async_add_external_statistics, get_last_statistics,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import EnergiaOnlineAuthError, EnergiaOnlineClient, EnergiaOnlineError
from .const import (
    DOMAIN, CONF_METERING_POINT, CONF_RESOLUTION,
    RESOLUTION_DAILY, RESOLUTION_QUARTER, UPDATE_SECONDS,
)
from .model import (
    aggregate_complete_days, aggregate_complete_hours,
    latest_local_totals, parse_consumption,
)

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


class EnergiaOnlineCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry):
        super().__init__(
            hass, _LOGGER, name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_SECONDS),
        )
        self.entry = entry
        self.api = EnergiaOnlineClient(async_get_clientsession(hass), entry.data)
        self._store = Store(hass, 1, f"{DOMAIN}_{entry.entry_id}_import")
        self._seen: dict[str, float] = {}
        self._loaded = False
        point = entry.data[CONF_METERING_POINT]
        self._stat_id = f"{DOMAIN}:{hashlib.sha256(point.encode()).hexdigest()[:20]}_consumption"
        self._resolution = entry.data[CONF_RESOLUTION]

    async def _async_update_data(self):
        if not self._loaded:
            saved = await self._store.async_load() or {}
            self._seen = {k: float(v) for k, v in saved.get("readings", {}).items()}
            self._loaded = True

        today = dt_util.now().astimezone(ZoneInfo("Europe/Helsinki")).date()
        first_month_day = today.replace(day=1)
        start = min(today - timedelta(days=7), first_month_day).isoformat()
        end = today.isoformat()
        try:
            result = await self.api.fetch(start, end, self._resolution)
            new_values = parse_consumption(result)
        except EnergiaOnlineAuthError:
            raise ConfigEntryAuthFailed("EnergiaOnline refused access") from None
        except (EnergiaOnlineError, ValueError):
            raise UpdateFailed("EnergiaOnline fetch failed; check resolution or connection") from None

        for stamp, value in new_values.items():
            self._seen[stamp.isoformat()] = value
        await self._store.async_save({"readings": self._seen})
        intervals = {datetime.fromisoformat(key): value for key, value in self._seen.items()}
        await self._async_import_statistics(intervals)
        summary = latest_local_totals(intervals, dt_util.now())
        summary["resolution"] = self._resolution
        summary["data_points"] = len(new_values)
        summary["statistic_id"] = self._stat_id
        return summary

    async def _async_import_statistics(self, intervals: dict[datetime, float]):
        if self._resolution == RESOLUTION_QUARTER:
            points = aggregate_complete_hours(intervals)
        elif self._resolution == RESOLUTION_DAILY:
            points = aggregate_complete_days(intervals, dt_util.now())
        else:
            return
        # Beta: append only. Revisions to previously imported periods are not updated.
        last = await get_instance(self.hass).async_add_executor_job(
            get_last_statistics, self.hass, 1, self._stat_id, True, set()
        )
        records = last.get(self._stat_id) or []
        last_start = dt_util.utc_from_timestamp(records[0]["start"]) if records else None
        running = float(records[0].get("sum") or 0) if records else 0.0
        updates = []
        finished_before = dt_util.utcnow().replace(minute=0, second=0, microsecond=0)
        for stamp, value in points:
            if stamp >= finished_before or (last_start is not None and stamp <= last_start):
                continue
            running = round(running + value, 6)
            updates.append(StatisticData(start=stamp, state=running, sum=running))
        if not updates:
            return
        metadata = StatisticMetaData(
            mean_type=StatisticMeanType.NONE,
            has_sum=True,
            name="Turku EnergiaOnline electricity consumption",
            source=DOMAIN,
            statistic_id=self._stat_id,
            unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            unit_class="energy",
        )
        async_add_external_statistics(self.hass, metadata, updates)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = EnergiaOnlineCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    success = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if success:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return success

"""Pure helpers for parsing provider energy samples. Uses no personal data."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from math import isfinite
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Helsinki")


def parse_consumption(payload: dict) -> dict[datetime, float]:
    """Extract UTC measurement-start time to kWh; ignore missing values."""
    main = payload.get("mainData") or {}
    stamps = main.get("timeSteps") or []
    series = [
        item for item in main.get("consumptionAndProductionDataList", [])
        if item.get("chartDataType") == "ConsumptionMeasured"
        and str(item.get("unit", "")).lower() == "kwh"
    ]
    if not series:
        raise ValueError("Measured kWh consumption series missing")
    values: dict[datetime, float] = {}
    # Do not double count alternative data series.
    for stamp, datum in zip(stamps, series[0].get("dataValues") or []):
        value = datum[0] if isinstance(datum, list) and datum else datum
        if isinstance(value, bool) or not isinstance(value, (float, int)):
            continue
        if not isfinite(value) or value < 0:
            continue
        dt = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("Naive timestamp")
        values[dt.astimezone(timezone.utc)] = float(value)
    return values


def aggregate_complete_hours(intervals: dict[datetime, float]) -> list[tuple[datetime, float]]:
    """Do not produce a fake hourly value unless all four quarter-hours exist."""
    groups = defaultdict(dict)
    for stamp, value in intervals.items():
        utc = stamp.astimezone(timezone.utc)
        hour = utc.replace(minute=0, second=0, microsecond=0)
        if utc.second or utc.microsecond or utc.minute not in (0, 15, 30, 45):
            continue
        groups[hour][utc.minute] = value
    return sorted((hour, round(sum(items.values()), 6)) for hour, items in groups.items()
                  if set(items) == {0, 15, 30, 45})


def aggregate_complete_days(intervals: dict[datetime, float], now: datetime) -> list[tuple[datetime, float]]:
    """Daily fallback places each finished-day total in last local hour; NOT hourly metering."""
    today = now.astimezone(TZ).date()
    result = []
    for stamp, value in intervals.items():
        local_day = stamp.astimezone(TZ).date()
        if local_day >= today:
            continue
        next_midnight = datetime.combine(local_day + timedelta(days=1), datetime.min.time(), tzinfo=TZ)
        result.append((next_midnight.astimezone(timezone.utc) - timedelta(hours=1), value))
    return sorted(result)


def latest_local_totals(intervals: dict[datetime, float], now: datetime) -> dict:
    if not intervals:
        return {"latest": None, "today": None, "month": None, "latest_time": None}
    today = now.astimezone(TZ).date()
    latest = max(intervals)
    day = [v for stamp, v in intervals.items() if stamp.astimezone(TZ).date() == today]
    month = [v for stamp, v in intervals.items()
             if (stamp.astimezone(TZ).year, stamp.astimezone(TZ).month) == (today.year, today.month)]
    return {
        "latest": intervals[latest],
        "latest_time": latest,
        "today": round(sum(day), 3) if day else None,
        "month": round(sum(month), 3) if month else None,
    }

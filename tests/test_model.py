"""Synthetic test measurements only; no users, credentials or HAR content."""
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path

file = Path(__file__).parents[1] / "custom_components" / "turkuenergia_online" / "model.py"
spec = importlib.util.spec_from_file_location("energy_model", file)
model = importlib.util.module_from_spec(spec)
spec.loader.exec_module(model)


def test_parsing_and_null_handling():
    example = {"mainData": {
        "timeSteps": [
            "2026-09-15T00:00:00+03:00",
            "2026-09-15T00:15:00+03:00",
            "2026-09-15T00:30:00+03:00",
            "2026-09-15T00:45:00+03:00",
        ],
        "consumptionAndProductionDataList": [
            {"chartDataType": "ConsumptionMeasured", "unit": "kWh",
             "dataValues": [[0.5, 1], [1.0, 1], None, [2.0, 1]]},
            {"chartDataType": "ConsumptionInvoiced", "unit": "kWh",
             "dataValues": [[99, 1]] * 4},
        ],
    }}
    readings = model.parse_consumption(example)
    assert list(readings.values()) == [0.5, 1.0, 2.0]
    assert model.aggregate_complete_hours(readings) == []


def test_complete_hours_over_dst_overlap():
    first = datetime(2026, 10, 25, tzinfo=timezone.utc)
    readings = {first + timedelta(minutes=15 * i): 0.25 for i in range(8)}
    assert model.aggregate_complete_hours(readings) == [
        (first, 1.0), (first + timedelta(hours=1), 1.0),
    ]


def test_daily_fallback_excludes_today():
    readings = {
        datetime(2026, 9, 15, tzinfo=timezone(timedelta(hours=3))): 8.0,
        datetime(2026, 9, 16, tzinfo=timezone(timedelta(hours=3))): 3.0,
    }
    assert len(model.aggregate_complete_days(
        readings, datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
    )) == 1


def test_missing_readings_do_not_become_zero():
    empty = model.latest_local_totals({}, datetime.now(timezone.utc))
    assert empty["today"] is None

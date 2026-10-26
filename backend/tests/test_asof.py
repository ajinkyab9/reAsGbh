from pathlib import Path

import pandas as pd
import pytest

from core.asof import (
    CUTOFF_PRESETS,
    asof_forecast,
    asof_forecast_range,
    cutoff_utc,
    delivery_hours,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DAY = "2026-01-15"  # delivery day used by the synthetic tests


def utc(ts: str) -> pd.Timestamp:
    return pd.Timestamp(ts, tz="UTC")


def make_wf(runs: dict[str, tuple[pd.DatetimeIndex, int]]) -> pd.DataFrame:
    """Build a tiny WINDFOR-shaped frame: {publish_time: (hours_covered, value)}."""
    rows = [
        {"publishTime": utc(publish), "startTime": hour, "generation": value}
        for publish, (hours, value) in runs.items()
        for hour in hours
    ]
    df = pd.DataFrame(rows)
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    return df


@pytest.fixture(scope="session")
def real_wf() -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / "windfor.parquet")


def test_cutoff_is_day_before_in_uk_time():
    assert cutoff_utc(DAY, "09:20") == utc("2026-01-14 09:20")


def test_cutoff_converts_british_summer_time():
    # January can't catch a timezone bug (GMT == UTC), so check a summer date.
    assert cutoff_utc("2026-07-15", "09:20") == utc("2026-07-14 08:20")


@pytest.mark.parametrize(
    "day, n_hours",
    [("2026-01-15", 24), ("2026-03-29", 23), ("2026-10-25", 25)],
    ids=["normal", "clocks-forward", "clocks-back"],
)
def test_delivery_hours_follow_uk_calendar_day(day, n_hours):
    assert len(delivery_hours(day)) == n_hours


def test_picks_latest_run_before_cutoff():
    hours = delivery_hours(DAY)
    wf = make_wf({"2026-01-14 07:30": (hours, 100), "2026-01-14 09:30": (hours, 999)})
    result = asof_forecast(wf, DAY, "09:20")
    assert (result["forecast_mw"] == 100).all()


def test_run_published_exactly_at_cutoff_is_excluded():
    hours = delivery_hours(DAY)
    wf = make_wf({"2026-01-14 04:30": (hours, 100), "2026-01-14 09:20": (hours, 999)})
    result = asof_forecast(wf, DAY, "09:20")
    assert (result["forecast_mw"] == 100).all()


def test_falls_back_to_earlier_run_for_uncovered_hours():
    hours = delivery_hours(DAY)
    wf = make_wf(
        {"2026-01-14 04:30": (hours, 100), "2026-01-14 07:30": (hours[:-2], 200)}
    )
    result = asof_forecast(wf, DAY, "09:20")
    assert (result["forecast_mw"].iloc[:-2] == 200).all()
    assert (result["forecast_mw"].iloc[-2:] == 100).all()


def test_hours_with_no_forecast_are_nan_not_dropped():
    hours = delivery_hours(DAY)
    wf = make_wf({"2026-01-14 07:30": (hours[:20], 100)})
    result = asof_forecast(wf, DAY, "09:20")
    assert len(result) == 24
    assert result["forecast_mw"].isna().sum() == 4


@pytest.mark.parametrize(
    "cutoff_time", CUTOFF_PRESETS.values(), ids=CUTOFF_PRESETS.keys()
)
def test_no_lookahead_and_full_coverage_on_real_data(real_wf, cutoff_time):
    days = pd.date_range("2026-01-01", "2026-02-01", freq="D")
    result = asof_forecast_range(real_wf, days, cutoff_time)
    cutoffs = result["deliveryDate"].map(lambda d: cutoff_utc(d, cutoff_time))

    assert len(result) == len(days) * 24
    assert result["forecast_mw"].notna().all()
    assert (result["publishTime"] < cutoffs).all(), "forecast published after cutoff"


@pytest.mark.parametrize(
    "day, cutoff_time, expected_run",
    [
        ("2026-01-15", "09:20", "2026-01-14 07:30"),  # 09:30 run misses EPEX by 10 min
        ("2026-01-15", "09:50", "2026-01-14 09:30"),
        ("2026-01-16", "15:30", "2026-01-15 12:25"),  # the one irregular run
    ],
)
def test_uses_expected_run_on_real_data(real_wf, day, cutoff_time, expected_run):
    result = asof_forecast(real_wf, day, cutoff_time)
    assert set(result["publishTime"]) == {utc(expected_run)}

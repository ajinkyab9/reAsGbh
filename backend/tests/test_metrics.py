"""Tests for core.metrics: error convention, summary numbers, no-look-ahead buffer."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from core.metrics import (
    buffer_backtest,
    buffer_backtest_summary,
    error_by_horizon,
    forecast_vs_actual,
    hourly_actuals,
    metrics_by_hour,
    summary_metrics,
)

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
JAN_2_TO_31 = pd.date_range("2026-01-02", "2026-01-31", freq="D")


def make_errors(errors_by_day: dict[str, list[float]]) -> pd.DataFrame:
    """Hand-made forecast_vs_actual-shaped frame with a constant actual of 1000 MW."""
    rows = []
    for day, errors in errors_by_day.items():
        for i, err in enumerate(errors):
            rows.append(
                {
                    "deliveryDate": pd.Timestamp(day).date(),
                    "startTime": pd.Timestamp(day, tz="UTC") + pd.Timedelta(hours=i),
                    "forecast_mw": 1000.0 + err,
                    "actual_mw": 1000.0,
                    "error_mw": float(err),
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture(scope="session")
def real_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    wf = pd.read_parquet(DATA_DIR / "windfor.parquet")
    fh = pd.read_parquet(DATA_DIR / "fuelhh_wind.parquet")
    return wf, fh


def test_hourly_actuals_average_both_half_hours_and_drop_incomplete_hours():
    fh = pd.DataFrame(
        {
            "startTime": pd.to_datetime(
                ["2026-01-15 10:00", "2026-01-15 10:30", "2026-01-15 11:00"], utc=True
            ),
            "generation": [100, 200, 999],
        }
    )
    out = hourly_actuals(fh)
    assert list(out["actual_mw"]) == [150.0]  # 11:00 has only one half hour


def test_summary_metrics_known_values_and_sign_convention():
    df = make_errors({"2026-01-15": [100, -100, 300]})
    m = summary_metrics(df)
    assert m["bias_mw"] == pytest.approx(100)  # positive = over forecast
    assert m["mae_mw"] == pytest.approx(500 / 3)
    assert m["rmse_mw"] == pytest.approx(np.sqrt(110_000 / 3))
    assert m["pct_hours_over_forecast"] == pytest.approx(200 / 3)


def test_buffer_uses_only_days_before_the_delivery_day():
    errors = {
        "2026-01-01": [100, 200],
        "2026-01-02": [300, 400],
        "2026-01-03": [0, 0],
        "2026-01-04": [0, 0],
    }
    bt = buffer_backtest(make_errors(errors), quantile=0.5, min_history_days=2)
    day3 = bt.set_index("deliveryDate").loc[pd.Timestamp("2026-01-03").date()]
    assert day3["buffer_mw"] == pytest.approx(250)  # median of days 1-2 only

    # Making day 3 and later wildly different must not change day 3's buffer.
    errors["2026-01-03"] = errors["2026-01-04"] = [99_999, 99_999]
    bt_changed = buffer_backtest(make_errors(errors), quantile=0.5, min_history_days=2)
    day3_changed = bt_changed.set_index("deliveryDate").loc[
        pd.Timestamp("2026-01-03").date()
    ]
    assert day3_changed["buffer_mw"] == pytest.approx(250)


def test_buffer_is_empty_until_enough_history():
    bt = buffer_backtest(
        make_errors({f"2026-01-0{d}": [100] for d in range(1, 6)}), min_history_days=3
    )
    assert bt["buffer_mw"].isna().tolist() == [True, True, True, False, False]


def test_headline_numbers_on_real_data(real_data):
    wf, fh = real_data
    m = summary_metrics(forecast_vs_actual(wf, fh, JAN_2_TO_31, "09:20"))
    assert m["n_hours"] == 720
    assert m["bias_mw"] == pytest.approx(1773, abs=1)
    assert m["mae_mw"] == pytest.approx(2073, abs=1)


def test_bias_correction_beats_raw_forecast_out_of_sample(real_data):
    wf, fh = real_data
    bt = buffer_backtest(forecast_vs_actual(wf, fh, JAN_2_TO_31, "09:20"))
    s = buffer_backtest_summary(bt)
    assert s["mae_bias_corrected_mw"] < s["mae_raw_mw"]


def test_breakdowns_have_expected_shape(real_data):
    wf, fh = real_data
    df = forecast_vs_actual(wf, fh, JAN_2_TO_31, "09:20")
    assert list(metrics_by_hour(df)["hour_uk"]) == list(range(24))
    assert list(error_by_horizon(wf, fh)["horizon_start_h"]) == list(range(0, 48, 6))

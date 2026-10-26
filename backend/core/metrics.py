"""the forecast available at the cutoff vs actual wind output."""

import numpy as np
import pandas as pd

from core.asof import DEFAULT_CUTOFF, UK_TZ, asof_forecast_range

SCOPES = {
    # actual reading of the brief: purchase decisions made in January.
    "decisions-in-january": pd.date_range("2026-01-02", "2026-02-01", freq="D"),
    # alternative reading: power delivered in January.
    "delivery-in-january": pd.date_range("2026-01-01", "2026-01-31", freq="D"),
}
DEFAULT_SCOPE = "decisions-in-january"


def hourly_actuals(fh: pd.DataFrame) -> pd.DataFrame:
    """averaging the two half hourly actual data into hourly values to match WINDFOR as WINDFOR is hourly and FUELHH is every 30 mins.

    Hours missing either half hour are dropped rather than half filled.
    """
    grouped = fh.groupby(fh["startTime"].dt.floor("h"))["generation"]
    hourly = grouped.agg(["mean", "count"])
    hourly = hourly[hourly["count"] == 2]
    return hourly["mean"].rename("actual_mw").rename_axis("startTime").reset_index()


def forecast_vs_actual(
    wf: pd.DataFrame,
    fh: pd.DataFrame,
    delivery_days: pd.DatetimeIndex = SCOPES[DEFAULT_SCOPE],
    cutoff_time: str = DEFAULT_CUTOFF,
) -> pd.DataFrame:
    """One row per delivery hour: the as of forecast, the actual data and  error."""
    forecast = asof_forecast_range(wf, delivery_days, cutoff_time)
    df = forecast.merge(hourly_actuals(fh), on="startTime", how="left")
    df["error_mw"] = df["forecast_mw"] - df["actual_mw"]
    return df[
        [
            "deliveryDate",
            "startTime",
            "forecast_mw",
            "actual_mw",
            "error_mw",
            "publishTime",
            "horizon_h",
        ]
    ]


def summary_metrics(df: pd.DataFrame) -> dict[str, float]:
    """Headline accuracy numbers over all hours that have both a forecast and an actual."""
    d = df.dropna(subset=["forecast_mw", "actual_mw"])
    err = d["error_mw"]
    abs_err = err.abs()
    mean_actual = d["actual_mw"].mean()
    return {
        "n_hours": len(d),
        "mean_actual_mw": float(mean_actual),
        "mean_forecast_mw": float(d["forecast_mw"].mean()),
        "bias_mw": float(err.mean()),
        "mae_mw": float(abs_err.mean()),
        "rmse_mw": float(np.sqrt((err**2).mean())),
        "nmae_pct": float(abs_err.mean() / mean_actual * 100),
        "pct_hours_over_forecast": float((err > 0).mean() * 100),
        "abs_error_p50_mw": float(abs_err.quantile(0.50)),
        "abs_error_p90_mw": float(abs_err.quantile(0.90)),
        "over_forecast_p90_mw": float(err.quantile(0.90)),
        "over_forecast_p95_mw": float(err.quantile(0.95)),
    }


def _group_metrics(d: pd.DataFrame, key) -> pd.DataFrame:
    g = d.groupby(key)["error_mw"]
    return pd.DataFrame(
        {
            "n_hours": g.size(),
            "bias_mw": g.mean(),
            "mae_mw": g.apply(lambda e: e.abs().mean()),
            "rmse_mw": g.apply(lambda e: np.sqrt((e**2).mean())),
        }
    )


def metrics_by_day(df: pd.DataFrame) -> pd.DataFrame:
    """accuracy per delivery day"""
    d = df.dropna(subset=["forecast_mw", "actual_mw"])
    out = _group_metrics(d, "deliveryDate")
    means = d.groupby("deliveryDate")[["forecast_mw", "actual_mw"]].mean()
    return out.join(means).reset_index()


def metrics_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    """accuracy by UK day time"""
    d = df.dropna(subset=["forecast_mw", "actual_mw"])
    hour_uk = d["startTime"].dt.tz_convert(UK_TZ).dt.hour.rename("hour_uk")
    return _group_metrics(d, hour_uk).reset_index()


def buffer_backtest(
    df: pd.DataFrame,
    quantile: float = 0.90,
    lookback_days: int | None = None,
    min_history_days: int = 3,
) -> pd.DataFrame:
    """Shortfall buffer per delivery day, computed only from earlier days' errors.
    Using only past days means the buffer is exactly what a trader could have computed at the time: no look-ahead.
    """
    d = df.dropna(subset=["forecast_mw", "actual_mw"])
    days = sorted(d["deliveryDate"].unique())
    rows = []
    for i, day in enumerate(days):
        start = 0 if lookback_days is None else max(0, i - lookback_days)
        prior_days = days[start:i]
        today = d[d["deliveryDate"] == day]
        row = {"deliveryDate": day, "n_prior_days": len(prior_days)}
        if len(prior_days) >= min_history_days:
            prior = d[d["deliveryDate"].isin(prior_days)]["error_mw"]
            buffer = float(prior.quantile(quantile))
            prior_bias = float(prior.mean())
            row |= {
                "buffer_mw": buffer,
                "prior_bias_mw": prior_bias,
                "coverage_pct": float((today["error_mw"] <= buffer).mean() * 100),
                "mae_raw_mw": float(today["error_mw"].abs().mean()),
                "mae_bias_corrected_mw": float(
                    (today["error_mw"] - prior_bias).abs().mean()
                ),
            }
        rows.append(row)
    return pd.DataFrame(rows)


def buffer_backtest_summary(bt: pd.DataFrame) -> dict[str, float]:
    """month level view of the backtest"""
    b = bt.dropna(subset=["buffer_mw"])
    return {
        "n_days": len(b),
        "mean_buffer_mw": float(b["buffer_mw"].mean()),
        "coverage_pct": float(b["coverage_pct"].mean()),
        "mae_raw_mw": float(b["mae_raw_mw"].mean()),
        "mae_bias_corrected_mw": float(b["mae_bias_corrected_mw"].mean()),
    }


def error_by_horizon(
    wf: pd.DataFrame, fh: pd.DataFrame, bin_hours: int = 6, max_horizon_h: int = 48
) -> pd.DataFrame:
    """accuracy by lead time and not just by cutoff.

    it shows how much better is a forecast made to a delivery day. its right now capped at 48 h as longer lead
    times exist only for lat jan runs where target hours fall after actual, therefore bins have less unrepresentative samples.
    """
    in_range = (wf["horizon_h"] > 0) & (wf["horizon_h"] < max_horizon_h)
    f = wf[in_range].merge(hourly_actuals(fh), on="startTime", how="inner")
    f["error_mw"] = f["generation"] - f["actual_mw"]
    f["horizon_start_h"] = (f["horizon_h"] // bin_hours * bin_hours).astype(int)
    return _group_metrics(f, "horizon_start_h").reset_index()

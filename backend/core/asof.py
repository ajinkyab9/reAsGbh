from datetime import date, timedelta

import pandas as pd

UK_TZ = "Europe/London"
CUTOFF_PRESETS = {
    "EPEX 60-min": "09:20",
    "N2EX": "09:50",
    "EPEX 30-min": "15:30",
}
DEFAULT_CUTOFF = CUTOFF_PRESETS["EPEX 60-min"]

DayLike = date | str | pd.Timestamp


def _as_date(day: DayLike) -> date:
    """normalise str,date or ts to plain date for better processing"""
    return pd.Timestamp(day).date()


def cutoff_utc(delivery_day: DayLike, cutoff_time: str) -> pd.Timestamp:
    """Decision cutoff for a delivery day: cutoff_time (UK local) on the day before, in UTC."""
    decision_day = _as_date(delivery_day) - timedelta(days=1)
    return pd.Timestamp(f"{decision_day} {cutoff_time}", tz=UK_TZ).tz_convert("UTC")


def delivery_hours(delivery_day: DayLike) -> pd.DatetimeIndex:
    """hourly UTC timestamps cover the delivery day, midnight to midnight UK time."""
    day_ts = _as_date(delivery_day)
    start_ts = pd.Timestamp(day_ts, tz=UK_TZ)
    end_ts = pd.Timestamp(day_ts + timedelta(days=1), tz=UK_TZ)
    return (
        pd.date_range(start_ts, end_ts, freq="h", inclusive="left")
        .tz_convert("UTC")
        .as_unit("us")
    )


def asof_forecast(
    wf: pd.DataFrame, delivery_day: DayLike, cutoff_time: str = DEFAULT_CUTOFF
) -> pd.DataFrame:
    """latest forecast is published before cutoff per delivery hour,
    each hour falls back to earlier run if latest hour does'nt cover it. hours with
    absolutely no forecast all combe ack as NaN and are not dropped
    """
    cutoff = cutoff_utc(delivery_day, cutoff_time)
    hours = delivery_hours(delivery_day)

    available = wf[(wf["publishTime"] < cutoff) & wf["startTime"].isin(hours)]
    latest = (
        available.sort_values("publishTime")
        .drop_duplicates(subset="startTime", keep="last")
        .set_index("startTime")
        .reindex(hours)
    )
    latest.index.name = "startTime"
    return latest.reset_index().rename(columns={"generation": "forecast_mw"})[
        ["startTime", "forecast_mw", "publishTime", "horizon_h"]
    ]


def asof_forecast_range(
    wf: pd.DataFrame, delivery_days, cutoff_time: str = DEFAULT_CUTOFF
) -> pd.DataFrame:
    """asof forecast for several delivery days, each with a delivery date column"""
    frames = []
    for day in delivery_days:
        df = asof_forecast(wf, day, cutoff_time)
        df.insert(0, "deliveryDate", _as_date(day))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)

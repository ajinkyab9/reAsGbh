import datetime as dt
import json
import platform
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, FastAPI, HTTPException

from core.asof import CUTOFF_PRESETS, DEFAULT_CUTOFF, cutoff_utc
from core.metrics import (
    DEFAULT_SCOPE,
    SCOPES,
    buffer_backtest,
    buffer_backtest_summary,
    forecast_vs_actual,
    metrics_by_day,
    summary_metrics,
)

# loading the data at once
DATA_DIR = Path(__file__).resolve().parent / "data"
WINDFOR = pd.read_parquet(DATA_DIR / "windfor.parquet")
FUELHH = pd.read_parquet(DATA_DIR / "fuelhh_wind.parquet")

DELIVERY_DAYS = SCOPES[DEFAULT_SCOPE]
BUFFER_QUANTILE = 0.90

app = FastAPI(
    title="Day Ahead Wind Forecast Monitor",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)
api = APIRouter(prefix="/api")

# helpers


def _records(df: pd.DataFrame) -> list[dict]:
    """dataframe to json safe list of dicts"""
    out = df.copy()
    numeric = out.select_dtypes("number").columns
    out[numeric] = out[numeric].round(1)
    return json.loads(out.to_json(orient="records", date_format="iso"))


def _rounded(metrics: dict[str, float]) -> dict[str, float]:
    return {k: round(v, 1) for k, v in metrics.items()}


def _check_cutoff(cutoff: str) -> None:
    if cutoff not in CUTOFF_PRESETS.values():
        raise HTTPException(
            400, f"cutoff should be one of {list(CUTOFF_PRESETS.values())}"
        )


@lru_cache
def _month(cutoff: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """hourly forecast vs actual and buffer backtest for entire scope. its cached for cutoff. here data never changes, so its computed once"""
    df = forecast_vs_actual(WINDFOR, FUELHH, DELIVERY_DAYS, cutoff)
    bt = buffer_backtest(df, quantile=BUFFER_QUANTILE)
    return df, bt


@api.get("/health")
def health():
    return {"status": "ok", "python": platform.python_version()}


@api.get("/meta")
def meta():
    """Options the UI needs: cutoff presets and the delivery days in scope."""
    return {
        "cutoffs": [{"label": k, "time": v} for k, v in CUTOFF_PRESETS.items()],
        "default_cutoff": DEFAULT_CUTOFF,
        "days": [d.date().isoformat() for d in DELIVERY_DAYS],
        "scope": DEFAULT_SCOPE,
        "buffer_quantile": BUFFER_QUANTILE,
        "error_convention": "error = forecast - actual (positive = over-forecast)",
    }


@api.get("/day")
def day(date: dt.date, cutoff: str = DEFAULT_CUTOFF):
    """Hourly forecast (as of the cutoff) vs actual for one delivery day."""
    _check_cutoff(cutoff)
    df, bt = _month(cutoff)
    hours = df[df["deliveryDate"] == date]
    if hours.empty:
        raise HTTPException(404, f"{date} is outside the delivery days in scope")

    buffer_row = bt[bt["deliveryDate"] == date].iloc[0]
    buffer_mw = buffer_row.get("buffer_mw")
    return {
        "date": date.isoformat(),
        "cutoff": cutoff,
        "cutoff_utc": cutoff_utc(date, cutoff).isoformat(),
        "runs_used": sorted({t.isoformat() for t in hours["publishTime"]}),
        "metrics": _rounded(summary_metrics(hours)),
        "buffer_mw": None if pd.isna(buffer_mw) else round(float(buffer_mw), 1),
        "hours": _records(hours.drop(columns="deliveryDate")),
    }


@api.get("/summary")
def summary(cutoff: str = DEFAULT_CUTOFF):
    """Month-level accuracy, the buffer backtest and per-day errors."""
    _check_cutoff(cutoff)
    df, bt = _month(cutoff)
    by_day = metrics_by_day(df).merge(
        bt[["deliveryDate", "buffer_mw", "coverage_pct"]], on="deliveryDate"
    )
    by_day["deliveryDate"] = by_day["deliveryDate"].astype(str)
    return {
        "cutoff": cutoff,
        "metrics": _rounded(summary_metrics(df)),
        "buffer": _rounded(buffer_backtest_summary(bt)),
        "days": _records(by_day),
    }


app.include_router(api)

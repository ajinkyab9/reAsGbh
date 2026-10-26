import argparse
import json
import logging
from pathlib import Path

import pandas as pd
import requests

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "backend" / "data"
DELIVERY_DAYS = pd.date_range(
    "2026-01-01", "2026-02-01", freq="D"
)  # covers both readings, delivery or decisions in jan
CUTOFFS = {
    "EPEX 60-min": "09:20",
    "N2EX": "09:50",
    "EPEX 30-min": "15:30",
}  # UK local time, day before delivery

FUELHH_FIRST_DAY = "2026-01-01"
FUELHH_LAST_DAY = "2026-02-01"

WINDFOR_RAW = RAW_DIR / "windfor.json"
FUELHH_RAW = RAW_DIR / "fuelhh_wind.json"
WINDFOR_OUT = OUT_DIR / "windfor.parquet"
FUELHH_OUT = OUT_DIR / "fuelhh_wind.parquet"

WINDFOR_PARAMS = {
    "publishDateTimeFrom": "2025-12-30T00:00Z",
    "publishDateTimeTo": "2026-01-31T23:59Z",
}
FUELHH_PARAMS = {
    "settlementDateFrom": FUELHH_FIRST_DAY,
    "settlementDateTo": FUELHH_LAST_DAY,
    "fuelType": "WIND",
}

logger = logging.getLogger(__name__)


def fetch(dataset: str, params: dict) -> list[dict]:
    """to fetch single time window from given Elexon endpoint"""
    stream_response = requests.get(
        f"{BASE}/{dataset}/stream", params=params, timeout=60
    )
    stream_response.raise_for_status()
    data = stream_response.json()
    if not isinstance(data, list):
        raise TypeError(f"{dataset}: expected a JSON list, got {type(data).__name__}")
    logger.info("%s: fetched %d records", dataset, len(data))
    return data


def save_raw(records: list[dict], path: Path) -> None:
    """write raw API record to main disk unchanged for persistence"""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f)
    logger.info("Saved raw json payload data (%d records) -> %s", len(records), path)


def load_raw(path: Path) -> list[dict]:
    """load raw api records previously saved by save_raw"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise TypeError(f"{path}: expected a JSON list, got {type(data).__name__}")
    logger.info("Loaded %d records: %s", len(data), path)
    return data


def clean_windfor(records: list[dict]) -> pd.DataFrame:
    """this turns raw WINDFOR into a typed, deduplicated and sorted dataframe with horizon_h"""
    df = pd.DataFrame(records)
    required_columns = {"publishTime", "startTime", "generation"}
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"WINDFOR: is missing columns {sorted(missing_columns)}")
    df = df[["publishTime", "startTime", "generation"]]
    if df.isna().any().any():
        raise ValueError("WINDFOR: null values found")

    for col in ("publishTime", "startTime"):
        df[col] = pd.to_datetime(df[col], utc=True)
    df["horizon_h"] = (df["startTime"] - df["publishTime"]).dt.total_seconds() / 3600
    row_count_before_drop = len(df)
    df = df.drop_duplicates(subset=["publishTime", "startTime"])
    if len(df) < row_count_before_drop:
        logger.warning(
            "WINDFOR: dropped %d duplicate rows", row_count_before_drop - len(df)
        )
    df = df.sort_values(["publishTime", "startTime"]).reset_index(drop=True)
    return df


def clean_fuelhh(records: list[dict]) -> pd.DataFrame:
    """this turns raw FUELHH wind records into a typed, deduped dataframe, one row per half hourly basis"""
    df = pd.DataFrame(records)
    required_columns = {
        "publishTime",
        "startTime",
        "settlementDate",
        "settlementPeriod",
        "generation",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(f"FUELHH: is missing columns {sorted(missing_columns)}")
    df = df[
        ["publishTime", "startTime", "settlementDate", "settlementPeriod", "generation"]
    ]
    if df.isna().any().any():
        raise ValueError("FUELHH: null values found")

    for col in ("publishTime", "startTime"):
        df[col] = pd.to_datetime(df[col], utc=True)
    row_count_before_drop = len(df)
    df = df.sort_values("publishTime").drop_duplicates(subset="startTime", keep="last")
    if len(df) < row_count_before_drop:
        logger.warning(
            "FUELHH: dropped %d duplicate rows", row_count_before_drop - len(df)
        )
    df = df[["startTime", "settlementDate", "settlementPeriod", "generation"]]
    return df.sort_values("startTime").reset_index(drop=True)


def validate_fuelhh(df: pd.DataFrame) -> None:
    """raise valueerror in the case when df does not have only one row per half hour in scope with valid generation nos"""
    start_ts = pd.Timestamp(FUELHH_FIRST_DAY, tz="Europe/London")
    end_ts = pd.Timestamp(FUELHH_LAST_DAY, tz="Europe/London") + pd.Timedelta(days=1)
    expected = pd.date_range(
        start_ts, end_ts, freq="30min", inclusive="left"
    ).tz_convert("UTC")
    problems = []
    actual_ts = pd.DatetimeIndex(df["startTime"])

    missing_hrs = expected.difference(actual_ts)
    if len(missing_hrs):
        problems.append(f"{len(missing_hrs)} missing half hrs, first: {missing_hrs[0]}")

    extra_hrs = actual_ts.difference(expected)
    if len(extra_hrs):
        problems.append(
            f"{len(extra_hrs)} half hours outside the provided scope, first: {extra_hrs[0]}"
        )

    n_duplicates = df["startTime"].duplicated().sum()
    if n_duplicates:
        problems.append(f"{n_duplicates} duplicate half hours")

    n_negative = (df["generation"] < 0).sum()
    if n_negative:
        problems.append(f"{n_negative} rows with negative generation detected")

    if problems:
        raise ValueError("FUELHH validation failed:\n - " + "\n - ".join(problems))
    logger.info("FUELHH validation passed: %d half hours", len(df))


def validate_windfor_coverage(
    wf: pd.DataFrame,
    delivery_days: pd.DatetimeIndex = DELIVERY_DAYS,
    cutoffs: dict[str, str] = CUTOFFS,
) -> None:
    """Raise ValueError unless, for every delivery day and cutoff, the latest run before the cutoff covers the whole day."""
    runs = wf["publishTime"].drop_duplicates()
    hours_by_run = wf.groupby("publishTime")["startTime"].apply(pd.DatetimeIndex)
    problems = []

    for day in delivery_days:
        decision_day = (day - pd.Timedelta(days=1)).date()
        start_ts = pd.Timestamp(day.date(), tz="Europe/London")
        expected_ts = pd.date_range(
            start_ts, start_ts + pd.Timedelta(days=1), freq="h", inclusive="left"
        ).tz_convert("UTC")

        for name, time_str in cutoffs.items():
            cutoff = pd.Timestamp(
                f"{decision_day} {time_str}", tz="Europe/London"
            ).tz_convert("UTC")
            before_cutoff = runs[runs < cutoff]
            if before_cutoff.empty:
                problems.append(f"{day.date()} {name}: no run published before cutoff")
                continue
            latest_run = before_cutoff.max()
            missing_hrs = expected_ts.difference(hours_by_run[latest_run])
            if len(missing_hrs):
                problems.append(
                    f"{day.date()} {name}: run {latest_run} missing {len(missing_hrs)} hours"
                )

    if problems:
        raise ValueError("WINDFOR coverage failed:\n - " + "\n - ".join(problems))
    logger.info(
        "WINDFOR coverage passed: %d days x %d cutoffs",
        len(delivery_days),
        len(cutoffs),
    )


def summarize(wf: pd.DataFrame, fh: pd.DataFrame) -> None:
    """Log a short summary of the ingested data."""
    runs = wf["publishTime"].drop_duplicates()
    runs_per_day = runs.dt.date.value_counts()
    logger.info(
        "WINDFOR: %d rows, %d runs (%d-%d per day), horizon %.1f to %.1f h",
        len(wf),
        len(runs),
        runs_per_day.min(),
        runs_per_day.max(),
        wf["horizon_h"].min(),
        wf["horizon_h"].max(),
    )
    logger.info(
        "WINDFOR publish times (UTC): %s",
        runs.dt.strftime("%H:%M").value_counts().sort_index().to_dict(),
    )
    logger.info(
        "FUELHH: %d half-hours, %s to %s, generation %d-%d MW",
        len(fh),
        fh["startTime"].min(),
        fh["startTime"].max(),
        fh["generation"].min(),
        fh["generation"].max(),
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    parser = argparse.ArgumentParser(
        description="Ingest Elexon WINDFOR and FUELHH data."
    )
    parser.add_argument(
        "--from-raw",
        action="store_true",
        help="rebuild parquet from saved raw JSON without calling the API",
    )
    args = parser.parse_args(argv)

    if not args.from_raw:
        save_raw(fetch("WINDFOR", WINDFOR_PARAMS), WINDFOR_RAW)
        save_raw(fetch("FUELHH", FUELHH_PARAMS), FUELHH_RAW)

    wf = clean_windfor(load_raw(WINDFOR_RAW))
    fh = clean_fuelhh(load_raw(FUELHH_RAW))

    try:
        validate_fuelhh(fh)
        validate_windfor_coverage(wf)
    except ValueError as e:
        logger.error("%s", e)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    wf.to_parquet(WINDFOR_OUT, index=False)
    fh.to_parquet(FUELHH_OUT, index=False)
    logger.info("Wrote %s and %s", WINDFOR_OUT, FUELHH_OUT)
    summarize(wf, fh)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

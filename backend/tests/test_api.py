import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_meta_lists_presets_and_days():
    body = client.get("/api/meta").json()
    assert [c["time"] for c in body["cutoffs"]] == ["09:20", "09:50", "15:30"]
    assert body["days"][0] == "2026-01-02"
    assert body["days"][-1] == "2026-02-01"


def test_day_returns_24_hours_from_the_run_available_at_cutoff():
    body = client.get(
        "/api/day", params={"date": "2026-01-15", "cutoff": "09:20"}
    ).json()
    assert len(body["hours"]) == 24
    assert body["runs_used"] == ["2026-01-14T07:30:00+00:00"]
    assert body["hours"][0]["forecast_mw"] == 15834


def test_day_has_no_buffer_before_enough_history():
    body = client.get("/api/day", params={"date": "2026-01-02"}).json()
    assert body["buffer_mw"] is None


def test_summary_shape():
    body = client.get("/api/summary", params={"cutoff": "09:20"}).json()
    assert set(body) == {"cutoff", "metrics", "buffer", "days"}
    assert len(body["days"]) == 31


@pytest.mark.parametrize(
    "path, params, status",
    [
        ("/api/day", {"date": "2026-03-01"}, 404),  # outside scope
        ("/api/day", {"date": "2026-01-15", "cutoff": "10:00"}, 400),  # not a preset
        ("/api/day", {"date": "not-a-date"}, 422),  # FastAPI validation
        ("/api/summary", {"cutoff": "10:00"}, 400),
    ],
)
def test_bad_requests(path, params, status):
    assert client.get(path, params=params).status_code == status

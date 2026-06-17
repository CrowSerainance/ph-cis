import pytest

httpx = pytest.importorskip("httpx")

import api.app as api_app
from fastapi.testclient import TestClient


client = TestClient(api_app.app)


FORECAST = {
    "time": [
        "2026-06-16",
        "2026-06-17",
        "2026-06-18",
        "2026-06-19",
        "2026-06-20",
        "2026-06-21",
        "2026-06-22",
    ],
    "precipitation_sum": [0.0, 0.2, 0.5, 0.9, 0.0, 3.0, 4.0],
    "temperature_2m_max": [34.0, 35.0, 36.0, 35.5, 30.0, 29.0, 28.0],
}


def test_advisory_uses_monkeypatched_forecast_loader(monkeypatch):
    loaded = []

    def fake_load(prov_key):
        loaded.append(prov_key)
        return FORECAST

    monkeypatch.setattr(api_app, "_load", fake_load)

    response = client.get("/advisory", params={"province": "Nueva Ecija", "crop": "corn", "stage": "vegetative"})

    assert response.status_code == 200
    body = response.json()
    assert loaded == ["nueva_ecija"]
    assert body["province"] == "Nueva Ecija"
    assert body["crop"] == "corn"
    assert body["stage"] == "vegetative"
    assert body["weekly_rain_mm"] == 8.6
    assert body["heat_days"] == 3
    assert body["dryspell_flag"] is True
    assert "Irrigate early morning" in body["advisory"]
    assert body["dates"] == FORECAST["time"]


def test_advisory_validation_rejects_unknown_province(monkeypatch):
    monkeypatch.setattr(api_app, "_load", lambda prov_key: FORECAST)

    response = client.get("/advisory", params={"province": "Unknown", "crop": "rice", "stage": "nursery"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unknown province"


def test_advisory_validation_rejects_unknown_crop(monkeypatch):
    monkeypatch.setattr(api_app, "_load", lambda prov_key: FORECAST)

    response = client.get("/advisory", params={"province": "Isabela", "crop": "banana", "stage": "nursery"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unknown crop"


def test_advisory_validation_rejects_unknown_stage(monkeypatch):
    monkeypatch.setattr(api_app, "_load", lambda prov_key: FORECAST)

    response = client.get("/advisory", params={"province": "Isabela", "crop": "rice", "stage": "tasseling"})

    assert response.status_code == 400
    assert response.json()["detail"]["error"] == "unknown stage"

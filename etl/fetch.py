import json, requests, datetime as dt
from core.config import PROVINCES
from core.paths import DATA_DIR, METADATA_PATH

DATA_DIR.mkdir(exist_ok=True)
SOURCE_PROVIDER = "Open-Meteo"
SOURCE_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_7day(lat, lon):
    # Daily precip & max temp for next 7 days
    url = (SOURCE_URL +
           f"?latitude={lat}&longitude={lon}"
           "&daily=precipitation_sum,temperature_2m_max"
           "&timezone=Asia%2FManila&forecast_days=7")
    r = requests.get(url, timeout=30); r.raise_for_status()
    return r.json()

def refresh_all():
    out = {}
    for key, meta in PROVINCES.items():
        js = fetch_7day(meta["lat"], meta["lon"])
        out[key] = js["daily"]
        (DATA_DIR / f"{key}.json").write_text(json.dumps(out[key]))
    refreshed_at = dt.datetime.now(dt.timezone.utc).isoformat()
    metadata = {
        "last_refresh_utc": refreshed_at,
        "source_provider": SOURCE_PROVIDER,
        "source_url": SOURCE_URL,
        "provinces_refreshed": [PROVINCES[key]["name"] for key in out],
        "province_keys_refreshed": list(out),
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (DATA_DIR / "last_refresh.txt").write_text(refreshed_at, encoding="utf-8")
    return out

if __name__ == "__main__":
    refresh_all(); print("OK")

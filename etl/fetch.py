import json, pathlib, requests, datetime as dt
from core.config import PROVINCES

DATA_DIR = pathlib.Path("data"); DATA_DIR.mkdir(exist_ok=True)

def fetch_7day(lat, lon):
    # Daily precip & max temp for next 7 days
    url = ("https://api.open-meteo.com/v1/forecast"
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
    (DATA_DIR / "last_refresh.txt").write_text(dt.datetime.now().isoformat())
    return out

if __name__ == "__main__":
    refresh_all(); print("OK")

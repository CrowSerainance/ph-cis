import json, pathlib
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from core.config import PROVINCES, CROPS
from core.metrics import weekly_rain_mm, heat_days, dryspell_count
from core.rules import advisory_text, sms_line

app = FastAPI(title="PH CIS API")
DATA_DIR = pathlib.Path("data")

class AdvisoryOut(BaseModel):
    province: str
    crop: str
    stage: str
    weekly_rain_mm: float
    heat_days: int
    dryspell_flag: bool
    advisory: str
    sms: str
    dates: list

def _load(prov_key):
    p = DATA_DIR / f"{prov_key}.json"
    if not p.exists(): raise FileNotFoundError
    return json.loads(p.read_text())

@app.get("/advisory", response_model=AdvisoryOut)
def advisory(province: str, crop: str, stage: str):
    prov_key = province.lower().replace(" ","_")
    if prov_key not in PROVINCES: raise HTTPException(400, "unknown province")
    if crop not in CROPS: raise HTTPException(400, "unknown crop")
    if stage not in CROPS[crop]["stages"]: raise HTTPException(400, "unknown stage")

    daily = _load(prov_key)
    rain = daily["precipitation_sum"]; tmax = daily["temperature_2m_max"]; dates = daily["time"]

    wr = weekly_rain_mm(rain)
    hd = heat_days(tmax, CROPS[crop]["thresholds"]["heat_day_tmax"])
    ds = bool(dryspell_count(rain, dry_thresh=1.0, spell_len=CROPS[crop]["thresholds"]["dryspell_days"]))

    text = advisory_text(crop, stage, wr, ds, hd)
    sms = sms_line(PROVINCES[prov_key]["name"], crop, stage, wr, ds, hd)

    return AdvisoryOut(
        province=PROVINCES[prov_key]["name"], crop=crop, stage=stage,
        weekly_rain_mm=wr, heat_days=hd, dryspell_flag=ds,
        advisory=text, sms=sms, dates=dates
    )

import csv
import io
import json
import pathlib
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel

from core.config import CROPS, PROVINCES
from core.metrics import dryspell_count, heat_days, weekly_rain_mm
from core.rules import SUPPORTED_LANGUAGES, advisory_text, sms_line

app = FastAPI(title="PH CIS API")
DATA_DIR = pathlib.Path("data")
Lang = Literal["en", "tl"]


class AdvisoryOut(BaseModel):
    province: str
    crop: str
    stage: str
    weekly_rain_mm: float
    heat_days: int
    dryspell_flag: bool
    advisory: str
    sms: str
    dates: list[str]


class AdvisoryCombination(BaseModel):
    province: str
    crop: str
    stage: str


class AdvisoryBulkRequest(BaseModel):
    combinations: list[AdvisoryCombination]


def _load(prov_key):
    p = DATA_DIR / f"{prov_key}.json"
    if not p.exists():
        raise HTTPException(404, f"forecast data not found for {prov_key}; run python -m etl.fetch")
    return json.loads(p.read_text())


def _province_key(province: str) -> str:
    prov_key = province.lower().replace(" ", "_")
    if prov_key not in PROVINCES:
        raise HTTPException(400, "unknown province")
    return prov_key


def _validate_crop_stage(crop: str, stage: str) -> None:
    if crop not in CROPS:
        raise HTTPException(400, "unknown crop")
    if stage not in CROPS[crop]["stages"]:
        raise HTTPException(400, "unknown stage")


def _validate_lang(lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, "unsupported lang; use en or tl")


def _build_advisory(province: str, crop: str, stage: str, lang: Lang = "en") -> AdvisoryOut:
    _validate_lang(lang)
    prov_key = _province_key(province)
    _validate_crop_stage(crop, stage)

    daily = _load(prov_key)
    rain = daily["precipitation_sum"]
    tmax = daily["temperature_2m_max"]
    dates = daily["time"]

    wr = weekly_rain_mm(rain)
    hd = heat_days(tmax, CROPS[crop]["thresholds"]["heat_day_tmax"])
    ds = bool(dryspell_count(rain, dry_thresh=1.0, spell_len=CROPS[crop]["thresholds"]["dryspell_days"]))

    text = advisory_text(crop, stage, wr, ds, hd, lang=lang)
    sms = sms_line(PROVINCES[prov_key]["name"], crop, stage, wr, ds, hd, lang=lang)

    return AdvisoryOut(
        province=PROVINCES[prov_key]["name"],
        crop=crop,
        stage=stage,
        weekly_rain_mm=wr,
        heat_days=hd,
        dryspell_flag=ds,
        advisory=text,
        sms=sms,
        dates=dates,
    )


def _default_combinations() -> list[AdvisoryCombination]:
    return [
        AdvisoryCombination(province=meta["name"], crop=crop, stage=stage)
        for meta in PROVINCES.values()
        for crop, cfg in CROPS.items()
        for stage in cfg["stages"]
    ]


def _query_combinations(
    province: list[str] | None,
    crop: list[str] | None,
    stage: list[str] | None,
) -> list[AdvisoryCombination]:
    if province is None and crop is None and stage is None:
        return _default_combinations()
    if not province or not crop or not stage:
        raise HTTPException(400, "province, crop, and stage must be supplied together")
    if not (len(province) == len(crop) == len(stage)):
        raise HTTPException(400, "province, crop, and stage lists must have the same length")
    return [
        AdvisoryCombination(province=prov, crop=crp, stage=stg)
        for prov, crp, stg in zip(province, crop, stage)
    ]


def _rows_to_csv(rows: list[AdvisoryOut]) -> str:
    fields = [
        "province",
        "crop",
        "stage",
        "weekly_rain_mm",
        "heat_days",
        "dryspell_flag",
        "advisory",
        "sms",
        "date_start",
        "date_end",
        "dates",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        item = row.dict()
        dates = item.pop("dates")
        item["date_start"] = dates[0] if dates else ""
        item["date_end"] = dates[-1] if dates else ""
        item["dates"] = ";".join(dates)
        writer.writerow(item)
    return buf.getvalue()


@app.get("/advisory", response_model=AdvisoryOut)
def advisory(province: str, crop: str, stage: str, lang: Lang = "en"):
    return _build_advisory(province, crop, stage, lang)


@app.get("/advisory_bulk", response_model=list[AdvisoryOut])
def advisory_bulk(
    province: list[str] | None = Query(default=None),
    crop: list[str] | None = Query(default=None),
    stage: list[str] | None = Query(default=None),
    lang: Lang = "en",
):
    combinations = _query_combinations(province, crop, stage)
    return [_build_advisory(item.province, item.crop, item.stage, lang) for item in combinations]


@app.post("/advisory_bulk", response_model=list[AdvisoryOut])
def advisory_bulk_post(payload: AdvisoryBulkRequest, lang: Lang = "en"):
    return [_build_advisory(item.province, item.crop, item.stage, lang) for item in payload.combinations]


@app.get("/export/csv")
def export_csv(
    province: list[str] | None = Query(default=None),
    crop: list[str] | None = Query(default=None),
    stage: list[str] | None = Query(default=None),
    lang: Lang = "en",
):
    combinations = _query_combinations(province, crop, stage)
    rows = [_build_advisory(item.province, item.crop, item.stage, lang) for item in combinations]
    return Response(
        content=_rows_to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ph-cis-advisories.csv"},
    )

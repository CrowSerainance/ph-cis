import csv
import io
import json
import re
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field

from core.config import CROPS, PROVINCES
from core.metrics import dryspell_count, heat_days, weekly_rain_mm
from core.paths import DATA_DIR, METADATA_PATH
from core.rules import SUPPORTED_LANGUAGES, advisory_text, sms_line

app = FastAPI(title="PH CIS API")
FORECAST_UNAVAILABLE_DETAIL = "forecast cache missing or stale; run python -m etl.fetch"
REQUIRED_FORECAST_KEYS = ("time", "precipitation_sum", "temperature_2m_max")
Lang = Literal["en", "tl"]


class RefreshMetadata(BaseModel):
    last_refresh_utc: str | None = None
    source_provider: str | None = None
    source_url: str | None = None
    provinces_refreshed: list[str] = Field(default_factory=list)
    province_keys_refreshed: list[str] = Field(default_factory=list)


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
    refresh_metadata: RefreshMetadata


class AdvisoryCombination(BaseModel):
    province: str
    crop: str
    stage: str


class AdvisoryBulkRequest(BaseModel):
    combinations: list[AdvisoryCombination]


def _load_refresh_metadata() -> dict:
    default = {
        "last_refresh_utc": None,
        "source_provider": None,
        "source_url": None,
        "provinces_refreshed": [],
        "province_keys_refreshed": [],
    }
    try:
        metadata = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default
    return {**default, **metadata}


def _load(prov_key):
    p = DATA_DIR / f"{prov_key}.json"
    return json.loads(p.read_text(encoding="utf-8"))


def _missing_forecast_keys(daily) -> list[str]:
    if not isinstance(daily, dict):
        return list(REQUIRED_FORECAST_KEYS)
    return [key for key in REQUIRED_FORECAST_KEYS if key not in daily]


def _load_daily_forecast(prov_key: str):
    try:
        daily = _load(prov_key)
        missing = _missing_forecast_keys(daily)
        if missing:
            raise KeyError(", ".join(missing))
    except (FileNotFoundError, json.JSONDecodeError, KeyError) as exc:
        raise HTTPException(
            status_code=503, detail=FORECAST_UNAVAILABLE_DETAIL
        ) from exc
    return daily


def _province_health(prov_key: str) -> dict:
    path = DATA_DIR / f"{prov_key}.json"
    status = {
        "province": PROVINCES[prov_key]["name"],
        "file": str(path),
        "exists": path.exists(),
        "valid_json": False,
        "has_required_keys": False,
        "missing_keys": list(REQUIRED_FORECAST_KEYS),
    }
    if not status["exists"]:
        return status
    try:
        daily = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return status

    status["valid_json"] = True
    missing = _missing_forecast_keys(daily)
    status["missing_keys"] = missing
    status["has_required_keys"] = not missing
    return status


def _slug(value: str) -> str:
    return re.sub(r"[\s_]+", "_", value.strip().lower().replace("-", "_")).strip(
        "_"
    )


def _accepted_provinces() -> list[str]:
    return [meta["name"] for meta in PROVINCES.values()]


def _province_key(province: str) -> str:
    prov_key = _slug(province)
    if prov_key not in PROVINCES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown province",
                "received": province,
                "normalized": prov_key,
                "accepted_provinces": _accepted_provinces(),
                "accepted_values": list(PROVINCES),
            },
        )
    return prov_key


def _crop_key(crop: str) -> str:
    crop_key = _slug(crop)
    if crop_key not in CROPS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown crop",
                "received": crop,
                "normalized": crop_key,
                "accepted_crops": list(CROPS),
            },
        )
    return crop_key


def _stage_key(crop: str, stage: str) -> str:
    stage_key = _slug(stage)
    accepted_stages = CROPS[crop]["stages"]
    if stage_key not in accepted_stages:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "unknown stage",
                "received": stage,
                "normalized": stage_key,
                "crop": crop,
                "accepted_stages": accepted_stages,
            },
        )
    return stage_key


def _validate_crop_stage(crop: str, stage: str) -> tuple[str, str]:
    crop_key = _crop_key(crop)
    return crop_key, _stage_key(crop_key, stage)


def _validate_lang(lang: str) -> None:
    if lang not in SUPPORTED_LANGUAGES:
        raise HTTPException(400, "unsupported lang; use en or tl")


def _build_advisory(
    province: str, crop: str, stage: str, lang: Lang = "en"
) -> AdvisoryOut:
    _validate_lang(lang)
    prov_key = _province_key(province)
    crop_key, stage_key = _validate_crop_stage(crop, stage)

    daily = _load_daily_forecast(prov_key)
    rain = daily["precipitation_sum"]
    tmax = daily["temperature_2m_max"]
    dates = daily["time"]

    wr = weekly_rain_mm(rain)
    hd = heat_days(tmax, CROPS[crop_key]["thresholds"]["heat_day_tmax"])
    ds = bool(
        dryspell_count(
            rain,
            dry_thresh=1.0,
            spell_len=CROPS[crop_key]["thresholds"]["dryspell_days"],
        )
    )

    text = advisory_text(crop_key, stage_key, wr, ds, hd, lang=lang)
    sms = sms_line(
        PROVINCES[prov_key]["name"], crop_key, stage_key, wr, ds, hd, lang=lang
    )

    return AdvisoryOut(
        province=PROVINCES[prov_key]["name"],
        crop=crop_key,
        stage=stage_key,
        weekly_rain_mm=wr,
        heat_days=hd,
        dryspell_flag=ds,
        advisory=text,
        sms=sms,
        dates=dates,
        refresh_metadata=RefreshMetadata(**_load_refresh_metadata()),
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
        raise HTTPException(
            400, "province, crop, and stage lists must have the same length"
        )
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
        item.pop("refresh_metadata", None)
        dates = item.pop("dates")
        item["date_start"] = dates[0] if dates else ""
        item["date_end"] = dates[-1] if dates else ""
        item["dates"] = ";".join(dates)
        writer.writerow(item)
    return buf.getvalue()


@app.get("/health")
def health():
    provinces = {prov_key: _province_health(prov_key) for prov_key in PROVINCES}
    return {
        "ok": all(item["has_required_keys"] for item in provinces.values()),
        "required_keys": list(REQUIRED_FORECAST_KEYS),
        "provinces": provinces,
        "refresh_metadata": _load_refresh_metadata(),
    }


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
    return [
        _build_advisory(item.province, item.crop, item.stage, lang)
        for item in combinations
    ]


@app.post("/advisory_bulk", response_model=list[AdvisoryOut])
def advisory_bulk_post(payload: AdvisoryBulkRequest, lang: Lang = "en"):
    return [
        _build_advisory(item.province, item.crop, item.stage, lang)
        for item in payload.combinations
    ]


@app.get("/export/csv")
def export_csv(
    province: list[str] | None = Query(default=None),
    crop: list[str] | None = Query(default=None),
    stage: list[str] | None = Query(default=None),
    lang: Lang = "en",
):
    combinations = _query_combinations(province, crop, stage)
    rows = [
        _build_advisory(item.province, item.crop, item.stage, lang)
        for item in combinations
    ]
    return Response(
        content=_rows_to_csv(rows),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ph-cis-advisories.csv"},
    )

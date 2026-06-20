# --- import path shim: make project root importable ---
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
# ------------------------------------------------------

import datetime as dt
import os

import requests
import streamlit as st
from core.config import CROPS, PROVINCES

DEFAULT_API_BASE_URL = "http://127.0.0.1:8000"
LANGUAGES = {"English": "en", "Tagalog": "tl"}
CACHE_STALE_AFTER = dt.timedelta(hours=24)


def parse_utc_timestamp(value: str | None) -> dt.datetime | None:
    """Parse API refresh timestamps as timezone-aware UTC datetimes."""
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def show_refresh_metadata(metadata: dict) -> None:
    """Display cache freshness details and warn when the forecast is stale."""
    refreshed_at = parse_utc_timestamp(metadata.get("last_refresh_utc"))
    source = (
        metadata.get("source_provider")
        or metadata.get("source_url")
        or "unknown source"
    )
    provinces = (
        metadata.get("provinces_refreshed")
        or metadata.get("province_keys_refreshed")
        or []
    )

    st.caption(f"Forecast source: {source}")
    if provinces:
        st.caption(f"Forecast provinces refreshed: {', '.join(provinces)}")

    if refreshed_at is None:
        st.warning(
            "Forecast refresh time is unavailable; cache freshness cannot be verified."
        )
        return

    age = dt.datetime.now(dt.timezone.utc) - refreshed_at
    st.caption(
        f"Forecast last refreshed: {refreshed_at.isoformat()} "
        f"({age.total_seconds() / 3600:.1f} hours ago)"
    )
    if age > CACHE_STALE_AFTER:
        st.warning(
            "Forecast cache is older than 24 hours. Run `python -m etl.fetch` "
            "to refresh before using advisories operationally."
        )


def configured_api_base_url() -> str:
    """Return the preferred API URL from secrets or the environment."""
    return (
        st.secrets.get("PH_CIS_API_URL")
        or st.secrets.get("api_base_url")
        or os.environ.get("PH_CIS_API_URL")
        or DEFAULT_API_BASE_URL
    )


def api_url(base_url: str, path: str) -> str:
    """Join an API base URL and path without producing double slashes."""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def get_api(path: str, params: dict[str, str], base_url: str) -> requests.Response | None:
    """Call the API and show a concise Streamlit error if the request fails."""
    url = api_url(base_url, path)
    try:
        response = requests.get(url, params=params, timeout=20)
    except requests.exceptions.ConnectionError:
        st.error(
            f"Cannot connect to the API at {base_url}. "
            "Check that the API is running and the URL is correct."
        )
        return None
    except requests.exceptions.RequestException as exc:
        st.error(f"API request failed: {exc}")
        return None

    if not response.ok:
        detail = response.text.strip() or response.reason
        st.error(f"API returned HTTP {response.status_code}: {detail}")
        return None

    return response


st.title("PH Rain & Heat Advisory (Pilot)")

api_base_url = st.sidebar.text_input(
    "API base URL",
    value=configured_api_base_url(),
    help="Set with Streamlit secrets PH_CIS_API_URL/api_base_url, the PH_CIS_API_URL environment variable, or edit here.",
).strip() or DEFAULT_API_BASE_URL

prov = st.selectbox("Province", [v["name"] for v in PROVINCES.values()])
crop = st.selectbox("Crop", list(CROPS.keys()))
stage = st.selectbox("Stage", CROPS[crop]["stages"])
lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
lang = LANGUAGES[lang_label]

q = {"province": prov, "crop": crop, "stage": stage, "lang": lang}
r = get_api("/advisory", q, api_base_url)
if r is not None:
    js = r.json()
    st.subheader("Weekly Summary")
    show_refresh_metadata(js.get("refresh_metadata", {}))
    st.write(js["advisory"])
    st.metric("7-day rain (mm)", js["weekly_rain_mm"])
    st.metric("Heat days (≥35°C)", js["heat_days"])
    st.metric("Dry-spell flag (≥5 days <1mm)", "Yes" if js["dryspell_flag"] else "No")
    st.code(js["sms"], language="text")

    if st.checkbox("Show CSV download"):
        csv_r = get_api("/export/csv", q, api_base_url)
        if csv_r is not None:
            st.download_button(
                "Download selected advisory CSV",
                data=csv_r.text,
                file_name="ph-cis-advisory.csv",
                mime="text/csv",
            )

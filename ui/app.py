# --- import path shim: make project root importable ---
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
# ------------------------------------------------------

import requests, streamlit as st
from core.config import PROVINCES, CROPS

API_BASE_URL = "http://127.0.0.1:8000"
LANGUAGES = {"English": "en", "Tagalog": "tl"}

st.title("PH Rain & Heat Advisory (Pilot)")

prov = st.selectbox("Province", [v["name"] for v in PROVINCES.values()])
crop = st.selectbox("Crop", list(CROPS.keys()))
stage = st.selectbox("Stage", CROPS[crop]["stages"])
lang_label = st.selectbox("Language", list(LANGUAGES.keys()))
lang = LANGUAGES[lang_label]

q = {"province": prov, "crop": crop, "stage": stage, "lang": lang}
r = requests.get(f"{API_BASE_URL}/advisory", params=q, timeout=20)
if r.ok:
    js = r.json()
    st.subheader("Weekly Summary")
    st.write(js["advisory"])
    st.metric("7-day rain (mm)", js["weekly_rain_mm"])
    st.metric("Heat days (≥35°C)", js["heat_days"])
    st.metric("Dry-spell flag (≥5 days <1mm)", "Yes" if js["dryspell_flag"] else "No")
    st.code(js["sms"], language="text")

    if st.checkbox("Show CSV download"):
        csv_r = requests.get(f"{API_BASE_URL}/export/csv", params=q, timeout=20)
        if csv_r.ok:
            st.download_button(
                "Download selected advisory CSV",
                data=csv_r.text,
                file_name="ph-cis-advisory.csv",
                mime="text/csv",
            )
        else:
            st.error(csv_r.text)
else:
    st.error(r.text)

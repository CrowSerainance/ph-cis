# --- import path shim: make project root importable ---
import sys, pathlib
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
# ------------------------------------------------------

import requests, streamlit as st
from core.config import PROVINCES, CROPS

st.title("PH Rain & Heat Advisory (Pilot)")

prov = st.selectbox("Province", [v["name"] for v in PROVINCES.values()])
crop = st.selectbox("Crop", list(CROPS.keys()))
stage = st.selectbox("Stage", CROPS[crop]["stages"])

q = {"province":prov,"crop":crop,"stage":stage}
r = requests.get("http://127.0.0.1:8000/advisory", params=q, timeout=20)
if r.ok:
    js = r.json()
    st.subheader("Weekly Summary")
    st.write(js["advisory"])
    st.metric("7-day rain (mm)", js["weekly_rain_mm"])
    st.metric("Heat days (≥35°C)", js["heat_days"])
    st.metric("Dry-spell flag (≥5 days <1mm)", "Yes" if js["dryspell_flag"] else "No")
    st.code(js["sms"], language="text")
else:
    st.error(r.text)

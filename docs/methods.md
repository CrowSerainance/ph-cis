@"
# Methods & Assumptions (v0.1)

**Scope:** Pilot coverage for Nueva Ecija and Isabela. Crops: **rice** and **corn**.

## Inputs
- **Forecast:** Open-Meteo daily `precipitation_sum (mm)` and `temperature_2m_max (°C)` for the next 7 days.
- **Time zone:** Asia/Manila. ETL refresh intended daily via Task Scheduler.
- **Location:** Province centroids (one point per province for pilot simplicity).

## Metrics
- **Weekly rain (mm):** sum over 7 days.
- **Heat-days (count):** number of days with Tmax ≥ **35 °C**.
- **Dry-spell flag (bool):** true if any run of **≥5 days** has precipitation < **1 mm**.

## Rules (first draft)
### Rice (nursery/transplanting)
- If **dry-spell** OR **weekly rain < 20 mm** → “Delay transplanting 3–5 days; prepare alternate water source.”
- If **weekly rain ≥ 80 mm** → “Expect waterlogging; raise seedbed and improve drainage.”

### Corn (vegetative/tasseling)
- If **heat-days ≥ 3** → “Irrigate early; avoid midday foliar sprays; delay N topdress.”
- If **weekly rain < 15 mm** → “Moisture stress likely; prioritize sandy fields.”

> Thresholds are placeholders for a pilot and require tuning with local agronomists and backtesting.

## Outputs
- **API:** `/advisory`, `/advisory_bulk`, `/export/csv` with `lang=en|tl`.
- **UI:** Streamlit single page consuming the API.
- **CSV:** One row per province for LGU/SMS workflows.

## Limitations
- Province-level aggregation hides local variability.
- Forecast uncertainty grows with lead time; update mid-week.
- Rules are not variety/soil specific yet.
- Not a substitute for official hazard warnings.

## Validation (planned)
- Back-test last 4–8 weeks for pilot provinces.
- Rapid feedback from municipal ag offices on clarity/usefulness.
- Adjust thresholds per crop stage and season.
"@ | Set-Content docs\methods.md -Encoding utf8

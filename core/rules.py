from core.config import CROPS

def advisory_text(crop, stage, weekly_rain, dryspell_flag, heat_day_count):
    th = CROPS[crop]["thresholds"]
    msgs = []
    if crop == "rice" and stage in ("transplanting","nursery"):
        if dryspell_flag or weekly_rain < th["weekly_rain_low"]:
            msgs.append("Delay transplanting 3–5 days; prepare alternate water source if possible.")
        if weekly_rain >= th["weekly_rain_high"]:
            msgs.append("Expect waterlogging; raise seedbed and improve drainage.")
    if crop == "corn" and stage in ("vegetative","tasseling"):
        if heat_day_count >= 3:
            msgs.append("Irrigate early morning; avoid midday foliar sprays and nitrogen topdress this week.")
        if weekly_rain < th["weekly_rain_low"]:
            msgs.append("Moisture stress likely; prioritize fields with sandy soils.")

    if not msgs:
        msgs.append("Conditions near normal. Proceed with planned activities and monitor updates mid-week.")
    return " ".join(msgs)

def sms_line(province_name, crop, stage, weekly_rain, dryspell_flag, heat_day_count):
    sig = "Dry" if dryspell_flag else "Wet" if weekly_rain>=80 else "Near-normal"
    return f"{province_name}: {crop}/{stage}: {sig}. 7-day rain {weekly_rain} mm; heat-days {heat_day_count}. Key: see advisory."

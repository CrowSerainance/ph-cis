from core.config import CROPS

SUPPORTED_LANGUAGES = {"en", "tl"}

_MESSAGES = {
    "en": {
        "rice_dry": "Delay transplanting 3–5 days; prepare alternate water source if possible.",
        "rice_wet": "Expect waterlogging; raise seedbed and improve drainage.",
        "corn_heat": "Irrigate early morning; avoid midday foliar sprays and nitrogen topdress this week.",
        "corn_dry": "Moisture stress likely; prioritize fields with sandy soils.",
        "normal": "Conditions near normal. Proceed with planned activities and monitor updates mid-week.",
        "dry_sig": "Dry",
        "wet_sig": "Wet",
        "normal_sig": "Near-normal",
        "sms_key": "Key: see advisory.",
        "rain_label": "7-day rain",
        "heat_label": "heat-days",
    },
    "tl": {
        "rice_dry": "Ipagpaliban ang paglilipat-tanim nang 3–5 araw; maghanda ng alternatibong mapagkukunan ng tubig kung maaari.",
        "rice_wet": "Asahan ang pagbabad ng tubig; itaas ang punlaan at ayusin ang daluyan ng tubig.",
        "corn_heat": "Magpatubig sa madaling-araw; iwasan ang pag-spray sa tanghali at paglalagay ng nitrogen topdress ngayong linggo.",
        "corn_dry": "Malamang ang stress sa kakulangan ng tubig; unahin ang mga bukiring mabuhangin ang lupa.",
        "normal": "Malapit sa normal ang kondisyon. Ituloy ang nakaplanong gawain at bantayan ang update sa kalagitnaan ng linggo.",
        "dry_sig": "Tuyo",
        "wet_sig": "Basang-basa",
        "normal_sig": "Halos normal",
        "sms_key": "Punto: tingnan ang payo.",
        "rain_label": "7-araw na ulan",
        "heat_label": "araw ng init",
    },
}


def _messages_for(lang):
    if lang not in SUPPORTED_LANGUAGES:
        raise ValueError(f"unsupported language: {lang}")
    return _MESSAGES[lang]


def advisory_text(crop, stage, weekly_rain, dryspell_flag, heat_day_count, lang="en"):
    th = CROPS[crop]["thresholds"]
    text = _messages_for(lang)
    msgs = []
    if crop == "rice" and stage in ("transplanting", "nursery"):
        if dryspell_flag or weekly_rain < th["weekly_rain_low"]:
            msgs.append(text["rice_dry"])
        if weekly_rain >= th["weekly_rain_high"]:
            msgs.append(text["rice_wet"])
    if crop == "corn" and stage in ("vegetative", "tasseling"):
        if heat_day_count >= 3:
            msgs.append(text["corn_heat"])
        if weekly_rain < th["weekly_rain_low"]:
            msgs.append(text["corn_dry"])

    if not msgs:
        msgs.append(text["normal"])
    return " ".join(msgs)


def sms_line(province_name, crop, stage, weekly_rain, dryspell_flag, heat_day_count, lang="en"):
    text = _messages_for(lang)
    sig = text["dry_sig"] if dryspell_flag else text["wet_sig"] if weekly_rain >= 80 else text["normal_sig"]
    return (
        f"{province_name}: {crop}/{stage}: {sig}. "
        f"{text['rain_label']} {weekly_rain} mm; {text['heat_label']} {heat_day_count}. "
        f"{text['sms_key']}"
    )

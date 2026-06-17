from core.rules import advisory_text, sms_line


def test_rice_nursery_dry_advisory_and_sms_signal():
    advisory = advisory_text("rice", "nursery", weekly_rain=19.9, dryspell_flag=False, heat_day_count=0)
    sms = sms_line("Nueva Ecija", "rice", "nursery", weekly_rain=19.9, dryspell_flag=True, heat_day_count=0)

    assert "Delay transplanting" in advisory
    assert "Nueva Ecija: rice/nursery: Dry." in sms
    assert "7-day rain 19.9 mm" in sms


def test_rice_transplanting_wet_advisory_and_sms_signal_at_80mm_boundary():
    advisory = advisory_text("rice", "transplanting", weekly_rain=80.0, dryspell_flag=False, heat_day_count=0)
    sms = sms_line("Isabela", "rice", "transplanting", weekly_rain=80.0, dryspell_flag=False, heat_day_count=0)

    assert "Expect waterlogging" in advisory
    assert "Isabela: rice/transplanting: Wet." in sms


def test_corn_vegetative_heat_and_dry_advisory():
    advisory = advisory_text("corn", "vegetative", weekly_rain=14.9, dryspell_flag=False, heat_day_count=3)

    assert "Irrigate early morning" in advisory
    assert "Moisture stress likely" in advisory


def test_corn_tasseling_near_normal_fallback_and_sms():
    advisory = advisory_text("corn", "tasseling", weekly_rain=15.0, dryspell_flag=False, heat_day_count=2)
    sms = sms_line("Nueva Ecija", "corn", "tasseling", weekly_rain=15.0, dryspell_flag=False, heat_day_count=2)

    assert advisory == "Conditions near normal. Proceed with planned activities and monitor updates mid-week."
    assert "Nueva Ecija: corn/tasseling: Near-normal." in sms

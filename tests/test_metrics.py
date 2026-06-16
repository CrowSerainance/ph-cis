from core.metrics import dryspell_count, heat_days, weekly_rain_mm


def test_weekly_rain_mm_sums_and_rounds_to_one_decimal_place():
    assert weekly_rain_mm([0.04, 0.05, 1.01, 2.0]) == 3.1


def test_dryspell_count_requires_five_consecutive_days_below_one_mm():
    assert dryspell_count([0.0, 0.2, 0.9, 0.99, 0.0]) == 1
    assert dryspell_count([0.0, 0.2, 1.0, 0.9, 0.0, 0.0]) == 0


def test_dryspell_count_treats_one_mm_as_wet_boundary():
    assert dryspell_count([0.0, 0.0, 0.0, 0.0, 1.0, 0.0]) == 0


def test_heat_days_counts_temperatures_at_or_above_35c_and_ignores_none():
    assert heat_days([34.9, 35.0, 35.1, None, 36.0]) == 3

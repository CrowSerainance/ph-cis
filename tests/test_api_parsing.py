import pytest
from fastapi import HTTPException

from api.app import _province_key, _slug, _validate_crop_stage


def test_slug_normalizes_whitespace_case_and_hyphens():
    assert _slug("  Nueva-  Ecija  ") == "nueva_ecija"
    assert _slug("Rice") == "rice"
    assert _slug("grain fill") == "grain_fill"


def test_province_crop_and_stage_accept_normalized_input():
    assert _province_key(" Nueva  Ecija ") == "nueva_ecija"
    assert _province_key("NUEVA-ECIJA") == "nueva_ecija"
    assert _validate_crop_stage(" Rice ", " TRANSPLANTING ") == (
        "rice",
        "transplanting",
    )


def test_unknown_province_lists_accepted_values():
    with pytest.raises(HTTPException) as exc_info:
        _province_key("Unknown")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "unknown province"
    assert "Nueva Ecija" in exc_info.value.detail["accepted_provinces"]
    assert "nueva_ecija" in exc_info.value.detail["accepted_values"]


def test_unknown_crop_lists_accepted_crops():
    with pytest.raises(HTTPException) as exc_info:
        _validate_crop_stage("banana", "nursery")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "unknown crop"
    assert exc_info.value.detail["accepted_crops"] == ["rice", "corn"]


def test_unknown_stage_lists_crop_stages():
    with pytest.raises(HTTPException) as exc_info:
        _validate_crop_stage("rice", "tasseling")

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail["error"] == "unknown stage"
    assert exc_info.value.detail["crop"] == "rice"
    assert "nursery" in exc_info.value.detail["accepted_stages"]

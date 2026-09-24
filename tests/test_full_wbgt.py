"""Forecast WBGT from daily max temperature (not hourly scan) — regression tests."""
from api.weather import (
    build_open_meteo_url,
    calculate_full_wbgt,
    calculate_wbgt,
    estimate_globe_temperature,
    process_open_meteo,
)


def test_globe_temperature_rises_with_solar():
    tg = estimate_globe_temperature(30.0, 800.0, 2.0)
    assert 40.0 <= tg <= 45.0
    assert estimate_globe_temperature(30.0, 0.0, 2.0) == 30.0
    assert estimate_globe_temperature(30.0, 800.0, 5.0) < estimate_globe_temperature(30.0, 800.0, 1.0)


def test_full_wbgt_exceeds_simplified_under_sun():
    full = calculate_full_wbgt(30.0, 50.0, 800.0, 2.0)
    simplified = calculate_wbgt(30.0, 50.0)
    assert full > simplified
    assert 32.0 <= full <= 36.0


def test_full_wbgt_formula_components():
    import math
    ta, rh = 30.0, 50.0
    ea = (rh / 100) * 6.105 * math.exp(17.27 * ta / (237.7 + ta))
    expected = 0.57 * ta + 0.32 * ea + 0.11 * ta
    assert calculate_full_wbgt(ta, rh, 0.0, 2.0) == expected


def test_url_is_daily_only():
    url = build_open_meteo_url(-1.317, 36.789)
    assert "hourly=" not in url
    assert "daily=temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean,wind_speed_10m_max,shortwave_radiation_sum" in url


def test_wbgt_from_daily_max_temperature():
    raw = {
        "daily": {
            "time": ["2026-09-24", "2026-09-25"],
            "temperature_2m_max": [30.0, 34.5],
            "temperature_2m_min": [18.0, 19.0],
            "relative_humidity_2m_mean": [60.0, 65.0],
            "wind_speed_10m_max": [12.0, 9.0],
            "shortwave_radiation_sum": [20.0, 27.0],
        },
    }
    result = process_open_meteo(raw, -1.317, 36.789)
    d1, d2 = result["daily"][0], result["daily"][1]
    # WBGT computed from the day's max temperature + mean humidity, nothing else
    assert d1["wbgt_max"] == calculate_wbgt(30.0, 60.0)
    assert d2["wbgt_max"] == calculate_wbgt(34.5, 65.0)
    assert d2["risk_tier"] == "Critical"


def test_wbgt_ignores_hourly_data_if_present():
    raw = {
        "daily": {
            "time": ["2026-09-24"],
            "temperature_2m_max": [30.0],
            "temperature_2m_min": [18.0],
            "relative_humidity_2m_mean": [60.0],
            "wind_speed_10m_max": [12.0],
            "shortwave_radiation_sum": [20.0],
        },
        "hourly": {
            "time": ["2026-09-24T13:00"],
            "temperature_2m": [35.0],
            "relative_humidity_2m": [80.0],
            "direct_radiation": [900.0],
            "wind_speed_10m": [1.0],
        },
    }
    result = process_open_meteo(raw, -1.317, 36.789)
    # Hourly 35C/80% would give a higher WBGT — must be ignored
    assert result["daily"][0]["wbgt_max"] == calculate_wbgt(30.0, 60.0)

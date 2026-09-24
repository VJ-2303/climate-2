"""Full WBGT (ACGIH outdoor formula with globe temperature) regression tests."""
from api.weather import (
    build_open_meteo_url,
    calculate_full_wbgt,
    calculate_wbgt,
    estimate_globe_temperature,
    process_open_meteo,
)


def test_globe_temperature_rises_with_solar():
    # 800 W/m2 direct sun, 2 m/s wind: globe ~12C above air (energy balance)
    tg = estimate_globe_temperature(30.0, 800.0, 2.0)
    assert 40.0 <= tg <= 45.0
    # No sun: globe equals air temp
    assert estimate_globe_temperature(30.0, 0.0, 2.0) == 30.0
    # More wind: better convection, cooler globe
    assert estimate_globe_temperature(30.0, 800.0, 5.0) < estimate_globe_temperature(30.0, 800.0, 1.0)


def test_full_wbgt_exceeds_simplified_under_sun():
    full = calculate_full_wbgt(30.0, 50.0, 800.0, 2.0)
    simplified = calculate_wbgt(30.0, 50.0)
    assert full > simplified
    # Hand check: Tg~42, ea=21.19 -> 0.57*42 + 0.32*21.19 + 0.11*30 ~ 34
    assert 32.0 <= full <= 36.0


def test_full_wbgt_formula_components():
    # Tg = Ta (no sun): WBGT = 0.57*Ta + 0.32*ea + 0.11*Ta
    import math
    ta, rh = 30.0, 50.0
    ea = (rh / 100) * 6.105 * math.exp(17.27 * ta / (237.7 + ta))
    expected = 0.57 * ta + 0.32 * ea + 0.11 * ta
    assert calculate_full_wbgt(ta, rh, 0.0, 2.0) == expected


def test_url_includes_solar_and_wind_hourly():
    url = build_open_meteo_url(-1.317, 36.789)
    assert "direct_radiation" in url
    assert "wind_speed_10m" in url
    assert "hourly=temperature_2m,relative_humidity_2m,direct_radiation,wind_speed_10m" in url


def test_process_open_meteo_uses_full_wbgt_peak():
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
            "time": ["2026-09-24T13:00", "2026-09-24T14:00"],
            "temperature_2m": [31.5, 30.0],
            "relative_humidity_2m": [70.0, 60.0],
            "direct_radiation": [750.0, 200.0],
            "wind_speed_10m": [2.0, 3.0],
        },
    }
    result = process_open_meteo(raw, -1.317, 36.789)
    day1 = result["daily"][0]
    expected_peak = calculate_full_wbgt(31.5, 70.0, 750.0, 2.0)
    assert day1["wbgt_max"] == expected_peak
    # Full (solar-loaded) peak must exceed the simplified estimate for the same hour
    assert expected_peak > calculate_wbgt(31.5, 70.0)


def test_process_open_meteo_falls_back_to_simplified_without_solar():
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
            "temperature_2m": [31.5],
            "relative_humidity_2m": [70.0],
            "direct_radiation": [None],
            "wind_speed_10m": [None],
        },
    }
    result = process_open_meteo(raw, -1.317, 36.789)
    day1 = result["daily"][0]
    assert day1["wbgt_max"] == calculate_wbgt(31.5, 70.0)

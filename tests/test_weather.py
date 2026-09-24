import pytest
from api.weather import calculate_wbgt, get_5day_forecast

def test_calculate_wbgt_formula():
    # Test realistic baseline: 30C, 60% humidity
    # e = 0.60 * 6.105 * exp(17.27 * 30 / (237.7 + 30)) = 0.60 * 6.105 * exp(1.9382) ~= 25.44 hPa
    # wbgt = 0.567 * 30 + 0.393 * 25.44 + 3.94 ~= 17.01 + 10.0 + 3.94 = 30.95 C
    wbgt = calculate_wbgt(temp_c=30.0, humidity_pct=60.0)
    assert round(wbgt, 1) == 30.9

def test_calculate_wbgt_bounds():
    # Dry heat: 35C, 20% humidity
    wbgt_dry = calculate_wbgt(temp_c=35.0, humidity_pct=20.0)
    # Humid heat: 35C, 80% humidity
    wbgt_humid = calculate_wbgt(temp_c=35.0, humidity_pct=80.0)
    assert wbgt_humid > wbgt_dry
    assert 20.0 <= wbgt_dry <= 35.0
    assert wbgt_humid >= 35.0

def test_get_5day_forecast_fallback():
    # Using forced fallback
    forecast = get_5day_forecast(lat=9.921851, lon=78.118200, force_fallback=True)
    assert "daily" in forecast
    assert len(forecast["daily"]) == 5
    first_day = forecast["daily"][0]
    assert "day" in first_day
    assert "temp_max" in first_day
    assert "temp_min" in first_day
    assert "humidity_mean" in first_day
    assert "wbgt_max" in first_day
    assert "risk_tier" in first_day
    assert "summary" in forecast
    assert "composite_alert" in forecast
    assert "timeline" in forecast

def test_process_open_meteo_uses_daytime_min_humidity():
    from api.weather import process_open_meteo
    raw = {
        "daily": {
            "time": ["2026-09-24"],
            "temperature_2m_max": [38.0],
            "temperature_2m_min": [24.0],
            "relative_humidity_2m_min": [30.0],
            "relative_humidity_2m_mean": [75.0],
            "wind_speed_10m_max": [10.0],
            "shortwave_radiation_sum": [25.0],
        }
    }
    result = process_open_meteo(raw, 9.921851, 78.118200)
    day = result["daily"][0]
    # At 38C and 30% min humidity, WBGT is ~33.2C (Moderate/High), NOT >42C (Critical)
    assert day["wbgt_max"] == calculate_wbgt(38.0, 30.0)
    assert day["wbgt_max"] < 35.0

def test_composite_heatwave_alert_escalation():
    from api.weather import get_composite_heatwave_alert
    # High temp + low humidity -> Orange alert based on IMD >= 45C
    alert1 = get_composite_heatwave_alert(temp_max=45.5, wbgt_max=32.0)
    assert alert1["alert_code"] == "ORANGE"
    assert "Orange" in alert1["alert_label"]

    # Moderate temp but extreme humid heat -> Red alert based on WBGT > 38C
    alert2 = get_composite_heatwave_alert(temp_max=37.0, wbgt_max=38.5)
    assert alert2["alert_code"] == "RED"
    assert "Red" in alert2["alert_label"]

def test_process_open_meteo_timeline():
    from api.weather import process_open_meteo
    # 12 days total: 7 historical + 5 forecast
    times = [f"2026-09-{17 + i:02d}" for i in range(12)]
    raw = {
        "daily": {
            "time": times,
            "temperature_2m_max": [32.0] * 12,
            "temperature_2m_min": [22.0] * 12,
            "relative_humidity_2m_min": [35.0] * 12,
            "relative_humidity_2m_mean": [60.0] * 12,
            "wind_speed_10m_max": [10.0] * 12,
            "shortwave_radiation_sum": [20.0] * 12,
        }
    }
    result = process_open_meteo(raw, 9.921851, 78.118200)
    assert len(result["timeline"]) == 12
    assert len(result["daily"]) == 5
    assert result["timeline"][0]["phase"] == "historical"
    assert result["timeline"][-1]["phase"] == "forecast"
    assert "composite_alert" in result

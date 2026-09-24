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

# Testing Patterns

**Analysis Date:** 2026-09-24

## Test Framework

**Runner:**
- Pytest (>=9.1.1)
- Root configuration: `conftest.py` ensures the project root directory is placed on `sys.path` so tests can import application modules (`api.main`, `api.rules`, `api.weather`).

**Client & Mocking Tools:**
- `fastapi.testclient.TestClient` - In-memory synchronous HTTP request client for FastAPI testing.
- `httpx` (>=0.28.1) - Transport backing `TestClient`.
- Standard library `unittest.mock` (`patch`, `MagicMock`) for mocking Open-Meteo external HTTP responses and cache invalidation.

**Run Commands:**
```bash
# Run all tests with concise output
uv run pytest tests/ -q

# Run all tests with standard verbosity
uv run pytest tests/

# Run a specific test suite
uv run pytest tests/test_forecast_api.py

# Run a single test case
uv run pytest tests/test_ui_and_alerts.py -k test_sms_alert_dispatch_endpoint
```

## Test File Organization

**Location:**
- Dedicated `tests/` directory at the project root.

**Structure:**
```
tests/
├── test_forecast_api.py   # Forecast API endpoint schemas and WBGT response structures
├── test_full_wbgt.py      # Wet-bulb globe temperature physics and formula validation
├── test_gap_fixes.py      # Spatial data edge cases, inpainting, and normalization
├── test_health_risk.py    # Health risk tier assignment and sector intelligence rules
├── test_shap.py           # SHAP explainability structure and top-3 attributions
├── test_ui_and_alerts.py  # SMS dispatch simulation and API responses
└── test_weather.py        # Weather URL construction, 1h cache, and fallback handling
```

## Test Structure & Patterns

**1. FastAPI Endpoint Testing Pattern (`tests/test_forecast_api.py`, `tests/test_ui_and_alerts.py`):**
```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_forecast_days_endpoint():
    response = client.get("/api/forecast/days")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert len(data["days"]) == 5
    for day in data["days"]:
        assert "day" in day
        assert "wbgt_max" in day
        assert "risk_tier" in day
        assert day["risk_tier"] in ["Low", "Medium", "High", "Critical"]
```

**2. Scientific / Physics Formula Unit Testing (`tests/test_full_wbgt.py`):**
```python
from api.weather import calculate_full_wbgt, estimate_globe_temperature

def test_wbgt_sun_vs_shade():
    # Outdoor WBGT in direct sun should exceed shaded WBGT under high solar radiation
    temp = 38.0
    rh = 55.0
    wind = 1.5
    sun_rad = 800.0  # W/m2 direct radiation
    shade_rad = 100.0

    wbgt_sun = calculate_full_wbgt(temp, rh, sun_rad, wind)
    wbgt_shade = calculate_full_wbgt(temp, rh, shade_rad, wind)
    assert wbgt_sun > wbgt_shade
```

**3. Deterministic Intelligence Profile Testing (`tests/test_health_risk.py`):**
```python
from api.rules import build_block_intelligence

def test_block_intelligence_structure():
    mock_props = {
        "block_id": "KIB-0001",
        "hvi_score": 75,
        "risk_class": "High",
        "surface_temp_celsius": 42.1,
        "temp_anomaly_celsius": 3.2,
        "building_density": 65,
        "ndvi": 20,
        "distance_to_water": 800,
        "distance_to_green": 600,
        "population_density": 80,
        "estimated_population": 450,
    }
    intel = build_block_intelligence("KIB-0001", mock_props, [75], {}, {}, { "KIB-0001": mock_props }, [])
    assert intel["risk_class"] == "High"
    assert "headline" in intel
    assert "why_hot_causes" in intel
    assert "required_controls" in intel
```

## Mocking & Isolation

**External Network Isolation:**
- External Open-Meteo weather calls are isolated in `tests/test_weather.py` using `unittest.mock.patch("urllib.request.urlopen")` to verify fallback handling without requiring live internet access.
- Tests verify that if network requests raise an error, the system successfully falls back to `data/fallback_forecast.json` without failing.

## Current Test Status

- **Total Test Cases:** 28 automated tests across 7 test suites
- **Execution Speed:** ~14 seconds
- **Pass Rate:** 100% (28 passed)

---

*Testing analysis: 2026-09-24*
*Update after adding test suites*

"""Gap-fix regression tests: align implementation with IMPLEMENTATION_PLAN.md spec."""
import json
import os

from fastapi.testclient import TestClient

from api.main import app
from api.rules import evaluate_5day_health_trajectory
from api.weather import calculate_wbgt, classify_wbgt_risk, get_5day_forecast

client = TestClient(app)

MOCK_FORECAST = {
    "daily": [
        {"day": 1, "date": "2026-09-24", "wbgt_max": 29.0},
        {"day": 2, "date": "2026-09-25", "wbgt_max": 30.5},
        {"day": 3, "date": "2026-09-26", "wbgt_max": 32.5},
        {"day": 4, "date": "2026-09-27", "wbgt_max": 31.0},
        {"day": 5, "date": "2026-09-28", "wbgt_max": 28.0},
    ]
}


# --- Slice 1: Plan 3.1 tier thresholds — Critical: WBGT > 32C ---

def test_critical_threshold_is_32():
    assert classify_wbgt_risk(32.1) == "Critical"
    assert classify_wbgt_risk(32.0) == "High"
    assert classify_wbgt_risk(30.0) == "High"
    assert classify_wbgt_risk(29.9) == "Moderate"
    assert classify_wbgt_risk(28.0) == "Moderate"
    assert classify_wbgt_risk(27.9) == "Low"


def test_trajectory_critical_threshold_is_32():
    props = {"block_id": "KIB-0001", "temp_anomaly_celsius": 0.0, "population_density": 50, "building_density": 50}
    traj = evaluate_5day_health_trajectory(props, {"daily": [{"day": 1, "date": "d", "wbgt_max": 32.1}]})
    assert traj[0]["health_risk_tier"] == "Critical"


# --- Slice 2: Plan 3.1 — modulate tier by social sensitivity (pop + metal roofs) ---

def test_tier_modulated_by_social_sensitivity():
    # High social sensitivity (pop 90, building 90 -> 0.7*90+0.3*90 = 90 >= 70) bumps tier up one level
    high_sens = {"block_id": "KIB-0001", "temp_anomaly_celsius": 0.0, "population_density": 90, "building_density": 90}
    low_sens = {"block_id": "KIB-0002", "temp_anomaly_celsius": 0.0, "population_density": 20, "building_density": 20}

    traj_high = evaluate_5day_health_trajectory(high_sens, MOCK_FORECAST)
    traj_low = evaluate_5day_health_trajectory(low_sens, MOCK_FORECAST)

    # Day 1: wbgt 29.0 -> base tier Moderate. High sensitivity must bump to High; low stays Moderate.
    assert traj_high[0]["health_risk_tier"] == "High"
    assert traj_low[0]["health_risk_tier"] == "Moderate"

    # Bump never exceeds Critical
    assert all(t["health_risk_tier"] in ("Low", "Moderate", "High", "Critical") for t in traj_high)


# --- Slice 3: Plan 1.2 — fallback peak day 34.5C / 65% humidity ---

def test_fallback_peak_scenario():
    fb = get_5day_forecast(force_fallback=True)
    daily = fb["daily"]
    peak = max(daily, key=lambda d: d["temp_max"])
    assert peak["temp_max"] == 34.5
    assert peak["humidity_mean"] == 65.0
    # Peak day WBGT must be consistent with the formula and Critical tier
    assert peak["wbgt_max"] == calculate_wbgt(34.5, 65.0)
    assert peak["risk_tier"] == "Critical"


# --- Slice 4: Plan 2.3 — top 3 SHAP contributions in block payload ---

def test_block_payload_shap_top3():
    res = client.get("/api/blocks/KIB-0001")
    assert res.status_code == 200
    factors = res.json()["shap_factors"]
    assert len(factors) == 3


# --- Slice 5: Plan 2.3 — SHAP integrated into 07_score_export output ---

def test_vulnerability_blocks_have_shap_top_factors():
    path = "data/output/vulnerability_blocks.geojson"
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    feats = data["features"]
    assert len(feats) > 0
    for feat in feats[:20]:
        props = feat["properties"]
        assert "shap_top_factors" in props, f"{props['block_id']} missing shap_top_factors"
        assert len(props["shap_top_factors"]) == 3
        assert "name" in props["shap_top_factors"][0]
        assert "contribution_celsius" in props["shap_top_factors"][0]


# --- Slice 6: Plan 1.1 — hourly metrics from Open-Meteo ---

def test_open_meteo_url_includes_hourly():
    from api.weather import build_open_meteo_url
    url = build_open_meteo_url(-1.317, 36.789)
    assert "hourly=temperature_2m,relative_humidity_2m" in url
    assert "daily=temperature_2m_max" in url


def test_process_open_meteo_uses_hourly_peak_wbgt():
    from api.weather import process_open_meteo
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
        },
    }
    result = process_open_meteo(raw, -1.317, 36.789)
    day1 = result["daily"][0]
    # Hourly peak WBGT (13:00, 31.5C/70%) must exceed daily-approx WBGT (30C/60%)
    expected_peak = calculate_wbgt(31.5, 70.0)
    assert day1["wbgt_max"] == expected_peak
    assert expected_peak > calculate_wbgt(30.0, 60.0)


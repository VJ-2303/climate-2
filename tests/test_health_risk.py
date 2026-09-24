from fastapi.testclient import TestClient
from api.main import app
from api.rules import evaluate_5day_health_trajectory, generate_automated_health_advisory

client = TestClient(app)

def test_evaluate_5day_health_trajectory():
    props = {
        "block_id": "KIB-0001",
        "temp_anomaly_celsius": 1.5,
        "population_density": 80,
        "building_density": 85,
    }
    mock_forecast = {
        "daily": [
            {"day": 1, "date": "2026-09-24", "wbgt_max": 29.0},
            {"day": 2, "date": "2026-09-25", "wbgt_max": 30.5},
            {"day": 3, "date": "2026-09-26", "wbgt_max": 38.0},
            {"day": 4, "date": "2026-09-27", "wbgt_max": 31.0},
            {"day": 5, "date": "2026-09-28", "wbgt_max": 28.0},
        ]
    }
    traj = evaluate_5day_health_trajectory(props, mock_forecast)
    assert len(traj) == 5
    assert traj[0]["day"] == 1
    # Day 3 base wbgt 38.0 + anomaly 1.5 * 0.4 = 38.6 => Critical (> 38.0)
    assert traj[2]["local_wbgt"] == 38.6
    assert traj[2]["health_risk_tier"] == "Critical"
    assert "risk_score" in traj[2]
    assert "advisory" in traj[2]

def test_generate_automated_health_advisory():
    shap_factors = [
        {"name": "Corrugated Metal Roofs & Built Cover (NDBI)", "contribution_celsius": "+1.8°C"}
    ]
    advisory = generate_automated_health_advisory(
        block_id="KIB-0001",
        local_wbgt=33.2,
        shap_factors=shap_factors,
        risk_tier="Critical"
    )
    assert "headline" in advisory
    assert "citizen_action" in advisory
    assert "officer_directive" in advisory
    assert "Corrugated Metal Roofs" in advisory["officer_directive"]

def test_day_layer_attributes_endpoint():
    for day in range(1, 6):
        res = client.get(f"/api/layers/forecast_day_{day}/attributes")
        assert res.status_code == 200
        data = res.json()
        assert "KIB-0001" in data
        assert isinstance(data["KIB-0001"], (int, float))

def test_block_intelligence_includes_health_trajectory():
    res = client.get("/api/blocks/KIB-0001")
    assert res.status_code == 200
    payload = res.json()
    assert "forecast_trajectory" in payload
    assert len(payload["forecast_trajectory"]) == 5
    assert "automated_advisory" in payload

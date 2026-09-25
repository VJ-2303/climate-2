import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.rules import (
    classify_land_cover,
    select_ecological_species,
    calculate_intervention_sizing,
    evaluate_neighborhood_context,
    evaluate_microclimate_diagnosis,
    format_humanized_factors,
    evaluate_5day_health_trajectory,
    generate_automated_health_advisory,
    build_block_intelligence,
    calculate_percentile,
)

client = TestClient(app)

def test_calculate_percentile():
    scores = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    assert calculate_percentile(50, scores) == 50
    assert calculate_percentile(5, scores) == 1
    assert calculate_percentile(105, scores) == 99

def test_classify_land_cover_archetypes():
    # 1. High density commercial / residential
    archetype, desc = classify_land_cover({"estimated_population": 80, "building_density": 60})
    assert archetype == "High-Density Commercial & Residential Cluster"

    # 2. Dense built-up settlement
    archetype, desc = classify_land_cover({"building_density": 55, "ndbi": 70, "estimated_population": 20})
    assert archetype == "Dense Built-up Area"

    # 3. Riparian wetland
    archetype, desc = classify_land_cover({"distance_to_water": 40, "ndvi": 60, "building_density": 10})
    assert archetype == "Riparian Wetland & Alluvial Green Corridor"

    # 4. High canopy green buffer
    archetype, desc = classify_land_cover({"ndvi": 75, "building_density": 10})
    assert archetype == "High-Canopy Agroforestry & Green Buffer"

    # 5. Exposed open ground
    archetype, desc = classify_land_cover({"ndvi": 20, "building_density": 15})
    assert archetype == "Exposed Open Ground & Pathways"

def test_select_ecological_species_by_zone():
    # Near water
    spec_water = select_ecological_species({"distance_to_water": 100, "building_density": 20})
    assert "Marudham" in spec_water["primary_species"]
    assert "Jamun" in spec_water["primary_species"]

    # Dense urban
    spec_dense = select_ecological_species({"distance_to_water": 300, "building_density": 50})
    assert "Pungan" in spec_dense["primary_species"]
    assert "Magizham" in spec_dense["primary_species"]

    # Open thoroughfare
    spec_open = select_ecological_species({"distance_to_water": 400, "building_density": 15})
    assert "Neem" in spec_open["primary_species"]
    assert "Vagai" in spec_open["primary_species"]

def test_calculate_intervention_sizing():
    props = {
        "building_density": 40,
        "ndvi": 20,
        "ai_heat_exposure": 70,
    }
    sizing = calculate_intervention_sizing(props)
    assert sizing["sector_footprint_sqm"] == 2500
    assert sizing["estimated_roof_sqm"] == 1000
    assert sizing["cool_roof_paint_liters"] == 110
    assert sizing["trees_to_target_canopy"] >= 3

def test_evaluate_neighborhood_context():
    block_to_grid = {"B1": (0, 0)}
    grid_to_block = {
        (0, 0): "B1",
        (-1, 0): "N1",
        (1, 0): "N2",
        (0, -1): "N3",
        (0, 1): "N4",
        (-1, -1): "N5",
    }
    # 5 hot neighbors => Thermal Canyon
    blocks_db = {
        "B1": {"ai_heat_exposure": 75},
        "N1": {"ai_heat_exposure": 70, "hvi_score": 75},
        "N2": {"ai_heat_exposure": 65, "hvi_score": 70},
        "N3": {"ai_heat_exposure": 60, "hvi_score": 68},
        "N4": {"ai_heat_exposure": 72, "hvi_score": 74},
        "N5": {"ai_heat_exposure": 80, "hvi_score": 82},
    }
    ctx = evaluate_neighborhood_context("B1", blocks_db["B1"], block_to_grid, grid_to_block, blocks_db)
    assert "Thermal Canyon Corridor" in ctx

def test_evaluate_microclimate_diagnosis_and_factors():
    props = {
        "ai_heat_exposure": 75,
        "hvi_score": 78,
        "ndvi": 25,
        "ndbi": 65,
        "building_density": 50,
        "estimated_population": 45,
        "distance_to_water": 350,
        "distance_to_green": 300,
        "cooling_deficit": 70,
        "population_density": 65,
    }
    diag = evaluate_microclimate_diagnosis(props)
    assert diag["is_thermally_hot"] is True
    assert diag["surface_temp_celsius"] > 50.0
    assert len(diag["why_hot_causes"]) >= 2
    assert len(diag["required_controls"]) >= 2

    factors = format_humanized_factors(props, diag["surface_temp_celsius"], diag["temp_anomaly_celsius"])
    assert len(factors) == 5
    ids = [f["id"] for f in factors]
    assert "surface_temperature" in ids
    assert "greenery" in ids
    assert "built_surfaces" in ids
    assert "cooling_access" in ids
    assert "crowding" in ids

def test_bilingual_advisory_with_shap_injection():
    shap_factors = [
        {"name": "Built-up / Impervious Surface (NDBI)", "contribution_celsius": "+2.4°C"}
    ]
    advisory = generate_automated_health_advisory(
        block_id="KIB-TEST",
        local_wbgt=39.5,
        shap_factors=shap_factors,
        risk_tier="Critical"
    )
    # Check English
    assert "CRITICAL HEAT EMERGENCY" in advisory["headline"]
    assert "Built-up / Impervious Surface (NDBI) (+2.4°C)" in advisory["officer_directive"]
    # Check Tamil
    assert "அதிதீவிர வெப்ப அவசரநிலை" in advisory["headline_ta"]
    assert "முக்கிய காரணி: Built-up / Impervious Surface (NDBI) (+2.4°C)" in advisory["officer_directive_ta"]

def test_api_block_endpoint_integrates_rules_and_shap():
    res = client.get("/api/blocks/KIB-0001")
    assert res.status_code == 200
    data = res.json()

    # Verify SHAP presence and accuracy
    assert "shap_factors" in data
    assert len(data["shap_factors"]) > 0
    top_shap = data["shap_factors"][0]
    assert "name" in top_shap
    assert "contribution_celsius" in top_shap
    assert "shap_base_temp" in data

    # Verify Rules intelligence outputs
    assert "land_cover_type" in data
    assert "why_hot_causes" in data
    assert "required_controls" in data
    assert "sizing" in data
    assert "cool_roof_paint_liters" in data["sizing"]
    assert "species_guidance" in data
    assert "forecast_trajectory" in data
    assert len(data["forecast_trajectory"]) == 5
    assert "automated_advisory" in data
    assert "headline_ta" in data["automated_advisory"]
    assert "factors" in data
    assert len(data["factors"]) == 5

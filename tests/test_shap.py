import os
import json
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_block_shap_explanations_file_format():
    shap_path = "data/processed/block_shap_explanations.json"
    assert os.path.exists(shap_path), f"{shap_path} should exist"
    
    with open(shap_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    assert "KIB-0001" in data
    block = data["KIB-0001"]
    assert "base_value" in block
    assert "factors" in block
    assert len(block["factors"]) > 0
    first_factor = block["factors"][0]
    assert "feature" in first_factor
    assert "name" in first_factor
    assert "shap_value" in first_factor
    assert "contribution_celsius" in first_factor

def test_api_block_intelligence_includes_shap():
    response = client.get("/api/blocks/KIB-0001")
    assert response.status_code == 200
    payload = response.json()
    assert "shap_factors" in payload
    assert isinstance(payload["shap_factors"], list)
    assert len(payload["shap_factors"]) > 0
    factor = payload["shap_factors"][0]
    assert "name" in factor
    assert "contribution_celsius" in factor

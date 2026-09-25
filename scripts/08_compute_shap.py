"""
Stage 08: Precompute SHAP Explainability for All 18,040 Blocks (SIH26083)
Uses TreeExplainer on Module 1 XGBoost to compute exact feature attributions for temperature anomalies.
"""

import os
import sys
import json
import numpy as np
import pandas as pd
import geopandas as gpd
from xgboost import XGBRegressor
import shap

FEATURE_COLS = [
    "mean_ndvi",
    "mean_ndwi",
    "mean_ndbi",
    "mean_building_density",
    "mean_road_density",
    "mean_distance_to_green",
    "mean_distance_to_water",
    "mean_population_density",
]

FEATURE_LABELS = {
    "mean_ndvi": "Tree Canopy & Vegetation (NDVI)",
    "mean_ndwi": "Surface Moisture & Water (NDWI)",
    "mean_ndbi": "Built-up / Impervious Surface (NDBI)",
    "mean_building_density": "Building Footprint Density",
    "mean_road_density": "Unshaded Path/Road Density",
    "mean_distance_to_green": "Distance to Vegetated Buffers",
    "mean_distance_to_water": "Distance to Water/Drainage Corridors",
    "mean_population_density": "Resident Demographic Density",
}

def main():
    print("Stage 08: Computing SHAP Feature Contributions...")
    
    model_path = "models/module1_xgb.json"
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        sys.exit(1)
        
    madurai_path = "data/processed/madurai_blocks_50m.geojson"
    if not os.path.exists(madurai_path):
        print(f"Error: {madurai_path} not found.")
        sys.exit(1)

    # 1. Load model and block table
    model = XGBRegressor()
    model.load_model(model_path)
    
    gdf = gpd.read_file(madurai_path)
    print(f"Loaded {len(gdf)} blocks for SHAP analysis.")
    
    X = gdf[FEATURE_COLS].copy()
    block_ids = gdf["block_id"].values
    
    # 2. Compute SHAP values with TreeExplainer
    print("Initializing TreeExplainer and calculating Shapley values...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X)
    
    base_val = float(explainer.expected_value) if hasattr(explainer, "expected_value") else 28.7
    print(f"Base expected temperature: {base_val:.2f}°C")
    
    # 3. Format per-block explanation entries
    explanations = {}
    for i, bid in enumerate(block_ids):
        row_shap = shap_values[i]
        
        # Sort factors by absolute impact descending
        factors = []
        for j, col in enumerate(FEATURE_COLS):
            val = float(row_shap[j])
            sign = "+" if val >= 0 else ""
            factors.append({
                "feature": col,
                "name": FEATURE_LABELS.get(col, col),
                "shap_value": round(val, 2),
                "contribution_celsius": f"{sign}{val:.2f}°C",
                "abs_impact": abs(val)
            })
            
        factors.sort(key=lambda x: x["abs_impact"], reverse=True)
        # Clean temporary sort key
        for f in factors:
            del f["abs_impact"]
            
        explanations[bid] = {
            "block_id": bid,
            "base_value": round(base_val, 2),
            "factors": factors[:5] # Top 5 primary drivers
        }
        
    out_path = "data/processed/block_shap_explanations.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(explanations, f)
        
    print(f"STAGE 8 SHAP: PASS | blocks: {len(explanations)} | artifact: {out_path}")

if __name__ == "__main__":
    main()

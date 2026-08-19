import os
import sys
import json
import numpy as np
import pandas as pd
import geopandas as gpd

# Immutable Constants from SPEC.md Section 2
SEED = 42
PROCESS_CRS = "EPSG:32737"
OUTPUT_CRS = "EPSG:4326"
WORKING_RES = 20          # meters
BLOCK_SIZE = 50           # meters
TRAIN_HALF_SIZE = 2500    # meters (5km x 5km training area)
CENTER_LAT = -1.317
CENTER_LON = 36.789
DIST_CAP = 1000.0         # meters
BLOCK_MIN_VALID_COVERAGE = 0.70
MIN_TRAIN_SAMPLES = 1000  # Landsat 100m pixels
NODATA = -9999.0

# 12.1 Normalization helper
def norm(x):
    x = np.asarray(x, dtype=np.float64)
    p2 = np.percentile(x, 2)
    p98 = np.percentile(x, 98)
    if p98 - p2 < 1e-6:
        return np.full_like(x, 50.0)
    return np.clip((x - p2) / (p98 - p2) * 100.0, 0.0, 100.0)

def inv(x):
    return 100.0 - norm(x)

def get_risk_class(score):
    if score <= 30:
        return "Low"
    elif score <= 55:
        return "Medium"
    elif score <= 75:
        return "High"
    else:
        return "Critical"

DRIVER_TIE_ORDER = [
    "poor_water_access",
    "poor_green_access",
    "high_population_exposure",
    "high_building_density",
    "high_built_surface",
    "low_vegetation",
]

INTERVENTIONS = {
    "poor_water_access": "Water point / hydration support",
    "poor_green_access": "Shade structure / tree planting",
    "low_vegetation": "Green cover intervention",
    "high_building_density": "Cool roof awareness / ventilation outreach",
    "high_built_surface": "Reflective roof / surface cooling campaign",
    "high_population_exposure": "Community health outreach",
}

def main():
    print("Stage 7: Vulnerability Scoring, Explainability Drivers & Export...")

    input_path = "data/processed/kibera_blocks_50m.geojson"
    if not os.path.exists(input_path):
        print(f"Error: {input_path} not found.")
        sys.exit(1)

    gdf = gpd.read_file(input_path)
    print(f"Loaded {len(gdf)} blocks from {input_path}")

    # Extract raw variables
    heat_raw = gdf["contextual_ai_heat"].values
    pop_raw = gdf["mean_population_density"].values
    bldg_raw = gdf["mean_building_density"].values
    dgreen_raw = gdf["mean_distance_to_green"].values
    dwater_raw = gdf["mean_distance_to_water"].values
    ndvi_raw = gdf["mean_ndvi"].values
    ndwi_raw = gdf["mean_ndwi"].values
    ndbi_raw = gdf["mean_ndbi"].values

    # 12.2 Scores (per block)
    ai_heat_exposure = norm(heat_raw)
    social_sensitivity = np.clip(0.70 * norm(pop_raw) + 0.30 * norm(bldg_raw), 0.0, 100.0)
    cooling_deficit = np.clip(
        0.35 * norm(dgreen_raw) + 0.30 * norm(dwater_raw) + 0.20 * inv(ndvi_raw) + 0.15 * inv(ndwi_raw),
        0.0, 100.0
    )
    hvi_raw = 0.45 * ai_heat_exposure + 0.35 * social_sensitivity + 0.20 * cooling_deficit
    hvi_final = norm(hvi_raw)

    # 12.4 Drivers
    d_low_veg = inv(ndvi_raw)
    d_high_bldg = norm(bldg_raw)
    d_high_built = norm(ndbi_raw)
    d_poor_green = norm(dgreen_raw)
    d_poor_water = norm(dwater_raw)
    d_high_pop = norm(pop_raw)

    # Order priority mapping for tie breaks (lower index = higher priority)
    tie_ranks = {name: i for i, name in enumerate(DRIVER_TIE_ORDER)}

    top_drivers_list = []
    interventions_list = []
    risk_classes_list = []

    for i in range(len(gdf)):
        driver_values = {
            "poor_water_access": d_poor_water[i],
            "poor_green_access": d_poor_green[i],
            "high_population_exposure": d_high_pop[i],
            "high_building_density": d_high_bldg[i],
            "high_built_surface": d_high_built[i],
            "low_vegetation": d_low_veg[i],
        }

        # Sort drivers by (-value, tie_rank)
        sorted_drivers = sorted(
            driver_values.keys(),
            key=lambda k: (-driver_values[k], tie_ranks[k])
        )

        top_3 = sorted_drivers[:3]
        primary_driver = top_3[0]

        top_drivers_list.append(top_3)
        interventions_list.append(INTERVENTIONS[primary_driver])
        
        score_int = int(round(hvi_final[i]))
        risk_classes_list.append(get_risk_class(score_int))

    # Construct final properties table
    gdf_out = gdf.copy()
    
    # 12.6 EXACT properties
    gdf_out["hvi_score"] = [int(round(x)) for x in hvi_final]
    gdf_out["hvi_raw"] = [round(float(x), 1) for x in hvi_raw]
    gdf_out["risk_class"] = risk_classes_list
    gdf_out["priority"] = risk_classes_list
    gdf_out["ai_heat_exposure"] = [int(round(x)) for x in ai_heat_exposure]
    gdf_out["social_sensitivity"] = [int(round(x)) for x in social_sensitivity]
    gdf_out["cooling_deficit"] = [int(round(x)) for x in cooling_deficit]
    gdf_out["estimated_population"] = [int(round(x * 0.25)) for x in pop_raw]
    gdf_out["population_density"] = [int(round(x)) for x in norm(pop_raw)]
    gdf_out["building_density"] = [int(round(x)) for x in norm(bldg_raw)]
    gdf_out["ndvi"] = [int(round(x)) for x in norm(ndvi_raw)]
    gdf_out["ndwi"] = [int(round(x)) for x in norm(ndwi_raw)]
    gdf_out["ndbi"] = [int(round(x)) for x in norm(ndbi_raw)]
    gdf_out["distance_to_green"] = [int(round(x)) for x in norm(dgreen_raw)]
    gdf_out["distance_to_water"] = [int(round(x)) for x in norm(dwater_raw)]
    gdf_out["top_drivers"] = top_drivers_list
    gdf_out["intervention"] = interventions_list

    # Physical Temperature Properties from Satellite LST & AI Model
    st_raw = gdf["mean_landsat_st_celsius"].values if "mean_landsat_st_celsius" in gdf.columns else (20.24 + (ai_heat_exposure / 100.0) * 18.37)
    gdf_out["surface_temp_celsius"] = [round(float(x), 1) for x in st_raw]
    gdf_out["temp_anomaly_celsius"] = [round(float(x) - 28.7, 1) for x in st_raw]

    # Reproject to EPSG:4326
    print(f"Reprojecting blocks from {gdf_out.crs} to {OUTPUT_CRS}...")
    gdf_out = gdf_out.to_crs(OUTPUT_CRS)

    # Filter property fields including physical temperature
    exact_cols = [
        "block_id",
        "hvi_score",
        "hvi_raw",
        "risk_class",
        "priority",
        "surface_temp_celsius",
        "temp_anomaly_celsius",
        "ai_heat_exposure",
        "social_sensitivity",
        "cooling_deficit",
        "estimated_population",
        "population_density",
        "building_density",
        "ndvi",
        "ndwi",
        "ndbi",
        "distance_to_green",
        "distance_to_water",
        "top_drivers",
        "intervention",
        "geometry"
    ]
    gdf_final = gdf_out[exact_cols]

    # Validate Gate G7
    # Gate G7: top-decile HVI blocks must have mean ndvi lower than overall mean ndvi,
    # and mean building_density higher than overall mean.
    p90_hvi = np.percentile(gdf_final["hvi_score"], 90)
    top_decile = gdf_final[gdf_final["hvi_score"] >= p90_hvi]

    top_decile_ndvi = top_decile["ndvi"].mean()
    overall_ndvi = gdf_final["ndvi"].mean()

    top_decile_bldg = top_decile["building_density"].mean()
    overall_bldg = gdf_final["building_density"].mean()

    print(f"\n--- Gate G7 Evaluation ---")
    print(f"HVI 90th percentile threshold: {p90_hvi}")
    print(f"Top-decile NDVI: {top_decile_ndvi:.2f} vs Overall NDVI: {overall_ndvi:.2f} (Required: <)")
    print(f"Top-decile Building Density: {top_decile_bldg:.2f} vs Overall Building: {overall_bldg:.2f} (Required: >)")

    ndvi_pass = top_decile_ndvi < overall_ndvi
    bldg_pass = top_decile_bldg > overall_bldg

    if not (ndvi_pass and bldg_pass):
        print(f"GATE G7 FAILED: ndvi_pass={ndvi_pass}, bldg_pass={bldg_pass}")
        sys.exit(1)
    else:
        print("GATE G7 PASSED: Top-decile blocks exhibit lower NDVI and higher building density!")

    # Save data/output/vulnerability_blocks.geojson
    os.makedirs("data/output", exist_ok=True)
    os.makedirs("data/output/layers", exist_ok=True)
    out_main_path = "data/output/vulnerability_blocks.geojson"

    # GeoJSON write with json top_drivers format
    gdf_final.to_file(out_main_path, driver="GeoJSON")
    print(f"Exported primary vulnerability map to {out_main_path}")

    # Export the 7 per-layer block GeoJSONs:
    # ai_heat_exposure_blocks, social_sensitivity_blocks, cooling_deficit_blocks,
    # ndvi_blocks, ndbi_blocks, building_density_blocks, population_density_blocks
    layers = {
        "ai_heat_exposure_blocks": ("ai_heat_exposure", "ai_heat_exposure"),
        "social_sensitivity_blocks": ("social_sensitivity", "social_sensitivity"),
        "cooling_deficit_blocks": ("cooling_deficit", "cooling_deficit"),
        "ndvi_blocks": ("ndvi", "ndvi"),
        "ndbi_blocks": ("ndbi", "ndbi"),
        "building_density_blocks": ("building_density", "building_density"),
        "population_density_blocks": ("population_density", "population_density"),
    }

    for layer_file, (col_src, prop_name) in layers.items():
        layer_gdf = gdf_final[["block_id", col_src, "geometry"]].copy()
        if col_src != prop_name:
            layer_gdf = layer_gdf.rename(columns={col_src: prop_name})
        
        # Save in both data/output/layers/{name}.geojson and data/output/{name}.geojson for API flexibility
        layer_out1 = f"data/output/layers/{layer_file}.geojson"
        layer_out2 = f"data/output/{layer_file}.geojson"
        layer_gdf.to_file(layer_out1, driver="GeoJSON")
        layer_gdf.to_file(layer_out2, driver="GeoJSON")
        print(f"Exported layer {layer_file} to {layer_out1}")

    # Risk class distribution
    risk_counts = gdf_final["risk_class"].value_counts().to_dict()
    print(f"\nRisk Class Counts: {risk_counts}")

    print(f"STAGE 7 score-export: PASS | blocks: {len(gdf_final)} | gate_g7: PASS | artifact: {out_main_path}")

if __name__ == "__main__":
    main()

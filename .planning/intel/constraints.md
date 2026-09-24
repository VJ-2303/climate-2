# Ingested Constraints

## CON-01: Immutable Pipeline Constants
- source: `AGENTS.md` / `SPEC.md §2`
- type: technical-constraint
- content:
  - `SEED = 42`
  - `PROCESS_CRS = "EPSG:32643"` (UTM Zone 43N)
  - `OUTPUT_CRS = "EPSG:4326"` (WGS84)
  - `WORKING_RES = 20` (meters)
  - `BLOCK_SIZE = 50` (meters)
  - `TRAIN_HALF_SIZE = 2500` (5km × 5km training window)
  - `CENTER_LAT = 9.921851`
  - `CENTER_LON = 78.118200`
  - `DIST_CAP = 1000.0` (meters)
  - `BLOCK_MIN_VALID_COVERAGE = 0.70`
  - `MIN_TRAIN_SAMPLES = 1000`
  - `NODATA = -9999.0`

## CON-02: Quantitative Pipeline Quality Gates
- source: `AGENTS.md` / `SPEC.md §3`
- type: validation-contract
- content:
  - Gate G1 (`01_build_blocks.py`): Valid blocks >= 500
  - Gate G2 & G3 (`02_train_module1.py`): Training pixels >= 1000; Validation R² >= 0.25 AND MAE <= 1.5°C
  - Gate G4 (`03_infer_module1.py`): Cell-mean difference <= 0.01°C
  - Gate G5 (`05_train_module2.py`): Validation Pearson correlation >= 0.90
  - Gate G6 (`06_infer_module2.py`): Standard deviation of `contextual_ai_heat` >= 5.0
  - Gate G7 (`07_score_export.py`): Top-decile HVI blocks have lower mean NDVI and higher building density than overall settlement mean

## CON-03: GeoJSON Export Schema Contract
- source: `AGENTS.md`
- type: api-contract
- content: Output feature properties in `data/output/vulnerability_blocks.geojson` must contain exact property keys:
  `block_id`, `risk_class`, `hvi_score`, `hvi_raw`, `ai_heat_exposure`, `social_sensitivity`, `cooling_deficit`, `surface_temp_celsius`, `temp_anomaly_celsius`, `estimated_population`, `priority`, `top_drivers`, `intervention`, `shap_top_factors`, `distance_to_water`, `distance_to_green`, `ndvi`, `ndwi`, `ndbi`, `building_density`, `population_density`, `geometry`

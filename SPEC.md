# SPEC.md

```markdown
# HeatViz Technical Specification (SPEC.md)

This document is the single source of truth for implementing HeatViz.
An AI coding agent must implement EXACTLY what is written here.
No interpretation, no substitution, no fallback logic, no alternative architecture.

---

## 1. Project Definition

HeatViz produces a block-level (50m x 50m) heat vulnerability map for Kibera, Nairobi.

Pipeline summary:

1. Load processed 20m rasters.
2. Build 50m block grid inside Kibera boundary.
3. Train Module 1 (Gradient Boosted Regression) at 100m, infer at 20m, bias-correct.
4. Build block graph, train Module 2 (Graph Attention Network), infer contextual heat.
5. Compute Heat Vulnerability Index (HVI), drivers, interventions.
6. Export GeoJSON, serve via FastAPI, render via Leaflet.

---

## 2. Immutable Constants

```python
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
```

These values MUST NOT be changed.

---

## 3. Input Data Contract (data/processed/)

All rasters: CRS EPSG:32737, 20m pixels, identical shape and transform.
The agent MUST assert identical shape/transform for all 9 rasters at startup.

| File | Meaning | Valid Range | Nodata |
|---|---|---|---|
| ndvi.tif | Vegetation index | [-1, 1] | -9999 |
| ndwi.tif | Water index | [-1, 1] | -9999 |
| ndbi.tif | Built-up index | [-1, 1] | -9999 |
| landsat_st_celsius.tif | Surface temperature (Celsius) | [10, 55] | -9999 |
| building_density.tif | Building coverage fraction | [0, 1] | 0 is valid |
| road_density.tif | Road coverage fraction | [0, 1] | 0 is valid |
| distance_to_green.tif | Meters to nearest green space | [0, 1000] | -9999 |
| distance_to_water.tif | Meters to nearest water | [0, 1000] | -9999 |
| population_density_20m.tif | People per hectare | [0, inf) | -9999 |

Vector input:

| File | CRS | Content |
|---|---|---|
| kibera_boundary.geojson | EPSG:32737 | Single closed polygon |

---

## 4. Repository Layout (agent must create)

```text
scripts/
    01_build_blocks.py
    02_train_module1.py
    03_infer_module1.py
    04_build_graph.py
    05_train_module2.py
    06_infer_module2.py
    07_score_export.py
api/
    main.py
web/
    index.html
    app.js
    style.css
models/                     (created at runtime)
data/processed/             (existing inputs + runtime outputs)
data/output/                (final exports)
SPEC.md
agents.md
memory.md
```

Scripts run in numeric order. Each script must exit non-zero if its validation gate fails.

---

## 5. Dependencies

```text
numpy pandas geopandas shapely pyproj rasterio scipy scikit-learn
xgboost torch torch-geometric fastapi uvicorn
```

---

## 6. Stage 1 — Block Grid (01_build_blocks.py)

1. Compute TRAIN_BOUNDS in EPSG:32737 by projecting (CENTER_LON, CENTER_LAT) and adding +/- TRAIN_HALF_SIZE on both axes.
2. Create square 50m grid covering kibera_boundary bounds, aligned so grid origin = floor(bounds_min / 50) * 50.
3. Keep blocks whose centroid is inside the boundary polygon.
4. Assign each 20m pixel to the block containing its pixel center.
5. For each block and each raster, compute mean of valid assigned pixels.
6. Coverage = valid_pixels / assigned_pixels. Drop blocks with coverage < 0.70.
7. Block IDs: `KIB-0001 ...` assigned in row-major grid order.
8. Save `data/processed/kibera_blocks_50m.geojson` (CRS 32737) with properties:
   block_id, grid_i, grid_j, coverage, and mean_<layer> for all 9 rasters.
9. Also compute and store `estimated_population = mean_population * 0.25`
   (WorldPop values are people per hectare; block = 0.25 ha).

Gate G1: block count >= 500. Else exit(1).

---

## 7. Stage 2 — Module 1 Training (02_train_module1.py)

1. Build 100m cells over TRAIN_BOUNDS (5x5 aggregation of 20m pixels).
2. For each 100m cell compute mean of the 8 feature rasters and mean of landsat_st_celsius,
   using only valid pixels; drop cells with coverage < 0.70 or nodata target.
3. Feature columns (exact names):
   mean_ndvi, mean_ndwi, mean_ndbi, mean_building_density,
   mean_road_density, mean_distance_to_green, mean_distance_to_water,
   mean_population_density
   Target: target_st_celsius
4. Gate G2: sample count >= MIN_TRAIN_SAMPLES. Else exit(1).
5. Split 80/20 by row with SEED.
6. Train XGBRegressor with EXACTLY:

```python
XGBRegressor(
    objective="reg:squarederror",
    n_estimators=400,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=SEED,
    tree_method="hist",
)
```

7. Gate G3: validation R2 >= 0.25 AND validation MAE <= 1.5. Else exit(1).
8. Save model to `models/module1_xgb.json`.
9. Append metrics to memory.md.

---

## 8. Stage 3 — Module 1 Inference + Bias Correction (03_infer_module1.py)

1. Predict at every valid 20m pixel inside TRAIN_BOUNDS using its own feature values.
2. For each 100m cell: correction = target_100m - mean(predictions in cell).
3. corrected_20m = prediction + correction (per pixel, using its cell).
4. Save `data/processed/ai_heat_base_20m.tif` (CRS 32737, nodata -9999).
5. Gate G4: max abs difference between cell-mean corrected values and target_100m <= 0.01.

---

## 9. Stage 4 — Graph Construction (04_build_graph.py)

1. Build graphs for (a) TRAIN area blocks and (b) Kibera blocks, using the same procedure:
   - Nodes = valid 50m blocks from Stage 1 logic (training area uses TRAIN_BOUNDS grid).
   - Node features (9): mean_ai_heat_base, mean_ndvi, mean_ndwi, mean_ndbi,
     mean_building_density, mean_road_density, mean_distance_to_green,
     mean_distance_to_water, mean_population_density.
     (mean_ai_heat_base obtained by aggregating ai_heat_base_20m.tif per block.)
   - Edges = 8-neighborhood via (grid_i, grid_j); undirected; include self-loops.
2. Normalize node features with percentile (2, 98) computed on TRAIN blocks,
   then divide by 100 (range 0-1). Apply same scaler to Kibera blocks.
3. Target per node = normalized mean_ai_heat_base (0-1).
4. Save PyG objects to `models/graph_train.pt` and `models/graph_kibera.pt`.

---

## 10. Stage 5 — Module 2 Training (05_train_module2.py)

Model (exact):

```python
class HeatGAT(torch.nn.Module):
    # GATv2Conv(in=9, out=32, heads=4) -> ELU -> Dropout(0.1)
    # GATv2Conv(in=128, out=16, heads=2, concat=False) -> ELU -> Dropout(0.1)
    # Linear(16, 1) -> Sigmoid
```

Training:

```text
Optimizer: Adam, lr=0.005
Epochs: 200, early stopping patience 20 on validation loss
Split: 80/20 nodes, SEED
Loss = 0.9 * MSE(pred, target) + 0.1 * mean_over_edges((pred_i - pred_j)^2)
```

Gate G5: validation Pearson correlation(pred, target) >= 0.90. Else exit(1).
Save `models/module2_gat.pt`.

---

## 11. Stage 6 — Module 2 Inference (06_infer_module2.py)

1. Load graph_kibera.pt and model.
2. Output contextual_heat_01 = model(x, edge_index).
3. contextual_ai_heat = contextual_heat_01 * 100.
4. Gate G6: std(contextual_ai_heat over Kibera blocks) >= 5.0.
5. Attach to block table.

---

## 12. Stage 7 — Scoring, Explainability, Export (07_score_export.py)

### 12.1 Normalization helper

```text
norm(x) over valid Kibera blocks:
    p2, p98 = percentiles(2, 98)
    if p98 - p2 < 1e-6: return 50
    return clip((x - p2) / (p98 - p2) * 100, 0, 100)
inv(x) = 100 - norm(x)
```

### 12.2 Scores (per block)

```text
AI_Heat_Exposure   = norm(contextual_ai_heat)
Social_Sensitivity = clip(0.70*norm(pop) + 0.30*norm(building), 0, 100)
Cooling_Deficit    = clip(0.35*norm(dist_green) + 0.30*norm(dist_water)
                          + 0.20*inv(ndvi) + 0.15*inv(ndwi), 0, 100)
HVI_raw            = 0.45*AI_Heat + 0.35*Social + 0.20*Cooling
HVI_final          = norm(HVI_raw)
```

### 12.3 Risk classes

```text
0-30 Low | 31-55 Medium | 56-75 High | 76-100 Critical
priority = same label as risk class
```

### 12.4 Drivers

```text
low_vegetation        = inv(ndvi)
high_building_density = norm(building)
high_built_surface    = norm(ndbi)
poor_green_access     = norm(dist_green)
poor_water_access     = norm(dist_water)
high_population_exposure = norm(pop)
```

top_drivers = 3 highest values; ties broken by this exact order:
poor_water_access, poor_green_access, high_population_exposure,
high_building_density, high_built_surface, low_vegetation.

### 12.5 Intervention (highest driver, same tie order)

```text
poor_water_access      -> "Water point / hydration support"
poor_green_access      -> "Shade structure / tree planting"
low_vegetation         -> "Green cover intervention"
high_building_density  -> "Cool roof awareness / ventilation outreach"
high_built_surface     -> "Reflective roof / surface cooling campaign"
high_population_exposure -> "Community health outreach"
```

### 12.6 Export

Reproject blocks to EPSG:4326 and write `data/output/vulnerability_blocks.geojson`
with EXACT properties:

```json
{
  "block_id": "KIB-0234",
  "hvi_score": 87, "hvi_raw": 79.4,
  "risk_class": "Critical", "priority": "Critical",
  "ai_heat_exposure": 89, "social_sensitivity": 84, "cooling_deficit": 82,
  "estimated_population": 312, "population_density": 78, "building_density": 85,
  "ndvi": 12, "ndwi": 6, "ndbi": 77,
  "distance_to_green": 69, "distance_to_water": 74,
  "top_drivers": ["poor_water_access", "high_building_density", "low_vegetation"],
  "intervention": "Water point / hydration support"
}
```

Also export per-layer block GeoJSONs (same geometry, single value property):
ai_heat_exposure_blocks, social_sensitivity_blocks, cooling_deficit_blocks,
ndvi_blocks, ndbi_blocks, building_density_blocks, population_density_blocks.

Gate G7: top-decile HVI blocks must have mean ndvi lower than overall mean ndvi,
and mean building_density higher than overall mean.

---

## 13. Backend (api/main.py)

FastAPI app serving:

```text
GET /                                    -> web/index.html
GET /static/...                          -> web assets
GET /data/vulnerability_blocks.geojson
GET /data/layers/{name}.geojson          -> the 7 layer files
```

Run: `uvicorn api.main:app --port 8000`.

---

## 14. Frontend (web/)

Leaflet from CDN. Requirements:

1. Basemap: OpenStreetMap tiles.
2. Choropleth of vulnerability_blocks.geojson styled by risk_class:
   Low #1a9850, Medium #ffffbf, High #f46d43, Critical #d73027.
3. Click -> side panel showing all properties, with driver display names:
   poor_water_access="Poor water access", poor_green_access="Poor green space access",
   high_population_exposure="High population exposure",
   high_building_density="High building density",
   high_built_surface="High built-up surface", low_vegetation="Low vegetation".
4. Layer control toggling the 7 layer GeoJSONs (single-value choropleth, 5-class blue scale).
5. Legend control with risk classes and colors.
6. Export button downloading vulnerability_blocks.geojson.

---

## 15. Prohibitions

The agent MUST NOT:

- Add fallback branches, try/except that skips a gate, or default values for failed data.
- Change any constant, weight, threshold, seed, or model architecture.
- Introduce U-Net, TransUNet, Transformers, GANs, CNNs, or any model not specified.
- Add data sources beyond Section 3.
- Rename output files or properties.
- Proceed to the next stage if any gate fails (exit non-zero instead).
```

---

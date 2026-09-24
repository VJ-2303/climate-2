# AGENTS.md — HeatViz Implementation Reference

Single-page contract for AI agents working on this codebase.
Authoritative spec: **SPEC.md**. Data sources: **docs/DATASETS.md**.

---

## What This Project Does

HeatViz maps **50m × 50m heat vulnerability** across Kibera, Nairobi (18,040 blocks).
It downscales 100m Landsat thermal data to 20m using XGBoost, then applies a Graph
Attention Network to capture neighborhood thermal diffusion, producing a composite
**Heat Vulnerability Index (HVI)** with root-cause drivers and intervention guidance.
Served via FastAPI + Leaflet.

---

## Immutable Constants (never change these)

```python
SEED = 42
PROCESS_CRS = "EPSG:32737"
OUTPUT_CRS  = "EPSG:4326"
WORKING_RES = 20            # meters
BLOCK_SIZE  = 50            # meters
TRAIN_HALF_SIZE = 2500      # meters → 5km × 5km training window
CENTER_LAT  = -1.317
CENTER_LON  = 36.789
DIST_CAP    = 1000.0        # meters
BLOCK_MIN_VALID_COVERAGE = 0.70
MIN_TRAIN_SAMPLES = 1000
NODATA = -9999.0
```

---

## Inputs — `data/processed/`

All 9 rasters share **identical CRS (32737), 20m pixel size, shape, and transform**.
Assert this at every stage start.

| File | Content | Valid range |
|---|---|---|
| `ndvi.tif` | Vegetation index | [-1, 1] |
| `ndwi.tif` | Water index | [-1, 1] |
| `ndbi.tif` | Built-up index | [-1, 1] |
| `landsat_st_celsius.tif` | Surface temperature | [10, 55] |
| `building_density.tif` | Building coverage fraction | [0, 1] |
| `road_density.tif` | Road coverage fraction | [0, 1] |
| `distance_to_green.tif` | Meters to nearest green | [0, 1000] |
| `distance_to_water.tif` | Meters to nearest water | [0, 1000] |
| `population_density_20m.tif` | People per hectare | [0, ∞) |
| `kibera_boundary.geojson` | EPSG:32737 single polygon | — |

---

## Pipeline — 7 Ordered Stages

```
01 → 02 → 03 → 04 → 05 → 06 → 07
```

Each script is standalone; pass gates or `exit(1)`. No skipping, no fallbacks.

### Stage 01 — Build 50m Block Grid (`01_build_blocks.py`)

- Project center → EPSG:32737; derive `TRAIN_BOUNDS` (±2500m square).
- Create 50m grid aligned to `floor(bounds_min/50)*50`.
- Keep blocks whose **centroid** is inside `kibera_boundary.geojson`.
- For each block, compute `mean_<layer>` from 20m pixels with centroid inside block; drop blocks where **any** layer coverage < 0.70.
- `estimated_population = mean_population_density × 0.25` (block = 0.25 ha).
- Save `data/processed/kibera_blocks_50m.geojson` (CRS 32737) with columns:
  `block_id, grid_i, grid_j, coverage, mean_*, estimated_population`.
- **Gate G1:** block count ≥ 500, else `exit(1)`.

### Stage 02 — Train Module 1 XGBoost (`02_train_module1.py`)

- Aggregate 20m pixels into 100m cells (5×5) over TRAIN_BOUNDS; drop cells with coverage < 0.70 or nodata target.
- Features (exact names): `mean_ndvi, mean_ndwi, mean_ndbi, mean_building_density, mean_road_density, mean_distance_to_green, mean_distance_to_water, mean_population_density`. Target: `target_st_celsius`.
- **Gate G2:** sample count ≥ MIN_TRAIN_SAMPLES, else `exit(1)`.
- 80/20 row split with SEED. Train exactly:

```python
XGBRegressor(
    objective="reg:squarederror",
    n_estimators=400, max_depth=6, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    random_state=SEED, tree_method="hist",
)
```

- **Gate G3:** val R² ≥ 0.25 AND val MAE ≤ 1.5, else `exit(1)`.
- Save `models/module1_xgb.json`. Append metrics to `memory.md`.

### Stage 03 — Module 1 Inference + Bias Correction (`03_infer_module1.py`)

- Predict at every valid 20m pixel inside TRAIN_BOUNDS.
- Per 100m cell: `correction = target_100m − mean(predictions in cell)`.
- `corrected_20m = prediction + correction`.
- **Gate G4:** max abs diff between cell-mean corrected and `target_100m` ≤ 0.01, else `exit(1)`.
- Save `data/processed/ai_heat_base_20m.tif` (CRS 32737, nodata −9999, float32).

### Stage 04 — Build Spatial Graph (`04_build_graph.py`)

- Build two PyG `Data` objects: one for TRAIN area blocks, one for all Kibera blocks.
- **Node features (9):** `mean_ai_heat_base, mean_ndvi, mean_ndwi, mean_ndbi, mean_building_density, mean_road_density, mean_distance_to_green, mean_distance_to_water, mean_population_density`.
  - `mean_ai_heat_base` = per-block mean of `ai_heat_base_20m.tif`.
- **Edges:** 8-neighborhood via `(grid_i, grid_j)`; undirected; include self-loops.
- **Normalize:** percentile(2, 98) computed on TRAIN blocks → divide by 100 → [0, 1]. Same scaler applied to Kibera blocks.
- **Target per node:** normalized `mean_ai_heat_base` (0–1).
- Save `models/graph_train.pt` and `models/graph_kibera.pt`.

### Stage 05 — Train Module 2 GAT (`05_train_module2.py`)

Exact architecture (frozen):

```python
class HeatGAT(nn.Module):
    # GATv2Conv(in=9, out=32, heads=4)     → ELU → Dropout(0.1)
    # GATv2Conv(in=128, out=16, heads=2, concat=False) → ELU → Dropout(0.1)
    # Linear(16, 1) → Sigmoid
```

Training:

```
Optimizer: Adam, lr=0.005
Epochs: 200, early stopping patience 20 on val loss
Split: 80/20 nodes, SEED
Loss = 0.9 × MSE(pred, target) + 0.1 × mean_over_edges((pred_i − pred_j)²)
```

- **Gate G5:** val Pearson correlation ≥ 0.90, else `exit(1)`.
- Save `models/module2_gat.pt`.

### Stage 06 — Module 2 Inference (`06_infer_module2.py`)

- Load `graph_kibera.pt` + `module2_gat.pt`.
- `contextual_heat_01 = model(x, edge_index)`.
- `contextual_ai_heat = contextual_heat_01 × 100`.
- **Gate G6:** `std(contextual_ai_heat) ≥ 5.0`, else `exit(1)`.
- Attach `contextual_ai_heat` to `kibera_blocks_50m.geojson` and overwrite.

### Stage 07 — Score, Explain, Export (`07_score_export.py`)

**Normalization helpers:**
```
norm(x): p2, p98 = percentiles(2, 98); clip((x−p2)/(p98−p2)×100, 0, 100)
inv(x) = 100 − norm(x)
```

**Scores:**
```
AI_Heat_Exposure   = norm(contextual_ai_heat)
Social_Sensitivity = clip(0.70×norm(pop) + 0.30×norm(building), 0, 100)
Cooling_Deficit    = clip(0.35×norm(dist_green) + 0.30×norm(dist_water)
                          + 0.20×inv(ndvi) + 0.15×inv(ndwi), 0, 100)
HVI_raw            = 0.45×AI_Heat + 0.35×Social + 0.20×Cooling
HVI_final          = norm(HVI_raw)
```

**Risk classes:** `0–30 Low | 31–55 Medium | 56–75 High | 76–100 Critical`

**Drivers (tie-break order):**
`poor_water_access, poor_green_access, high_population_exposure, high_building_density, high_built_surface, low_vegetation`
Top 3 by value; intervention = highest driver's mapping.

**Outputs (exact property names):**
```
data/output/vulnerability_blocks.geojson   ← EPSG:4326, all 20 properties
data/output/layers/<name>.geojson          ← 7 single-value layer files
data/output/<name>.geojson                 ← duplicate for API flexibility
```

- **Gate G7:** top-decile HVI blocks must have `mean(ndvi) < overall mean(ndvi)` AND `mean(building_density) > overall mean(building_density)`, else `exit(1)`.

---

## Artifacts Map

| Path | Producer | Consumer |
|---|---|---|
| `data/processed/kibera_blocks_50m.geojson` | 01, updated by 06 | 02, 04, 06, 07 |
| `data/processed/ai_heat_base_20m.tif` | 03 | 04 |
| `models/module1_xgb.json` | 02 | 03 |
| `models/graph_train.pt` | 04 | 05 |
| `models/graph_kibera.pt` | 04 | 06 |
| `models/module2_gat.pt` | 05 | 06 |
| `data/output/vulnerability_blocks.geojson` | 07 | API, web |
| `data/output/layers/*.geojson` | 07 | API |

---

## Backend — `api/main.py`

FastAPI, startup loads all GeoJSONs into memory (`blocks_db` dict). GZip middleware on.

| Endpoint | Returns |
|---|---|
| `GET /` | `web/index.html` |
| `GET /data/vulnerability_blocks.geojson` | Main HVI GeoJSON |
| `GET /data/layers/{name}.geojson` | One of 7 layer files |
| `GET /api/layers/{name}/attributes` | `{block_id: score}` lightweight map |
| `GET /api/blocks/{block_id}` | Full block intelligence payload (rules engine) |

Rules engine (`api/rules.py`) computes physical diagnosis, intervention sizing, species guidance, heat-health advisory — all deterministic, no ML at serve time.

---

## Frontend — `web/`

Leaflet from CDN. Choropleth by `risk_class`:
`Low #1a9850 | Medium #ffffbf | High #f46d43 | Critical #d73027`

Layer switching uses `/api/layers/{name}/attributes` (lightweight, no geometry reload).
Zone Planner: draw polygon → aggregate population + risk distribution.
Offline: CacheStorage tile caching.

---

## Run Commands

```bash
# Serve existing outputs (no ML needed)
source .venv/bin/activate
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Full pipeline (after deps install)
python scripts/01_build_blocks.py
python scripts/02_train_module1.py
python scripts/03_infer_module1.py
python scripts/04_build_graph.py
python scripts/05_train_module2.py
python scripts/06_infer_module2.py
python scripts/07_score_export.py
```

---

## Hard Prohibitions

- No `try/except` that silently skips a gate or substitutes a default value.
- No changes to any constant, weight, threshold, seed, or model architecture.
- No model architectures beyond XGBoost + HeatGAT (no CNNs, Transformers, GANs, U-Net).
- No data sources beyond the 5 specified (Landsat, Sentinel-2, OSM, WorldPop, Kibera boundary).
- No renaming of output files or GeoJSON property keys.
- If a gate fails → `exit(1)`. Never proceed to next stage.

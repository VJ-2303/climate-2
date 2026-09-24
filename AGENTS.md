# AGENTS.md — HeatViz/ThermalGuard Implementation Contract

Agent contract for this codebase. Authoritative spec (physics, formulas, UI): **SPEC.md**.
Data sources: **docs/DATASETS.md**.

---

## Immutable Constants (never change)

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

Frozen weights/thresholds (see SPEC.md §2): HVI 0.45/0.35/0.20 · social 0.70/0.30 ·
cooling 0.35/0.30/0.20/0.15 · WBGT tiers 28/30/32 (Critical > 32.0) · anomaly factor 0.4 ·
settlement mean 28.7 · tier-bump threshold 70 · risk-score zero point 24.0.

---

## Inputs — `data/processed/`

9 rasters, identical CRS (32737), 20m pixels, shape, transform — assert at every stage start.

| File | Valid range |
|---|---|
| `ndvi.tif`, `ndwi.tif`, `ndbi.tif` | [-1, 1] |
| `landsat_st_celsius.tif` | [10, 55] |
| `building_density.tif`, `road_density.tif` | [0, 1] |
| `distance_to_green.tif`, `distance_to_water.tif` | [0, 1000] |
| `population_density_20m.tif` | [0, ∞) people/ha |
| `kibera_boundary.geojson` | EPSG:32737 single polygon |

---

## Pipeline — 8 Stages

`01 → 02 → 08 → 03 → 04 → 05 → 06 → 07` — standalone, gate fail = `exit(1)`, no fallbacks.

| Stage | Script | Gate |
|---|---|---|
| 01 block grid | `01_build_blocks.py` | G1: blocks ≥ 500 |
| 02 XGBoost ST | `02_train_module1.py` | G2: samples ≥ 1000 · G3: val R² ≥ 0.25 AND MAE ≤ 1.5 |
| 08 SHAP | `08_compute_shap.py` | all blocks explained, else exit(1) |
| 03 infer + bias | `03_infer_module1.py` | G4: cell-mean diff ≤ 0.01°C |
| 04 graph | `04_build_graph.py` | 8-neighbor + self-loops, p2/p98 scaler from TRAIN |
| 05 GAT | `05_train_module2.py` | G5: val Pearson ≥ 0.90 |
| 06 GAT infer | `06_infer_module2.py` | G6: std(contextual_ai_heat) ≥ 5.0 |
| 07 score/export | `07_score_export.py` | G7: top-decile HVI has lower NDVI + higher building density |

Stage details and formulas: SPEC.md §2–§3.

---

## Artifacts Map

| Path | Producer | Consumer |
|---|---|---|
| `data/processed/kibera_blocks_50m.geojson` | 01, updated by 06 | 02, 04, 06, 07 |
| `data/processed/ai_heat_base_20m.tif` | 03 | 04 |
| `data/processed/block_shap_explanations.json` | 08 | 07, `api/main.py` |
| `models/module1_xgb.json` | 02 | 03, 08 |
| `models/graph_train.pt` / `graph_kibera.pt` | 04 | 05 / 06 |
| `models/module2_gat.pt` | 05 | 06 |
| `data/output/vulnerability_blocks.geojson` | 07 | API, officer UI |
| `data/output/layers/*.geojson` | 07 | API |
| `data/fallback_forecast.json` | manual | `api/weather.py` (offline) |

`vulnerability_blocks.geojson` properties (exact names — never rename):
`block_id, risk_class, hvi_score, hvi_raw, ai_heat_exposure, social_sensitivity, cooling_deficit,
surface_temp_celsius, temp_anomaly_celsius, estimated_population, priority, top_drivers,
intervention, shap_top_factors, distance_to_water, distance_to_green, ndvi, ndwi, ndbi,
building_density, population_density, geometry`

---

## Backend — `api/`

- `main.py` — FastAPI, startup loads GeoJSONs into `blocks_db` + SHAP cache; GZip on.
  Routes: SPEC.md §4. Officer UI only (`/` and `/officer` → `web/officer.html`). No public portal.
- `weather.py` — full WBGT (SPEC.md §2.1), Open-Meteo fetch (hourly T/RH/solar/wind),
  1h cache, fallback file on failure. `build_open_meteo_url` / `process_open_meteo` are
  the testable seams.
- `rules.py` — deterministic block intelligence: physical diagnosis, SHAP top-3,
  5-day health trajectory (tier modulation), advisories, intervention sizing. No ML at serve time.

## Frontend — `web/`

`officer.html` + `officer.js` (extends `app.js` map engine via globals: `currentLayer`,
`RISK_COLORS`, `openSidebar`). Forecast dropdown, SHAP waterfall, sparkline, SMS modal.
Layer colors: `Low #1a9850 | Medium #ffffbf | High #f46d43 | Critical #d73027`.

---

## Run Commands

```bash
source .venv/bin/activate

# Full pipeline
python scripts/01_build_blocks.py
python scripts/02_train_module1.py
python scripts/08_compute_shap.py
python scripts/03_infer_module1.py
python scripts/04_build_graph.py
python scripts/05_train_module2.py
python scripts/06_infer_module2.py
python scripts/07_score_export.py

# Serve
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Tests
python -m pytest tests/ -q
```

---

## Hard Prohibitions

- No `try/except` that silently skips a gate or substitutes defaults.
- No changes to constants, weights, thresholds, seeds, or model architectures (SPEC.md §7).
- No model families beyond XGBoost + HeatGAT.
- No data sources beyond SPEC.md §6.
- No renaming of output files or GeoJSON property keys (adding keys is allowed).
- Gate fail → `exit(1)`. Never proceed to next stage.

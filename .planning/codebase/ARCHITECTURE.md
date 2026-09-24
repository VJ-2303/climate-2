# Architecture

**Analysis Date:** 2026-09-24

## Pattern Overview

**Overall:** Multi-Stage Offline Geospatial ML Pipeline + Asynchronous Microclimate Intelligence REST API + Canvas-Accelerated Leaflet SPA Command Center.

**Key Characteristics:**
- **Deterministic Pipeline Gates:** Every ML/data pipeline stage operates standalone with strict quality gates (G1 through G7); failures trigger immediate `exit(1)` with no silent fallbacks.
- **Physics-Informed Two-Stage AI:** Combines XGBoost gradient-boosted decision trees (Module 1: super-resolving 100m satellite thermal data to 20m) with Graph Attention Networks (Module 2: HeatGAT modeling thermal advection and 8-neighbor neighborhood heat spillover).
- **Explainable by Design:** Local TreeSHAP attributions computed per 50m micro-sector, giving urban planners exact physical root causes (e.g. canopy deficit vs. built surface fraction).
- **Sub-10ms Serving Layer:** Precomputed GeoJSON layers loaded into an in-memory spatial index on API startup; no heavy ML inference executed on request threads.
- **Client-Side Scalability:** Renders 36,913 polygons in the browser via Leaflet Canvas rendering and lightweight attribute dictionaries ({block_id: score}) for 0ms layer toggling.

## Layers

**1. Offline Data Engineering & Machine Learning Pipeline (`scripts/`, `process.py`):**
- Purpose: Ingest raw satellite/OSM data, generate 50m vector blocks, train downscaling models, compute SHAP attributions, run GAT smoothing, and export scored GeoJSON datasets.
- Contains:
  - `process.py`: Raw satellite band extraction, cloud masking, and 20m master grid alignment.
  - `scripts/01_build_blocks.py` through `scripts/08_compute_shap.py`: 8 sequential pipeline stages.
- Depends on: `rasterio`, `geopandas`, `xgboost`, `torch-geometric`, `shap`.
- Used by: Produces artifacts consumed by the API and web frontend.

**2. Climate Intelligence API Layer (`api/`):**
- Purpose: Serve geospatial GeoJSON layers, compute dynamic wet-bulb globe temperature (WBGT) heatwave forecasts, and generate sector intelligence profiles.
- Contains:
  - `api/main.py`: FastAPI routes, lifespan dataset loading, spatial grid indexing, GZip middleware, and static asset mounting.
  - `api/weather.py`: Open-Meteo fetching, 1-hour caching, fallback handling, and WBGT thermal index calculations.
  - `api/rules.py`: Deterministic block intelligence engine (physical land-cover diagnosis, SHAP top-3 causes, intervention sizing, 5-day physiological risk trajectories).
- Depends on: Local disk artifacts (`data/output/`, `data/processed/`), Open-Meteo API.
- Used by: Frontend web interfaces (`web/app.js`, `web/officer.js`).

**3. Frontend Presentation & Command Center (`web/`):**
- Purpose: Provide municipal officers with high-contrast heat vulnerability maps, 5-day heatwave timeline scrubbers, sector inspection drawer with SHAP waterfall charts, and SMS emergency dispatch.
- Contains:
  - `web/officer.html` / `web/index.html`: Dashboard layout, sidebar drawers, modal dialogs.
  - `web/app.js`: Base Leaflet map initialization, 2x buffer boundary constraints, cached tile layer, GeoJSON canvas styling, and overview dashboards.
  - `web/officer.js`: Officer command center extensions (forecast dropdown, sparklines, SHAP waterfall rendering, SMS modal dispatch).
  - `web/style.css`: Unified dark/light design system with high-contrast risk colors.
- Depends on: API endpoints (`/data/*`, `/api/*`), Leaflet, Leaflet.draw, Turf.js.

## Data Flow

### 1. Offline Pipeline Execution Flow
```
Raw Satellite Rasters (Sentinel-2, Landsat 8/9, OSM, WorldPop)
                    │
                    ▼
          [process.py] 20m Aligned Rasters
                    │
                    ▼
          [01_build_blocks.py] 50m Vector Grid (36,913 Blocks)
                    │
                    ├──────────────────────────┐
                    ▼                          ▼
          [02_train_module1.py]       [08_compute_shap.py]
          XGBoost LST Downscaling     TreeSHAP Local Attributions
                    │                          │
                    ▼                          │
          [03_infer_module1.py]                │
          20m Base Heat + Residual Correction  │
                    │                          │
                    ▼                          │
          [04_build_graph.py]                  │
          8-Neighbor Spatial Graph             │
                    │                          │
                    ▼                          │
          [05_train_module2.py]                │
          PyG HeatGAT Training                 │
                    │                          │
                    ▼                          │
          [06_infer_module2.py]                │
          Contextual AI Heat Smoothing         │
                    │                          │
                    └───────────┬──────────────┘
                                ▼
                      [07_score_export.py]
                      HVI Formula & Gate G7
                                │
                                ▼
          `data/output/vulnerability_blocks.geojson`
```

### 2. Request / Serving Lifecycle Flow
1. **Application Startup (`api/main.py`):**
   - `lifespan` hook calls `load_dataset_into_memory()`.
   - Reads `data/output/vulnerability_blocks.geojson`, populates `blocks_db` hash map.
   - Reads `data/processed/madurai_blocks_50m.geojson`, builds 2D spatial grid index `(grid_i, grid_j) <-> block_id`.
   - Reads `data/processed/block_shap_explanations.json` into `shap_db`.
   - Precomputes attribute dictionaries for all 7 sub-layers into `layer_attributes_cache`.
2. **Client Map Loading (`web/app.js`):**
   - Browser requests `GET /data/vulnerability_blocks.geojson` (compressed via GZip).
   - Leaflet initializes with Canvas renderer and adds polygons styled by `risk_class` (Critical, High, Medium, Low).
3. **Sector Inspection (`web/app.js` -> `web/officer.js`):**
   - User clicks sector polygon -> triggers `openSidebar(props)`.
   - Calls `GET /api/blocks/{block_id}`.
   - `api/rules.py` generates full physical profile, land cover classification, 5-day health trajectory, and SHAP top-3 causes in <5ms.
   - `web/officer.js` renders SHAP waterfall bars, temperature anomaly pill, and 5-day risk sparkline.
4. **Emergency Alert Dispatch (`web/officer.js`):**
   - User clicks "Dispatch SMS Alert" -> opens modal -> sends `POST /api/alerts/dispatch`.
   - API records dispatch audit event and returns immediate confirmation.

## Key Abstractions

- **Heat Vulnerability Index (HVI):** Composite 0-100 metric calculated as:
  `HVI = 0.45 * AI_Heat_Exposure + 0.35 * Social_Sensitivity + 0.20 * Cooling_Deficit`
- **HeatGAT (Graph Attention Network):** 2-layer GAT model with multi-head attention that learns spatial temperature influence weights across 8-connected neighboring blocks.
- **Wet-Bulb Globe Temperature (WBGT):** Physiological thermal stress index incorporating air temperature, humidity, solar radiation, and wind speed.
- **CachedTileLayer (`web/app.js`):** Custom Leaflet tile layer subclassing `L.TileLayer` that queries the browser's `CacheStorage` before making network requests, enabling resilient offline map browsing.

## Entry Points

- **Pipeline Runner:** CLI scripts executed in order (`scripts/01_build_blocks.py` through `scripts/08_compute_shap.py`).
- **API Server:** `uvicorn api.main:app --reload` (`api/main.py`).
- **Web UI:** Route `/` or `/officer` serving `web/officer.html`.

## Error Handling

- **Pipeline Quality Gates:** Strict assertion gates (G1 through G7) defined in `AGENTS.md` / `SPEC.md`. Any gate failure exits immediately with status code 1.
- **API Boundary:** FastAPI `HTTPException` returning clear JSON error objects for missing blocks or invalid forecast days.
- **Weather Resilience:** Network exceptions during Open-Meteo fetches automatically fall back to `data/fallback_forecast.json` without failing user requests.

---

*Architecture analysis: 2026-09-24*
*Update after structural architectural changes*

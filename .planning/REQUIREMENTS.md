# Requirements: HeatViz (ThermalGuard)

**Defined:** 2026-09-24  
**Core Value:** Provide municipal officers with sub-10ms explainable heat vulnerability intelligence, 5-day heatwave WBGT forecasts, and targeted emergency cooling intervention sizing across 36,913 50m micro-sectors.

## v1 Requirements

### Data Engineering & Spatial Tiling (DATA)
- [x] **DATA-01**: Ingest and align Sentinel-2, Landsat 8/9, OSM, and WorldPop rasters to 20m master grid in `EPSG:32643` (`process.py`).
- [x] **DATA-02**: Discretize study area into 50m × 50m vector polygon blocks clipped to Madurai municipal boundary with >=70% valid coverage (`01_build_blocks.py`).
- [x] **DATA-03**: Calculate zonal mean features for all 9 predictor variables across every 50m block (`01_build_blocks.py`).

### Machine Learning & Spatial GNN (MODEL)
- [x] **MODEL-01**: Train XGBoost downscaling model on Landsat LST pixels achieving Validation R² >= 0.25 and MAE <= 1.5°C (`02_train_module1.py`).
- [x] **MODEL-02**: Generate 20m predicted Land Surface Temperature with cell-mean bias difference <= 0.01°C (`03_infer_module1.py`).
- [x] **MODEL-03**: Construct 8-neighbor spatial adjacency graph with node features and self-loops (`04_build_graph.py`).
- [x] **MODEL-04**: Train 2-layer HeatGAT with multi-head attention achieving Validation Pearson correlation >= 0.90 (`05_train_module2.py`).
- [x] **MODEL-05**: Run HeatGAT spatial inference to produce smoothed `contextual_ai_heat` with std >= 5.0 (`06_infer_module2.py`).

### Explainability & Scoring (EXPLAIN)
- [x] **EXPLAIN-01**: Compute TreeSHAP local feature attributions for 100% of 50m sector blocks (`08_compute_shap.py`).
- [x] **EXPLAIN-02**: Compute Heat Vulnerability Index (HVI) using 0.45 Heat / 0.35 Social / 0.20 Cooling deficit formula (`07_score_export.py`).
- [x] **EXPLAIN-03**: Validate Gate G7 ensuring top-decile HVI blocks have lower NDVI and higher building density than overall mean (`07_score_export.py`).
- [x] **EXPLAIN-04**: Export final datasets to `data/output/vulnerability_blocks.geojson` and individual sub-layers in `EPSG:4326` (`07_score_export.py`).

### Climate Intelligence API (API)
- [x] **API-01**: Implement FastAPI backend with in-memory startup caching of 36,913 blocks and 2D spatial grid (`api/main.py`).
- [x] **API-02**: Enable GZip compression middleware providing ~88% payload reduction on GeoJSON endpoints (`api/main.py`).
- [x] **API-03**: Provide `/api/blocks/{block_id}` returning physical archetype, thermal causes, intervention sizing, and 5-day trajectory (`api/rules.py`).
- [x] **API-04**: Provide `/api/layers/{name}/attributes` returning lightweight `{block_id: score}` key-value pairs for 0ms layer toggling (`api/main.py`).

### Weather & WBGT Forecasting (FORECAST)
- [x] **FORECAST-01**: Fetch hourly weather from Open-Meteo API for Madurai coordinates with 1-hour cache (`api/weather.py`).
- [x] **FORECAST-02**: Compute daily maximum Wet-Bulb Globe Temperature (WBGT) and project sector physiological heat risk (`api/weather.py`).
- [x] **FORECAST-03**: Seamlessly fallback to offline `data/fallback_forecast.json` when Open-Meteo is unreachable (`api/weather.py`).

### Command Center UI & Alerts (UI)
- [x] **UI-01**: Leaflet Canvas-accelerated vector mapping rendering all 36,913 sectors smoothly with high-contrast risk colors (`web/app.js`).
- [x] **UI-02**: Offline basemap tile caching using browser CacheStorage API (`heatviz-tiles-v2`) (`web/app.js`).
- [x] **UI-03**: Sector inspection drawer with TreeSHAP waterfall charts, anomaly pills, and 5-day risk sparklines (`web/officer.js`).
- [x] **UI-04**: 5-day heatwave forecast timeline scrubber updating map styling dynamically (`web/officer.js`).
- [x] **UI-05**: Interactive SMS emergency alert dispatch modal with simulated multi-channel broadcast and audit logging (`web/officer.js`, `api/main.py`).

## v2 Requirements (Deferred)

- **SCALE-01**: Dynamic Vector Tile pipeline (MVT / PMTiles) to replace monolithic GeoJSON transfer.
- **INTEG-01**: Live integration with state disaster management SMS gateways (TNSDMA CAP / BSNL).
- **TEMPORAL-01**: Longitudinal multi-year satellite time series analysis for urban heat trend tracking.

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01, DATA-02, DATA-03 | Phase 1: Data Pipeline & Spatial Tiling | Complete |
| MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05 | Phase 2: Two-Stage ML & Spatial GNN | Complete |
| EXPLAIN-01, EXPLAIN-02, EXPLAIN-03, EXPLAIN-04 | Phase 3: Explainability & Vulnerability Scoring | Complete |
| API-01, API-02, API-03, API-04 | Phase 4: Fast Microclimate Intelligence API | Complete |
| FORECAST-01, FORECAST-02, FORECAST-03 | Phase 5: Weather & WBGT Thermal Stress Engine | Complete |
| UI-01, UI-02, UI-03, UI-04, UI-05 | Phase 6: Officer Command Center & Emergency Dispatch | Complete |

**Coverage:**
- v1 requirements: 20 total
- Mapped to phases: 20
- Unmapped: 0

---
*Requirements defined: 2026-09-24*
*Last updated: 2026-09-24 after doc ingest*

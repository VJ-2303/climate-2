# Roadmap: HeatViz (ThermalGuard)

## Overview

HeatViz establishes an end-to-end urban climate intelligence platform for Madurai, transitioning from multimodal satellite earth observation and GNN spatial modeling to sub-10ms API intelligence delivery and municipal emergency command center operations.

## Phases

- [x] **Phase 1: Data Engineering & Spatial Tiling** - Preprocess 20m aligned rasters and generate 50m micro-sector vector grid.
- [x] **Phase 2: Two-Stage ML & Spatial GNN** - Train XGBoost thermal downscaling and HeatGAT spatial neighborhood advection models.
- [x] **Phase 3: Explainability & Vulnerability Scoring** - TreeSHAP local factor attribution, HVI formulation, and Gate G7 export.
- [x] **Phase 4: Fast Microclimate Intelligence API** - FastAPI backend with in-memory spatial indexing, GZip compression, and rules engine.
- [x] **Phase 5: Weather & WBGT Thermal Stress Engine** - Open-Meteo forecasting, WBGT computation, caching, and fallback handling.
- [x] **Phase 6: Officer Command Center & Emergency Dispatch** - Canvas map rendering, SHAP waterfall charts, sparklines, and SMS alerts.
- [ ] **Phase 7: Production Optimization & Vector Tiling** - Implement dynamic vector tiling (PMTiles/MVT) and production deployment hardening.

## Phase Details

### Phase 1: Data Engineering & Spatial Tiling
**Goal**: Establish 20m analysis-ready raster stack and 50m vector micro-sector grid for Madurai.
**Depends on**: Nothing (foundational phase)
**Requirements**: DATA-01, DATA-02, DATA-03
**Success Criteria**:
  1. 9 master rasters aligned to `EPSG:32643` at 20m resolution.
  2. 36,913 50m vector blocks generated within Madurai boundary (Gate G1 passed).
  3. Zonal mean metrics extracted for all predictors per block.

### Phase 2: Two-Stage ML & Spatial GNN
**Goal**: Predict high-resolution Land Surface Temperature and model spatial heat advection.
**Depends on**: Phase 1
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05
**Success Criteria**:
  1. XGBoost downscaling model achieves Validation R² >= 0.25 and MAE <= 1.5°C (Gates G2, G3).
  2. Predicted 20m thermal raster has cell-mean bias <= 0.01°C (Gate G4).
  3. PyG 8-neighbor spatial graph constructed and HeatGAT trained to Pearson >= 0.90 (Gate G5).
  4. Contextual AI heat exposure standard deviation >= 5.0 (Gate G6).

### Phase 3: Explainability & Vulnerability Scoring
**Goal**: Explain physical drivers for every block and export final vulnerability layers.
**Depends on**: Phase 2
**Requirements**: EXPLAIN-01, EXPLAIN-02, EXPLAIN-03, EXPLAIN-04
**Success Criteria**:
  1. TreeSHAP attributions computed for all 36,913 blocks.
  2. HVI composite scores computed using 0.45 Heat / 0.35 Social / 0.20 Cooling weights.
  3. Gate G7 passed (top-decile HVI blocks have lower NDVI and higher building density).
  4. Multi-layer GeoJSON files exported to `data/output/` in `EPSG:4326`.

### Phase 4: Fast Microclimate Intelligence API
**Goal**: Deliver sub-10ms REST API serving layers and block diagnosis.
**Depends on**: Phase 3
**Requirements**: API-01, API-02, API-03, API-04
**Success Criteria**:
  1. Startup lifespan loads all 36k blocks and 2D grid index into memory.
  2. GZip middleware compresses 26MB GeoJSON responses by ~88%.
  3. `/api/blocks/{block_id}` returns full physical profile, causes, and interventions in <10ms.
  4. Lightweight attribute endpoints return `{block_id: score}` for instant layer switching.

### Phase 5: Weather & WBGT Thermal Stress Engine
**Goal**: Ingest real-time numerical weather forecasts and model physiological heat stress.
**Depends on**: Phase 4
**Requirements**: FORECAST-01, FORECAST-02, FORECAST-03
**Success Criteria**:
  1. Open-Meteo forecasts fetched for Madurai coordinates with 1-hour cache.
  2. Daily maximum WBGT calculated and projected across blocks.
  3. Resilient fallback to local `data/fallback_forecast.json` on network failure.

### Phase 6: Officer Command Center & Emergency Dispatch
**Goal**: Provide municipal disaster officers with interactive decision support and alerting.
**Depends on**: Phase 5
**Requirements**: UI-01, UI-02, UI-03, UI-04, UI-05
**Success Criteria**:
  1. 36k polygons rendered smoothly on Leaflet with high-contrast risk colors.
  2. Sector drawer displays SHAP waterfall charts, anomaly pills, and 5-day risk sparklines.
  3. Forecast timeline scrubber updates map layer colors in real time.
  4. Interactive SMS modal simulates multi-channel dispatch with audit tracking.

### Phase 7: Production Optimization & Vector Tiling
**Goal**: Eliminate 26MB initial GeoJSON download and harden for municipal enterprise deployment.
**Depends on**: Phase 6
**Requirements**: SCALE-01, INTEG-01
**Success Criteria**:
  1. Convert monolithic GeoJSON into dynamic vector tiles (PMTiles / MVT).
  2. Initial client payload reduced from 3.2MB (gzip) to <250KB per viewport.
  3. Integrate live SMS gateway webhook hooks.

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Data Engineering & Spatial Tiling | 1/1 | Complete | 2026-09-24 |
| 2. Two-Stage ML & Spatial GNN | 1/1 | Complete | 2026-09-24 |
| 3. Explainability & Vulnerability Scoring | 1/1 | Complete | 2026-09-24 |
| 4. Fast Microclimate Intelligence API | 1/1 | Complete | 2026-09-24 |
| 5. Weather & WBGT Thermal Stress Engine | 1/1 | Complete | 2026-09-24 |
| 6. Officer Command Center & Emergency Dispatch | 1/1 | Complete | 2026-09-24 |
| 7. Production Optimization & Vector Tiling | 0/2 | Planned | - |

---
*Roadmap defined: 2026-09-24*
*Last updated: 2026-09-24 after doc ingest*

# HeatViz (ThermalGuard)

## What This Is

HeatViz (ThermalGuard) is an end-to-end hyperlocal urban heat vulnerability platform designed for Madurai, Tamil Nadu. It ingests multimodal earth observation data (Sentinel-2, Landsat 8/9, OpenStreetMap, WorldPop) through a physics-informed two-stage machine learning pipeline (XGBoost downscaling + HeatGAT graph attention) to quantify microclimate risk across 36,913 50m micro-sectors. It delivers actionable decision support to municipal disaster management officers, urban planners, and primary healthcare centers (UPHC).

## Core Value

Provide municipal officers with sub-10ms explainable heat vulnerability intelligence, 5-day heatwave WBGT forecasts, and targeted emergency cooling intervention sizing across 36,913 50m micro-sectors.

## Requirements

### Validated
- [x] Preprocessed 20m analysis-ready rasters for Madurai in UTM Zone 43N (`process.py`)
- [x] Discretized 50m micro-sector grid covering 36,913 blocks (`01_build_blocks.py`)
- [x] Module 1 XGBoost satellite surface temperature downscaling (`02_train_module1.py`, `03_infer_module1.py`)
- [x] TreeSHAP local feature attribution per block (`08_compute_shap.py`)
- [x] Module 2 HeatGAT 8-neighbor spatial graph advection modeling (`04_build_graph.py`, `05_train_module2.py`, `06_infer_module2.py`)
- [x] Composite Heat Vulnerability Index (HVI) scoring and multi-layer GeoJSON export (`07_score_export.py`)
- [x] High-performance FastAPI backend with in-memory spatial index and GZip compression (`api/main.py`)
- [x] Wet-Bulb Globe Temperature (WBGT) 5-day heatwave forecasting with Open-Meteo and offline fallback (`api/weather.py`)
- [x] Deterministic block intelligence with physical root causes and intervention sizing (`api/rules.py`)
- [x] Leaflet Canvas-rendered officer command center dashboard (`web/officer.html`, `web/officer.js`, `web/app.js`)
- [x] Simulated multi-channel SMS emergency alert dispatch endpoint (`/api/alerts/dispatch`)

### Active
- [ ] Production vector tiling (PMTiles/MVT) to optimize initial GeoJSON payload delivery
- [ ] Real SMS gateway integration (TNSDMA Common Alerting Protocol / BSNL)
- [ ] Longitudinal model retraining pipeline with multi-temporal satellite imagery

### Out of Scope
- Public-facing community web portal (strictly officer command center)
- Multi-city generalization without spatial retraining (specifically hyper-tuned to Madurai UTM Zone 43N)
- Real-time deep learning inference on request threads (precomputed deterministic serving architecture)

## Context

Madurai experiences extreme summer temperatures exceeding 42°C, exacerbated by dense informal settlements, low tree canopy cover, and extensive impervious tin and concrete rooftops. HeatViz addresses the limitations of coarse 1km-25km climate models by delivering actionable 50m micro-sector intelligence with explainable root causes (TreeSHAP) and physical intervention sizing.

## Constraints

- **Coordinate System**: Processing strictly in `EPSG:32643` (UTM Zone 43N); export in `EPSG:4326` (WGS84).
- **Working Resolution**: 20m raster resolution, 50m aggregated vector grid.
- **Model Architecture**: Restricted to XGBoost for downscaling and PyTorch Geometric HeatGAT for spatial neighborhood smoothing.
- **Serving Performance**: Sub-10ms response times via in-memory caching and deterministic rule engines.
- **Quality Gates**: Strict quantitative assertions G1 through G7 with immediate `exit(1)` on failure.

## Key Decisions

<decisions>
| Decision | Rationale | Outcome |
|----------|-----------|---------|
| `EPSG:32643` for processing, `EPSG:4326` for export | True metric 20m/50m Euclidean spatial calculations in UTM Zone 43N, reprojected for standard web Leaflet display | ✓ Good |
| 50m Block Aggregation | Bridges 20m raster physics with recognizable municipal micro-sectors | ✓ Good |
| XGBoost + HeatGAT Architecture | Combines gradient-boosted tabular super-resolution with graph neural network neighborhood thermal advection | ✓ Good |
| HVI Weights (0.45 Heat / 0.35 Social / 0.20 Cooling) | Balances physical heat exposure with demographic sensitivity and access deficits | ✓ Good |
| Deterministic Serving Layer | Eliminates ML latency and GPU dependencies at API request time | ✓ Good |
| GZipMiddleware + Attribute Endpoint Separation | Reduces 26MB GeoJSON network load by 88% and allows instantaneous client-side theme switching | ✓ Good |
</decisions>

---
*Last updated: 2026-09-24 after doc ingest from SPEC.md and AGENTS.md*

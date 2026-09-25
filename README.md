# HeatViz — Hyperlocal Climate & Heat Vulnerability Intelligence

> **AI-powered 50m block-level urban heat vulnerability mapping, root-cause diagnostics, and targeted intervention planning for informal settlements.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Leaflet](https://img.shields.io/badge/frontend-Leaflet-199900.svg)](https://leafletjs.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Overview

Dense informal settlements face disproportionate heat stress due to contiguous corrugated metal roofs, lack of vegetation, high structural density, and limited water access. Standard meteorological stations and low-resolution satellite feeds (100m–1km) miss the microclimate canyons within settlements.

**HeatViz** bridges this resolution gap:
- Downscales satellite thermal data to **50m $\times$ 50m sectors** (36,913 sectors across Madurai, Tamil Nadu).
- Uses a **two-tier AI pipeline**: Gradient Boosted Trees (XGBoost) for physical surface downscaling + Graph Attention Networks (GAT) for neighborhood thermal diffusion.
- Computes a composite **Heat Vulnerability Index (HVI)** combining AI Heat Exposure, Social Sensitivity, and Cooling Deficit.
- Provides **explainable root-cause diagnostics** and **actionable material sizing** (cool-roof paint volumes, native tree species, water kiosks) for community planners.

---

## 2. System Architecture

```text
[Data Ingestion]
  ├── NASA/USGS Landsat 8/9 (100m Thermal Band 10)
  ├── ESA Sentinel-2 (10–20m Multi-spectral: NDVI, NDWI, NDBI)
  ├── OpenStreetMap (Urban Buildings, Road Network, Water, Greenery)
  └── WorldPop (100m Gridded Population Census)
         │
         ▼
[AI Pipeline]
  ├── Stage 00: process.py Raw Satellite & GIS Standardization (EPSG:32643)
  ├── Stage 01: Build 50m Uniform Spatial Grid (36,913 blocks in EPSG:32643)
  ├── Stage 02-03: Module 1 (XGBoost) Downscaling (100m → 20m + Bias Correction)
  ├── Stage 08: TreeSHAP Feature Attribution (Top-3 drivers per block)
  ├── Stage 04-06: Module 2 (GAT) Spatial Graph Diffusion (8-Neighbor Graph)
  └── Stage 07: HVI Scoring, Explainability Drivers & GeoJSON Export (EPSG:4326)
         │
         ▼
[Serving & Presentation]
  ├── FastAPI Backend (In-memory spatial index, GZip compression, Caching)
  └── Leaflet Web Console (HTML5 Canvas 60 FPS rendering, Zone Planner, Offline Cache)
```

---

## 3. Quickstart

### Prerequisites
- Python 3.10, 3.11, or 3.12
- `uv` (recommended) or `python3-venv`

### Fast Setup (Using Preprocessed Data — No Training Needed)

1. **Create virtual environment & install runtime dependencies:**
   ```bash
   uv venv --python 3.11 .venv
   source .venv/bin/activate
   uv pip install geopandas fastapi uvicorn
   ```

2. **Generate output layers (one-time, ~3 seconds):**
   ```bash
   python scripts/07_score_export.py
   ```

3. **Start the server:**
   ```bash
   uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
   ```

4. **Open in browser:**
   ```
   http://127.0.0.1:8000
   ```

### Running Tests
```bash
python -m pytest tests/ -q
# All 63 unit and integration tests passing
```

For full pipeline execution from raw rasters through all 8 stages, see [AGENTS.md](AGENTS.md).

---

## 4. Repository Structure

```text
├── README.md                      # Project overview, architecture, and quickstart
├── SPEC.md                        # Technical specification, math formulas, and gate thresholds
├── AGENTS.md                      # Autonomous implementation rules and execution contract
├── memory.md                      # Execution status, verification metrics, and session history
│
├── api/                           # FastAPI Backend
│   ├── main.py                    # REST endpoints, static mounts, GZip & attribute cache
│   ├── admin.py                   # PIN auth, zonal hierarchy & sensitive facilities directory
│   ├── rules.py                   # Deterministic microclimate intelligence, trajectory & bilingual advisory
│   ├── weather.py                 # Multi-model WBGT calculation, 12-day timeline & IMD composite heatwave alerts
│   ├── sms.py                     # Twilio SMS / WhatsApp dispatch integration & fallback handler
│   └── audit.py                   # Persistent SQLite emergency dispatch audit trail
│
├── web/                           # Client-side Web Applications
│   ├── officer.html / officer.js  # Officer Command Center with 12-day historical scrubber & dispatch audit viewer
│   ├── admin.js                   # Administrative command drawer, PIN login, facility directory & bulk alerts
│   ├── public.html / public.js    # Mobile-first Citizen Heat Safety Portal with bilingual Tamil/English guidance
│   ├── app.js                     # Leaflet Canvas engine, layer toggles, zone drawing, PWA cache
│   └── style.css                  # Institutional dashboard styling & risk color variables
│
├── process.py                     # Raw satellite & GIS ingestion, warping, and 20m raster generation
├── scripts/                       # Ordered Pipeline Stages (01 to 08)
│   ├── 01_build_blocks.py         # Grid creation & raster zonal statistics
│   ├── 02_train_module1.py        # XGBoost thermal downscaling training
│   ├── 08_compute_shap.py         # TreeSHAP feature attributions
│   ├── 03_infer_module1.py        # 20m inference & mean-preserving bias correction
│   ├── 04_build_graph.py          # 8-neighbor spatial graph construction
│   ├── 05_train_module2.py        # PyTorch Geometric GAT model training
│   ├── 06_infer_module2.py        # Contextual neighborhood heat inference
│   └── 07_score_export.py         # HVI composite scoring, drivers & GeoJSON export
│
├── tests/                         # Automated Test Suite (63 Tests)
│   ├── test_admin.py              # Zonal hierarchy, PIN auth & facility endpoints
│   ├── test_audit.py              # SQLite audit persistence & querying
│   ├── test_forecast_api.py       # Weather endpoint responses & caching
│   ├── test_full_wbgt.py          # Liljegren outdoor solar WBGT formulas
│   ├── test_gap_fixes.py          # Attribute mapping & spatial bounds
│   ├── test_health_risk.py        # WBGT health risk tier classification
│   ├── test_rules_complete.py     # Deterministic intelligence, SHAP & Tamil translation
│   ├── test_shap.py               # TreeSHAP consistency & cache loading
│   ├── test_sms.py                # Twilio SMS client & payload verification
│   ├── test_ui_and_alerts.py      # Layer attribute endpoints & status codes
│   └── test_weather.py            # ECMWF/ICON/GFS multi-model blending
│
├── data/                          # Spatial Data Assets
│   ├── processed/                 # Aligned 20m rasters & intermediate GeoJSONs
│   ├── output/                    # Exported GeoJSON layers for web serving
│   ├── fallback_forecast.json     # Offline contingency weather baseline
│   └── audit_log.db               # SQLite dispatch audit database
│
└── docs/                          # In-depth Documentation
    ├── DATASETS.md                # 5 core satellite and urban data sources reference
    ├── DATA_DOWNLOAD.md           # Download procedures and band extraction guide
    ├── RESEARCH.md                # Physiological heat stress and microclimate downscaling framework
    ├── LST_GUIDE.md               # Land surface temperature physics, sensors & processing
    └── UI-SPEC.md                 # Citizen portal visual tokens & component specification
```

---

## 5. Documentation Directory

| Document | Purpose |
|---|---|
| [README.md](README.md) | Entry point: High-level overview, architecture, and quick start |
| [SPEC.md](SPEC.md) | Authoritative technical specification: Constants, mathematical formulas, gate checks |
| [docs/DATASETS.md](docs/DATASETS.md) | Satellite (Landsat/Sentinel) & GIS data provenance, sensors, and bands |
| [docs/DATA_DOWNLOAD.md](docs/DATA_DOWNLOAD.md) | Official download portals, search queries, and band conversion steps |
| [docs/RESEARCH.md](docs/RESEARCH.md) | Heat stress epidemiology, WBGT Liljegren formulation, and urban mitigation science |
| [docs/LST_GUIDE.md](docs/LST_GUIDE.md) | Land surface temperature physics, spaceborne TIRS sensors & downscaling |
| [docs/UI-SPEC.md](docs/UI-SPEC.md) | Citizen portal design specification, tokens, and bilingual Tamil components |
| [AGENTS.md](AGENTS.md) | Implementation protocol and execution rulebook for automated agents |
| [memory.md](memory.md) | Append-only execution history, calibration records, and gate metrics |

---

## 6. Core Features & Capabilities

- **Interactive 50m Sector Inspector**: Click any sector to view physical Land Surface Temperature, thermal anomaly vs. settlement baseline, building density, and population exposure.
- **12-Day Continuous Timeline (Past 7 Days Replay + 5-Day Forecast)**: Retrospective historical analysis and predictive multi-model ensemble (ECMWF + ICON + GFS) via Open-Meteo.
- **Dual Composite Heatwave Alert**: Synthesizes official IMD plains heatwave thresholds ($T_{\max} \ge 40^\circ\text{C}$, departure $\ge +4.5^\circ\text{C}$) with NDMA physiological WBGT danger tiers ($30^\circ\text{C}, 34^\circ\text{C}, 38^\circ\text{C}$).
- **Physiological WBGT Calibration**: Uses concurrent daytime minimum humidity ($RH_{\min} \approx 28\text{--}35\%$) at peak $T_{\max}$ to prevent synthetic nocturnal humidity inflation.
- **Citizen Heat Safety Portal (`/public`)**: Mobile-first, bilingual English and Tamil (தமிழ்) advisory portal with location lookup, danger hours, and hydration stations.
- **Sensitive Facilities Command Directory**: PIN-authenticated administrative drawer managing 30 schools, hospitals, clinics, and colleges across Madurai with live contact editing and one-click emergency SMS broadcast via Twilio.
- **Explainable Root Causes (TreeSHAP)**: Identifies dominant drivers using TreeSHAP attributions with quantitative contributions.
- **Targeted Interventions**: Recommends customized remediation (elastomeric cool-roof paint liters, native Tamil Nadu shade tree counts, hydration nodes).
- **Persistent Dispatch Audit Trail**: SQLite-backed emergency broadcast logger (`data/audit_log.db`) tracking targeted SMS/WhatsApp advisories.
- **Sub-Layer Suite**: Instant switching across 8 thematic layers with sub-16ms transitions.
- **Zone Planner Tool**: Draw custom polygon boundaries directly on the map to compute aggregate population, mean temperature, and risk distribution.
- **Offline Tile Caching**: Built-in CacheStorage integration allows downloading and viewing base tiles with zero network latency.
- **Rigorous Test Suite**: 63 automated tests verifying weather physics, XGBoost/GAT pipelines, SHAP explainability, deterministic rules, and dispatch integrity.

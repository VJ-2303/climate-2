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
- Downscales satellite thermal data to **50m $\times$ 50m sectors** (18,040 sectors across Kibera, Nairobi).
- Uses a **two-tier AI pipeline**: Gradient Boosted Trees (XGBoost) for physical surface downscaling + Graph Attention Networks (GAT) for neighborhood thermal diffusion.
- Computes a composite **Heat Vulnerability Index (HVI)** combining AI Heat Exposure, Social Sensitivity, and Cooling Deficit.
- Provides **explainable root-cause diagnostics** and **actionable material sizing** (cool-roof paint volumes, native tree species, water kiosks) for community planners.

---

## 2. System Architecture

```text
[Data Ingestion]
  ├── NASA/USGS Landsat 8/9 (100m Thermal Band 10)
  ├── ESA Sentinel-2 (10–20m Multi-spectral: NDVI, NDWI, NDBI)
  ├── OpenStreetMap (36,438 Buildings, 5,952 Paths, Water, Greenery)
  └── WorldPop (100m Gridded Population Census)
         │
         ▼
[AI Pipeline]
  ├── Stage 01: Build 50m Uniform Spatial Grid (18,040 blocks in EPSG:32737)
  ├── Stage 02-03: Module 1 (XGBoost) Downscaling (100m → 20m + Bias Correction)
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

For advanced setup (including training XGBoost and GAT from raw rasters), see [SETUP.md](SETUP.md).

---

## 4. Repository Structure

```text
├── README.md                      # Project overview, architecture, and quickstart
├── SETUP.md                       # Detailed execution and environment setup guide
├── SPEC.md                        # Technical specification, math formulas, and gate thresholds
├── AGENTS.md                      # Autonomous implementation rules and execution contract
├── memory.md                      # Execution status, verification metrics, and session history
│
├── api/                           # FastAPI Backend
│   ├── main.py                    # REST endpoints, static mounts, GZip & attribute cache
│   └── rules.py                   # Rule-based microclimate intelligence & intervention engine
│
├── web/                           # Client-side GIS Web Application
│   ├── index.html                 # Semantic UI layout (map, drawers, overview modal, controls)
│   ├── app.js                     # Leaflet Canvas engine, layer toggles, zone drawing, PWA cache
│   └── style.css                  # Institutional dashboard styling & risk color variables
│
├── scripts/                       # Ordered Pipeline Stages (01 to 07)
│   ├── 01_build_blocks.py         # Grid creation & raster zonal statistics
│   ├── 02_train_module1.py        # XGBoost thermal downscaling training
│   ├── 03_infer_module1.py        # 20m inference & mean-preserving bias correction
│   ├── 04_build_graph.py          # 8-neighbor spatial graph construction
│   ├── 05_train_module2.py        # PyTorch Geometric GAT model training
│   ├── 06_infer_module2.py        # Contextual neighborhood heat inference
│   └── 07_score_export.py         # HVI composite scoring, drivers & GeoJSON export
│
├── data/                          # Spatial Data Assets
│   ├── processed/                 # Aligned 20m rasters & intermediate GeoJSONs
│   └── output/                    # Exported GeoJSON layers for web serving
│
└── docs/                          # In-depth Documentation
    └── DATASETS.md                # 5 core satellite and urban data sources reference
```

---

## 5. Documentation Directory

| Document | Purpose |
|---|---|
| [README.md](README.md) | Entry point: High-level overview, architecture, and quick start |
| [SETUP.md](SETUP.md) | Step-by-step installation instructions for preprocessed and training modes |
| [SPEC.md](SPEC.md) | Authoritative technical specification: Constants, mathematical formulas, gate checks |
| [docs/DATASETS.md](docs/DATASETS.md) | Satellite (Landsat/Sentinel) & GIS data provenance, sensors, and bands |
| [AGENTS.md](AGENTS.md) | Implementation protocol and execution rulebook for automated agents |
| [memory.md](memory.md) | Append-only execution history and gate validation metrics |

---

## 6. Core Features & Capabilities

- **Interactive 50m Sector Inspector**: Click any sector to view physical Land Surface Temperature, thermal anomaly vs. settlement baseline, building density, and population exposure.
- **Explainable Root Causes**: Identifies dominant drivers (e.g., poor water access, low vegetation canopy, high metal-roof density).
- **Targeted Interventions**: Recommends customized remediation (elastomeric cool-roof paint liters, native Kenyan shade tree counts, hydration nodes).
- **Sub-Layer Suite**: Instant switching across 8 thematic layers (Composite HVI, Thermal Exposure, Social Sensitivity, Cooling Deficit, NDVI, NDBI, Building Footprint, Population Density) with sub-16ms transitions.
- **Zone Planner Tool**: Draw custom polygon boundaries directly on the map to compute aggregate population, mean temperature, and risk distribution.
- **Offline Tile Caching**: Built-in CacheStorage integration allows downloading and viewing base tiles with zero network latency.
- **Zero API Key Required**: Built entirely on open GIS standards using OpenStreetMap and ESRI World Imagery.

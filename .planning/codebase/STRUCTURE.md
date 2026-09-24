# Codebase Structure

**Analysis Date:** 2026-09-24

## Directory Layout

```
climate-2/
├── api/                    # FastAPI backend and intelligence rules
│   ├── main.py             # Server entry point, endpoints, caching
│   ├── rules.py            # Deterministic block diagnosis, SHAP top-3, advisories
│   └── weather.py          # Open-Meteo fetching, WBGT calculations, caching
├── data/                   # Data layers and outputs
│   ├── processed/          # 9 master 20m GeoTIFFs, 50m block GeoJSON, SHAP json
│   ├── output/             # Final vulnerability_blocks.geojson, layer sub-GeoJSONs
│   └── fallback_forecast.json # Offline 5-day weather backup
├── docs/                   # Scientific documentation and data source specs
│   ├── DATASETS.md         # Source dataset specifications and links
│   ├── DATA_DOWNLOAD.md    # Instructions for raw satellite band downloads
│   └── RESEARCH.md         # Research literature and mathematical formulas
├── models/                 # Serialized ML & GNN models (generated, gitignored)
├── scripts/                # Standalone pipeline stages (01 to 08)
│   ├── 01_build_blocks.py  # 50m vector grid generation and zonal stats
│   ├── 02_train_module1.py # XGBoost downscaler training
│   ├── 03_infer_module1.py # 20m raster inference & bias correction
│   ├── 04_build_graph.py   # PyTorch Geometric 8-neighbor graph builder
│   ├── 05_train_module2.py # HeatGAT model training
│   ├── 06_infer_module2.py # Contextual AI heat inference
│   ├── 07_score_export.py  # HVI scoring, driver ranking, GeoJSON export
│   └── 08_compute_shap.py  # TreeSHAP feature attributions
├── tests/                  # Pytest test suite
│   ├── test_forecast_api.py # Forecast endpoints and payload formats
│   ├── test_full_wbgt.py   # Wet-bulb globe temperature formulas
│   ├── test_gap_fixes.py   # Edge cases, missing data, and normalization
│   ├── test_health_risk.py # Block intelligence and health risk tier classification
│   ├── test_shap.py        # SHAP factor structure and top-3 attributions
│   ├── test_ui_and_alerts.py # SMS dispatch simulation and API responses
│   └── test_weather.py     # Open-Meteo URL building, caching, and fallback
├── web/                    # Static frontend web application
│   ├── app.js              # Leaflet core map engine, layers, drawer
│   ├── officer.js          # Officer command center extensions (SHAP, forecast, SMS)
│   ├── officer.html        # Primary officer command center UI
│   ├── index.html          # Public / baseline view
│   └── style.css           # Styling, design tokens, responsive layout
├── AGENTS.md               # Implementation contract and immutable constants
├── SPEC.md                 # Authoritative project specification
├── process.py              # Raw data preprocessing & inpainting pipeline
├── pyproject.toml          # UV project configuration and dependencies
└── requirements.txt        # Standard pip dependency manifest
```

## Directory Purposes

**`api/`:**
- Purpose: Asynchronous backend application serving spatial layers, block intelligence, and forecast calculations.
- Contains: Python modules with FastAPI routes, Pydantic data schemas, weather fetchers, and rule engines.
- Key files:
  - `api/main.py`: ASGI entry point, startup lifespan caching, route handlers, GZip middleware.
  - `api/rules.py`: Deterministic block intelligence generator producing physical descriptions, thermal causes, intervention sizing, and 5-day trajectories.
  - `api/weather.py`: Open-Meteo API consumer with 1-hour cache and WBGT daily maximum calculator.

**`scripts/`:**
- Purpose: Numbered, sequential data pipeline stages from vector block generation to final GeoJSON export.
- Contains: Standalone Python CLI scripts executing in sequence: `01 -> 02 -> 08 -> 03 -> 04 -> 05 -> 06 -> 07`.
- Key files:
  - `scripts/01_build_blocks.py`: Generates 50m polygon grid clipped to Madurai municipal boundary.
  - `scripts/02_train_module1.py`: Trains XGBoost LST downscaling model on Landsat pixels.
  - `scripts/08_compute_shap.py`: Computes TreeSHAP local feature attributions per sector block.
  - `scripts/07_score_export.py`: Evaluates Gate G7, computes HVI scores, and exports GeoJSON files to `data/output/`.

**`data/`:**
- Purpose: Stores input rasters, intermediary vector datasets, model outputs, and offline backups.
- Subdirectories:
  - `data/processed/`: 9 standardized 20m rasters (EPSG:32643), `madurai_blocks_50m.geojson`, and `block_shap_explanations.json`.
  - `data/output/`: Exported final `vulnerability_blocks.geojson` and `layers/*.geojson` (EPSG:4326).

**`web/`:**
- Purpose: Client-side single page application (SPA) providing map navigation and officer decision support.
- Key files:
  - `web/officer.html`: Officer command center interface.
  - `web/app.js`: Core Leaflet map engine, CachedTileLayer, GeoJSON canvas renderer, and event listeners.
  - `web/officer.js`: Extensions for SHAP waterfall visualization, sparklines, forecast timelines, and SMS modal.
  - `web/style.css`: Clean, high-contrast dark/light theme CSS with responsive breakpoints.

**`tests/`:**
- Purpose: Automated test coverage validating API contracts, weather calculations, and data constraints.
- Key files: 7 test files prefixed with `test_*.py` executed via Pytest.

## Key File Locations

**Entry Points:**
- API Web Server: `api/main.py`
- Preprocessing Script: `process.py`
- Pipeline Execution: `scripts/01_build_blocks.py` through `scripts/07_score_export.py`
- Web Dashboard: `web/officer.html`

**Configuration & Specifications:**
- Implementation Contract: `AGENTS.md`
- Authoritative Science & UI Spec: `SPEC.md`
- Package Config: `pyproject.toml`, `requirements.txt`
- Git Ignore: `.gitignore`

## Naming Conventions

**Pipeline Scripts:**
- Pattern: `scripts/0X_action_module.py` (two-digit prefix indicating execution sequence).

**API Modules:**
- Pattern: `snake_case.py` (e.g. `main.py`, `rules.py`, `weather.py`).

**Test Files:**
- Pattern: `tests/test_<feature>.py` (discovered automatically by Pytest).

**Web Assets:**
- Pattern: `kebab-case` or descriptive filenames (`app.js`, `officer.js`, `style.css`).

## Where to Add New Code

**New API Endpoint:**
- Define route handler in `api/main.py`.
- Add business/climate logic into `api/rules.py` or `api/weather.py`.
- Add corresponding test in `tests/test_<feature>.py`.

**New Pipeline Stage:**
- Create `scripts/0X_<description>.py`.
- Add explicit gate checks with `sys.exit(1)` on failure.
- Update `AGENTS.md` and pipeline runner documentation.

**New Web Visualization Feature:**
- Add HTML markup in `web/officer.html`.
- Add presentation logic and event handlers in `web/officer.js` or `web/app.js`.
- Add design styles in `web/style.css`.

---

*Structure analysis: 2026-09-24*
*Update after directory structure changes*

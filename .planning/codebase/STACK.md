# Technology Stack

**Analysis Date:** 2026-09-24

## Languages

**Primary:**
- Python 3.12 - All pipeline stages, machine learning modules, backend API services, and data transformation scripts (`scripts/`, `api/`, `process.py`, `tests/`)

**Secondary:**
- JavaScript (ES6+) - Interactive web frontend map engine, officer command center dashboard, dynamic charting, and SMS dispatch UI (`web/app.js`, `web/officer.js`)
- HTML5 / CSS3 - UI structure, styling, responsive layouts, and modal components (`web/index.html`, `web/officer.html`, `web/style.css`)

## Runtime

**Environment:**
- CPython 3.12.9 (Windows x86_64 / Linux / macOS)
- Modern Web Browser (Chrome, Firefox, Edge, Safari) supporting Canvas and CacheStorage API

**Package Manager:**
- `uv` (v0.5+) with `pyproject.toml` and `uv.lock`
- Standard `pip` compatibility via `requirements.txt`

## Frameworks

**Core Backend:**
- FastAPI (>=0.100.0) - High-performance asynchronous REST API serving GeoJSON vector tiles, block intelligence, and forecast data (`api/main.py`)
- Uvicorn (>=0.22.0) - ASGI web server implementation
- Pydantic (>=2.0.0) - Data validation and settings management

**Machine Learning & Graph AI:**
- XGBoost (>=2.0.0) - Module 1 Land Surface Temperature downscaling model (`scripts/02_train_module1.py`, `scripts/03_infer_module1.py`) and context-guided inpainting
- PyTorch (>=2.0.0) - Deep learning computation engine for spatial representations
- PyTorch Geometric (torch-geometric >=2.4.0) - Module 2 HeatGAT (Graph Attention Network) for neighborhood heat spillover modeling (`scripts/04_build_graph.py`, `scripts/05_train_module2.py`, `scripts/06_infer_module2.py`)
- SHAP (TreeExplainer) - Local feature attribution and explainable AI top-factor calculation (`scripts/08_compute_shap.py`)

**Geospatial & Scientific Computing:**
- GeoPandas (>=0.14.0) & Shapely (>=2.0.0) - Vector geometry processing, spatial joins, coordinate transformations, and GeoJSON serialization
- Rasterio (>=1.3.0) & PyProj (>=3.5.0) - Raster I/O, reprojection, and affine transformations
- NumPy (>=1.24.0) & SciPy (>=1.10.0) - Matrix manipulation, percentile normalization, and Euclidean distance transform (`distance_transform_edt`)
- Matplotlib (>=3.7.0) & Pillow (>=10.0.0) - Scientific visualization and image operations

**Testing:**
- Pytest (>=9.0.0) - Test runner and assertion framework (`tests/`)
- HTTPX (>=0.28.0) - Asynchronous and synchronous HTTP client backing `fastapi.testclient.TestClient`

**Frontend Libraries (CDN-loaded):**
- Leaflet (1.9.4) - Interactive mapping engine with Canvas-based vector polygon rendering
- Leaflet.draw (1.0.4) - Spatial polygon drawing controls for intervention zone planning
- Turf.js (6.5.0) - Client-side geospatial analysis (point-in-polygon, centroid calculations)

## Key Dependencies

**Critical:**
- `fastapi` & `uvicorn` - Power the entire API layer and static frontend serving
- `torch-geometric` & `torch` - Underpin the spatial Graph Attention Network for microclimate smoothing
- `xgboost` - Powers satellite Land Surface Temperature (LST) super-resolution
- `geopandas` & `rasterio` - Handle all 20m raster manipulation and 50m vector micro-sector tiling

**Infrastructure:**
- `GZipMiddleware` (`fastapi.middleware.gzip`) - Provides ~88% gzip compression on 26MB GeoJSON network payloads
- `aiohttp` / `urllib` - Open-Meteo external weather fetching with fallback handling

## Configuration

**Environment:**
- Offline-first configuration: no mandatory cloud API keys required for core execution
- Local file caches and fallback datasets (`data/fallback_forecast.json`) ensure functionality without internet access

**Build & Tooling:**
- `pyproject.toml` - Python project dependencies and build system configuration (`uv_build`)
- `.gitignore` - Enforces exclusions for `.venv/`, `data/raw/`, `models/`, and `data/output/`
- `AGENTS.md` / `SPEC.md` - Definitive architectural specification and immutable pipeline constants

## Platform Requirements

**Development:**
- Windows 10/11, Ubuntu 22.04+, or macOS
- Python 3.12+ with UV or standard Python virtual environment
- GDAL/PROJ C-libraries (bundled automatically via PyPI binary wheels for Rasterio/GeoPandas)

**Production:**
- Lightweight Linux container (Docker) or standalone server running `uvicorn api.main:app`
- Minimum 4GB RAM recommended for PyG graph construction and 26MB GeoJSON in-memory caching

---

*Stack analysis: 2026-09-24*
*Update after major dependency changes*

# Coding Conventions

**Analysis Date:** 2026-09-24

## Naming Patterns

**Files & Directories:**
- Pipeline scripts: Prefixed with execution order, e.g. `scripts/01_build_blocks.py`, `scripts/07_score_export.py`
- Python backend modules: Lowercase `snake_case.py`, e.g. `api/main.py`, `api/rules.py`, `api/weather.py`
- Test files: Prefixed with `test_*.py`, e.g. `tests/test_forecast_api.py`
- Frontend assets: Lowercase `kebab-case` or concise names, e.g. `web/app.js`, `web/officer.js`, `web/style.css`

**Python Functions & Variables:**
- Functions: `snake_case()`, e.g. `build_block_intelligence()`, `calculate_full_wbgt()`, `load_dataset_into_memory()`
- Variables: `snake_case`, e.g. `block_id`, `heat_exposure`, `surface_temp`
- Global Constants: `UPPER_SNAKE_CASE`, e.g. `SEED`, `PROCESS_CRS`, `OUTPUT_CRS`, `WORKING_RES`, `BLOCK_SIZE`, `DIST_CAP`, `NODATA`

**JavaScript Functions & Variables:**
- Functions: `camelCase()`, e.g. `renderPrimaryLayer()`, `openSidebar()`, `selectForecastDay()`
- Global Objects / Constants: `UPPER_SNAKE_CASE`, e.g. `RISK_COLORS`, `THEMATIC_PALETTES`, `MADURAI_BOUNDS_2X`, `CENTER`
- Variables: `camelCase`, e.g. `currentLayer`, `primaryData`, `activeForecastDay`

**GeoJSON Property Keys (Exact Specification — Never Rename):**
- Output feature attributes in `vulnerability_blocks.geojson` must strictly match:
  `block_id`, `risk_class`, `hvi_score`, `hvi_raw`, `ai_heat_exposure`, `social_sensitivity`, `cooling_deficit`, `surface_temp_celsius`, `temp_anomaly_celsius`, `estimated_population`, `priority`, `top_drivers`, `intervention`, `shap_top_factors`, `distance_to_water`, `distance_to_green`, `ndvi`, `ndwi`, `ndbi`, `building_density`, `population_density`, `geometry`

## Code Style & Formatting

**Python:**
- Target version: Python 3.12+
- Type Hints: Type annotations used on all public API endpoints and rule functions (`typing.Dict`, `typing.List`, `typing.Tuple`, `typing.Any`)
- Imports: Standard library first (`json`, `logging`, `pathlib`), followed by third-party packages (`fastapi`, `geopandas`, `numpy`, `rasterio`), followed by local application modules (`from api.rules import ...`)
- Logging: Standard library `logging.getLogger("heatviz.api")` used instead of raw `print` statements in the `api/` package

**JavaScript:**
- Target version: ECMAScript 2022+ (vanilla, no transpiler)
- Strict mode: IIFE pattern with `"use strict";` in modular extensions (`web/officer.js`)
- Color Standards: High-contrast domain-specific ramps:
  - Low: `#1a9850`
  - Medium: `#ffffbf`
  - High: `#f46d43`
  - Critical: `#d73027`

## Error Handling & Architectural Gates

**Pipeline Quality Gates (Hard Prohibitions):**
- Pipeline stages must fail fast and explicitly: gate failures immediately trigger `sys.exit(1)`.
- Never use silent `try/except` blocks that suppress gate failures or substitute synthetic default data.
- Quality gates enforced:
  - G1 (`01_build_blocks.py`): Valid blocks >= 500
  - G2 & G3 (`02_train_module1.py`): Samples >= 1000, Validation R² >= 0.25, MAE <= 1.5°C
  - G4 (`03_infer_module1.py`): Cell-mean difference <= 0.01°C
  - G5 (`05_train_module2.py`): Validation Pearson correlation >= 0.90
  - G6 (`06_infer_module2.py`): Standard deviation of `contextual_ai_heat` >= 5.0
  - G7 (`07_score_export.py`): Top-decile HVI blocks exhibit lower NDVI and higher building density than overall mean

**API Error Handling:**
- Route parameters and block identifiers validated against in-memory dictionary.
- Missing entities raise `fastapi.HTTPException(status_code=404, detail="...")`.
- External service failures (e.g. Open-Meteo downtime) catch network exceptions and seamlessly fall back to local `data/fallback_forecast.json` with warning logs.

---

*Conventions analysis: 2026-09-24*
*Update when coding standards evolve*

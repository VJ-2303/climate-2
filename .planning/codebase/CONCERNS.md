# Codebase Concerns

**Analysis Date:** 2026-09-24

## Tech Debt

**1. Primary Vector Payload Size (26MB GeoJSON):**
- Issue: `data/output/vulnerability_blocks.geojson` is 26.7 MB on disk containing all 36,913 50m micro-sector polygons.
- Why: High spatial fidelity requires every individual 50m block geometry to be available for interactive rooftop/street level inspection.
- Impact: Initial page load must download and parse a large GeoJSON structure, causing ~500ms-1500ms client parsing delay on slower hardware.
- Current mitigation: Handled via `GZipMiddleware` in `api/main.py` (reducing network payload from 26MB to ~3.2MB) and attribute-only lightweight JSON endpoints (`/api/layers/{name}/attributes`) for instant layer switching without re-downloading geometries.
- Long-term fix approach: Generate dynamic Vector Tiles (MVT / Mapbox Vector Tiles or PMTiles) with spatial indexing for production deployment.

**2. Deprecated `datetime.utcnow()` in SMS Dispatch:**
- Issue: `api/main.py:205` calls `datetime.utcnow().strftime(...)`.
- Why: Standard legacy Python datetime timestamping.
- Impact: Emits Python 3.12 `DeprecationWarning` during test runs; scheduled for removal in future Python releases.
- Fix approach: Update to `datetime.now(datetime.timezone.utc)` (or `datetime.now(datetime.UTC)`).

**3. TestClient Deprecation Warning with Starlette:**
- Issue: `tests/` trigger `StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated; install httpx2 instead.`
- Why: Recent Starlette versions transition toward modern test client bindings.
- Impact: Non-fatal test warnings during Pytest execution.

**4. Legacy Bounding Variable Nomenclature:**
- Issue: Variables like `KIBERA_BOUNDS_2X = MADURAI_BOUNDS_2X` and block ID prefixes (`KIB-0001`) remain in `web/app.js` and `api/`.
- Why: Retained to maintain strict compatibility with test suites and immutable property schemas specified in `SPEC.md`.
- Impact: Slight naming cognitive dissonance for developers working exclusively on Madurai.

## Known Fragile Areas

**1. Generated Output Dependency (`data/output/`):**
- Why fragile: Both `data/output/` and `models/` are excluded by `.gitignore`.
- Common failures: On a fresh repository clone, `data/output/vulnerability_blocks.geojson` does not exist. Starting the server without running Stage 7 will cause the frontend map to fail with a 404 alert (`Could not load vulnerability dataset`).
- Safe modification: Ensure `scripts/07_score_export.py` (or the full pipeline `scripts/01` - `07`) is executed to generate the required GeoJSONs prior to starting the web service.

**2. Strict Gate Pipeline Architecture:**
- Why fragile: Pipeline stages `01` through `07` have strict assertion gates (e.g. G3: Validation R² >= 0.25 and MAE <= 1.5; G5: Pearson >= 0.90; G7: Top-decile HVI NDVI check).
- Common failures: Modifying raster inputs, normalization percentiles, or CRS constants can cause gate failure and trigger immediate `sys.exit(1)`.
- Safe modification: Adhere strictly to the frozen constants and thresholds in `SPEC.md §2` and `AGENTS.md`.

## Security Considerations

**1. Open-Meteo Rate Limiting & Network Resilience:**
- Risk: Excessive outbound requests to Open-Meteo public endpoints could lead to IP rate limiting.
- Current mitigation: Robust 1-hour in-memory cache in `api/weather.py` minimizes external calls. Any HTTP or network failure automatically falls back to `data/fallback_forecast.json` without failing requests or alerting users.
- Recommendations: In production, configure an optional private weather forecast caching proxy or dedicated API key if call volume increases.

**2. SMS Dispatch Simulation:**
- Risk: Unauthorized bulk alerting if exposed directly to the public internet.
- Current mitigation: `/api/alerts/dispatch` is currently an internal simulation endpoint returning structured audit logs.
- Recommendations: When connecting to real SMS gateways (e.g. TNSDMA CAP / BSNL), implement authentication tokens, role-based access control (RBAC), and daily dispatch quotas.

## Performance Bottlenecks

**1. In-Memory Startup Ingestion (`load_dataset_into_memory`):**
- Problem: The first time an endpoint accessing `blocks_db` is called (or on server boot), the API reads and parses 26MB of GeoJSON and 28MB of SHAP explanations.
- Measurement: Takes ~1.5 - 2.5 seconds on server startup.
- Cause: Reading large uncompressed JSON files from disk and constructing Python dictionary objects and 2D grid indexes for 36,913 blocks.
- Improvement path: Pre-serialize the parsed database into a binary format (e.g. SQLite database, Arrow, or DuckDB) for instant startup.

**2. Browser Canvas Rendering of 36k Polygons:**
- Problem: Leaflet SVG rendering would crash browser tabs when rendering 36k vector polygons.
- Current mitigation: Map engine uses `L.canvas({ padding: 0.5 })`, keeping rendering smooth (60fps) on modern desktop browsers.

## Scaling Limits

**Geographic Scope:**
- The current pipeline and models are hyper-tuned specifically for Madurai, Tamil Nadu (UTM Zone 43N, EPSG:32643, center lat: 9.921851, lon: 78.118200).
- Scaling to other cities requires acquiring localized Sentinel-2, Landsat, OSM, and boundary data, updating CRS parameters in `AGENTS.md`, and re-running the full training and GAT pipeline.

---

*Concerns audit: 2026-09-24*
*Update as issues are resolved or discovered*

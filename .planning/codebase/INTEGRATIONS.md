# External Integrations

**Analysis Date:** 2026-09-24

## APIs & External Services

**Weather & Climate Forecasts:**
- Open-Meteo Historical & Forecast Weather API (`https://api.open-meteo.com/v1/forecast`)
  - Used for: Hyperlocal meteorological forcing data for Madurai (lat: 9.921851, lon: 78.118200)
  - Client: Python `urllib.request` / `requests` in `api/weather.py`
  - Parameters requested: `temperature_2m`, `relative_humidity_2m`, `direct_normal_irradiance`, `diffuse_radiation`, `wind_speed_10m`, `timezone=Asia/Kolkata`
  - Authentication: None required (free public tier)
  - Caching & Fallback: In-memory 1-hour TTL cache; on network failure or rate limit, automatically falls back to offline local baseline (`data/fallback_forecast.json`) without interrupting the server
  - Metrics derived: Wet-Bulb Globe Temperature (WBGT) daily maxima and 5-day heatwave risk tiers

**Map Basemap & Tile Services:**
- OpenStreetMap Carto Light:
  - URL template: `https://tile.openstreetmap.org/{z}/{x}/{y}.png`
  - Used for: Default clean cartographic reference layer
  - Client: Leaflet `CachedTileLayer` (`web/app.js`)
- ESRI World Imagery:
  - URL template: `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}`
  - Used for: High-resolution satellite rooftop and land-cover verification
- ESRI World Boundaries & Places:
  - URL template: `https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}`
  - Used for: Satellite place name and administrative label overlay

## Data Storage & Formats

**Geospatial Rasters (GeoTIFF):**
- Storage: Local filesystem (`data/processed/`)
- Format: Single-band Cloud-Optimized GeoTIFF (`.tif`), EPSG:32643, 20m resolution, LZW compression
- Key rasters: `ndvi.tif`, `ndwi.tif`, `ndbi.tif`, `landsat_st_celsius.tif`, `building_density.tif`, `road_density.tif`, `distance_to_green.tif`, `distance_to_water.tif`, `population_density_20m.tif`, `ai_heat_base_20m.tif`

**Vector Micro-Sectors (GeoJSON):**
- Storage: Local filesystem (`data/output/` and `data/processed/`)
- Coordinate Reference System: Reprojected to standard web WGS84 (`EPSG:4326`)
- Key files:
  - `data/output/vulnerability_blocks.geojson` (36,913 polygons with full HVI properties, physical temperatures, and SHAP factors)
  - `data/output/layers/*.geojson` (individual attribute sub-layers for fast loading)

**In-Memory Databases & Caching:**
- `blocks_db`: Fast hash map (`dict[str, dict]`) storing all 36,913 block feature properties for instant lookup by `block_id`
- `block_to_grid` & `grid_to_block`: 2D spatial coordinate index mapping `(grid_i, grid_j)` to `block_id` for O(1) 8-neighbor spatial queries
- `shap_db`: Hash map storing TreeSHAP feature attributions and base expected values from `data/processed/block_shap_explanations.json`
- `layer_attributes_cache`: In-memory key-value dictionary (`{block_id: score}`) allowing client to switch between map themes without downloading 26MB GeoJSON geometries repeatedly

## Authentication & Identity

**Current Architecture:**
- Operational Role Model: Officer Command Center (`web/officer.html`) designed for municipal disaster management officers, urban planners, and primary healthcare centers (UPHC)
- Public / Authentication: Currently runs on trusted internal municipal network or localhost without session authentication. No external OAuth or database identity provider required.

## Emergency Alert & Communication Integration

**SMS & Emergency Broadcast Simulation:**
- Endpoint: `POST /api/alerts/dispatch` (`api/main.py`)
- Purpose: Dispatches localized heat warning advisories directly to vulnerable communities in selected micro-sectors
- Integrated Delivery Channels (Simulated):
  - TNSDMA Common Alerting Protocol (CAP) / BSNL SMS Gateway
  - WhatsApp Emergency Community Broadcast
  - Urban Primary Health Centre (UPHC) Ward Volunteers Outreach
  - 108 Emergency Ambulance Staging Notifications
- Audit trail: Returns unique audit ID (`DISP-XXXXXXXX`), ISO-8601 UTC timestamp, recipient count, and verification status

## Environment Configuration

**Required Variables:**
- None required for standard offline operation. The platform is self-contained.

**Offline & Local Stubs:**
- Offline weather fallback: `data/fallback_forecast.json` contains precomputed 5-day WBGT values for Madurai
- Browser tile cache: `web/app.js` registers a custom `CachedTileLayer` using the browser's `CacheStorage` API (`heatviz-tiles-v2`), caching downloaded map tiles locally so maps remain functional during network dropouts

---

*Integration audit: 2026-09-24*
*Update when adding/removing external services*

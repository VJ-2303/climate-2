# Ingested Context

## Domain Background: Madurai Heat Vulnerability
- source: `SPEC.md §1`, `docs/RESEARCH.md`
- context: Madurai is an ancient, rapidly growing industrial and cultural center in southern Tamil Nadu, characterized by intense summer temperatures, dense urban settlements, low tree canopy cover, and substantial vulnerable populations in informal settlements. Rapid urbanization and high impervious surface fractions amplify the Urban Heat Island (UHI) effect.

## Primary Data Sources
- source: `docs/DATASETS.md`, `docs/DATA_DOWNLOAD.md`
- context:
  1. Sentinel-2 MSI (Copernicus): Bands B02, B03, B04, B08, B11, B12 at 10m/20m for optical indices (NDVI, NDWI, NDBI).
  2. Landsat 8/9 Collection 2 Tier 1 (USGS): Thermal band 10 (100m native resampled to 30m) for surface temperature calibration.
  3. OpenStreetMap (OSM): Building polygons, road centerlines, water bodies, and parks/green spaces.
  4. WorldPop: 100m unconstrained population density raster downsampled to 20m.
  5. Open-Meteo API: High-resolution numerical weather forecasts for hourly solar radiation, temperature, relative humidity, and wind speed.

## Target User Archetype
- source: `SPEC.md §5`
- context: Municipal Disaster Management Officers, Urban Health Officials, and City Ward Engineers seeking actionable, hyperlocal intelligence to deploy cool roofs, shade canopies, water hydration points, and emergency medical staging ahead of acute heatwaves.

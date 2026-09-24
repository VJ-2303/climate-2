# Ingested Requirements

## REQ-01: Micro-Sector Vector Grid Generation
- source: `SPEC.md §3.1`
- description: Discretize the Madurai study area into uniform 50m × 50m polygon blocks clipped to municipal boundaries.
- acceptance_criteria:
  - Generates >= 500 valid blocks with minimum valid data coverage >= 0.70 (Gate G1).
  - Calculates zonal mean metrics for NDVI, NDWI, NDBI, LST, building density, road density, distance to water, distance to green, and population density per block.

## REQ-02: Satellite Surface Temperature Downscaling (Module 1)
- source: `SPEC.md §3.2`
- description: Train an XGBoost regressor to predict high-resolution (20m) surface temperatures from optical spectral indices and spatial proximity layers using Landsat 100m pixels.
- acceptance_criteria:
  - Training dataset contains >= 1000 pixels (Gate G2).
  - Validation R² >= 0.25 and MAE <= 1.5°C (Gate G3).
  - Cell-mean residual temperature difference between input Landsat and downscaled raster <= 0.01°C (Gate G4).

## REQ-03: Spatial Contextual Heat Smoothing via GNN (Module 2)
- source: `SPEC.md §3.5`
- description: Construct an 8-neighbor spatial graph and train HeatGAT (Graph Attention Network) to model thermal spillover and environmental buffering across adjacent blocks.
- acceptance_criteria:
  - Validation Pearson correlation >= 0.90 (Gate G5).
  - Standard deviation of contextual heat exposure >= 5.0 (Gate G6).

## REQ-04: Local Feature Explainability (TreeSHAP)
- source: `SPEC.md §3.8`
- description: Compute local TreeSHAP feature attributions for every 50m block, explaining the exact positive and negative physical temperature drivers.
- acceptance_criteria:
  - 100% of blocks in the study area have computed SHAP explanations stored in `block_shap_explanations.json`.
  - Top-3 SHAP factors attached to exported GeoJSON properties and served via `/api/blocks/{block_id}`.

## REQ-05: Real-Time 5-Day Heatwave & WBGT Forecast
- source: `SPEC.md §2.1`, `SPEC.md §4.2`
- description: Integrate Open-Meteo weather forecasts to derive daily maximum Wet-Bulb Globe Temperature (WBGT) and project sector physiological heat risk for days 1 to 5.
- acceptance_criteria:
  - Computes hourly WBGT and daily maximum.
  - Implements 1-hour in-memory cache and offline fallback (`data/fallback_forecast.json`).
  - Provides timeline endpoints `/api/forecast/days` and `/api/layers/forecast_day_{day}/attributes`.

## REQ-06: Officer Command Center Dashboard
- source: `SPEC.md §5`
- description: Single-page web dashboard for municipal disaster management officers with Canvas-accelerated vector mapping, sector inspection drawer, SHAP waterfall charts, and SMS dispatch simulation.
- acceptance_criteria:
  - Renders all 36,913 sectors smoothly without frame drops.
  - Sidebar displays thermal diagnosis, land-cover archetype, SHAP waterfall, 5-day WBGT sparkline, and targeted intervention estimates.
  - Interactive SMS modal triggers simulated multi-channel dispatch with audit tracking.

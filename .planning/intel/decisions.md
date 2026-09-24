# Ingested Decisions

## DEC-001: Coordinate Reference Systems
- source: `AGENTS.md` / `SPEC.md`
- status: locked (Accepted)
- decision: Analysis and model training CRS is strictly `EPSG:32643` (UTM Zone 43N). Final exported GeoJSON vectors are reprojected to `EPSG:4326` (WGS84).
- scope: geospatial raster and vector processing

## DEC-002: Spatial Resolution and Grid Partitioning
- source: `AGENTS.md` / `SPEC.md`
- status: locked (Accepted)
- decision: Working raster resolution is fixed at 20 meters. Aggregated municipal micro-sector blocks are fixed at 50m × 50m polygons clipped to the Madurai municipal boundary.
- scope: grid partitioning, raster resolution

## DEC-003: Model Families & Pipeline Architecture
- source: `AGENTS.md` / `SPEC.md`
- status: locked (Accepted)
- decision: ML downscaling is strictly limited to XGBoost (Module 1). Neighborhood thermal advection is strictly modeled via HeatGAT (Module 2, PyTorch Geometric Graph Attention Network). No alternative model families permitted.
- scope: machine learning, graph neural networks

## DEC-004: Heat Vulnerability Index (HVI) Weighting
- source: `AGENTS.md` / `SPEC.md`
- status: locked (Accepted)
- decision: HVI is defined as `0.45 * AI_Heat_Exposure + 0.35 * Social_Sensitivity + 0.20 * Cooling_Deficit`. Risk tiers: Low (<=45), Medium (46-70), High (71-85), Critical (>85).
- scope: vulnerability scoring, risk classification

## DEC-005: Deterministic Serving Architecture
- source: `AGENTS.md` / `SPEC.md`
- status: locked (Accepted)
- decision: No heavy ML inference at request/serve time. All spatial block intelligence, SHAP attributions, and land cover profiles are precomputed and queried deterministically in sub-10ms via `api/rules.py`.
- scope: backend API, performance

## DEC-006: Pipeline Quality Gates
- source: `AGENTS.md`
- status: locked (Accepted)
- decision: Every pipeline stage (01-07) enforces strict quantitative assertion gates (G1-G7). Any failure must trigger immediate `sys.exit(1)` with no silent skips or fallback substitutions.
- scope: data pipeline integrity

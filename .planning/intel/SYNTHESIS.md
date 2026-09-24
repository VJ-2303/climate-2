# Ingested Docs Synthesis

**Synthesis Date:** 2026-09-24  
**Ingested Sources:** `SPEC.md`, `AGENTS.md`, `docs/DATASETS.md`, `docs/DATA_DOWNLOAD.md`, `docs/RESEARCH.md`

## Executive Summary
HeatViz (ThermalGuard) is an end-to-end hyperlocal urban heat vulnerability platform designed for Madurai, Tamil Nadu. The platform fuses multimodal earth observation data (Sentinel-2, Landsat 8/9, OpenStreetMap, WorldPop) through a physics-informed two-stage machine learning pipeline (XGBoost downscaling + HeatGAT spatial graph attention) to quantify heat risk across 36,913 50m micro-sectors.

The system delivers explainable local root causes via TreeSHAP, models daily 5-day heatwave trajectories using Wet-Bulb Globe Temperature (WBGT), and provides municipal officers with an interactive Command Center dashboard featuring high-contrast risk maps, sector inspection drawers, and emergency SMS dispatch simulations.

## Key Ingested Metrics & Contracts
- **Spatial Coverage:** Madurai municipal study area, 36,913 50m vector blocks.
- **CRS Alignment:** Processing in EPSG:32643 (UTM Zone 43N), visualization in EPSG:4326.
- **HVI Formulation:** 45% AI Heat Exposure + 35% Social Sensitivity + 20% Cooling Deficit.
- **Quality Gates:** 7 sequential gates enforcing minimum sample counts, downscaling accuracy (R² >= 0.25, MAE <= 1.5°C), spatial GNN correlation (Pearson >= 0.90), and physical coherence.
- **FastAPI Backend:** Precomputes spatial structures for sub-10ms query latency, with GZip compression and resilient offline fallback weather data.

# SPEC.md — ThermalGuard (SIH26083)

Authoritative specification. Agent contract (constants, gates, prohibitions): **AGENTS.md**.

**ThermalGuard** maps 50m × 50m heat vulnerability across Kibera, Nairobi (18,040 blocks),
issues 5-day full-WBGT heatwave early warnings, explains every score with SHAP, and drives a
deterministic health-risk engine. Officer-only web UI (FastAPI + Leaflet).

---

## 1. System Architecture

```
Landsat/OSM/WorldPop rasters (20m, EPSG:32737)
  → Module 1: XGBoost 100m→20m surface-temp downscaling (+ per-cell bias correction)
  → Module 2: GATv2 graph attention (8-neighbor blocks) → contextual heat
  → HVI composite (exposure + social sensitivity + cooling deficit)
  → SHAP TreeExplainer → per-block top-3 drivers
  → Open-Meteo 5-day forecast → FULL WBGT → hyperlocal per-block downscaling
  → Health Risk Engine (deterministic tiers, advisories, SMS dispatch)
  → FastAPI + Leaflet officer UI
```

## 2. Physics

### 2.1 Full WBGT (ACGIH outdoor formula)

```
WBGT = 0.57·Tg + 0.32·ea + 0.11·Ta
ea   = (RH/100) × 6.105 × exp(17.27·Ta / (237.7 + Ta))        # Magnus vapor pressure
Tg   = globe temp from energy balance (Liljegren 2002):
       εσ(Tg⁴ − Ta⁴) + h(Tg − Ta) = (1 − α)·Sr / 4
       h = 5.65·v^0.8,  α = 0.05,  ε = 0.95,  σ = 5.67e-8      # 150mm matte-black globe
```

Inputs per hourly step: `temperature_2m`, `relative_humidity_2m`, `direct_radiation`,
`wind_speed_10m` (Open-Meteo). Daily peak WBGT = max over hourly pairs.
Per-hour fallback (solar/wind missing): simplified shade formula
`0.567·Ta + 0.393·ea + 3.94`.

### 2.2 Risk Tiers (frozen)

| WBGT | Tier |
|---|---|
| < 28.0 | Low |
| 28.0 – 30.0 | Moderate |
| 30.0 – 32.0 | High |
| > 32.0 | Critical |

### 2.3 Hyperlocal Downscaling

```
local_wbgt(block, day) = day_peak_wbgt + temp_anomaly_celsius × 0.4
temp_anomaly_celsius   = block_surface_temp − 28.7   # settlement mean
```

### 2.4 HVI Composite (frozen weights)

```
AI_Heat_Exposure   = norm(contextual_ai_heat)
Social_Sensitivity = 0.70·norm(population) + 0.30·norm(building_density)
Cooling_Deficit    = 0.35·norm(dist_green) + 0.30·norm(dist_water)
                     + 0.20·inv(ndvi) + 0.15·inv(ndwi)
HVI_final = norm(0.45·AI + 0.35·Social + 0.20·Cooling)
norm(x) = p2/p98-clip to 0–100;  inv(x) = 100 − norm(x)
```

Risk classes: `0–30 Low | 31–55 Medium | 56–75 High | 76–100 Critical`.

### 2.5 Health Risk Engine (deterministic, no ML at serve time)

Per block × forecast day:
```
base_score = clip((local_wbgt − 24.0) × 10, 0, 100)
risk_score = clip(0.75·base + 0.15·norm(pop) + 0.10·norm(building), 0, 100)
tier       = tier(local_wbgt)
if Social_Sensitivity ≥ 70 and tier ≠ Critical: bump tier up one level
```

Advisory = worst day over 5: tier → action text (officer_action + citizen_action).

## 3. Pipeline — 8 Stages

`01 → 02 → 08 → 03 → 04 → 05 → 06 → 07` — standalone scripts, gate fail = `exit(1)`.
Gate values and artifact map: AGENTS.md.

| Stage | Script | Output |
|---|---|---|
| 01 | `01_build_blocks.py` | 50m block grid, per-layer means, population |
| 02 | `02_train_module1.py` | XGBoost ST model (100m cells) |
| 08 | `08_compute_shap.py` | per-block SHAP top-5 → `block_shap_explanations.json` |
| 03 | `03_infer_module1.py` | `ai_heat_base_20m.tif` (bias-corrected) |
| 04 | `04_build_graph.py` | PyG train + Kibera graphs (9 node features) |
| 05 | `05_train_module2.py` | HeatGAT (frozen architecture) |
| 06 | `06_infer_module2.py` | `contextual_ai_heat` on blocks |
| 07 | `07_score_export.py` | HVI + drivers + `shap_top_factors` (top 3) → GeoJSONs |

## 4. API

| Endpoint | Returns |
|---|---|
| `GET /` , `GET /officer` | Officer UI (`web/officer.html`) |
| `GET /data/vulnerability_blocks.geojson` | Main HVI GeoJSON (EPSG:4326) |
| `GET /data/layers/{name}.geojson` | One of 7 layer files |
| `GET /api/layers/{name}/attributes` | `{block_id: score}` lightweight map |
| `GET /api/layers/forecast_day_{1..5}/attributes` | Per-block 5-day forecast risk scores |
| `GET /api/blocks/{block_id}` | Full block intelligence: HVI, SHAP top-3, 5-day health trajectory, advisory |
| `GET /api/forecast/days` | 5-day WBGT summary (day, date, wbgt_max, tier) |
| `GET /api/forecast/summary` | Forecast summary + peak day |
| `POST /api/alerts/dispatch` | Simulated SMS dispatch → `{audit_id, recipients_count, channels}` |

Weather source: Open-Meteo live (1h cache) → offline fallback `data/fallback_forecast.json`
(heatwave scenario, peak 34.5°C/65%, WBGT 37.4°C) on network failure.

## 5. UI — Officer Command Center (only)

- Choropleth: `Low #1a9850 | Medium #ffffbf | High #f46d43 | Critical #d73027`
- 7 layer switchers (lightweight attribute endpoints, no geometry reload)
- **Forecast dropdown** (topbar): HVI current + Day 1–5 WBGT views; map recolors per day
- **SHAP waterfall** in block sidebar: top-3 drivers with ±°C contributions
- **5-day trajectory sparkline** + tier badges per day
- **SMS dispatch modal**: block → recipient group → simulated dispatch with audit trail
- Zone Planner (polygon → population + risk aggregation), search, offline tile cache

No public/citizen portal (removed — officer-only deployment).

## 6. Data Sources (frozen — no additions)

Landsat Collection-2 ST · Sentinel-2 indices · OSM buildings/roads · WorldPop · Kibera boundary.
Weather: Open-Meteo (ECMWF-based) + local fallback file.

## 7. Model Constraints (frozen)

- Module 1: XGBoost `n_estimators=400, max_depth=6, lr=0.05, subsample=0.8, colsample=0.8, seed=42`
- Module 2: HeatGAT — `GATv2Conv(9→32, h=4) → GATv2Conv(128→16, h=2) → Linear(16→1) → Sigmoid`;
  Adam lr=0.005, 200 epochs, early stop patience 20, loss = 0.9·MSE + 0.1·edge-smooth
- No CNNs, Transformers, GANs, U-Net. No ML at serve time.

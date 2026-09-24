# SPEC.md — ThermalGuard (SIH26083)

Authoritative specification. Agent contract (constants, gates, prohibitions): **AGENTS.md**.

**ThermalGuard** maps 50m × 50m heat vulnerability across Madurai, Tamil Nadu (36,913 blocks),
issues 5-day full-WBGT heatwave early warnings, explains every score with SHAP, and drives a
deterministic health-risk engine. Officer-only web UI (FastAPI + Leaflet).

---

## 1. System Architecture

```
Landsat/OSM/WorldPop rasters (20m, EPSG:32643)
  → Module 1: XGBoost 100m→20m surface-temp downscaling (+ per-cell bias correction)
  → Module 2: GATv2 graph attention (8-neighbor blocks) → contextual heat
  → HVI composite (exposure + social sensitivity + cooling deficit)
  → SHAP TreeExplainer → per-block top-3 drivers
  → Open-Meteo 5-day forecast → FULL WBGT → hyperlocal per-block downscaling
  → Health Risk Engine (deterministic tiers, advisories, SMS dispatch)
  → FastAPI + Leaflet officer UI
```

## 2. Physics

### 2.1 WBGT (daily-max method)

```
WBGT = 0.567·Ta + 0.393·ea + 3.94
ea   = (RH/100) × 6.105 × exp(17.27·Ta / (237.7 + Ta))        # Magnus vapor pressure
```

Per forecast day: `Ta = temperature_2m_max`, `RH = relative_humidity_2m_min` (concurrent
daytime minimum humidity at peak afternoon temperature to prevent nocturnal inflation;
falls back to `relative_humidity_2m_mean` if missing). One WBGT per day from the day's max temperature.

**Multi-model blend & timeline:** single fetch with `models=ecmwf_ifs025,icon_seamless,gfs025`,
`past_days=7`, `forecast_days=5`, providing a continuous 12-day retrospective and predictive timeline.
Per-model suffixed fields are element-wise averaged before WBGT computation (`_blend_daily_models`).

**Dual Composite Heatwave Alert:**
Synthesizes official India Meteorological Department (IMD) criteria for plains:
- Normal (Green): $T_{\max} < 38^\circ\text{C}$
- Heat Alert (Yellow): $T_{\max} \ge 38^\circ\text{C}$ or departure $\ge +3.0^\circ\text{C}$
- Heatwave (Orange): $T_{\max} \ge 40^\circ\text{C}$ and departure $\ge +4.5^\circ\text{C}$ (or absolute $T_{\max} \ge 45^\circ\text{C}$)
- Severe Heatwave (Red): $T_{\max} \ge 40^\circ\text{C}$ and departure $\ge +6.5^\circ\text{C}$ (or absolute $T_{\max} \ge 47^\circ\text{C}$)
Harmonized with NDMA WBGT stress tiers (30/34/38°C), where the higher severity determines the public alert code.

Available but not in the pipeline: full ACGIH outdoor WBGT `0.57·Tg + 0.32·ea + 0.11·Ta`
with globe temp from the Liljegren 2002 energy balance (`calculate_full_wbgt`,
`estimate_globe_temperature` in `api/weather.py`).

### 2.2 Risk Tiers (frozen — IMD/NDMA tropical standards)

| WBGT | Tier |
|---|---|
| < 30.0 | Low |
| 30.0 – 34.0 | Moderate |
| 34.0 – 38.0 | High |
| > 38.0 | Critical |

### 2.3 Hyperlocal Downscaling

```
local_wbgt(block, day) = day_peak_wbgt + temp_anomaly_celsius × 0.4
temp_anomaly_celsius   = block_surface_temp − 49.5   # settlement mean
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

Risk classes: `0–45 Low | 46–70 Medium | 71–85 High | 86–100 Critical`.

### 2.5 Health Risk Engine (deterministic, no ML at serve time)

Per block × forecast day:
```
base_score = clip((local_wbgt − 28.0) × 10, 0, 100)
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
| 04 | `04_build_graph.py` | PyG train + Madurai graphs (9 node features) |
| 05 | `05_train_module2.py` | HeatGAT (frozen architecture) |
| 06 | `06_infer_module2.py` | `contextual_ai_heat` on blocks |
| 07 | `07_score_export.py` | HVI + drivers + `shap_top_factors` (top 3) → GeoJSONs |

## 4. API

| Endpoint | Returns |
|---|---|
| `GET /` , `GET /officer` | Officer UI (`web/officer.html`) |
| `GET /public` | Citizen Heat Safety Portal (`web/public.html`) |
| `GET /data/vulnerability_blocks.geojson` | Main HVI GeoJSON (EPSG:4326) |
| `GET /data/layers/{name}.geojson` | One of 7 layer files |
| `GET /api/layers/{name}/attributes` | `{block_id: score}` lightweight map |
| `GET /api/layers/forecast_day_{-7..5}/attributes` | Per-block 12-day timeline risk scores (past 7 days replay + 5-day forecast) |
| `GET /api/blocks/{block_id}` | Full block intelligence: HVI, SHAP top-3, 5-day health trajectory, bilingual advisory |
| `GET /api/forecast/days` | 12-day timeline & 5-day WBGT summary, real-time current weather, and composite alert |
| `GET /api/forecast/summary` | Forecast summary + peak day + composite alert |
| `POST /api/alerts/dispatch` | Targeted SMS emergency dispatch → SQLite persistence `{audit_id, recipients_count, channels}` |
| `GET /api/alerts/audit` | Recent emergency dispatch audit trail from SQLite (`data/audit_log.db`) |

Weather source: Open-Meteo live (1h cache) → offline fallback `data/fallback_forecast.json`
(heatwave scenario, peak 34.5°C/65%, WBGT 37.4°C) on network failure.

## 5. UI — Dual Deployment

### 5.1 Officer Command Center (`/` and `/officer`)
- Choropleth: `Low #1a9850 | Medium #ffffbf | High #f46d43 | Critical #d73027`
- 7 layer switchers (lightweight attribute endpoints, no geometry reload)
- **12-Day Timeline dropdown** (topbar): HVI baseline + Past 7 Days historical replay + Next 5 Days WBGT forecast
- **Real-time Weather & Composite Alert Badge** in topbar (IMD + NDMA tier)
- **SHAP waterfall** in block sidebar: top-3 drivers with ±°C contributions
- **5-day trajectory sparkline** + tier badges per day
- **SMS dispatch modal**: block → recipient group → simulated dispatch with audit trail
- **Audit Log Modal**: persistent SQLite dispatch audit trail viewer
- Zone Planner (polygon → population + risk aggregation), search, offline tile cache

### 5.2 Citizen Heat Safety Portal (`/public`)
- Mobile-first, citizen-friendly interface
- Hyperlocal geolocation ("My Location" GPS / IP locator) & landmark lookup across 15 Madurai hubs
- Real-time weather, apparent temp, and danger hours (e.g. 11:00 AM – 3:30 PM)
- 3-step actionable safety checklist with bilingual English and Tamil (தமிழ்) guidance
- Designated public hydration kiosks and cooling shelters

## 6. Data Sources (frozen — no additions)

Landsat Collection-2 ST · Sentinel-2 indices · OSM buildings/roads · WorldPop · Madurai boundary.
Weather: Open-Meteo (ECMWF/ICON/GFS blend) + local fallback file.

## 7. Model Constraints (frozen)

- Module 1: XGBoost `n_estimators=400, max_depth=6, lr=0.05, subsample=0.8, colsample=0.8, seed=42`
- Module 2: HeatGAT — `GATv2Conv(9→32, h=4) → GATv2Conv(128→16, h=2) → Linear(16→1) → Sigmoid`;
  Adam lr=0.005, 200 epochs, early stop patience 20, loss = 0.9·MSE + 0.1·edge-smooth
- No CNNs, Transformers, GANs, U-Net. No ML at serve time.

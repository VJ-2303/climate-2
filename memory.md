
# Execution & Calibration Memory

## System Configuration (Madurai, Tamil Nadu)
- Target CRS: EPSG:32643 (UTM Zone 43N)
- Grid: 36,913 blocks (50m × 50m)
- Baseline Surface Temp: 49.5°C
- HVI Tiers: Low <= 45, Medium 46-70, High 71-85, Critical > 85
- WBGT Risk Tiers: Low < 30.0°C, Moderate 30.0-34.0°C, High 34.0-38.0°C, Critical > 38.0°C
- Risk Zero Point: 28.0°C

## Stage 02 — 2026-09-24T13:33:37Z
- samples: 2500
- val_r2: 0.6603
- val_mae: 1.0015
- artifact: models/module1_xgb.json
- gate_g3: PASS

## Stage 02 — 2026-09-24T14:22:31Z
- samples: 2500
- val_r2: 0.6603
- val_mae: 1.0015
- artifact: models/module1_xgb.json
- gate_g3: PASS

## Realtime Heatwave Early Detection & Madurai Calibration — 2026-09-25
- Daytime Peak Humidity Calibration: Paired Tmax with concurrent daytime minimum relative humidity (relative_humidity_2m_min ~28-35%) instead of night-inflated diurnal mean (RH_mean ~70%). Resolved overinflated WBGT (42.6°C -> 31.5-34.5°C) and restored realistic physiological risk distribution.
- 12-Day Historical & Forecast Timeline: 7-day retrospective replay + 5-day predictive forecast powered by 3-model ensemble (ECMWF + ICON + GFS).
- Dual Composite Alert System: Harmonized IMD air temperature heatwave criteria (Tmax >= 40°C or departure >= +4.5°C) with NDMA WBGT thresholds (30/34/38°C).
- Dual-Portal Deployment: Officer Command Center (`/` and `/officer`) + Citizen Heat Safety Portal (`/public`) with bilingual English and Tamil (தமிழ்) advisories.
- Persistent Dispatch Audit Trail: SQLite-backed emergency broadcast logger (`data/audit_log.db`) tracking targeted SMS/WhatsApp advisories.
- Test Coverage: 63 automated tests passing across weather, API, admin, SMS dispatch, full-WBGT, rules engine, SHAP, and audit persistence.

## Sensitive Facilities Command & UI Alignment — 2026-09-25
- Administrative Command Directory (`api/admin.py`, `web/admin.js`): PIN-authenticated zonal authority (Zones 1-5 + Master DDMA) managing 30 sensitive facilities (Schools, Hospitals, Clinics, Colleges) with phone verification and emergency contact provisioning.
- One-Click Category Emergency Broadcast: Dispatches targeted SMS alerts to verified schools, hospitals, or colleges with live Twilio API integration and automated fallback simulation.
- UI Institutional Restraint: Aligned left-side Admin Command Panel (`#admin-directory-panel`) with right-side inspector drawer (`.inspector-drawer`), adopting dark slate hero KPI cards, clean broadcast chips, segmented category tabs, and neutral status pills.
- Rules & SHAP Engine Verification: Full end-to-end integration verified in `tests/test_rules_complete.py` across microclimate diagnostics, top-3 SHAP attributions, 5-day health trajectories, Tamil/English advisories, and botanical intervention sizing.

# Land Surface Temperature (LST) Guide: Physics, Processing & HeatViz Implementation

This technical reference explains the physics of **Land Surface Temperature (LST)**, how it is captured from space, how it differs from ambient air temperature, and how the HeatViz platform ingests, downscales, and utilizes LST across Madurai, Tamil Nadu.

---

## 1. Executive Summary: What is LST?

**Land Surface Temperature (LST)** is the radiative skin temperature of the Earth's physical surface—the outermost layer of solid objects such as rooftops, road pavements, stone walkways, barren soil, and tree canopies.

### LST vs. Ambient Air Temperature ($T_a$)

| Dimension | Land Surface Temperature (LST) | Ambient Air Temperature ($T_a$) |
|---|---|---|
| **What it measures** | Radiometric temperature of solid physical surfaces | Thermodynamic temperature of circulating air |
| **Measurement height** | Surface interface (0 m) | Standard meteorological height (1.5 m – 2.0 m in the shade) |
| **Observation sensor** | Spaceborne Thermal Infrared Sensor (NASA/USGS Landsat 8/9 TIRS Band 10) | Ventilated, shaded weather station sensors (Open-Meteo / IMD) |
| **Spatial variation** | **Hyperlocal & heterogeneous**: Can vary by 15°C–25°C between a shaded park and a tin-roof house 50 meters away | **Macro & smooth**: Relatively uniform across several square kilometers |
| **Typical Madurai midday values (dry season)** | **45.0°C – 64.2°C** (average ~49.5°C) | **34.0°C – 38.0°C** |
| **Primary role in HeatViz** | Identifies **where physical heat traps exist** to direct cool-roof painting and tree planting | Drives **real-time health advisories**, hydration alerts, and worker safety warnings |

> **Real-World Analogy:**  
> On a sunny 36°C afternoon in Madurai, the ambient air circulating through the streets is 36°C. However, the dark asphalt road or the unpainted metal hood of a car absorbs solar radiation and heats up to **55°C – 65°C**. Landsat LST measures the hot asphalt and metal roofs, not the shaded air.

---

## 2. Satellite Origin & Physical Measurement Principles

The LST data used in HeatViz is derived from the **NASA / USGS Landsat 8 and Landsat 9 Earth Observation Satellites**.

### Satellite Mission Parameters
- **Satellites**: Landsat 8 (launched Feb 2013) & Landsat 9 (launched Sep 2021).
- **Sensor**: **TIRS (Thermal Infrared Sensor)**.
- **Spectral Band**: **Band 10** (Thermal Infrared, center wavelength: $10.89\text{ }\mu\text{m}$, range: $10.60\text{ }\mu\text{m} - 11.19\text{ }\mu\text{m}$).
- **Spatial Resolution**: Acquired natively at 100 m, resampled by USGS to 30 m in Level-2 products, and ingested into HeatViz at **20 m** working resolution (`PROCESS_CRS = "EPSG:32643"`).
- **Orbit & Overpass Time**: Sun-synchronous orbit at 705 km altitude. Madurai (*WRS-2 Path 143, Row 53/54*) is imaged around **10:30 AM – 11:30 AM local solar time**, under clear-sky dry season conditions when solar radiant heating is near its peak.

### Radiative Transfer & Planck's Law Inversion

Satellites measure electromagnetic radiance emitted from the surface through the atmospheric column. The USGS Level-2 Surface Temperature science product applies the **single-channel Radiative Transfer Equation (RTE)**:

$$L_{\text{sensor}} = \left[ \epsilon \cdot B(T_s) + (1 - \epsilon) L_{\text{atm}}^\downarrow \right] \tau + L_{\text{atm}}^\uparrow$$

Where:
- $L_{\text{sensor}}$: Top-of-Atmosphere (TOA) spectral radiance measured by Landsat TIRS Band 10 ($\text{W}/(\text{m}^2 \cdot \text{sr} \cdot \mu\text{m})$).
- $\epsilon$: Surface spectral emissivity of the terrestrial material (dimensionless, typically 0.92–0.98).
- $B(T_s)$: Blackbody radiance at Land Surface Temperature $T_s$, governed by **Planck's Radiation Law**:
  $$B(T_s) = \frac{c_1}{\lambda^5 \left( \exp\left(\frac{c_2}{\lambda T_s}\right) - 1 \right)}$$
  *(with calibration constants $c_1 = 1.191 \times 10^8\text{ W}\cdot\mu\text{m}^4/\text{m}^2\text{sr}$ and $c_2 = 1.439 \times 10^4\text{ }\mu\text{m}\cdot\text{K}$)*.
- $\tau$: Atmospheric transmittance along the sensor view path.
- $L_{\text{atm}}^\uparrow$: Upwelling atmospheric thermal radiance.
- $L_{\text{atm}}^\downarrow$: Downwelling atmospheric thermal radiance reflected by the ground.

#### Atmospheric Correction & Emissivity Estimation
1. **Atmospheric Parameters ($\tau, L_{\text{atm}}^\uparrow, L_{\text{atm}}^\downarrow$)**: Interpolated from **NCEP (National Centers for Environmental Prediction)** global atmospheric reanalysis profiles, modeled through **MODTRAN** radiative transfer code.
2. **Surface Emissivity ($\epsilon$)**: Derived using the Normalized Difference Vegetation Index (NDVI) Threshold method combined with the **ASTER Global Emissivity Dataset (ASTER GED)**:
   $$\epsilon = \epsilon_v \cdot P_v + \epsilon_s \cdot (1 - P_v) + C_\lambda$$
   *(where $P_v$ is fractional vegetation cover, $\epsilon_v$ is vegetation emissivity, and $\epsilon_s$ is soil/built emissivity)*.
3. **Solving for Surface Temperature ($T_s$)**:
   Inverting Planck's equation yields surface temperature in Kelvin ($T_s$), which is converted to Celsius:
   $$T_s(^\circ\text{C}) = T_s(\text{K}) - 273.15$$

---

## 3. Why LST Exceeds 50°C and Reaches up to 64°C in Madurai

In the HeatViz dataset for Madurai, LST ranges from **32.7°C to 64.2°C**, with a citywide mean of **49.5°C**. 

```
┌────────────────────────────────────────────────────────────────────────┐
│                   MADURAI LST RASTER DISTRIBUTION                      │
│                                                                        │
│   32.7°C              49.5°C             55.4°C         64.2°C         │
│     ├─── Water /       ├─── Settlement    ├─── 95th      └─── Peak Tin │
│     │    Dense Trees   │    Mean          │    Percentile     & Rock   │
└────────────────────────────────────────────────────────────────────────┘
```

This elevated thermal skin profile is driven by four physical mechanisms:

### 1. High Solar Irradiance at Low Tropical Latitude (9.92°N)
Madurai sits in southern Tamil Nadu's semi-arid tropical belt. During the late-morning satellite overpass (10:30–11:30 AM), the solar zenith angle is small, delivering **800 to 1,000 W/m² of direct shortwave radiation** to unshaded surfaces.

### 2. High Built-Up & Impervious Surface Density (NDBI)
Many informal settlements and commercial areas in Madurai feature unpainted corrugated galvanized iron (GI / "tin") roofs and asbestos roofing sheets:
- Galvanized iron has low thermal mass and high solar absorptivity ($0.65 - 0.85$).
- Under midday sun, unpainted sheet metal roofs regularly reach **55°C to 72°C**.
- Dense asphalt road corridors absorb up to 95% of solar rays, heating the pavement to **55°C – 62°C**.

### 3. Lack of Evaporative Cooling & Vegetative Shade (NDVI Deficit)
Vegetation cools surfaces through **transpiration** (evaporating water absorbs latent heat) and **shading** (intercepting photons before they reach the ground). In sectors where tree canopy coverage is near zero ($\text{NDVI} < 0.20$), 100% of solar irradiance is converted into sensible heat.

### 4. Bare Granite Outcrops & Dry Sandy Soils
Madurai is bordered by prominent rocky granite formations (Thiruparankundram, Yanaimalai, Pasumalai) and the dry Vaigai riverbed during drought/dry seasons. Dry sand and bare rock possess low heat capacities and zero soil moisture, causing surface skin temperatures to exceed **60°C**.

### The Downward Radiation Hazard (Stefan-Boltzmann Law)
High surface skin temperature is not merely a number on a satellite map—it directly harms residents through downward radiative heating:

$$j^* = \epsilon \cdot \sigma \cdot T^4$$

*(where $\sigma = 5.67 \times 10^{-8}\text{ W}/(\text{m}^2\cdot\text{K}^4)$)*

- A cool shaded tile roof at **35°C** (308 K) emits **$\sim 490\text{ W/m}^2$** of thermal radiation.
- A hot tin roof at **57°C** (330 K) emits **$\sim 670\text{ W/m}^2$** of longwave radiation downward into the room below.
- This creates an intense radiative oven effect, elevating indoor temperatures by 3°C–5°C above the outside air and triggering heat exhaustion and nocturnal insomnia.

---

## 4. The HeatViz LST Processing Pipeline

HeatViz integrates LST across an 8-stage pipeline:

```
[Raw Landsat TIRS Band 10]
          │
          ▼
 1. data/processed/landsat_st_celsius.tif  (20m raster, EPSG:32643)
          │
          ▼
 2. scripts/01_build_blocks.py             (50m block aggregation: mean_landsat_st_celsius)
          │
          ▼
 3. scripts/02_train_module1.py           (XGBoost downscaling with Sentinel-2 & OSM features)
          │
          ▼
 4. scripts/08_compute_shap.py            (TreeSHAP explainability: physical drivers of heat)
          │
          ▼
 5. scripts/04_build_graph.py & 05/06     (GAT Graph Neural Network: spatial heat diffusion)
          │
          ▼
 6. scripts/07_score_export.py            (Final GeoJSON export: surface_temp_celsius & anomaly)
          │
          ▼
 7. api/ & web/                           (Officer UI, real-time weather integration & advisories)
```

### Stage 1: Raster Ingestion & 50m Block Aggregation (`01_build_blocks.py`)
- Ingests `landsat_st_celsius.tif` alongside 8 co-registered 20m rasters (NDVI, NDBI, NDWI, building density, road density, population density, distance to green, distance to water).
- Overlays the **36,913 uniform 50m $\times$ 50m sector grid** (`madurai_blocks_50m.geojson`).
- Computes `mean_landsat_st_celsius` for each sector by averaging all 20m pixel centers falling within that block's geometric bounds.

### Stage 2 & 3: AI Microclimate Downscaling (`02_train_module1.py`, `03_infer_module1.py`)
- Trains an **XGBoost regressor** on a 5 km × 5 km central training window (`TRAIN_HALF_SIZE = 2500m`, centered at `9.921851°N, 78.118200°E`).
- Uses optical bands, building geometry, and distance features to learn microclimate heat patterns:
  $$\widehat{\text{LST}} = f_{\text{XGB}}(\text{NDVI}, \text{NDBI}, \text{NDWI}, \text{BuildingDens}, \text{RoadDens}, \text{PopDens}, \text{DistGreen}, \text{DistWater})$$
- Gate G3 enforces strict validation accuracy: $\text{Val } R^2 \ge 0.25$ and $\text{MAE} \le 1.5^\circ\text{C}$.
- Stage 03 enforces zero systematic bias: Cell-mean difference between inferred and raw LST $\le 0.01^\circ\text{C}$.

### Stage 4, 5 & 6: Spatial Graph Heat Diffusion (`04` to `06`)
- Constructs an 8-neighbor spatial adjacency graph across all 36,913 sectors.
- Evaluates a **HeatGAT (Graph Attention Network)** to capture lateral thermal advection (e.g., wind transporting hot air from a 58°C tin-roof cluster into an adjacent residential street).
- Computes `contextual_ai_heat` normalized across the settlement.

### Stage 7: Scoring & Export (`07_score_export.py`)
- Computes the physical thermal properties exported in `data/output/vulnerability_blocks.geojson`:
  ```json
  "surface_temp_celsius": 50.1,
  "temp_anomaly_celsius": 0.6,
  "ai_heat_exposure": 88
  ```
- `temp_anomaly_celsius` represents the sector's departure from the settlement baseline:
  $$\Delta T = \text{LST}_{\text{block}} - \text{Mean}_{\text{settlement}} \quad (\text{baseline } = 49.5^\circ\text{C})$$

---

## 5. How HeatViz Presents LST vs. Real-Time Weather in the UI

To avoid confusing users between solid surface skin temperature and ambient weather, the HeatViz platform presents both metrics simultaneously with clear semantic separation:

### 1. Global Header Bar
Displays real-time ambient station weather alongside the satellite LST baseline:
```
Live: 27.1°C (Feels 30.9°C) • LST Avg: 49.5°C
```

### 2. Map Block Hover Tooltip
Shows both ambient microclimate air temperature and satellite surface temperature:
```
KIB-0001 • Air: 27.4°C • LST: 50.1°C • HVI: 88 (Critical)
```
*(In 5-Day Forecast mode, it switches dynamically to show predicted daily Air Max and local WBGT heat stress).*

### 3. Sector Profile Drawer (Sidebar KPIs)
When inspecting any 50m block:
- **Air Temp**: Hyperlocal ambient air temperature ($\sim 27.4^\circ\text{C}$ nighttime / $35.6^\circ\text{C}$ daytime max), calibrated using live Open-Meteo weather downscaled by the sector's microclimate anomaly:
  $$T_{\text{ambient}} = T_{\text{station}} + (\Delta T \times 0.35)$$
- **Surface (LST)**: Radiometric satellite skin temperature ($50.1^\circ\text{C}$).
- **Anomaly**: Relative thermal load relative to Madurai's mean ($+0.6^\circ\text{C}$).
- **Peak Roof Temp**: Estimated midday metal roof surface temperature ($~58.2^\circ\text{C}$).

### 4. Prescriptive Action (Guided by LST)
Because LST identifies *where* heat is absorbed, HeatViz automatically sizes interventions based on each block's thermal load:
- **Cool Roof Coatings**: For blocks with elevated LST and high built density ($\text{NDBI} \ge 50$), calculates the liters of high-albedo white elastomeric coating needed to reflect 80%+ of incoming solar irradiance (dropping roof skin temperature from ~57°C down to ~38°C–40°C).
- **Canopy Shading**: For blocks with elevated LST and low vegetation ($\text{NDVI} < 50$), calculates the exact deficit and recommends native Tamil Nadu tree species (*Azadirachta indica* / Neem, *Pongamia pinnata* / Pungan) tailored to soil moisture conditions.

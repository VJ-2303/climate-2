# HeatViz Data Sources Guide (Compact & Clear)

This guide explains the **5 original data sources** used to build the HeatViz system: where the raw data came from, what was collected, and why it is used.

---

## 1. NASA / USGS Landsat 8 & 9 (Satellite Thermal Data)

* **Source**: United States Geological Survey (USGS) & NASA.
* **Sensor**: Thermal Infrared Sensor (TIRS) aboard Landsat 8 and 9.
* **What was downloaded**: Spaceborne thermal infrared satellite imagery (Band 10) covering Nairobi (Path 168, Row 61) during clear-sky dry season conditions.
* **Why we used it**: 
  - Measures the actual **Land Surface Temperature (LST)** in degrees Celsius ($^\circ\text{C}$).
  - Serves as the ground-truth thermal benchmark to train the AI downscaling model.

---

## 2. ESA Copernicus Sentinel-2 (Satellite Optical & Surface Data)

* **Source**: European Space Agency (ESA) Copernicus Earth Observation Programme.
* **Sensor**: Multi-Spectral Instrument (MSI) aboard Sentinel-2A and 2B satellites.
* **What was downloaded**: High-resolution (10m–20m) optical imagery across 4 spectral bands: Green, Red, Near-Infrared (NIR), and Shortwave Infrared (SWIR).
* **Why we used it**:
  - **Vegetation / Greenery (NDVI)**: Calculated from Red & NIR bands to measure tree canopy and shade.
  - **Tin Roofs & Built-Up Areas (NDBI)**: Calculated from SWIR & NIR bands to detect heat-trapping corrugated iron roofs.
  - **Moisture & Water (NDWI)**: Calculated from Green & NIR bands to track soil moisture and wetland cooling corridors.

---

## 3. OpenStreetMap & Map Kibera Project (Urban Structure & Infrastructure)

* **Source**: OpenStreetMap (OSM) community, Humanitarian OpenStreetMap Team (HOT Kenya), and the local Map Kibera Project.
* **What was downloaded**: Crowdsourced vector GIS data extracted via the Overpass API:
  - **36,438 building outlines**: Exact shapes and positions of residential shacks, schools, and health clinics.
  - **5,952 roads and pathways**: Pedestrian alleys, dirt paths, and the railway line.
  - **509 green spaces**: Parks, grass patches, school grounds, and tree clusters.
  - **70 water bodies & streams**: The Nairobi Dam and Motoine / Ngong River drainage channels.
* **Why we used it**:
  - Computes **Building Footprint Density** and estimated rooftop square meters for cool-roof retrofits.
  - Computes **Road/Path Density** to identify unshaded pedestrian heat corridors.
  - Calculates walking **distances to the nearest park/tree shade** and **nearest water body**.

---

## 4. WorldPop & Meta CIESIN (Demographic Population Data)

* **Source**: WorldPop Research Group (University of Southampton) in collaboration with UN-Habitat and Meta/Columbia University (High Resolution Settlement Layer).
* **What was downloaded**: 100m gridded population count for Kenya, based on official census figures combined with satellite settlement mapping.
* **Why we used it**:
  - Disaggregated using building outlines to estimate resident counts per 50m block (**410,801 total residents** across Kibera).
  - Used to weight heat vulnerability: ensuring emergency cooling interventions (water kiosks, cool roofs) are prioritized where the most people live.

---

## 5. Nairobi City County & Map Kibera (Settlement Boundary)

* **Source**: Nairobi City County Government GIS Directorate & Humanitarian Data Exchange (HDX).
* **What was downloaded**: Official administrative boundary polygon for the Kibera informal settlement.
* **Why we used it**:
  - Sets the spatial boundary to crop all satellite rasters and divide Kibera into a grid of **18,040 uniform 50m $\times$ 50m sectors**.

---

## Summary Matrix

| Data Source | Provider | Raw Content Collected | Purpose in HeatViz |
|---|---|---|---|
| **Landsat 8 / 9** | NASA / USGS | Thermal Infrared Band 10 (100m) | Baseline Surface Temperature ($^\circ\text{C}$) & AI training |
| **Sentinel-2** | ESA Copernicus | Multispectral Bands 3, 4, 8, 11 (10–20m) | Tree Canopy (NDVI), Tin Roofs (NDBI), Moisture (NDWI) |
| **OpenStreetMap** | OSM / Map Kibera | 36,438 Buildings, 5,952 Paths, 70 Rivers | Building density, path density, distance to shade/water |
| **WorldPop** | Univ. of Southampton | Gridded Population Census (100m) | Resident population exposure (410k residents) |
| **Kibera Boundary** | Nairobi City County | Administrative Polygon | Defines the 18,040 50m block analysis grid |

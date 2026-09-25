# HeatViz Data Sources Guide (Compact & Clear)

This guide explains the **5 core data sources** used to build the HeatViz system for Madurai, Tamil Nadu: where the raw data came from, what was collected, and why it is used.

---

## 1. NASA / USGS Landsat 8 & 9 (Satellite Thermal Data)

* **Source**: United States Geological Survey (USGS) & NASA.
* **Sensor**: Thermal Infrared Sensor (TIRS) aboard Landsat 8 and 9.
* **What was downloaded**: Spaceborne thermal infrared satellite imagery (Band 10, Level-2 Surface Temperature) covering Madurai (Path 143, Row 53/54) during clear-sky dry season conditions.
* **Why we used it**: 
  - Measures the actual **Land Surface Temperature (LST)** in degrees Celsius ($^\circ\text{C}$).
  - Serves as the ground-truth thermal benchmark to train the Module 1 downscaling model.

---

## 2. ESA Copernicus Sentinel-2 (Satellite Optical & Surface Data)

* **Source**: European Space Agency (ESA) Copernicus Earth Observation Programme.
* **Sensor**: Multi-Spectral Instrument (MSI) aboard Sentinel-2A and 2B satellites (Tile 44PMV / 44PMU).
* **What was downloaded**: High-resolution (10m–20m) optical imagery across spectral bands: B02 (Blue), B03 (Green), B04 (Red), B08 (NIR), B11/B12 (SWIR), and Scene Classification Layer (SCL).
* **Why we used it**:
  - **Vegetation / Greenery (NDVI)**: Calculated from Red & NIR bands to measure tree canopy and shade.
  - **Built-Up Areas & Impervious Surfaces (NDBI)**: Calculated from SWIR & NIR bands to characterize urban built-up and impervious surface density. *(Note: NDBI is used as a spectral indicator of built-up/impervious surface characteristics; it is not used as a direct roof-material classifier).*
  - **Moisture & Water (NDWI)**: Calculated from Green & NIR bands to track surface moisture and riparian cooling corridors.

---

## 3. OpenStreetMap (Urban Structure & Infrastructure)

* **Source**: OpenStreetMap (OSM) community and contributors via Overpass API.
* **What was downloaded**: Crowdsourced vector GIS data extracted for the Madurai metropolitan area:
  - **Building outlines**: Exact shapes and positions of residential structures, commercial areas, and community facilities.
  - **Roads and pathways**: Primary thoroughfares, local street networks, and pedestrian alleys.
  - **Green spaces**: Parks, tree-lined avenues, temple grounds, and agricultural buffers.
  - **Water bodies & drainage channels**: The Vaigai River corridor, irrigation canals, and local water tanks (*kanmois*).
* **Why we used it**:
  - Computes **Building Footprint Density** and rooftop area for cool-roof retrofits.
  - Computes **Road/Path Density** to identify unshaded pedestrian heat corridors.
  - Calculates Euclidean walking **distances to the nearest park/tree shade** and **nearest water body**.

---

## 4. WorldPop (Demographic Population Data)

* **Source**: WorldPop Research Group (University of Southampton) in collaboration with Meta / Columbia University CIESIN.
* **What was downloaded**: 100m gridded population count for India (constrained settlement layer).
* **Why we used it**:
  - Disaggregated across 50m sectors to estimate resident exposure counts (~**538,248 residents** across the Madurai study area).
  - Used to weight heat vulnerability: ensuring emergency cooling interventions (water kiosks, cool roofs, tree canopy) are prioritized where vulnerable populations reside.

---

## 5. Municipal Administrative & Study Area Boundary

* **Source**: Madurai urban spatial boundary polygon (`data/processed/madurai_boundary.geojson`).
* **What was downloaded**: Projected boundary polygon in UTM Zone 43N (`EPSG:32643`).
* **Why we used it**:
  - Sets the spatial boundary to crop all satellite rasters and divide the urban area into a grid of **36,913 uniform 50m $\times$ 50m sectors**.

---

## Summary Matrix

| Data Source | Provider | Raw Content Collected | Purpose in HeatViz |
|---|---|---|---|
| **Landsat 8 / 9** | NASA / USGS | Thermal Infrared Band 10 (100m) | Baseline Surface Temperature ($^\circ\text{C}$) & AI training |
| **Sentinel-2** | ESA Copernicus | Multispectral Bands (B02–B12, SCL) | Tree Canopy (NDVI), Built Cover (NDBI), Moisture (NDWI) |
| **OpenStreetMap** | OSM Community | Buildings, Highways, Parks, Vaigai River / Tanks | Building density, road density, distance to shade/water |
| **WorldPop** | Univ. of Southampton | Gridded Population Census (100m, India) | Resident population exposure (~538k residents) |
| **Madurai Boundary** | Municipal GIS | Administrative Polygon (`EPSG:32643`) | Defines the 36,913 50m block analysis grid |

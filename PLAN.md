# HeatViz Implementation Plan

## 1. Project Summary

HeatViz is an AI-powered hyperlocal heat vulnerability mapping system for informal settlements.

The system identifies which specific city blocks are most vulnerable to heat stress by combining satellite thermal data, high-resolution surface data, open urban data, and population data.

The final output is an interactive map where NGOs and health workers can see:

- Which blocks are most heat-vulnerable.
- Why each block is vulnerable.
- How many people may be exposed.
- What intervention should be prioritized.

The demo area is Kibera, Nairobi, Kenya.

---

## 2. Locked Scope

The project will produce a working MVP focused on one settlement.

The final system will include:

- Satellite and urban data extraction.
- AI-based thermal downscaling.
- Graph-based neighborhood heat refinement.
- Heat vulnerability scoring.
- Explainable risk drivers.
- Intervention recommendations.
- A web map with clickable 50m blocks.

The system will not include:

- Real-time IoT sensors.
- Drone data processing.
- User accounts.
- Production cloud scaling.
- Multi-city processing.
- Paid data services.

The output is a relative vulnerability score, not an exact medical or meteorological temperature measurement.

---

## 3. Demo Area

Target area:

```text
Kibera, Nairobi, Kenya
```

Approximate center:

```text
Latitude: -1.317
Longitude: 36.789
```

Analysis boundary:

```text
kibera_boundary.geojson
```

Approximate bounding box:

```text
South: -1.335
West: 36.765
North: -1.295
East: 36.810
```

Model training area:

```text
5km x 5km area around Kibera
```

The training area is used to train the AI models.

The final vulnerability map is generated only inside the Kibera boundary.

---

## 4. System Architecture

The system follows this pipeline:

```text
Data Sources
    Sentinel-2
    Landsat 8/9
    OpenStreetMap
    WorldPop
    Kibera boundary
        |
        v
Preprocessing
    Reprojection
    Clipping
    Cloud masking
    Resampling
    Grid alignment
        |
        v
Feature Extraction
    NDVI
    NDWI
    NDBI
    Building density
    Road density
    Distance to green space
    Distance to water
    Population density
        |
        v
AI Module 1
    Thermal downscaling model
    Predicts fine-resolution heat exposure
        |
        v
AI Module 2
    Graph context refinement model
    Refines heat exposure using neighborhood structure
        |
        v
Vulnerability Scoring
    AI heat exposure
    Social sensitivity
    Cooling access deficit
        |
        v
Explainability Layer
    Top risk drivers
    Intervention recommendations
        |
        v
Web Map
    50m vulnerability blocks
    Layer toggles
    Block details
    GeoJSON export
```

---

## 5. Data Sources

The system uses only free and open data sources.

### 5.1 Sentinel-2

Purpose:

```text
High-resolution surface features
```

Used for:

```text
Vegetation
Water presence
Built-up surface intensity
```

Dataset:

```text
Sentinel-2 Level-2A surface reflectance
```

Required bands:

```text
B02 Blue
B03 Green
B04 Red
B08 NIR
B11 SWIR
B12 SWIR
SCL scene classification
```

### 5.2 Landsat 8/9

Purpose:

```text
Thermal surface temperature baseline
```

Used for:

```text
Training the thermal downscaling model
Validating heat exposure predictions
```

Dataset:

```text
Landsat 8 or Landsat 9
Collection 2
Level-2 Surface Temperature
```

Required band:

```text
ST_B10
```

QA band:

```text
QA_PIXEL
```

### 5.3 OpenStreetMap

Purpose:

```text
Hyperlocal urban structure
```

Used for:

```text
Building density
Road density
Distance to green space
Distance to water
Graph context features
```

Required features:

```text
Buildings
Roads and paths
Water features
Green spaces
```

### 5.4 WorldPop

Purpose:

```text
Social exposure
```

Used for:

```text
Population density
Estimated exposed population
Social sensitivity scoring
```

Dataset:

```text
Kenya population raster
100m gridded population
```

### 5.5 Kibera Boundary

Purpose:

```text
Final analysis boundary
```

Used for:

```text
Clipping final outputs
Generating 50m blocks
Displaying the demo area
```

---

## 6. Data Extraction

### 6.1 Sentinel-2 Extraction

Download a Sentinel-2 Level-2A scene covering Kibera.

Selection criteria:

```text
Cloud cover below 5% over Kibera
No cloud shadow over Kibera
Valid surface reflectance
Recent scene preferred
```

Cloud masking uses the SCL band.

Keep these classes:

```text
2 Dark area
4 Vegetation
5 Not vegetated
6 Water
```

Mask these classes:

```text
0 No data
1 Saturated or defective
3 Cloud shadow
7 Cloud low probability
8 Cloud medium probability
9 Cloud high probability
10 Cirrus
11 Snow or ice
```

### 6.2 Landsat Extraction

Download a Landsat 8 or Landsat 9 Collection 2 Level-2 scene.

Selection criteria:

```text
Cloud cover below 5%
Thermal band covers Kibera
No cloud or shadow over Kibera
Same season as Sentinel-2 where possible
```

Use QA_PIXEL to mask:

```text
Fill pixels
Cloud pixels
Cloud shadow pixels
```

QA_PIXEL bits to mask:

```text
Bit 0 Fill
Bit 3 Cloud shadow
Bit 4 Cloud
```

Convert surface temperature to Celsius:

```text
Surface Temperature Kelvin = ST_B10 * 0.00341802 + 149.0
Surface Temperature Celsius = Surface Temperature Kelvin - 273.15
```

### 6.3 OpenStreetMap Extraction

Extract OSM features using the Kibera bounding box.

Bounding box:

```text
-1.335, 36.765, -1.295, 36.810
```

Required tags:

Buildings:

```text
building=*
```

Roads and paths:

```text
highway=*
```

Water:

```text
natural=water
waterway=*
amenity=drinking_water
```

Green spaces:

```text
leisure=park
leisure=garden
leisure=pitch
leisure=playground
landuse=grass
landuse=recreation_ground
landuse=village_green
```

Output files:

```text
osm_buildings.geojson
osm_roads.geojson
osm_water.geojson
osm_green.geojson
```

### 6.4 WorldPop Extraction

Download the Kenya population raster.

Required output:

```text
worldpop_population.tif
```

Use WorldPop values to estimate population exposure inside final 50m blocks.

### 6.5 Boundary Extraction

Create or download a Kibera boundary polygon.

Required output:

```text
kibera_boundary.geojson
```

The boundary must be clean and closed.

It must cover the demo area without including unnecessary surrounding regions.

---

## 7. Coordinate System and Grid

### 7.1 Processing CRS

All geospatial processing uses:

```text
EPSG:32737
```

This is the appropriate UTM zone for Nairobi.

### 7.2 Output CRS

The final GeoJSON for the web map uses:

```text
EPSG:4326
```

### 7.3 Working Raster Grid

All raster layers are aligned to:

```text
20m x 20m
```

This grid is used for:

```text
Satellite indices
Landsat heat prediction
OSM raster features
AI Module 1 inference
```

### 7.4 Final Analysis Grid

The final vulnerability map uses vector blocks of:

```text
50m x 50m
```

This grid is used for:

```text
Graph modeling
Vulnerability scoring
Web map display
Intervention assignment
```

---

## 8. Preprocessing Pipeline

All data must be cleaned and aligned before modeling.

### Step 1: Reproject Data

Reproject all layers to:

```text
EPSG:32737
```

### Step 2: Clip Data

Clip training layers to the 5km x 5km training area.

Clip final output layers to:

```text
kibera_boundary.geojson
```

### Step 3: Align Rasters

Align all rasters to the same 20m grid.

All rasters must share:

```text
Same CRS
Same pixel size
Same grid origin
Same extent for the selected area
```

### Step 4: Resample Sentinel Bands

Resample Sentinel-2 10m bands to 20m.

Bands to resample:

```text
B02
B03
B04
B08
```

Keep SWIR bands at 20m:

```text
B11
B12
```

Use bilinear resampling.

### Step 5: Resample Landsat

Resample Landsat surface temperature to the 20m working grid.

Use bilinear resampling.

This layer is used as the coarse thermal reference.

### Step 6: Rasterize OSM

Convert OSM vector data into raster features.

Generate:

```text
building_density.tif
road_density.tif
distance_to_green.tif
distance_to_water.tif
```

### Step 7: Process WorldPop

Create two outputs:

```text
population_density_20m.tif
population_block_estimates.geojson
```

The 20m layer is used as an AI input feature.

The block-level layer is used for final population exposure reporting.

---

## 9. Feature Engineering

All feature layers are generated at 20m resolution unless stated otherwise.

### 9.1 NDVI

NDVI represents vegetation.

Formula:

```text
NDVI = (B08 - B04) / (B08 + B04)
```

Interpretation:

```text
High NDVI = vegetation and cooling
Low NDVI = low vegetation and higher heat risk
```

### 9.2 NDWI

NDWI represents water presence.

Formula:

```text
NDWI = (B03 - B08) / (B03 + B08)
```

Interpretation:

```text
High NDWI = water presence and cooling
Low NDWI = dry surface and higher heat risk
```

### 9.3 NDBI

NDBI represents built-up surfaces.

Formula:

```text
NDBI = (B11 - B08) / (B11 + B08)
```

Interpretation:

```text
High NDBI = built-up surface and higher heat risk
Low NDBI = less built-up surface and lower heat risk
```

### 9.4 Building Density

For each 20m cell:

```text
Building Density = total building footprint area inside cell / 400
```

For each 50m block:

```text
Building Density = total building footprint area inside block / 2500
```

### 9.5 Road Density

For each 20m cell:

```text
Road Density = total road length inside cell / 400
```

For each 50m block:

```text
Road Density = total road length inside block / 2500
```

### 9.6 Distance to Green Space

For each cell or block center:

```text
Distance to nearest OSM green space feature
```

Distance is capped at:

```text
1000m
```

Higher distance means lower cooling access.

### 9.7 Distance to Water

For each cell or block center:

```text
Distance to nearest OSM water feature
```

Distance is capped at:

```text
1000m
```

Higher distance means lower cooling access.

### 9.8 Population Density

For AI input:

```text
Relative population density at 20m
```

For final reporting:

```text
Estimated population inside each 50m block
```

Population estimation uses areal interpolation from WorldPop 100m pixels.

---

## 10. AI Module 1: Thermal Downscaling

### 10.1 Purpose

Landsat provides real thermal information, but it is coarse.

Sentinel-2 provides high-resolution surface detail, but it has no thermal band.

AI Module 1 learns the relationship between surface features and thermal behavior.

It predicts a fine-resolution heat exposure surface from coarse Landsat temperature and high-resolution features.

### 10.2 Training Area

Training is performed over:

```text
5km x 5km area around Kibera
```

This provides enough Landsat pixels for stable training.

### 10.3 Training Samples

Each training sample is one Landsat 100m pixel.

For each valid Landsat pixel, calculate the mean of all 20m feature layers inside that pixel.

Training feature columns:

```text
mean_ndvi
mean_ndwi
mean_ndbi
mean_building_density
mean_road_density
mean_distance_to_green
mean_distance_to_water
mean_population_density
```

Training target:

```text
landsat_surface_temperature_celsius
```

Minimum required valid training samples:

```text
1000 Landsat pixels
```

### 10.4 Model Type

Use a gradient-boosted regression model.

Objective:

```text
Predict continuous surface temperature
```

Locked hyperparameters:

```text
objective = squared error
n_estimators = 400
max_depth = 6
learning_rate = 0.05
subsample = 0.8
colsample_bytree = 0.8
random_state = 42
```

GPU acceleration may be used if available.

### 10.5 Training Split

Use:

```text
80% training
20% validation
```

Split by Landsat pixel using fixed random seed:

```text
42
```

### 10.6 Inference

Run the trained model on every valid 20m pixel inside Kibera.

Input:

```text
20m feature layers
```

Output:

```text
predicted_heat_20m.tif
```

### 10.7 Bias Correction

Bias correction is mandatory.

For each Landsat 100m pixel:

```text
Mean Predicted Heat = average of all valid 20m predictions inside that Landsat pixel
Correction = Landsat Surface Temperature Celsius - Mean Predicted Heat
Corrected 20m Heat = Predicted 20m Heat + Correction
```

Output:

```text
ai_heat_base_20m.tif
```

This layer preserves the Landsat thermal signal while adding fine spatial detail.

---

## 11. Final 50m Block Grid

Generate a vector grid inside Kibera.

Block size:

```text
50m x 50m
```

Block ID format:

```text
KIB-0001
KIB-0002
KIB-0003
```

Each block must contain at least:

```text
70% valid 20m pixel coverage
```

Blocks below this coverage threshold are excluded from final scoring.

For each valid block, calculate mean values from the 20m layers.

Block features:

```text
mean_ai_heat_base
mean_ndvi
mean_ndwi
mean_ndbi
mean_building_density
mean_road_density
mean_distance_to_green
mean_distance_to_water
mean_population_density
estimated_population
```

---

## 12. AI Module 2: Graph Context Refinement

### 12.1 Purpose

Heat risk in informal settlements is not isolated to one block.

A block becomes more dangerous when it is surrounded by dense buildings, low vegetation, and limited cooling access.

AI Module 2 uses a graph model to refine heat exposure based on neighborhood context.

### 12.2 Graph Nodes

Each node is one valid 50m block.

Node feature vector:

```text
mean_ai_heat_base
mean_ndvi
mean_ndwi
mean_ndbi
mean_building_density
mean_road_density
mean_distance_to_green
mean_distance_to_water
mean_population_density
```

All node features are normalized before training.

### 12.3 Graph Edges

Connect each block to its 8 surrounding neighbors.

Neighbors:

```text
North
South
East
West
Northeast
Northwest
Southeast
Southwest
```

Edges are undirected.

Self-loops are included.

### 12.4 Model Type

Use a Graph Attention Network.

The model learns how neighboring blocks influence the heat exposure of each block.

### 12.5 Model Architecture

Locked architecture:

```text
Input:
Node feature vector

Layer 1:
Graph Attention Layer
Hidden size = 32
Attention heads = 4
Activation = ELU
Dropout = 0.1

Layer 2:
Graph Attention Layer
Hidden size = 16
Attention heads = 2
Activation = ELU
Dropout = 0.1

Output Layer:
Linear layer
Output size = 1
Activation = Sigmoid
```

Output range:

```text
0 to 1
```

Scaled output:

```text
0 to 100
```

### 12.6 Training Target

For each node:

```text
Target = normalized mean_ai_heat_base
```

Target range:

```text
0 to 1
```

### 12.7 Training Graph Area

Train the graph model using 50m blocks generated from the full 5km x 5km training area.

Final inference is run only on Kibera blocks.

### 12.8 Training Split

Use:

```text
80% training nodes
20% validation nodes
```

Fixed random seed:

```text
42
```

### 12.9 Loss Function

Total loss:

```text
Total Loss =
    0.9 * Prediction Loss
  + 0.1 * Spatial Smoothness Loss
```

Prediction loss:

```text
MSE(predicted_heat, target_heat)
```

Spatial smoothness loss:

```text
Mean squared difference between connected neighbor predictions
```

### 12.10 Training Configuration

Locked configuration:

```text
Optimizer = Adam
Learning rate = 0.005
Epochs = 200
Early stopping patience = 20
Random seed = 42
```

### 12.11 Inference

Run the trained graph model on the Kibera block graph.

Output per block:

```text
contextual_ai_heat_score
```

Range:

```text
0 to 100
```

This becomes the final AI heat exposure layer.

---

## 13. Normalization Method

All scoring layers are normalized to:

```text
0 to 100
```

Normalization formula:

```text
normalized = ((value - p2) / (p98 - p2)) * 100
```

Where:

```text
p2 = 2nd percentile of valid block values
p98 = 98th percentile of valid block values
```

Clamp output:

```text
Minimum = 0
Maximum = 100
```

If:

```text
p98 - p2 < 0.000001
```

Then set all normalized values to:

```text
50
```

Inverse normalization:

```text
inverse = 100 - normalized
```

---

## 14. Vulnerability Scoring

The final Heat Vulnerability Index combines three components.

```text
Heat Vulnerability Index =
    AI Heat Exposure
  + Social Sensitivity
  + Cooling Access Deficit
```

### 14.1 AI Heat Exposure

```text
AI_Heat_Exposure = normalized(contextual_ai_heat_score)
```

### 14.2 Social Sensitivity

```text
Social_Sensitivity =
    0.70 * normalized_population_density
  + 0.30 * normalized_building_density
```

Clamp to:

```text
0 to 100
```

### 14.3 Cooling Access Deficit

```text
Cooling_Access_Deficit =
    0.35 * normalized_distance_to_green
  + 0.30 * normalized_distance_to_water
  + 0.20 * inverse_NDVI
  + 0.15 * inverse_NDWI
```

Clamp to:

```text
0 to 100
```

### 14.4 Raw HVI

```text
HVI_raw =
    0.45 * AI_Heat_Exposure
  + 0.35 * Social_Sensitivity
  + 0.20 * Cooling_Access_Deficit
```

### 14.5 Final HVI

```text
HVI_final = normalized(HVI_raw)
```

Range:

```text
0 to 100
```

### 14.6 Risk Classes

```text
0 to 30 = Low
31 to 55 = Medium
56 to 75 = High
76 to 100 = Critical
```

---

## 15. Explainability Layer

Each block must explain why it is vulnerable.

Driver scores:

```text
low_vegetation = inverse_NDVI
high_building_density = normalized_building_density
high_built_surface = normalized_NDBI
poor_green_access = normalized_distance_to_green
poor_water_access = normalized_distance_to_water
high_population_exposure = normalized_population_density
```

Select the top three highest driver scores.

Tie-break order:

```text
poor_water_access
poor_green_access
high_population_exposure
high_building_density
high_built_surface
low_vegetation
```

Example:

```text
Block ID: KIB-0234
HVI Score: 87
Risk Class: Critical

Top Risk Drivers:
1. poor_water_access
2. high_building_density
3. low_vegetation
```

---

## 16. Intervention Logic

Each block receives one suggested intervention.

Priority rule:

```text
If HVI_final >= 75:
    Priority = Critical

If HVI_final >= 56 and < 75:
    Priority = High

If HVI_final >= 31 and < 56:
    Priority = Medium

If HVI_final <= 30:
    Priority = Low
```

Intervention mapping uses the highest driver score.

```text
poor_water_access = Water point / hydration support
poor_green_access = Shade structure / tree planting
low_vegetation = Green cover intervention
high_building_density = Cool roof awareness / ventilation outreach
high_built_surface = Reflective roof / surface cooling campaign
high_population_exposure = Community health outreach
```

Tie-break order:

```text
poor_water_access
poor_green_access
high_population_exposure
high_building_density
high_built_surface
low_vegetation
```

---

## 17. Final Output Schema

Main output file:

```text
vulnerability_blocks.geojson
```

CRS:

```text
EPSG:4326
```

Geometry:

```text
50m x 50m polygon block
```

Each feature contains these properties:

```json
{
  "block_id": "KIB-0234",
  "hvi_score": 87,
  "hvi_raw": 79.4,
  "risk_class": "Critical",
  "priority": "Critical",
  "ai_heat_exposure": 89,
  "social_sensitivity": 84,
  "cooling_deficit": 82,
  "estimated_population": 312,
  "population_density": 78,
  "building_density": 85,
  "ndvi": 12,
  "ndwi": 6,
  "ndbi": 77,
  "distance_to_green": 69,
  "distance_to_water": 74,
  "top_drivers": [
    "poor_water_access",
    "high_building_density",
    "low_vegetation"
  ],
  "intervention": "Water point / hydration support"
}
```

---

## 18. Web Application Requirements

The web application must display:

```text
OpenStreetMap basemap
Kibera boundary
50m vulnerability blocks
Color-coded risk overlay
Block click panel
Layer toggles
Legend
Export button
```

### 18.1 Map Colors

```text
Low = Green
Medium = Yellow
High = Orange
Critical = Red
```

### 18.2 Block Click Panel

When a block is clicked, display:

```text
Block ID
HVI Score
Risk Class
Priority
AI Heat Exposure
Social Sensitivity
Cooling Access Deficit
Estimated Population
Top Risk Drivers
Suggested Intervention
```

### 18.3 Layer Toggles

The map must allow toggling:

```text
Final Heat Vulnerability
AI Heat Exposure
NDVI
NDBI
Building Density
Population Density
Cooling Access Deficit
```

### 18.4 Legend

The legend must show:

```text
Risk classes
Color scale
Data sources
```

### 18.5 Export

The app must allow:

```text
Download vulnerability_blocks.geojson
```

---

## 19. Repository Structure

```text
heatviz/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── output/
│
├── models/
│
├── notebooks/
│
├── scripts/
│
├── api/
│
├── web/
│
├── PLAN.md
└── README.md
```

### Raw Data Files

```text
sentinel_b02.tif
sentinel_b03.tif
sentinel_b04.tif
sentinel_b08.tif
sentinel_b11.tif
sentinel_b12.tif
sentinel_scl.tif
landsat_st_b10.tif
landsat_qa_pixel.tif
osm_buildings.geojson
osm_roads.geojson
osm_water.geojson
osm_green.geojson
worldpop_population.tif
kibera_boundary.geojson
```

### Processed Files

```text
ndvi.tif
ndwi.tif
ndbi.tif
landsat_st_celsius.tif
building_density.tif
road_density.tif
distance_to_green.tif
distance_to_water.tif
population_density_20m.tif
ai_heat_base_20m.tif
kibera_blocks_50m.geojson
kibera_graph.json
```

### Output Files

```text
vulnerability_blocks.geojson
ai_heat_exposure_blocks.geojson
social_sensitivity_blocks.geojson
cooling_deficit_blocks.geojson
```

---

## 20. Validation Criteria

The system is considered complete only if all of the following are true.

```text
1. Sentinel-2 covers Kibera with no clouds.
2. Landsat surface temperature covers Kibera with no clouds.
3. OSM buildings are present inside Kibera.
4. OSM water or green features are present.
5. WorldPop population values are non-zero.
6. All processing layers use EPSG:32737.
7. All rasters align to the same 20m grid.
8. NDVI, NDWI, and NDBI are calculated correctly.
9. Landsat surface temperature is converted to Celsius.
10. AI Module 1 is trained on 100m aggregated samples.
11. AI Module 1 inference is produced at 20m.
12. Bias correction preserves Landsat thermal means.
13. 50m block grid is generated inside Kibera.
14. Block features are aggregated correctly.
15. Graph nodes and edges are generated.
16. Graph AI produces contextual heat exposure.
17. Social sensitivity is calculated.
18. Cooling access deficit is calculated.
19. Final HVI score is calculated.
20. Risk classes are assigned.
21. Top drivers are generated.
22. Interventions are generated.
23. vulnerability_blocks.geojson is exported in EPSG:4326.
24. Web map loads correctly.
25. Block click panel displays all required fields.
26. Layer toggles work.
27. Legend is visible.
28. GeoJSON export works.

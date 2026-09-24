# HeatViz Data Download Guide

This guide tells you exactly which format to pick on each website, how to download it, and where to place it in the repo. All formats below were verified against the official portals.

---

## 0. Accounts You Need First (Free)

| Portal | Account | Why |
|---|---|---|
| Copernicus Dataspace | Free registration | Required to download Sentinel-2 products |
| USGS EarthExplorer | Free registration | Required to download Landsat products |
| WorldPop / Overpass / geojson.io | None | Direct public download |

---

## 1. The Format Confusion, Solved

This is the quick answer to "there are many formats, which one do I pick?"

| Source | Formats you will see on the site | The ONE you must pick | Why |
|---|---|---|---|
| Sentinel-2 (Copernicus) | JPG, PNG, KMZ, GeoTIFF preview exports, and the full product ZIP | **Full product ZIP (SAFE format)** | The JPG/PNG/GeoTIFF buttons in the Browser are visual preview exports only . The real science bands (B11, B12, SCL) only come inside the SAFE ZIP as JPEG2000 files . |
| Landsat (EarthExplorer) | Collection 2 Level-1, Collection 2 Level-2, Analysis Ready Data, various bundles | **Landsat Collection 2 Level-2 Science Product** | Only Level-2 contains the Surface Temperature band (ST_B10) and QA_PIXEL . |
| WorldPop | 1km vs 100m, counts vs density, GeoTIFF vs ASCII XYZ | **100m Population Counts, GeoTIFF** | The 100m GeoTIFF is the resolution our pipeline expects . |
| OSM (Overpass) | GeoJSON, KML, GPX, raw OSM XML | **GeoJSON** | GeoJSON loads directly into GeoPandas and our pipeline . |
| Boundary (geojson.io) | GeoJSON, TopoJSON | **GeoJSON** | Matches our boundary file spec. |

---

## 2. Sentinel-2 (Copernicus Dataspace)

Portal: `https://browser.dataspace.copernicus.eu`

### Search Steps

1. Log in with your free account.
2. In the search panel, set:
   - Collection: **Sentinel-2**
   - Processing level: **L2A**
   - Time range: last 12 months
   - Cloud coverage: **max 5%**
3. Zoom to Madurai, Tamil Nadu (or paste coordinates `9.921851, 78.118200`) and draw a small box around it.
4. Pick a scene where Madurai itself has no clouds (use the true-color preview).
5. Click **Download** on that scene. You will receive one `.zip` file (the SAFE product).

### What Is Inside the ZIP

The ZIP is a SAFE archive. After unzipping, the band images live under `GRANULE/*/IMG_DATA/` in three resolution folders: `R10m`, `R20m`, `R60m` . The files are JPEG2000 (`.jp2`) .

You need exactly these 7 files (names contain the patterns below):

| File pattern inside ZIP | Folder | Our raw name |
|---|---|---|
| `*_B02_10m.jp2` | R10m | sentinel_b02 |
| `*_B03_10m.jp2` | R10m | sentinel_b03 |
| `*_B04_10m.jp2` | R10m | sentinel_b04 |
| `*_B08_10m.jp2` | R10m | sentinel_b08 |
| `*_B11_20m.jp2` | R20m | sentinel_b11 |
| `*_B12_20m.jp2` | R20m | sentinel_b12 |
| `*_SCL_20m.jp2` | R20m | sentinel_scl |

### Convert to GeoTIFF (required)

Our pipeline reads GeoTIFF, so convert each jp2 once after download:

```bash
gdal_translate *_B02_10m.jp2 data/raw/sentinel_b02.tif -co COMPRESS=LZW
gdal_translate *_B03_10m.jp2 data/raw/sentinel_b03.tif -co COMPRESS=LZW
gdal_translate *_B04_10m.jp2 data/raw/sentinel_b04.tif -co COMPRESS=LZW
gdal_translate *_B08_10m.jp2 data/raw/sentinel_b08.tif -co COMPRESS=LZW
gdal_translate *_B11_20m.jp2 data/raw/sentinel_b11.tif -co COMPRESS=LZW
gdal_translate *_B12_20m.jp2 data/raw/sentinel_b12.tif -co COMPRESS=LZW
gdal_translate *_SCL_20m.jp2 data/raw/sentinel_scl.tif -co COMPRESS=LZW
```

Do not delete the unzipped SAFE folder until the conversion succeeds.

---

## 3. Landsat 8/9 (USGS EarthExplorer)

Portal: `https://earthexplorer.usgs.gov`

### Search Steps

1. Log in.
2. Search Criteria tab: enter coordinates `9.921851, 78.118200` (or "Madurai, Tamil Nadu, India").
3. Date range: last 12 months. Under "Additional Criteria" set cloud cover **Less Than 5%**.
4. Data Sets tab: open **Landsat → Landsat Collection 2 Level-2** and tick it .
5. Results: pick a scene covering Madurai with low cloud (Path 143, Row 53/54).
6. Click the download icon, then in **Download Options** choose **Landsat Collection 2 Level-2 Science Product** (GeoTIFF). Do not choose Level-1.

### What Is Inside the ZIP

The Level-2 Science Product package is a ZIP of GeoTIFF files plus metadata . Keep exactly these 3 files:

| File pattern inside ZIP | Our raw name |
|---|---|
| `*_ST_B10.tif` | landsat_st_b10.tif |
| `*_QA_PIXEL.tif` | landsat_qa_pixel.tif |
| `*_MTL.txt` | landsat_mtl.txt |

The `ST_B10` file is the Surface Temperature band and `QA_PIXEL` is the quality mask; both are carried through in the Level-2 package . The `MTL.txt` holds the scaling constants the pipeline uses.

Copy and rename:

```bash
cp LC0*_ST_B10.tif   data/raw/landsat_st_b10.tif
cp LC0*_QA_PIXEL.tif data/raw/landsat_qa_pixel.tif
cp LC0*_MTL.txt      data/raw/landsat_mtl.txt
```

(Your scene ID starts with LC08 or LC09; adjust the pattern accordingly.)

---

## 4. WorldPop Population (India, 100m)

Portal: `https://hub.worldpop.org/geodata/country?iso3=IND`

### Which Dataset

Pick the **100m Population Counts (constrained, 2020)** for India. It is delivered as a single GeoTIFF at about 100m (3 arc seconds) .

Direct pages you can use (same dataset, different mirrors):

- WorldPop Hub summary page: `https://hub.worldpop.org/geodata/summary?id=49792` (Constrained 2020, 100m, India) 
- HDX mirror: `https://data.humdata.org/dataset/worldpop-population-counts-for-india` 

### Steps

1. Open one of the pages above.
2. Click **Download Entire Dataset** (a single `.tif` file) .
3. Rename and place:

```bash
cp ind_ppp_2020*.tif data/raw/worldpop_population.tif
```

Notes:

- The file is in geographic coordinates (EPSG:4326); the pipeline reprojects it later .
- Do not download the 1km (30 arc) version and do not download the ASCII XYZ format.

---

## 5. OpenStreetMap (Overpass Turbo)

Portal: `https://overpass-turbo.eu`

### Steps

1. Paste this query into the left editor (it uses the Madurai urban bbox):

```text
[out:json][timeout:300];
(
  way["building"](9.870,78.050,9.970,78.180);
  way["highway"](9.870,78.050,9.970,78.180);
  way["natural"="water"](9.870,78.050,9.970,78.180);
  way["waterway"](9.870,78.050,9.970,78.180);
  way["amenity"="drinking_water"](9.870,78.050,9.970,78.180);
  way["landuse"~"grass|recreation_ground|village_green"](9.870,78.050,9.970,78.180);
  way["leisure"~"park|garden|pitch|playground"](9.870,78.050,9.970,78.180);
  node["amenity"="drinking_water"](9.870,78.050,9.970,78.180);
);
out geom;
```

2. Click **Run**. Wait for the map to fill with buildings and roads.
3. Click **Export**, then choose **download as GeoJSON** (raw data directly as GeoJSON) .
4. You will get one combined GeoJSON. Split it into our four raw files by tag (a 10-line Python/GeoPandas script, or filter manually):

| Filter | Our raw name |
|---|---|
| `building` tag present | osm_buildings.geojson |
| `highway` tag present | osm_roads.geojson |
| `natural=water`, `waterway`, or `amenity=drinking_water` | osm_water.geojson |
| `landuse` or `leisure` green tags | osm_green.geojson |

---

## 6. Madurai Boundary (geojson.io)

Portal: `https://geojson.io`

### Steps

1. Zoom to Madurai and switch on the satellite basemap.
2. Use the polygon tool to trace the urban study area outline. Close the polygon.
3. The right panel shows the GeoJSON. Click **Save → GeoJSON**.
4. Place the file:

```bash
cp map.geojson data/raw/madurai_boundary.geojson
```

---

## 7. Final Folder Placement

After all downloads and conversions, `data/raw/` must contain exactly these 16 files:

```text
data/raw/
    sentinel_b02.tif
    sentinel_b03.tif
    sentinel_b04.tif
    sentinel_b08.tif
    sentinel_b11.tif
    sentinel_b12.tif
    sentinel_scl.tif
    landsat_st_b10.tif
    landsat_qa_pixel.tif
    landsat_mtl.txt
    osm_buildings.geojson
    osm_roads.geojson
    osm_water.geojson
    osm_green.geojson
    worldpop_population.tif
    madurai_boundary.geojson
```

Everything else (unzipped SAFE folders, Landsat zips, extra bands) can be deleted or moved outside the repo after the checks below pass.

---

## 8. Post-Download Checks (5 Minutes)

Run these before starting the preprocessing pipeline (`process.py`). If any check fails, re-download that file.

1. All 7 Sentinel tifs open and report CRS EPSG:32643 or EPSG:4326 (reprojection happens during preprocessing).
2. `sentinel_scl.tif` contains values 2, 4, 5, 6 over Madurai (not all zeros).
3. `landsat_st_b10.tif` opens and has non-zero values over Madurai after applying the scale factor from `landsat_mtl.txt`.
4. `landsat_qa_pixel.tif` opens and is the same size as `landsat_st_b10.tif`.
5. `osm_buildings.geojson` contains at least 1000 features.
6. `osm_water.geojson` or `osm_green.geojson` contains at least 1 feature.
7. `worldpop_population.tif` has non-zero values inside the boundary.
8. `madurai_boundary.geojson` is a single valid closed polygon.

Once all 8 checks pass, the raw data layer is verified and `process.py` can be executed.

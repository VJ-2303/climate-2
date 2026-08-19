#!/usr/bin/env python3
"""
HeatViz Data Preprocessing Pipeline (Script 01)
Preprocesses raw Sentinel-2, Landsat 8/9, OpenStreetMap, WorldPop, and Kibera Boundary data
into standardized 20m analysis-ready rasters aligned to EPSG:32737.
"""

import os
import glob
import zipfile
import shutil
import warnings
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.features import rasterize
from shapely.geometry import mapping
from scipy.ndimage import distance_transform_edt

warnings.filterwarnings("ignore")

# Define repository directories
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_DIR = os.path.join(BASE_DIR, "data", "output")
TEMP_DIR = os.path.join(BASE_DIR, "data", "temp")

# Geospatial parameters
TARGET_CRS = "EPSG:32737"  # UTM Zone 37S (Metric, Nairobi)
TARGET_RESOLUTION = 20.0   # 20 meters cell size
EPSILON = 1e-10
NODATA_VAL = -9999.0


def setup_directories():
    """Ensure all required data directories exist."""
    for d in [RAW_DIR, PROCESSED_DIR, OUTPUT_DIR, TEMP_DIR]:
        os.makedirs(d, exist_ok=True)
    print("✓ Directories initialized.")


def extract_sentinel_safe():
    """Extract and convert Sentinel-2 SAFE archive JP2 bands to GeoTIFF."""
    required_bands = [
        "sentinel_b02.tif", "sentinel_b03.tif", "sentinel_b04.tif",
        "sentinel_b08.tif", "sentinel_b11.tif", "sentinel_b12.tif",
        "sentinel_scl.tif"
    ]
    all_exist = all(os.path.exists(os.path.join(RAW_DIR, f)) for f in required_bands)
    if all_exist:
        print("✓ All Sentinel-2 raw GeoTIFF bands already exist.")
        return

    safe_zips = glob.glob(os.path.join(RAW_DIR, "S2*.SAFE.zip")) or glob.glob(os.path.join(RAW_DIR, "*.zip"))
    if not safe_zips:
        print("! Warning: No Sentinel-2 SAFE zip found in data/raw.")
        return

    safe_zip = safe_zips[0]
    print(f"Extracting Sentinel-2 SAFE archive: {os.path.basename(safe_zip)}...")
    sentinel_temp = os.path.join(TEMP_DIR, "sentinel_extract")
    os.makedirs(sentinel_temp, exist_ok=True)

    with zipfile.ZipFile(safe_zip, 'r') as zip_ref:
        jp2_members = [m for m in zip_ref.namelist() if m.lower().endswith('.jp2') and 'IMG_DATA' in m]
        for member in jp2_members:
            zip_ref.extract(member, sentinel_temp)

    # Map bands to output filenames
    band_mapping = {
        "B02_10m.jp2": "sentinel_b02.tif",
        "B03_10m.jp2": "sentinel_b03.tif",
        "B04_10m.jp2": "sentinel_b04.tif",
        "B08_10m.jp2": "sentinel_b08.tif",
        "B11_20m.jp2": "sentinel_b11.tif",
        "B12_20m.jp2": "sentinel_b12.tif",
        "SCL_20m.jp2": "sentinel_scl.tif",
    }

    for pattern, out_name in band_mapping.items():
        matches = glob.glob(os.path.join(sentinel_temp, "**", f"*{pattern}"), recursive=True)
        if matches:
            src_jp2 = matches[0]
            dst_tif = os.path.join(RAW_DIR, out_name)
            print(f"  Converting {pattern} -> {out_name}...")
            with rasterio.open(src_jp2) as src:
                profile = src.profile.copy()
                profile.update(
                    driver='GTiff',
                    compress='lzw',
                    tiled=True,
                    blockxsize=256,
                    blockysize=256
                )
                with rasterio.open(dst_tif, 'w', **profile) as dst:
                    dst.write(src.read())
        else:
            print(f"  ! Warning: {pattern} not found in extracted archive.")

    shutil.rmtree(sentinel_temp, ignore_errors=True)
    print("✓ Sentinel-2 bands extracted and converted successfully.")


def standardize_landsat_and_worldpop():
    """Standardize filenames for Landsat and WorldPop raw data files."""
    st_matches = glob.glob(os.path.join(RAW_DIR, "*ST_B10*.TIF")) + glob.glob(os.path.join(RAW_DIR, "*ST_B10*.tif"))
    st_matches = [f for f in st_matches if os.path.basename(f) != "landsat_st_b10.tif"]
    if st_matches and not os.path.exists(os.path.join(RAW_DIR, "landsat_st_b10.tif")):
        shutil.copyfile(st_matches[0], os.path.join(RAW_DIR, "landsat_st_b10.tif"))
        print(f"✓ Copied {os.path.basename(st_matches[0])} -> landsat_st_b10.tif")

    qa_matches = glob.glob(os.path.join(RAW_DIR, "*QA_PIXEL*.TIF")) + glob.glob(os.path.join(RAW_DIR, "*QA_PIXEL*.tif"))
    qa_matches = [f for f in qa_matches if os.path.basename(f) != "landsat_qa_pixel.tif"]
    if qa_matches and not os.path.exists(os.path.join(RAW_DIR, "landsat_qa_pixel.tif")):
        shutil.copyfile(qa_matches[0], os.path.join(RAW_DIR, "landsat_qa_pixel.tif"))
        print(f"✓ Copied {os.path.basename(qa_matches[0])} -> landsat_qa_pixel.tif")

    mtl_matches = glob.glob(os.path.join(RAW_DIR, "*MTL*.txt"))
    mtl_matches = [f for f in mtl_matches if os.path.basename(f) != "landsat_mtl.txt"]
    if mtl_matches and not os.path.exists(os.path.join(RAW_DIR, "landsat_mtl.txt")):
        shutil.copyfile(mtl_matches[0], os.path.join(RAW_DIR, "landsat_mtl.txt"))
        print(f"✓ Copied {os.path.basename(mtl_matches[0])} -> landsat_mtl.txt")

    pop_matches = glob.glob(os.path.join(RAW_DIR, "ken_ppp_2020*.tif"))
    pop_matches = [f for f in pop_matches if os.path.basename(f) != "worldpop_population.tif"]
    if pop_matches and not os.path.exists(os.path.join(RAW_DIR, "worldpop_population.tif")):
        shutil.copyfile(pop_matches[0], os.path.join(RAW_DIR, "worldpop_population.tif"))
        print(f"✓ Copied {os.path.basename(pop_matches[0])} -> worldpop_population.tif")


def split_osm_data():
    """Split export.geojson into 4 categorized GeoJSON files."""
    osm_export = os.path.join(RAW_DIR, "export.geojson")
    target_files = [
        "osm_buildings.geojson", "osm_roads.geojson",
        "osm_water.geojson", "osm_green.geojson"
    ]
    all_exist = all(os.path.exists(os.path.join(RAW_DIR, f)) for f in target_files)
    if all_exist:
        print("✓ Categorized OSM GeoJSON files already exist.")
        return

    if not os.path.exists(osm_export):
        print("! Warning: export.geojson not found in data/raw.")
        return

    print("Splitting OSM export.geojson into feature layers...")
    gdf = gpd.read_file(osm_export)
    print(f"  Total features loaded: {len(gdf)}")

    # 1. Buildings
    if 'building' in gdf.columns:
        buildings = gdf[gdf['building'].notna()].copy()
    else:
        buildings = gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
    buildings.to_file(os.path.join(RAW_DIR, "osm_buildings.geojson"), driver="GeoJSON")
    print(f"  ✓ Buildings: {len(buildings)} features saved.")

    # 2. Roads
    if 'highway' in gdf.columns:
        roads = gdf[gdf['highway'].notna()].copy()
    else:
        roads = gpd.GeoDataFrame(columns=gdf.columns, crs=gdf.crs)
    roads.to_file(os.path.join(RAW_DIR, "osm_roads.geojson"), driver="GeoJSON")
    print(f"  ✓ Roads: {len(roads)} features saved.")

    # 3. Water
    water_mask = np.zeros(len(gdf), dtype=bool)
    if 'natural' in gdf.columns:
        water_mask = water_mask | (gdf['natural'] == 'water')
    if 'waterway' in gdf.columns:
        water_mask = water_mask | (gdf['waterway'].notna())
    if 'amenity' in gdf.columns:
        water_mask = water_mask | (gdf['amenity'] == 'drinking_water')
    water = gdf[water_mask].copy()
    water.to_file(os.path.join(RAW_DIR, "osm_water.geojson"), driver="GeoJSON")
    print(f"  ✓ Water: {len(water)} features saved.")

    # 4. Green spaces
    green_mask = np.zeros(len(gdf), dtype=bool)
    if 'landuse' in gdf.columns:
        green_mask = green_mask | (gdf['landuse'].isin(['grass', 'recreation_ground', 'village_green']))
    if 'leisure' in gdf.columns:
        green_mask = green_mask | (gdf['leisure'].isin(['park', 'garden', 'pitch', 'playground']))
    green = gdf[green_mask].copy()
    green.to_file(os.path.join(RAW_DIR, "osm_green.geojson"), driver="GeoJSON")
    print(f"  ✓ Green spaces: {len(green)} features saved.")


def build_master_grid_and_process():
    """
    Construct the unified 20m EPSG:32737 master raster grid covering 100% of the Kibera
    boundary plus buffer, and reproject/resample all layers onto this grid.
    """
    print("\n" + "=" * 60)
    print("Executing Master Processing Pipeline (EPSG:32737 @ 20m)")
    print("=" * 60)

    # 1. Process Boundary
    print("\n[1/7] Processing Kibera Boundary...")
    boundary_raw_path = os.path.join(RAW_DIR, "kibera_boundary.geojson")
    boundary = gpd.read_file(boundary_raw_path)
    boundary_utm = boundary.to_crs(TARGET_CRS)
    boundary_utm.to_file(os.path.join(PROCESSED_DIR, "kibera_boundary.geojson"), driver="GeoJSON")
    print(f"✓ Reprojected boundary to {TARGET_CRS}")

    # Determine master bounds: cover the entire boundary polygon + 1000m buffer
    b_minx, b_miny, b_maxx, b_maxy = boundary_utm.total_bounds
    buffer_m = 1000.0
    
    minx = np.floor((b_minx - buffer_m) / TARGET_RESOLUTION) * TARGET_RESOLUTION
    maxx = np.ceil((b_maxx + buffer_m) / TARGET_RESOLUTION) * TARGET_RESOLUTION
    miny = np.floor((b_miny - buffer_m) / TARGET_RESOLUTION) * TARGET_RESOLUTION
    maxy = np.ceil((b_maxy + buffer_m) / TARGET_RESOLUTION) * TARGET_RESOLUTION

    master_width = int(round((maxx - minx) / TARGET_RESOLUTION))
    master_height = int(round((maxy - miny) / TARGET_RESOLUTION))
    master_transform = rasterio.transform.from_origin(minx, maxy, TARGET_RESOLUTION, TARGET_RESOLUTION)

    print(f"Master Grid Extent: [{minx:.1f}, {miny:.1f}, {maxx:.1f}, {maxy:.1f}]")
    print(f"Master Grid Dimensions: {master_width} cols x {master_height} rows @ 20m resolution ({master_width * master_height:,} total cells)")

    master_meta = {
        'driver': 'GTiff',
        'dtype': 'float32',
        'nodata': NODATA_VAL,
        'width': master_width,
        'height': master_height,
        'count': 1,
        'crs': TARGET_CRS,
        'transform': master_transform,
        'compress': 'lzw'
    }

    def reproject_to_master(src_path, resampling_method=Resampling.bilinear):
        """Reproject any raster file to the exact master grid."""
        dest_arr = np.full((master_height, master_width), NODATA_VAL, dtype=np.float32)
        with rasterio.open(src_path) as src:
            reproject(
                source=rasterio.band(src, 1),
                destination=dest_arr,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=master_transform,
                dst_crs=TARGET_CRS,
                dst_nodata=NODATA_VAL,
                resampling=resampling_method
            )
        return dest_arr

    def save_master_raster(arr, out_name, nodata=NODATA_VAL, dtype='float32'):
        meta = master_meta.copy()
        meta.update(dtype=dtype, nodata=nodata)
        out_path = os.path.join(PROCESSED_DIR, out_name)
        with rasterio.open(out_path, 'w', **meta) as dst:
            dst.write(arr.astype(dtype), 1)
        valid_vals = arr[arr != nodata]
        min_v = np.nanmin(valid_vals) if len(valid_vals) > 0 else 0.0
        max_v = np.nanmax(valid_vals) if len(valid_vals) > 0 else 0.0
        mean_v = np.nanmean(valid_vals) if len(valid_vals) > 0 else 0.0
        print(f"✓ Saved {out_name} (shape={arr.shape}, range=[{min_v:.3f}, {max_v:.3f}], mean={mean_v:.3f})")

    # 2. Resample Sentinel-2 bands and compute NDVI, NDWI, NDBI
    print("\n[2/7] Computing Sentinel-2 Spectral Indices...")
    s2_raw_exists = os.path.exists(os.path.join(RAW_DIR, "sentinel_b02.tif"))
    if s2_raw_exists:
        b02 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b02.tif"))
        b03 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b03.tif"))
        b04 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b04.tif"))
        b08 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b08.tif"))
        b11 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b11.tif"))
        b12 = reproject_to_master(os.path.join(RAW_DIR, "sentinel_b12.tif"))

        valid_mask = (b02 != NODATA_VAL) & (b03 != NODATA_VAL) & (b04 != NODATA_VAL) & (b08 != NODATA_VAL) & (b11 != NODATA_VAL)

        # NDVI = (B08 - B04) / (B08 + B04 + EPSILON)
        ndvi = np.full((master_height, master_width), NODATA_VAL, dtype=np.float32)
        ndvi[valid_mask] = (b08[valid_mask] - b04[valid_mask]) / (b08[valid_mask] + b04[valid_mask] + EPSILON)
        save_master_raster(ndvi, "ndvi.tif")

        # NDWI = (B03 - B08) / (B03 + B08 + EPSILON)
        ndwi = np.full((master_height, master_width), NODATA_VAL, dtype=np.float32)
        ndwi[valid_mask] = (b03[valid_mask] - b08[valid_mask]) / (b03[valid_mask] + b08[valid_mask] + EPSILON)
        save_master_raster(ndwi, "ndwi.tif")

        # NDBI = (B11 - B08) / (B11 + B08 + EPSILON)
        ndbi = np.full((master_height, master_width), NODATA_VAL, dtype=np.float32)
        ndbi[valid_mask] = (b11[valid_mask] - b08[valid_mask]) / (b11[valid_mask] + b08[valid_mask] + EPSILON)
        save_master_raster(ndbi, "ndbi.tif")
    elif os.path.exists(os.path.join(PROCESSED_DIR, "ndvi.tif")):
        print("✓ Reusing existing processed NDVI, NDWI, NDBI master rasters.")
    else:
        raise FileNotFoundError("Neither raw Sentinel-2 bands nor processed indices exist.")

    # 3. Process Landsat Surface Temperature with QA Cloud Masking
    print("\n[3/7] Processing Landsat Surface Temperature (°C)...")
    landsat_raw_exists = os.path.exists(os.path.join(RAW_DIR, "landsat_st_b10.tif"))
    if landsat_raw_exists:
        st_raw = reproject_to_master(os.path.join(RAW_DIR, "landsat_st_b10.tif"), resampling_method=Resampling.bilinear)
        qa_raw = reproject_to_master(os.path.join(RAW_DIR, "landsat_qa_pixel.tif"), resampling_method=Resampling.nearest)

        st_celsius = np.full((master_height, master_width), NODATA_VAL, dtype=np.float32)
        valid_st_mask = (st_raw > 0) & (st_raw != NODATA_VAL)

        # QA bitmask: Bit 0: Fill, Bit 3: Cloud shadow, Bit 4: Cloud
        qa_int = qa_raw.astype(np.uint16)
        cloud_mask = ((qa_int & (1 << 0)) != 0) | ((qa_int & (1 << 3)) != 0) | ((qa_int & (1 << 4)) != 0)

        valid_st = valid_st_mask & (~cloud_mask)
        st_celsius[valid_st] = (st_raw[valid_st] * 0.00341802 + 149.0) - 273.15
        save_master_raster(st_celsius, "landsat_st_celsius.tif")
    elif os.path.exists(os.path.join(PROCESSED_DIR, "landsat_st_celsius.tif")):
        print("✓ Reusing existing processed Landsat surface temperature master raster.")
    else:
        raise FileNotFoundError("Neither raw Landsat bands nor processed temperature raster exists.")

    # 4. OSM Building Density (Sub-pixel fractional area)
    print("\n[4/7] Generating Fractional Building Density Raster (sub-pixel rasterization)...")
    buildings_gdf = gpd.read_file(os.path.join(RAW_DIR, "osm_buildings.geojson")).to_crs(TARGET_CRS)
    if len(buildings_gdf) > 0:
        sub_scale = 5  # 5x5 sub-pixels per 20m cell = 4m sub-resolution
        sub_h = master_height * sub_scale
        sub_w = master_width * sub_scale
        sub_res = TARGET_RESOLUTION / sub_scale
        sub_transform = rasterio.transform.from_origin(minx, maxy, sub_res, sub_res)
        
        shapes = [(mapping(geom), 1.0) for geom in buildings_gdf.geometry if geom is not None and not geom.is_empty]
        sub_building_mask = rasterize(
            shapes=shapes,
            out_shape=(sub_h, sub_w),
            transform=sub_transform,
            fill=0.0,
            dtype=np.float32
        )
        # Reshape and compute mean fractional building coverage per 20m cell
        building_density = sub_building_mask.reshape(master_height, sub_scale, master_width, sub_scale).mean(axis=(1, 3))
    else:
        building_density = np.zeros((master_height, master_width), dtype=np.float32)
    save_master_raster(building_density, "building_density.tif", nodata=NODATA_VAL)

    # 5. OSM Road Density
    print("\n[5/7] Generating Road Density Raster...")
    roads_gdf = gpd.read_file(os.path.join(RAW_DIR, "osm_roads.geojson")).to_crs(TARGET_CRS)
    if len(roads_gdf) > 0:
        sub_scale = 5
        sub_h = master_height * sub_scale
        sub_w = master_width * sub_scale
        sub_res = TARGET_RESOLUTION / sub_scale
        sub_transform = rasterio.transform.from_origin(minx, maxy, sub_res, sub_res)
        
        shapes = [(mapping(geom), 1.0) for geom in roads_gdf.geometry if geom is not None and not geom.is_empty]
        sub_road_mask = rasterize(
            shapes=shapes,
            out_shape=(sub_h, sub_w),
            transform=sub_transform,
            fill=0.0,
            dtype=np.float32
        )
        road_density = sub_road_mask.reshape(master_height, sub_scale, master_width, sub_scale).mean(axis=(1, 3))
    else:
        road_density = np.zeros((master_height, master_width), dtype=np.float32)
    save_master_raster(road_density, "road_density.tif", nodata=NODATA_VAL)

    # 6. Distance to Green Space & Water (capped at 1000m)
    print("\n[6/7] Computing Distance Transforms (capped at 1000m)...")
    green_gdf = gpd.read_file(os.path.join(RAW_DIR, "osm_green.geojson")).to_crs(TARGET_CRS)
    if len(green_gdf) > 0:
        green_shapes = [(mapping(geom), 1) for geom in green_gdf.geometry if geom is not None and not geom.is_empty]
        green_raster = rasterize(green_shapes, out_shape=(master_height, master_width), transform=master_transform, fill=0, dtype=np.uint8)
        dist_green = distance_transform_edt(green_raster == 0) * TARGET_RESOLUTION
        dist_green = np.clip(dist_green, 0.0, 1000.0).astype(np.float32)
    else:
        dist_green = np.full((master_height, master_width), 1000.0, dtype=np.float32)
    save_master_raster(dist_green, "distance_to_green.tif")

    water_gdf = gpd.read_file(os.path.join(RAW_DIR, "osm_water.geojson")).to_crs(TARGET_CRS)
    if len(water_gdf) > 0:
        water_shapes = [(mapping(geom), 1) for geom in water_gdf.geometry if geom is not None and not geom.is_empty]
        water_raster = rasterize(water_shapes, out_shape=(master_height, master_width), transform=master_transform, fill=0, dtype=np.uint8)
        dist_water = distance_transform_edt(water_raster == 0) * TARGET_RESOLUTION
        dist_water = np.clip(dist_water, 0.0, 1000.0).astype(np.float32)
    else:
        dist_water = np.full((master_height, master_width), 1000.0, dtype=np.float32)
    save_master_raster(dist_water, "distance_to_water.tif")

    # 7. WorldPop Population Density (20m)
    print("\n[7/7] Processing WorldPop Population Density...")
    pop_raw_exists = os.path.exists(os.path.join(RAW_DIR, "worldpop_population.tif"))
    if pop_raw_exists:
        pop_raw = reproject_to_master(os.path.join(RAW_DIR, "worldpop_population.tif"), resampling_method=Resampling.bilinear)
        pop_density = np.where(pop_raw != NODATA_VAL, np.clip(pop_raw, 0.0, None), NODATA_VAL).astype(np.float32)
        save_master_raster(pop_density, "population_density_20m.tif", nodata=NODATA_VAL)
    elif os.path.exists(os.path.join(PROCESSED_DIR, "population_density_20m.tif")):
        print("✓ Reusing existing processed population density master raster.")
    else:
        raise FileNotFoundError("Neither raw WorldPop nor processed population density raster exists.")

    print("\n" + "=" * 60)
    print("✅ All 10 Preprocessing Steps Completed Successfully!")
    print("=" * 60)


def main():
    setup_directories()
    extract_sentinel_safe()
    standardize_landsat_and_worldpop()
    split_osm_data()
    build_master_grid_and_process()


if __name__ == "__main__":
    main()

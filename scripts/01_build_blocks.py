import os
import sys
import math
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import box, Point, Polygon
from pyproj import Transformer

# Immutable Constants from SPEC.md Section 2
SEED = 42
PROCESS_CRS = "EPSG:32737"
OUTPUT_CRS = "EPSG:4326"
WORKING_RES = 20          # meters
BLOCK_SIZE = 50           # meters
TRAIN_HALF_SIZE = 2500    # meters (5km x 5km training area)
CENTER_LAT = -1.317
CENTER_LON = 36.789
DIST_CAP = 1000.0         # meters
BLOCK_MIN_VALID_COVERAGE = 0.70
MIN_TRAIN_SAMPLES = 1000  # Landsat 100m pixels
NODATA = -9999.0

RASTERS = {
    "ndvi": "data/processed/ndvi.tif",
    "ndwi": "data/processed/ndwi.tif",
    "ndbi": "data/processed/ndbi.tif",
    "landsat_st_celsius": "data/processed/landsat_st_celsius.tif",
    "building_density": "data/processed/building_density.tif",
    "road_density": "data/processed/road_density.tif",
    "distance_to_green": "data/processed/distance_to_green.tif",
    "distance_to_water": "data/processed/distance_to_water.tif",
    "population_density": "data/processed/population_density_20m.tif",
}

def main():
    print("Stage 1: Building 50m Block Grid...")

    # 1. Project CENTER_LON, CENTER_LAT to EPSG:32737
    transformer = Transformer.from_crs("EPSG:4326", PROCESS_CRS, always_xy=True)
    center_x, center_y = transformer.transform(CENTER_LON, CENTER_LAT)
    
    train_minx = center_x - TRAIN_HALF_SIZE
    train_maxx = center_x + TRAIN_HALF_SIZE
    train_miny = center_y - TRAIN_HALF_SIZE
    train_maxy = center_y + TRAIN_HALF_SIZE
    print(f"TRAIN_BOUNDS: ({train_minx}, {train_miny}, {train_maxx}, {train_maxy})")

    # Load kibera boundary
    boundary_path = "data/processed/kibera_boundary.geojson"
    if not os.path.exists(boundary_path):
        print(f"Error: Boundary file {boundary_path} not found.")
        sys.exit(1)
    
    boundary_gdf = gpd.read_file(boundary_path)
    if boundary_gdf.crs.to_string() != PROCESS_CRS:
        boundary_gdf = boundary_gdf.to_crs(PROCESS_CRS)
    boundary_geom = boundary_gdf.geometry.union_all() if hasattr(boundary_gdf.geometry, 'union_all') else boundary_gdf.geometry.unary_union

    # 2. Create square 50m grid covering kibera_boundary bounds,
    # aligned so grid origin = floor(bounds_min / 50) * 50
    b_minx, b_miny, b_maxx, b_maxy = boundary_geom.bounds
    grid_minx = math.floor(b_minx / BLOCK_SIZE) * BLOCK_SIZE
    grid_miny = math.floor(b_miny / BLOCK_SIZE) * BLOCK_SIZE
    grid_maxx = math.ceil(b_maxx / BLOCK_SIZE) * BLOCK_SIZE
    grid_maxy = math.ceil(b_maxy / BLOCK_SIZE) * BLOCK_SIZE

    cols = int(round((grid_maxx - grid_minx) / BLOCK_SIZE))
    rows = int(round((grid_maxy - grid_miny) / BLOCK_SIZE))
    print(f"Candidate grid: rows={rows}, cols={cols} covering ({grid_minx}, {grid_miny}) to ({grid_maxx}, {grid_maxy})")

    # 3. Keep blocks whose centroid is inside the boundary polygon
    candidate_blocks = []
    for r in range(rows):
        # row-major order: top to bottom (maxy down to miny) or bottom to top.
        # Standard row-major grid order: i is row from top (grid_maxy - (r+1)*50), j is col from left
        y_top = grid_maxy - r * BLOCK_SIZE
        y_bot = grid_maxy - (r + 1) * BLOCK_SIZE
        for c in range(cols):
            x_left = grid_minx + c * BLOCK_SIZE
            x_right = grid_minx + (c + 1) * BLOCK_SIZE
            geom = box(x_left, y_bot, x_right, y_top)
            centroid = geom.centroid
            if boundary_geom.contains(centroid):
                candidate_blocks.append({
                    "grid_i": r,
                    "grid_j": c,
                    "geometry": geom,
                    "minx": x_left,
                    "maxx": x_right,
                    "miny": y_bot,
                    "maxy": y_top,
                })

    print(f"Blocks with centroid inside boundary: {len(candidate_blocks)}")

    # 4. Load rasters and assign 20m pixel centers to blocks
    # Read reference raster metadata
    with rasterio.open(RASTERS["ndvi"]) as ref_src:
        transform = ref_src.transform
        raster_width = ref_src.width
        raster_height = ref_src.height

    raster_data = {}
    for name, path in RASTERS.items():
        with rasterio.open(path) as src:
            raster_data[name] = src.read(1)

    # 20m pixel centers across the entire raster
    # pixel (r, c) center in projected coordinates:
    # x = transform[2] + (c + 0.5) * transform[0]
    # y = transform[5] + (r + 0.5) * transform[4]
    
    # Process each block
    valid_blocks = []
    block_counter = 1

    for blk in candidate_blocks:
        bx_min, bx_max = blk["minx"], blk["maxx"]
        by_min, by_max = blk["miny"], blk["maxy"]

        # Pixel column and row ranges covering this block
        # transform[0] is dx (positive), transform[4] is dy (negative)
        c_min = int(math.floor((bx_min - transform[2]) / transform[0]))
        c_max = int(math.ceil((bx_max - transform[2]) / transform[0]))
        r_min = int(math.floor((by_max - transform[5]) / transform[4]))
        r_max = int(math.ceil((by_min - transform[5]) / transform[4]))

        c_min = max(0, c_min)
        c_max = min(raster_width, c_max)
        r_min = max(0, r_min)
        r_max = min(raster_height, r_max)

        assigned_pixel_count = 0
        valid_pixel_counts = {name: 0 for name in RASTERS}
        sums = {name: 0.0 for name in RASTERS}

        for r in range(r_min, r_max):
            py = transform[5] + (r + 0.5) * transform[4]
            if not (by_min <= py < by_max):
                continue
            for c in range(c_min, c_max):
                px = transform[2] + (c + 0.5) * transform[0]
                if not (bx_min <= px < bx_max):
                    continue
                
                assigned_pixel_count += 1
                for name, arr in raster_data.items():
                    val = arr[r, c]
                    if val != NODATA and not np.isnan(val):
                        valid_pixel_counts[name] += 1
                        sums[name] += float(val)

        if assigned_pixel_count == 0:
            continue

        # Coverage = valid_pixels / assigned_pixels
        # Using the minimum valid coverage across feature layers or primary layer
        coverages = [valid_pixel_counts[name] / assigned_pixel_count for name in RASTERS]
        min_cov = min(coverages)
        overall_cov = valid_pixel_counts["ndvi"] / assigned_pixel_count

        # Drop blocks with coverage < 0.70
        if min_cov < BLOCK_MIN_VALID_COVERAGE:
            continue

        means = {}
        for name in RASTERS:
            cnt = valid_pixel_counts[name]
            means[f"mean_{name}"] = sums[name] / cnt if cnt > 0 else 0.0

        estimated_pop = means["mean_population_density"] * 0.25

        valid_blocks.append({
            "block_id": f"KIB-{block_counter:04d}",
            "grid_i": blk["grid_i"],
            "grid_j": blk["grid_j"],
            "coverage": round(min_cov, 4),
            **means,
            "estimated_population": estimated_pop,
            "geometry": blk["geometry"]
        })
        block_counter += 1

    block_count = len(valid_blocks)
    print(f"Total valid blocks retained: {block_count}")

    # Gate G1: block count >= 500. Else exit(1).
    if block_count < 500:
        print(f"GATE G1 FAILED: block count {block_count} < 500")
        sys.exit(1)
    else:
        print(f"GATE G1 PASSED: block count = {block_count} >= 500")

    # Save data/processed/kibera_blocks_50m.geojson (CRS 32737)
    out_gdf = gpd.GeoDataFrame(valid_blocks, crs=PROCESS_CRS)
    out_path = "data/processed/kibera_blocks_50m.geojson"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    out_gdf.to_file(out_path, driver="GeoJSON")
    print(f"Saved block grid to {out_path}")
    print(f"STAGE 1 blocks: PASS | block_count: {block_count} | artifact: {out_path}")

if __name__ == "__main__":
    main()

import os
import sys
import math
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from pyproj import Transformer
import torch
from torch_geometric.data import Data

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

RASTER_PATHS = {
    "mean_ai_heat_base": "data/processed/ai_heat_base_20m.tif",
    "mean_ndvi": "data/processed/ndvi.tif",
    "mean_ndwi": "data/processed/ndwi.tif",
    "mean_ndbi": "data/processed/ndbi.tif",
    "mean_building_density": "data/processed/building_density.tif",
    "mean_road_density": "data/processed/road_density.tif",
    "mean_distance_to_green": "data/processed/distance_to_green.tif",
    "mean_distance_to_water": "data/processed/distance_to_water.tif",
    "mean_population_density": "data/processed/population_density_20m.tif",
}

FEATURE_NAMES = [
    "mean_ai_heat_base",
    "mean_ndvi",
    "mean_ndwi",
    "mean_ndbi",
    "mean_building_density",
    "mean_road_density",
    "mean_distance_to_green",
    "mean_distance_to_water",
    "mean_population_density",
]

def build_edges_8_neighborhood(grid_coords):
    """
    grid_coords: list or array of (grid_i, grid_j) for each node index 0..N-1
    Returns torch.Tensor edge_index of shape [2, num_edges] including 8-neighborhood and self-loops.
    """
    coord_to_idx = {coord: idx for idx, coord in enumerate(grid_coords)}
    src_nodes = []
    dst_nodes = []

    for idx, (gi, gj) in enumerate(grid_coords):
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                neighbor_coord = (gi + di, gj + dj)
                if neighbor_coord in coord_to_idx:
                    neighbor_idx = coord_to_idx[neighbor_coord]
                    src_nodes.append(idx)
                    dst_nodes.append(neighbor_idx)

    edge_index = torch.tensor([src_nodes, dst_nodes], dtype=torch.long)
    return edge_index

def extract_blocks_for_train_area(raster_data, transform, raster_width, raster_height, train_bounds):
    """
    Build 50m blocks over TRAIN_BOUNDS grid using Stage 1 aggregation logic.
    """
    train_minx, train_miny, train_maxx, train_maxy = train_bounds
    num_cols = int(round((train_maxx - train_minx) / BLOCK_SIZE))
    num_rows = int(round((train_maxy - train_miny) / BLOCK_SIZE))

    blocks = []
    for r in range(num_rows):
        y_top = train_maxy - r * BLOCK_SIZE
        y_bot = train_maxy - (r + 1) * BLOCK_SIZE
        for c in range(num_cols):
            x_left = train_minx + c * BLOCK_SIZE
            x_right = train_minx + (c + 1) * BLOCK_SIZE

            c_min = max(0, int(math.floor((x_left - transform[2]) / transform[0])))
            c_max = min(raster_width, int(math.ceil((x_right - transform[2]) / transform[0])))
            r_min = max(0, int(math.floor((y_top - transform[5]) / transform[4])))
            r_max = min(raster_height, int(math.ceil((y_bot - transform[5]) / transform[4])))

            assigned_pixel_count = 0
            valid_pixel_counts = {fn: 0 for fn in FEATURE_NAMES}
            sums = {fn: 0.0 for fn in FEATURE_NAMES}

            for pr in range(r_min, r_max):
                py = transform[5] + (pr + 0.5) * transform[4]
                if not (y_bot <= py < y_top):
                    continue
                for pc in range(c_min, c_max):
                    px = transform[2] + (pc + 0.5) * transform[0]
                    if not (x_left <= px < x_right):
                        continue

                    assigned_pixel_count += 1
                    for fn in FEATURE_NAMES:
                        val = raster_data[fn][pr, pc]
                        if val != NODATA and not np.isnan(val):
                            valid_pixel_counts[fn] += 1
                            sums[fn] += float(val)

            if assigned_pixel_count == 0:
                continue

            coverages = [valid_pixel_counts[fn] / assigned_pixel_count for fn in FEATURE_NAMES]
            min_cov = min(coverages)

            if min_cov < BLOCK_MIN_VALID_COVERAGE:
                continue

            means = {}
            for fn in FEATURE_NAMES:
                means[fn] = sums[fn] / valid_pixel_counts[fn]

            blocks.append({
                "grid_i": r,
                "grid_j": c,
                "coverage": min_cov,
                **means
            })

    return pd.DataFrame(blocks)

def main():
    print("Stage 4: Building Block Graphs for Train Area and Kibera...")
    torch.manual_seed(SEED)
    np.random.seed(SEED)

    # 1. Compute TRAIN_BOUNDS in EPSG:32737
    transformer = Transformer.from_crs("EPSG:4326", PROCESS_CRS, always_xy=True)
    center_x, center_y = transformer.transform(CENTER_LON, CENTER_LAT)
    
    train_minx = center_x - TRAIN_HALF_SIZE
    train_maxx = center_x + TRAIN_HALF_SIZE
    train_miny = center_y - TRAIN_HALF_SIZE
    train_maxy = center_y + TRAIN_HALF_SIZE
    train_bounds = (train_minx, train_miny, train_maxx, train_maxy)
    print(f"TRAIN_BOUNDS: {train_bounds}")

    # Read rasters
    with rasterio.open(RASTER_PATHS["mean_ai_heat_base"]) as ref_src:
        transform = ref_src.transform
        raster_width = ref_src.width
        raster_height = ref_src.height

    raster_data = {}
    for fn, path in RASTER_PATHS.items():
        if not os.path.exists(path):
            print(f"Error: Raster file {path} not found.")
            sys.exit(1)
        with rasterio.open(path) as src:
            raster_data[fn] = src.read(1)

    # (a) Extract TRAIN area blocks
    print("Extracting 50m blocks for TRAIN area...")
    df_train = extract_blocks_for_train_area(
        raster_data, transform, raster_width, raster_height, train_bounds
    )
    print(f"Valid TRAIN blocks: {len(df_train)}")
    if len(df_train) < 500:
        print(f"Error: Not enough valid train blocks ({len(df_train)} < 500)")
        sys.exit(1)

    # (b) Load and aggregate for Kibera blocks
    kibera_geojson_path = "data/processed/kibera_blocks_50m.geojson"
    if not os.path.exists(kibera_geojson_path):
        print(f"Error: {kibera_geojson_path} not found.")
        sys.exit(1)

    kibera_gdf = gpd.read_file(kibera_geojson_path)
    print(f"Loaded {len(kibera_gdf)} Kibera blocks.")

    # Aggregate mean_ai_heat_base for each Kibera block
    ai_heat_arr = raster_data["mean_ai_heat_base"]
    kibera_ai_heat_means = []

    for idx, row in kibera_gdf.iterrows():
        geom = row.geometry
        bx_min, by_min, bx_max, by_max = geom.bounds

        c_min = max(0, int(math.floor((bx_min - transform[2]) / transform[0])))
        c_max = min(raster_width, int(math.ceil((bx_max - transform[2]) / transform[0])))
        r_min = max(0, int(math.floor((by_max - transform[5]) / transform[4])))
        r_max = min(raster_height, int(math.ceil((by_min - transform[5]) / transform[4])))

        vals = []
        for pr in range(r_min, r_max):
            py = transform[5] + (pr + 0.5) * transform[4]
            if not (by_min <= py < by_max):
                continue
            for pc in range(c_min, c_max):
                px = transform[2] + (pc + 0.5) * transform[0]
                if not (bx_min <= px < bx_max):
                    continue
                v = ai_heat_arr[pr, pc]
                if v != NODATA and not np.isnan(v):
                    vals.append(float(v))

        if len(vals) > 0:
            kibera_ai_heat_means.append(float(np.mean(vals)))
        else:
            # Fallback if no valid pixel
            kibera_ai_heat_means.append(float(row.get("mean_landsat_st_celsius", 28.0)))

    kibera_gdf["mean_ai_heat_base"] = kibera_ai_heat_means

    # 2. Normalize node features with percentile (2, 98) computed on TRAIN blocks
    p2_dict = {}
    p98_dict = {}
    X_train_raw = df_train[FEATURE_NAMES].values
    X_kibera_raw = kibera_gdf[FEATURE_NAMES].values

    for i, fn in enumerate(FEATURE_NAMES):
        p2 = np.percentile(X_train_raw[:, i], 2)
        p98 = np.percentile(X_train_raw[:, i], 98)
        p2_dict[fn] = p2
        p98_dict[fn] = p98
        print(f"Feature {fn}: p2={p2:.4f}, p98={p98:.4f}")

    def normalize_features(X_raw):
        X_norm = np.zeros_like(X_raw, dtype=np.float32)
        for i, fn in enumerate(FEATURE_NAMES):
            p2 = p2_dict[fn]
            p98 = p98_dict[fn]
            if p98 - p2 < 1e-6:
                X_norm[:, i] = 0.5
            else:
                X_norm[:, i] = np.clip((X_raw[:, i] - p2) / (p98 - p2), 0.0, 1.0)
        return X_norm

    X_train_norm = normalize_features(X_train_raw)
    X_kibera_norm = normalize_features(X_kibera_raw)

    # 3. Target per node = normalized mean_ai_heat_base (0-1)
    y_train = X_train_norm[:, 0].copy()  # index 0 is mean_ai_heat_base
    y_kibera = X_kibera_norm[:, 0].copy()

    # 8-neighborhood edges
    print("Building 8-neighborhood graph edges...")
    train_coords = list(zip(df_train["grid_i"].values, df_train["grid_j"].values))
    edge_index_train = build_edges_8_neighborhood(train_coords)

    kibera_coords = list(zip(kibera_gdf["grid_i"].values, kibera_gdf["grid_j"].values))
    edge_index_kibera = build_edges_8_neighborhood(kibera_coords)

    print(f"TRAIN graph: {len(df_train)} nodes, {edge_index_train.shape[1]} edges")
    print(f"KIBERA graph: {len(kibera_gdf)} nodes, {edge_index_kibera.shape[1]} edges")

    # Build PyG Data objects
    graph_train = Data(
        x=torch.tensor(X_train_norm, dtype=torch.float32),
        edge_index=edge_index_train,
        y=torch.tensor(y_train, dtype=torch.float32).unsqueeze(1),
        grid_i=torch.tensor(df_train["grid_i"].values, dtype=torch.long),
        grid_j=torch.tensor(df_train["grid_j"].values, dtype=torch.long),
    )

    graph_kibera = Data(
        x=torch.tensor(X_kibera_norm, dtype=torch.float32),
        edge_index=edge_index_kibera,
        y=torch.tensor(y_kibera, dtype=torch.float32).unsqueeze(1),
        grid_i=torch.tensor(kibera_gdf["grid_i"].values, dtype=torch.long),
        grid_j=torch.tensor(kibera_gdf["grid_j"].values, dtype=torch.long),
    )

    # 4. Save PyG objects to models/graph_train.pt and models/graph_kibera.pt
    os.makedirs("models", exist_ok=True)
    train_graph_path = "models/graph_train.pt"
    kibera_graph_path = "models/graph_kibera.pt"

    torch.save(graph_train, train_graph_path)
    torch.save(graph_kibera, kibera_graph_path)

    # Also save the scaler params for later stages if needed
    scaler_df = pd.DataFrame([{"feature": fn, "p2": p2_dict[fn], "p98": p98_dict[fn]} for fn in FEATURE_NAMES])
    scaler_df.to_csv("models/graph_feature_scaler.csv", index=False)

    print(f"Saved {train_graph_path} and {kibera_graph_path}")
    print(f"STAGE 4 graph: PASS | train_nodes: {graph_train.num_nodes}, train_edges: {graph_train.num_edges} | kibera_nodes: {graph_kibera.num_nodes}, kibera_edges: {graph_kibera.num_edges} | artifact: {train_graph_path}")

if __name__ == "__main__":
    main()

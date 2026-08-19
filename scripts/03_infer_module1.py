import os
import sys
import math
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from xgboost import XGBRegressor

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

FEATURE_RASTERS = {
    "mean_ndvi": "data/processed/ndvi.tif",
    "mean_ndwi": "data/processed/ndwi.tif",
    "mean_ndbi": "data/processed/ndbi.tif",
    "mean_building_density": "data/processed/building_density.tif",
    "mean_road_density": "data/processed/road_density.tif",
    "mean_distance_to_green": "data/processed/distance_to_green.tif",
    "mean_distance_to_water": "data/processed/distance_to_water.tif",
    "mean_population_density": "data/processed/population_density_20m.tif",
}
TARGET_RASTER = "data/processed/landsat_st_celsius.tif"

FEATURE_COLS = [
    "mean_ndvi",
    "mean_ndwi",
    "mean_ndbi",
    "mean_building_density",
    "mean_road_density",
    "mean_distance_to_green",
    "mean_distance_to_water",
    "mean_population_density",
]

def main():
    print("Stage 3: Module 1 Inference + Bias Correction...")

    # Load trained model
    model_path = "models/module1_xgb.json"
    if not os.path.exists(model_path):
        print(f"Error: Model file {model_path} does not exist.")
        sys.exit(1)

    model = XGBRegressor()
    model.load_model(model_path)
    print(f"Loaded model from {model_path}")

    # Compute TRAIN_BOUNDS in EPSG:32737
    transformer = Transformer.from_crs("EPSG:4326", PROCESS_CRS, always_xy=True)
    center_x, center_y = transformer.transform(CENTER_LON, CENTER_LAT)
    
    train_minx = center_x - TRAIN_HALF_SIZE
    train_maxx = center_x + TRAIN_HALF_SIZE
    train_miny = center_y - TRAIN_HALF_SIZE
    train_maxy = center_y + TRAIN_HALF_SIZE
    print(f"TRAIN_BOUNDS: ({train_minx}, {train_miny}, {train_maxx}, {train_maxy})")

    # Read rasters
    with rasterio.open(TARGET_RASTER) as target_src:
        meta = target_src.meta.copy()
        transform = target_src.transform
        raster_width = target_src.width
        raster_height = target_src.height
        target_arr = target_src.read(1)

    feature_arrays = {}
    for feat_name, path in FEATURE_RASTERS.items():
        with rasterio.open(path) as src:
            feature_arrays[feat_name] = src.read(1)

    # 1. Identify valid 20m pixels inside TRAIN_BOUNDS and predict
    valid_pixels = []  # list of (r, c, cell_r, cell_c, feat_dict)
    cell_size = 100.0
    num_cols = int(round((train_maxx - train_minx) / cell_size))
    num_rows = int(round((train_maxy - train_miny) / cell_size))

    # Pre-calculate 100m cell targets
    cell_targets = {}
    for cr in range(num_rows):
        cell_top = train_maxy - cr * cell_size
        cell_bot = train_maxy - (cr + 1) * cell_size
        for cc in range(num_cols):
            cell_left = train_minx + cc * cell_size
            cell_right = train_minx + (cc + 1) * cell_size

            c_min = max(0, int(math.floor((cell_left - transform[2]) / transform[0])))
            c_max = min(raster_width, int(math.ceil((cell_right - transform[2]) / transform[0])))
            r_min = max(0, int(math.floor((cell_top - transform[5]) / transform[4])))
            r_max = min(raster_height, int(math.ceil((cell_bot - transform[5]) / transform[4])))

            t_vals = []
            for pr in range(r_min, r_max):
                py = transform[5] + (pr + 0.5) * transform[4]
                if not (cell_bot <= py < cell_top):
                    continue
                for pc in range(c_min, c_max):
                    px = transform[2] + (pc + 0.5) * transform[0]
                    if not (cell_left <= px < cell_right):
                        continue
                    t_val = target_arr[pr, pc]
                    if t_val != NODATA and not np.isnan(t_val) and 10.0 <= t_val <= 55.0:
                        t_vals.append(float(t_val))

            if len(t_vals) > 0:
                cell_targets[(cr, cc)] = np.mean(t_vals)

    print(f"Computed target_100m for {len(cell_targets)} cells")

    # Collect 20m pixels inside TRAIN_BOUNDS for inference
    pixel_records = []
    for r in range(raster_height):
        py = transform[5] + (r + 0.5) * transform[4]
        if not (train_miny <= py < train_maxy):
            continue
        cr = int(math.floor((train_maxy - py) / cell_size))
        cr = min(max(0, cr), num_rows - 1)

        for c in range(raster_width):
            px = transform[2] + (c + 0.5) * transform[0]
            if not (train_minx <= px < train_maxx):
                continue
            cc = int(math.floor((px - train_minx) / cell_size))
            cc = min(max(0, cc), num_cols - 1)

            # Check if all feature rasters are valid
            is_valid = True
            feat_vals = {}
            for fn in FEATURE_COLS:
                val = feature_arrays[fn][r, c]
                if val == NODATA or np.isnan(val):
                    is_valid = False
                    break
                feat_vals[fn] = float(val)

            if is_valid:
                pixel_records.append({
                    "r": r,
                    "c": c,
                    "cell_r": cr,
                    "cell_c": cc,
                    **feat_vals
                })

    df_pixels = pd.DataFrame(pixel_records)
    print(f"Total valid 20m pixels inside TRAIN_BOUNDS: {len(df_pixels)}")

    if len(df_pixels) == 0:
        print("Error: No valid 20m pixels found.")
        sys.exit(1)

    # Predict at 20m resolution
    preds_20m = model.predict(df_pixels[FEATURE_COLS])
    df_pixels["pred_20m"] = preds_20m

    # 2. For each 100m cell: correction = target_100m - mean(predictions in cell)
    # 3. corrected_20m = prediction + correction (per pixel, using its cell)
    cell_groups = df_pixels.groupby(["cell_r", "cell_c"])
    cell_corrections = {}
    cell_mean_preds = cell_groups["pred_20m"].mean()

    for (cr, cc), mean_pred in cell_mean_preds.items():
        if (cr, cc) in cell_targets:
            correction = cell_targets[(cr, cc)] - mean_pred
            cell_corrections[(cr, cc)] = correction
        else:
            cell_corrections[(cr, cc)] = 0.0

    df_pixels["correction"] = df_pixels.apply(
        lambda row: cell_corrections.get((row["cell_r"], row["cell_c"]), 0.0), axis=1
    )
    df_pixels["corrected_20m"] = df_pixels["pred_20m"] + df_pixels["correction"]

    # 5. Gate G4: max abs difference between cell-mean corrected values and target_100m <= 0.01
    cell_corrected_means = df_pixels.groupby(["cell_r", "cell_c"])["corrected_20m"].mean()
    max_abs_diff = 0.0
    evaluated_cells = 0

    for (cr, cc), mean_corr in cell_corrected_means.items():
        if (cr, cc) in cell_targets:
            diff = abs(mean_corr - cell_targets[(cr, cc)])
            if diff > max_abs_diff:
                max_abs_diff = diff
            evaluated_cells += 1

    print(f"Evaluated {evaluated_cells} cells for Gate G4.")
    print(f"Max abs difference (cell-mean corrected vs target_100m): {max_abs_diff:.6f} (Threshold: <= 0.01)")

    if max_abs_diff > 0.01:
        print(f"GATE G4 FAILED: max_abs_diff={max_abs_diff:.6f} > 0.01")
        sys.exit(1)
    else:
        print(f"GATE G4 PASSED: max_abs_diff={max_abs_diff:.6f} <= 0.01")

    # 4. Save data/processed/ai_heat_base_20m.tif (CRS 32737, nodata -9999)
    out_raster = np.full((raster_height, raster_width), NODATA, dtype=np.float32)
    for _, row in df_pixels.iterrows():
        out_raster[int(row["r"]), int(row["c"])] = np.float32(row["corrected_20m"])

    out_meta = meta.copy()
    out_meta.update({
        "driver": "GTiff",
        "dtype": "float32",
        "nodata": NODATA,
        "count": 1,
    })

    out_path = "data/processed/ai_heat_base_20m.tif"
    with rasterio.open(out_path, "w", **out_meta) as dst:
        dst.write(out_raster, 1)

    print(f"Saved ai_heat_base_20m to {out_path}")
    print(f"STAGE 3 m1-infer: PASS | pixels: {len(df_pixels)} | max_diff: {max_abs_diff:.6f} | artifact: {out_path}")

if __name__ == "__main__":
    main()

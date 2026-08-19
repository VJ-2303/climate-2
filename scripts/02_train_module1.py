import os
import sys
import math
import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
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
TARGET_COL = "target_st_celsius"

def main():
    print("Stage 2: Module 1 Training (XGBoost Regressor)...")

    # 1. Compute TRAIN_BOUNDS in EPSG:32737
    transformer = Transformer.from_crs("EPSG:4326", PROCESS_CRS, always_xy=True)
    center_x, center_y = transformer.transform(CENTER_LON, CENTER_LAT)
    
    train_minx = center_x - TRAIN_HALF_SIZE
    train_maxx = center_x + TRAIN_HALF_SIZE
    train_miny = center_y - TRAIN_HALF_SIZE
    train_maxy = center_y + TRAIN_HALF_SIZE
    print(f"TRAIN_BOUNDS: ({train_minx}, {train_miny}, {train_maxx}, {train_maxy})")

    # Read rasters
    with rasterio.open(TARGET_RASTER) as target_src:
        transform = target_src.transform
        raster_width = target_src.width
        raster_height = target_src.height
        target_arr = target_src.read(1)

    feature_arrays = {}
    for feat_name, path in FEATURE_RASTERS.items():
        with rasterio.open(path) as src:
            feature_arrays[feat_name] = src.read(1)

    # 2. Build 100m cells over TRAIN_BOUNDS (5x5 aggregation of 20m pixels)
    cell_size = 100.0
    num_cols = int(round((train_maxx - train_minx) / cell_size))
    num_rows = int(round((train_maxy - train_miny) / cell_size))
    print(f"100m grid over TRAIN_BOUNDS: {num_rows} rows x {num_cols} cols = {num_rows * num_cols} cells")

    samples = []
    for r in range(num_rows):
        # row-major order: top to bottom (train_maxy down to train_miny)
        cell_top = train_maxy - r * cell_size
        cell_bot = train_maxy - (r + 1) * cell_size
        for c in range(num_cols):
            cell_left = train_minx + c * cell_size
            cell_right = train_minx + (c + 1) * cell_size

            # Pixel column and row ranges covering this 100m cell
            c_min = int(math.floor((cell_left - transform[2]) / transform[0]))
            c_max = int(math.ceil((cell_right - transform[2]) / transform[0]))
            r_min = int(math.floor((cell_top - transform[5]) / transform[4]))
            r_max = int(math.ceil((cell_bot - transform[5]) / transform[4]))

            c_min = max(0, c_min)
            c_max = min(raster_width, c_max)
            r_min = max(0, r_min)
            r_max = min(raster_height, r_max)

            assigned_pixel_count = 0
            valid_target_count = 0
            target_sum = 0.0
            feat_valid_counts = {fn: 0 for fn in FEATURE_COLS}
            feat_sums = {fn: 0.0 for fn in FEATURE_COLS}

            for pr in range(r_min, r_max):
                py = transform[5] + (pr + 0.5) * transform[4]
                if not (cell_bot <= py < cell_top):
                    continue
                for pc in range(c_min, c_max):
                    px = transform[2] + (pc + 0.5) * transform[0]
                    if not (cell_left <= px < cell_right):
                        continue

                    assigned_pixel_count += 1

                    # Target
                    t_val = target_arr[pr, pc]
                    if t_val != NODATA and not np.isnan(t_val) and 10.0 <= t_val <= 55.0:
                        valid_target_count += 1
                        target_sum += float(t_val)

                    # Features
                    for fn in FEATURE_COLS:
                        f_val = feature_arrays[fn][pr, pc]
                        if f_val != NODATA and not np.isnan(f_val):
                            feat_valid_counts[fn] += 1
                            feat_sums[fn] += float(f_val)

            if assigned_pixel_count == 0 or valid_target_count == 0:
                continue

            # Coverage check: drop cells with coverage < 0.70 or nodata target
            target_coverage = valid_target_count / assigned_pixel_count
            min_feat_coverage = min(feat_valid_counts[fn] / assigned_pixel_count for fn in FEATURE_COLS)
            cell_coverage = min(target_coverage, min_feat_coverage)

            if cell_coverage < BLOCK_MIN_VALID_COVERAGE:
                continue

            row_data = {}
            for fn in FEATURE_COLS:
                row_data[fn] = feat_sums[fn] / feat_valid_counts[fn]
            row_data[TARGET_COL] = target_sum / valid_target_count
            row_data["cell_row"] = r
            row_data["cell_col"] = c
            row_data["coverage"] = cell_coverage
            samples.append(row_data)

    df = pd.DataFrame(samples)
    sample_count = len(df)
    print(f"Total valid 100m training samples: {sample_count}")

    # 4. Gate G2: sample count >= MIN_TRAIN_SAMPLES. Else exit(1).
    if sample_count < MIN_TRAIN_SAMPLES:
        print(f"GATE G2 FAILED: sample count {sample_count} < {MIN_TRAIN_SAMPLES}")
        sys.exit(1)
    else:
        print(f"GATE G2 PASSED: sample count = {sample_count} >= {MIN_TRAIN_SAMPLES}")

    # 5. Split 80/20 by row with SEED
    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.20, random_state=SEED
    )
    print(f"Train samples: {len(X_train)}, Validation samples: {len(X_val)}")

    # 6. Train XGBRegressor with EXACT hyperparameters from SPEC Section 7
    model = XGBRegressor(
        objective="reg:squarederror",
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=SEED,
        tree_method="hist",
    )

    print("Fitting XGBRegressor...")
    model.fit(X_train, y_train)

    # Predictions & Validation metrics
    y_pred_val = model.predict(X_val)
    val_r2 = float(r2_score(y_val, y_pred_val))
    val_mae = float(mean_absolute_error(y_val, y_pred_val))

    print(f"Validation R2: {val_r2:.4f} (Threshold: >= 0.25)")
    print(f"Validation MAE: {val_mae:.4f} (Threshold: <= 1.5)")

    # 7. Gate G3: validation R2 >= 0.25 AND validation MAE <= 1.5. Else exit(1).
    if val_r2 < 0.25 or val_mae > 1.5:
        print(f"GATE G3 FAILED: val_r2={val_r2:.4f} (req >= 0.25), val_mae={val_mae:.4f} (req <= 1.5)")
        sys.exit(1)
    else:
        print(f"GATE G3 PASSED: val_r2={val_r2:.4f} >= 0.25, val_mae={val_mae:.4f} <= 1.5")

    # 8. Save model to models/module1_xgb.json
    os.makedirs("models", exist_ok=True)
    model_path = "models/module1_xgb.json"
    model.save_model(model_path)
    print(f"Saved model to {model_path}")

    # 9. Append metrics to memory.md
    print(f"STAGE 2 m1-train: PASS | samples: {sample_count} | R2: {val_r2:.4f} | MAE: {val_mae:.4f} | artifact: {model_path}")

if __name__ == "__main__":
    main()

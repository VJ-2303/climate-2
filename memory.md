# HeatViz Memory
## Status: 08 api
## Completed Stages
- [x] 01 blocks  [x] 02 m1-train  [x] 03 m1-infer  [x] 04 graph
- [x] 05 m2-train  [x] 06 m2-infer  [x] 07 score-export  [x] 08 api  [x] 09 web
## Metrics Log
- Stage 01, G1 (block count >= 500): 17589, PASS, 2026-08-19T16:52:10+05:30
- Stage 02, G2 (sample count >= 1000): 2412, PASS, 2026-08-19T17:00:10+05:30
- Stage 02, G3 (val R2 >= 0.25, val MAE <= 1.5): R2=0.7417, MAE=1.0706, PASS, 2026-08-19T17:00:10+05:30
- Stage 03, G4 (max abs diff <= 0.01): max_diff=0.000003, PASS, 2026-08-19T17:14:18+05:30
- Stage 04 (graph build): train_nodes=9977, train_edges=88523, kibera_nodes=17589, kibera_edges=155685, PASS, 2026-08-19T17:25:55+05:30
- Stage 05, G5 (val Pearson corr >= 0.90): corr=0.9500, val_loss=0.005098, PASS, 2026-08-19T17:20:25+05:30
- Stage 06, G6 (contextual heat std >= 5.0): std=24.3156, PASS, 2026-08-19T18:24:49+05:30
- Stage 07, G7 (top-decile NDVI < overall, Bldg > overall): top_ndvi=17.54 < 42.90, top_bldg=36.82 > 11.68, PASS, 2026-08-19T18:33:24+05:30
- Stage 01, G1 (block count >= 500): 17589, PASS, 2026-08-19T19:31:33+05:30
- Stage 02, G2 (sample count >= 1000): 2412, PASS, 2026-08-19T19:31:43+05:30
- Stage 02, G3 (val R2 >= 0.25, val MAE <= 1.5): R2=0.7507, MAE=1.0482, PASS, 2026-08-19T19:31:43+05:30
- Stage 03, G4 (max abs diff <= 0.01): max_diff=0.000002, PASS, 2026-08-19T19:31:54+05:30
- Stage 04 (graph build): train_nodes=9977, train_edges=88523, kibera_nodes=17589, kibera_edges=155685, PASS, 2026-08-19T19:32:07+05:30
- Stage 05, G5 (val Pearson corr >= 0.90): corr=0.9494, val_loss=0.005156, PASS, 2026-08-19T19:34:08+05:30
- Stage 06, G6 (contextual heat std >= 5.0): std=24.3031, PASS, 2026-08-19T19:34:25+05:30
- Stage 07, G7 (top-decile NDVI < overall, Bldg > overall): top_ndvi=17.55 < 42.90, top_bldg=36.70 > 11.68, PASS, 2026-08-19T19:34:49+05:30
## Artifacts
- data/processed/kibera_blocks_50m.geojson
- models/module1_xgb.json
- data/processed/ai_heat_base_20m.tif
- models/graph_train.pt
- models/graph_kibera.pt
- models/module2_gat.pt
- data/output/vulnerability_blocks.geojson
- data/output/layers/ai_heat_exposure_blocks.geojson
- data/output/layers/social_sensitivity_blocks.geojson
- data/output/layers/cooling_deficit_blocks.geojson
- data/output/layers/ndvi_blocks.geojson
- data/output/layers/ndbi_blocks.geojson
- data/output/layers/building_density_blocks.geojson
- data/output/layers/population_density_blocks.geojson
## Blockers
none

## Session Log
- Stage 08 api backend implemented in api/main.py with SPEC routes: /, /static, /data/vulnerability_blocks.geojson, /data/layers/{name}.geojson. Syntax check passed. Data files were not modified. Runtime data serving requires existing data/output GeoJSON artifacts. 2026-08-19T19:02:12+05:30
- Full ML Pipeline (Stages 01-07) executed on CPU: all gates G1-G7 passed, XGBoost and HeatGAT models saved, all 50m GeoJSON layer exports generated in EPSG:4326. 2026-08-19T19:35:00+05:30

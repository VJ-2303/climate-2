# HeatViz — Quick Setup Guide (Preprocessed Data Mode)

Run HeatViz using pre-processed data without training ML models (Module 1 XGBoost / Module 2 GAT).

---

## Prerequisites

- Python 3.10, 3.11, or 3.12
- `uv` (recommended) or standard `python3-venv` / `pip`
- Pre-processed data present at `data/processed/kibera_blocks_50m.geojson`

---

## 1. Environment Setup

### Option A: Using `uv` (Fastest)

```bash
# Create Python 3.11/3.12 virtual environment
uv venv --python 3.11 .venv

# Activate environment
source .venv/bin/activate

# Install runtime dependencies (no PyTorch/XGBoost required)
uv pip install geopandas fastapi uvicorn
```

### Option B: Using Standard Python `pip`

```bash
# Create virtual environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install minimal runtime dependencies
pip install geopandas fastapi uvicorn
```

---

## 2. Export Vulnerability Layers (One-time)

If `data/output/vulnerability_blocks.geojson` does not exist yet, generate it from `data/processed/kibera_blocks_50m.geojson`:

```bash
python scripts/07_score_export.py
```

This takes ~3 seconds and generates:
- `data/output/vulnerability_blocks.geojson` (18,040 sectors with HVI scores and drivers)
- `data/output/layers/*.geojson` (7 sub-layer attribute geojsons)

---

## 3. Run Application Server

Start the FastAPI server:

```bash
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open browser at:
```
http://127.0.0.1:8000
```

---

## 4. Full ML Pipeline (Optional: Retrain Models from Scratch)

To train Module 1 (XGBoost) and Module 2 (PyTorch Geometric GAT) from raw satellite rasters:

```bash
# Install full dependencies
uv pip install -r requirements.txt

# Execute stages in numeric order
python scripts/01_build_blocks.py     # Build 50m grid & aggregate rasters (Gate G1)
python scripts/02_train_module1.py    # Train XGBoost at 100m (Gates G2, G3)
python scripts/03_infer_module1.py    # 20m inference & bias correction (Gate G4)
python scripts/04_build_graph.py      # Build 8-neighbor spatial graph
python scripts/05_train_module2.py    # Train GAT context model (Gate G5)
python scripts/06_infer_module2.py    # Infer contextual heat (Gate G6)
python scripts/07_score_export.py     # Compute HVI scores & export GeoJSON (Gate G7)
```

---

## 5. Notes on Basemaps & API Keys

- **No API key is required**: Default street basemap uses OpenStreetMap (`tile.openstreetmap.org`) and satellite imagery uses ESRI World Imagery. Both are 100% free and public.
- If you previously opened the map and saw an **"API key required"** watermark, clear your browser cache or click **Clear Cache** in the Offline Cache modal (`v2` tile cache flushes old Carto tiles automatically).

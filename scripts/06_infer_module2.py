import os
import sys
import numpy as np
import geopandas as gpd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GATv2Conv

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

# Exact Model Architecture from SPEC.md Section 10
class HeatGAT(nn.Module):
    def __init__(self):
        super().__init__()
        # GATv2Conv(in=9, out=32, heads=4) -> ELU -> Dropout(0.1)
        self.conv1 = GATv2Conv(in_channels=9, out_channels=32, heads=4)
        self.dropout1 = nn.Dropout(0.1)
        
        # GATv2Conv(in=128, out=16, heads=2, concat=False) -> ELU -> Dropout(0.1)
        self.conv2 = GATv2Conv(in_channels=128, out_channels=16, heads=2, concat=False)
        self.dropout2 = nn.Dropout(0.1)
        
        # Linear(16, 1) -> Sigmoid
        self.linear = nn.Linear(16, 1)

    def forward(self, x, edge_index):
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = self.dropout1(x)
        
        x = self.conv2(x, edge_index)
        x = F.elu(x)
        x = self.dropout2(x)
        
        x = self.linear(x)
        x = torch.sigmoid(x)
        return x

def main():
    print("Stage 6: Module 2 Inference (Graph Attention Network Contextual Heat)...")

    # 1. Load graph_kibera.pt and model
    graph_path = "models/graph_kibera.pt"
    model_path = "models/module2_gat.pt"

    if not os.path.exists(graph_path):
        print(f"Error: {graph_path} not found.")
        sys.exit(1)
    if not os.path.exists(model_path):
        print(f"Error: {model_path} not found.")
        sys.exit(1)

    data = torch.load(graph_path, weights_only=False)
    print(f"Loaded Kibera graph: {data.num_nodes} nodes, {data.edge_index.shape[1]} edges")

    model = HeatGAT()
    model.load_state_dict(torch.load(model_path, weights_only=True))
    model.eval()
    print(f"Loaded trained HeatGAT model from {model_path}")

    # 2. Output contextual_heat_01 = model(x, edge_index)
    with torch.no_grad():
        contextual_heat_01 = model(data.x, data.edge_index)

    # 3. contextual_ai_heat = contextual_heat_01 * 100
    contextual_ai_heat = contextual_heat_01.cpu().numpy().flatten() * 100.0
    print(f"Inferred contextual_ai_heat for {len(contextual_ai_heat)} blocks.")
    print(f"Summary stats: min={contextual_ai_heat.min():.4f}, mean={contextual_ai_heat.mean():.4f}, std={contextual_ai_heat.std():.4f}, max={contextual_ai_heat.max():.4f}")

    # 4. Gate G6: std(contextual_ai_heat over Kibera blocks) >= 5.0
    std_val = float(np.std(contextual_ai_heat))
    print(f"Standard deviation: {std_val:.4f} (Threshold: >= 5.0)")

    if std_val < 5.0:
        print(f"GATE G6 FAILED: std={std_val:.4f} < 5.0")
        sys.exit(1)
    else:
        print(f"GATE G6 PASSED: std={std_val:.4f} >= 5.0")

    # 5. Attach to block table
    kibera_geojson_path = "data/processed/kibera_blocks_50m.geojson"
    if not os.path.exists(kibera_geojson_path):
        print(f"Error: {kibera_geojson_path} not found.")
        sys.exit(1)

    gdf = gpd.read_file(kibera_geojson_path)
    if len(gdf) != len(contextual_ai_heat):
        print(f"Error: Row count mismatch: {len(gdf)} blocks vs {len(contextual_ai_heat)} predictions")
        sys.exit(1)

    gdf["contextual_ai_heat"] = contextual_ai_heat
    gdf.to_file(kibera_geojson_path, driver="GeoJSON")
    print(f"Attached contextual_ai_heat and saved updated block table to {kibera_geojson_path}")
    print(f"STAGE 6 m2-infer: PASS | blocks: {len(gdf)} | std: {std_val:.4f} | artifact: {kibera_geojson_path}")

if __name__ == "__main__":
    main()

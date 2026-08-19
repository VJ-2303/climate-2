import os
import sys
import copy
import numpy as np
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
    print("Stage 5: Module 2 Training (Graph Attention Network - HeatGAT)...")

    torch.manual_seed(SEED)
    np.random.seed(SEED)

    train_graph_path = "models/graph_train.pt"
    if not os.path.exists(train_graph_path):
        print(f"Error: {train_graph_path} not found.")
        sys.exit(1)

    data = torch.load(train_graph_path, weights_only=False)
    print(f"Loaded train graph: {data.num_nodes} nodes, {data.num_edges} edges")

    # Split: 80/20 nodes, SEED
    num_nodes = data.num_nodes
    rng = np.random.RandomState(SEED)
    perm = rng.permutation(num_nodes)
    train_size = int(0.8 * num_nodes)

    train_idx = perm[:train_size]
    val_idx = perm[train_size:]

    train_mask = torch.zeros(num_nodes, dtype=torch.bool)
    train_mask[train_idx] = True

    val_mask = torch.zeros(num_nodes, dtype=torch.bool)
    val_mask[val_idx] = True

    print(f"Train nodes: {train_mask.sum().item()}, Val nodes: {val_mask.sum().item()}")

    # Model & Optimizer
    model = HeatGAT()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.005)

    x = data.x
    edge_index = data.edge_index
    target = data.y  # shape [N, 1]

    # Pre-extract edge indices for smoothness loss
    src_nodes = edge_index[0]
    dst_nodes = edge_index[1]

    # Training settings
    epochs = 200
    patience = 20
    best_val_loss = float("inf")
    patience_counter = 0
    best_model_state = None
    best_epoch = 0

    print("Beginning GAT training for 200 epochs with patience 20...")
    for epoch in range(1, epochs + 1):
        model.train()
        optimizer.zero_grad()

        pred = model(x, edge_index)

        # Loss = 0.9 * MSE(pred, target) + 0.1 * mean_over_edges((pred_i - pred_j)^2)
        mse_loss = F.mse_loss(pred[train_mask], target[train_mask])
        edge_diff = pred[src_nodes] - pred[dst_nodes]
        smoothness_loss = torch.mean(edge_diff ** 2)

        loss = 0.9 * mse_loss + 0.1 * smoothness_loss
        loss.backward()
        optimizer.step()

        # Validation
        model.eval()
        with torch.no_grad():
            val_pred = model(x, edge_index)
            val_mse = F.mse_loss(val_pred[val_mask], target[val_mask])
            val_edge_diff = val_pred[src_nodes] - val_pred[dst_nodes]
            val_smoothness = torch.mean(val_edge_diff ** 2)
            val_loss = 0.9 * val_mse + 0.1 * val_smoothness

        if val_loss.item() < best_val_loss:
            best_val_loss = val_loss.item()
            best_model_state = copy.deepcopy(model.state_dict())
            best_epoch = epoch
            patience_counter = 0
        else:
            patience_counter += 1

        if epoch % 20 == 0 or epoch == 1 or patience_counter == 0:
            print(f"Epoch {epoch:03d} | Train Loss: {loss.item():.6f} (MSE: {mse_loss.item():.6f}) | Val Loss: {val_loss.item():.6f} (MSE: {val_mse.item():.6f}) | Patience: {patience_counter}/{patience}")

        if patience_counter >= patience:
            print(f"Early stopping triggered at epoch {epoch}. Best epoch was {best_epoch} with val loss {best_val_loss:.6f}")
            break

    # Load best model
    model.load_state_dict(best_model_state)
    model.eval()

    with torch.no_grad():
        final_pred = model(x, edge_index)
        y_val_pred = final_pred[val_mask].cpu().numpy().flatten()
        y_val_true = target[val_mask].cpu().numpy().flatten()

    # Pearson correlation
    corr_matrix = np.corrcoef(y_val_pred, y_val_true)
    val_corr = float(corr_matrix[0, 1])
    val_mse_final = float(np.mean((y_val_pred - y_val_true) ** 2))
    val_mae_final = float(np.mean(np.abs(y_val_pred - y_val_true)))

    print(f"\nFinal Validation Pearson Correlation: {val_corr:.4f} (Threshold: >= 0.90)")
    print(f"Final Validation MSE: {val_mse_final:.6f}, MAE: {val_mae_final:.4f}")

    # Gate G5: validation Pearson correlation(pred, target) >= 0.90. Else exit(1).
    if val_corr < 0.90:
        print(f"GATE G5 FAILED: val_corr={val_corr:.4f} < 0.90")
        sys.exit(1)
    else:
        print(f"GATE G5 PASSED: val_corr={val_corr:.4f} >= 0.90")

    # Save models/module2_gat.pt
    out_model_path = "models/module2_gat.pt"
    torch.save(model.state_dict(), out_model_path)
    print(f"Saved model checkpoint to {out_model_path}")
    print(f"STAGE 5 m2-train: PASS | best_epoch: {best_epoch} | corr: {val_corr:.4f} | val_loss: {best_val_loss:.6f} | artifact: {out_model_path}")

if __name__ == "__main__":
    main()

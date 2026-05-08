"""
Heterogeneous Graph Neural Network Training Script.
Predicts cascade failure probability for each node given an initial failure set.
"""
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.data import HeteroData
from torch_geometric.nn import HeteroConv, GATConv, Linear
from torch_geometric.transforms import ToUndirected
import numpy as np
import json
import os
from datetime import datetime
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score


# ─── Node and Edge Type Definitions ───────────────────────────────────────────

NODE_TYPES = ["power", "transport", "telecom", "emergency", "mobility", "service"]
EDGE_TYPES = [
    ("power",     "powers",         "telecom"),
    ("power",     "powers",         "emergency"),
    ("power",     "powers",         "mobility"),
    ("power",     "powers",         "service"),
    ("telecom",   "provides_comms", "emergency"),
    ("telecom",   "provides_comms", "transport"),
    ("transport", "road_access",    "emergency"),
    ("transport", "road_access",    "service"),
    ("transport", "enables_access", "mobility"),
    ("service",   "fuel_supply",    "emergency"),
    ("service",   "fuel_supply",    "power"),
]

NODE_FEATURE_DIM = 12  # See docs/04_ml_models.md


# ─── Model Definition ─────────────────────────────────────────────────────────

class CascadeGNN(nn.Module):
    """
    Heterogeneous Graph Attention Network for cascade failure prediction.
    
    Predicts P(node fails within T hours) given initial failure set.
    """
    def __init__(
        self,
        in_channels: int = NODE_FEATURE_DIM,
        hidden_channels: int = 64,
        num_heads: int = 4,
        dropout: float = 0.2,
    ):
        super().__init__()
        self.dropout = dropout

        # Type-specific input projections
        self.input_proj = nn.ModuleDict({
            node_type: nn.Linear(in_channels, hidden_channels)
            for node_type in NODE_TYPES
        })

        # Layer 1: Heterogeneous GAT
        self.conv1 = HeteroConv(
            {
                edge_type: GATConv(
                    in_channels=hidden_channels,
                    out_channels=hidden_channels // num_heads,
                    heads=num_heads,
                    dropout=dropout,
                    add_self_loops=False,
                )
                for edge_type in EDGE_TYPES
            },
            aggr="sum",
        )

        # Layer 2: Heterogeneous GAT
        self.conv2 = HeteroConv(
            {
                edge_type: GATConv(
                    in_channels=hidden_channels,
                    out_channels=hidden_channels,
                    heads=1,
                    dropout=dropout,
                    add_self_loops=False,
                )
                for edge_type in EDGE_TYPES
            },
            aggr="sum",
        )

        # Output classifier per node type
        self.classifiers = nn.ModuleDict({
            node_type: nn.Sequential(
                nn.Linear(hidden_channels, 32),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(32, 1),
            )
            for node_type in NODE_TYPES
        })

    def forward(self, x_dict: dict, edge_index_dict: dict) -> dict:
        # Project inputs
        h = {
            node_type: F.relu(self.input_proj[node_type](x))
            for node_type, x in x_dict.items()
            if node_type in self.input_proj
        }

        # Layer 1
        h = self.conv1(h, edge_index_dict)
        h = {k: F.relu(F.dropout(v, p=self.dropout, training=self.training)) for k, v in h.items()}

        # Layer 2
        h = self.conv2(h, edge_index_dict)
        h = {k: F.relu(v) for k, v in h.items()}

        # Classify each node type
        out = {
            node_type: torch.sigmoid(self.classifiers[node_type](h[node_type]))
            for node_type in NODE_TYPES
            if node_type in h
        }
        return out


# ─── Synthetic Graph Generation ───────────────────────────────────────────────

def generate_synthetic_hetero_graph(n_nodes_per_type: int = 50) -> tuple:
    """
    Generate a synthetic heterogeneous graph for training.
    Returns (HeteroData, labels_dict).
    """
    data = HeteroData()

    # Node features
    for node_type in NODE_TYPES:
        n = n_nodes_per_type
        features = np.random.randn(n, NODE_FEATURE_DIM).astype(np.float32)
        # Feature 0: initial failure flag (binary)
        features[:, 0] = (np.random.random(n) < 0.15).astype(np.float32)
        data[node_type].x = torch.FloatTensor(features)
        data[node_type].num_nodes = n

    # Edges
    for src_type, edge_name, dst_type in EDGE_TYPES:
        n_src = n_nodes_per_type
        n_dst = n_nodes_per_type
        n_edges = np.random.randint(n_src // 2, n_src * 2)
        src_idx = np.random.randint(0, n_src, n_edges)
        dst_idx = np.random.randint(0, n_dst, n_edges)
        # Remove self-loops
        mask = src_idx != dst_idx
        edge_index = torch.LongTensor(np.stack([src_idx[mask], dst_idx[mask]]))
        data[src_type, edge_name, dst_type].edge_index = edge_index

    # Labels: cascade failure probability
    # Nodes with high initial failure rate in their neighborhood are more likely to fail
    labels = {}
    for node_type in NODE_TYPES:
        n = n_nodes_per_type
        initial_failures = data[node_type].x[:, 0].numpy()
        # Simple cascade: nodes near failed nodes have higher failure probability
        cascade_prob = 0.1 + 0.6 * initial_failures + np.random.uniform(0, 0.3, n)
        labels[node_type] = torch.FloatTensor(np.clip(cascade_prob, 0, 1) > 0.5).long()

    return data, labels


# ─── Training ─────────────────────────────────────────────────────────────────

def train_gnn(
    output_dir: str = "ml_pipeline/artifacts",
    epochs: int = 100,
    lr: float = 1e-3,
    patience: int = 15,
):
    """Train the cascade failure GNN."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training GNN on: {device}")

    # Generate training data (replace with real DB data in production)
    print("Generating synthetic graph training data...")
    n_graphs = 200  # 200 disaster scenarios
    train_graphs = [generate_synthetic_hetero_graph(50) for _ in range(int(n_graphs * 0.7))]
    val_graphs = [generate_synthetic_hetero_graph(50) for _ in range(int(n_graphs * 0.15))]
    test_graphs = [generate_synthetic_hetero_graph(50) for _ in range(int(n_graphs * 0.15))]

    print(f"Train graphs: {len(train_graphs)}, Val: {len(val_graphs)}, Test: {len(test_graphs)}")

    model = CascadeGNN(
        in_channels=NODE_FEATURE_DIM,
        hidden_channels=64,
        num_heads=4,
        dropout=0.2,
    ).to(device)

    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    criterion = nn.BCELoss()

    best_val_auc = 0.0
    patience_counter = 0

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        for data, labels in train_graphs:
            data = data.to(device)
            labels_device = {k: v.float().to(device) for k, v in labels.items()}

            optimizer.zero_grad()
            out = model(data.x_dict, data.edge_index_dict)

            loss = sum(
                criterion(out[nt].squeeze(), labels_device[nt])
                for nt in NODE_TYPES if nt in out
            )
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_graphs)
        scheduler.step()

        # Validate
        model.eval()
        all_preds, all_labels = [], []
        with torch.no_grad():
            for data, labels in val_graphs:
                data = data.to(device)
                out = model(data.x_dict, data.edge_index_dict)
                for nt in NODE_TYPES:
                    if nt in out:
                        all_preds.extend(out[nt].squeeze().cpu().numpy())
                        all_labels.extend(labels[nt].numpy())

        val_auc = roc_auc_score(all_labels, all_preds) if len(set(all_labels)) > 1 else 0.5

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:3d}/{epochs} | Train Loss: {train_loss:.4f} | Val AUC: {val_auc:.4f}")

        if val_auc > best_val_auc:
            best_val_auc = val_auc
            patience_counter = 0
            os.makedirs(output_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(output_dir, "gnn_cascade_best.pt"))
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    # Test evaluation
    model.load_state_dict(torch.load(os.path.join(output_dir, "gnn_cascade_best.pt")))
    model.eval()
    all_preds, all_labels = [], []
    with torch.no_grad():
        for data, labels in test_graphs:
            data = data.to(device)
            out = model(data.x_dict, data.edge_index_dict)
            for nt in NODE_TYPES:
                if nt in out:
                    all_preds.extend(out[nt].squeeze().cpu().numpy())
                    all_labels.extend(labels[nt].numpy())

    all_preds_bin = (np.array(all_preds) > 0.5).astype(int)
    test_auc = roc_auc_score(all_labels, all_preds)
    test_f1 = f1_score(all_labels, all_preds_bin, zero_division=0)
    test_precision = precision_score(all_labels, all_preds_bin, zero_division=0)
    test_recall = recall_score(all_labels, all_preds_bin, zero_division=0)

    print(f"\n=== Test Set Evaluation ===")
    print(f"AUC-ROC:   {test_auc:.4f}")
    print(f"F1 Score:  {test_f1:.4f}")
    print(f"Precision: {test_precision:.4f}")
    print(f"Recall:    {test_recall:.4f}")

    config = {
        "model_type": "CascadeGNN",
        "version": "gnn-v1.0",
        "node_types": NODE_TYPES,
        "edge_types": [list(e) for e in EDGE_TYPES],
        "in_channels": NODE_FEATURE_DIM,
        "hidden_channels": 64,
        "num_heads": 4,
        "trained_at": datetime.now().isoformat(),
        "test_auc": float(test_auc),
        "test_f1": float(test_f1),
    }
    with open(os.path.join(output_dir, "gnn_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ GNN model saved to {output_dir}/gnn_cascade_best.pt")
    return model, config


if __name__ == "__main__":
    train_gnn(output_dir="ml_pipeline/artifacts")

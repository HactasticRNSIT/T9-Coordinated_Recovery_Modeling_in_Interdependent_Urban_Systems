"""
LSTM Recovery Timeline Predictor Training Script.

Trains a sequence model to predict hours-to-restoration for infrastructure nodes.
Input: Time-series of node status observations
Output: Predicted hours until full restoration
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split
import joblib
import os
import json
from datetime import datetime


# ─── Model Definition ─────────────────────────────────────────────────────────

class RecoveryLSTM(nn.Module):
    """
    LSTM with attention for recovery timeline prediction.
    
    Input:  (batch, seq_len, input_size) — time-series of node observations
    Output: (batch, 1) — predicted hours to restoration
    """
    def __init__(self, input_size: int = 8, hidden_size: int = 128, num_layers: int = 2, dropout: float = 0.2):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout if num_layers > 1 else 0.0,
            batch_first=True,
        )
        self.attention = nn.MultiheadAttention(
            embed_dim=hidden_size,
            num_heads=4,
            dropout=0.1,
            batch_first=True,
        )
        self.layer_norm = nn.LayerNorm(hidden_size)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )
        # Softplus ensures non-negative output (hours must be >= 0)
        self.output_activation = nn.Softplus()

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # LSTM encoding
        lstm_out, _ = self.lstm(x)  # (batch, seq, hidden)

        # Self-attention over sequence
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        attn_out = self.layer_norm(lstm_out + attn_out)  # residual

        # Use last timestep representation
        last_hidden = attn_out[:, -1, :]  # (batch, hidden)

        # Predict hours to restoration
        out = self.fc(last_hidden)
        return self.output_activation(out)


# ─── Dataset ──────────────────────────────────────────────────────────────────

class RecoveryDataset(Dataset):
    """
    Dataset of node recovery sequences.
    
    Each sample is a sequence of observations for one node during one incident,
    with the label being hours_to_restoration at the last observed timestep.
    """
    def __init__(self, sequences: np.ndarray, labels: np.ndarray):
        self.sequences = torch.FloatTensor(sequences)
        self.labels = torch.FloatTensor(labels).unsqueeze(1)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.labels[idx]


# ─── Feature Engineering ──────────────────────────────────────────────────────

SEQUENCE_FEATURES = [
    "operational_pct_norm",
    "repair_progress_pct_norm",
    "repair_crew_assigned",
    "hours_since_failure_norm",
    "load_pct_norm",
    "dependency_recovery_pct_norm",  # avg % of dependencies restored
    "disaster_severity_norm",
    "criticality_score",
]

SEQ_LEN = 12  # 12 observations = 6 hours at 30-min intervals


def build_sequences(df: pd.DataFrame, scaler: StandardScaler = None) -> tuple:
    """
    Build fixed-length sequences from status history DataFrame.
    Pads shorter sequences with zeros, truncates longer ones.
    """
    sequences = []
    labels = []

    # Group by (node_id, incident_id)
    for (node_id, incident_id), group in df.groupby(["node_id", "incident_id"]):
        group = group.sort_values("hours_since_failure")

        # Skip if node was never failed
        if group["status"].iloc[0] != "failed":
            continue

        # Extract feature matrix
        feature_cols = [c for c in SEQUENCE_FEATURES if c in group.columns]
        feature_matrix = group[feature_cols].values.astype(np.float32)

        # Pad or truncate to SEQ_LEN
        if len(feature_matrix) >= SEQ_LEN:
            seq = feature_matrix[:SEQ_LEN]
        else:
            pad = np.zeros((SEQ_LEN - len(feature_matrix), len(feature_cols)), dtype=np.float32)
            seq = np.vstack([feature_matrix, pad])

        # Label: hours_to_restoration at last observed timestep
        label = group["hours_to_restoration"].iloc[min(SEQ_LEN - 1, len(group) - 1)]
        if pd.isna(label) or label < 0:
            continue

        sequences.append(seq)
        labels.append(float(label))

    return np.array(sequences), np.array(labels)


# ─── Training ─────────────────────────────────────────────────────────────────

def train_model(
    data_path: str = None,
    output_dir: str = "ml_pipeline/artifacts",
    epochs: int = 100,
    batch_size: int = 256,
    lr: float = 1e-3,
    patience: int = 10,
):
    """Train the LSTM recovery predictor."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Training on: {device}")

    # Load data (from DB or CSV)
    if data_path and os.path.exists(data_path):
        df = pd.read_csv(data_path)
    else:
        print("No data path provided — generating synthetic training data...")
        df = generate_synthetic_training_data()

    print(f"Loaded {len(df)} status history records")

    # Build sequences
    sequences, labels = build_sequences(df)
    print(f"Built {len(sequences)} training sequences")

    if len(sequences) == 0:
        raise ValueError("No valid sequences found in data")

    # Train/val/test split
    X_train, X_temp, y_train, y_temp = train_test_split(sequences, labels, test_size=0.3, random_state=42)
    X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

    print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

    # Datasets and loaders
    train_ds = RecoveryDataset(X_train, y_train)
    val_ds = RecoveryDataset(X_val, y_val)
    test_ds = RecoveryDataset(X_test, y_test)

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=0)
    test_loader = DataLoader(test_ds, batch_size=batch_size, shuffle=False, num_workers=0)

    # Model
    input_size = sequences.shape[2]
    model = RecoveryLSTM(input_size=input_size, hidden_size=128, num_layers=2, dropout=0.2)
    model = model.to(device)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")

    # Optimizer and loss
    optimizer = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)
    criterion = nn.HuberLoss(delta=5.0)  # Robust to outliers

    # Training loop
    best_val_loss = float("inf")
    patience_counter = 0
    train_losses = []
    val_losses = []

    for epoch in range(epochs):
        # Train
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            pred = model(X_batch)
            loss = criterion(pred, y_batch)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            train_loss += loss.item() * len(X_batch)
        train_loss /= len(train_ds)

        # Validate
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in val_loader:
                X_batch, y_batch = X_batch.to(device), y_batch.to(device)
                pred = model(X_batch)
                val_loss += criterion(pred, y_batch).item() * len(X_batch)
        val_loss /= len(val_ds)

        scheduler.step(val_loss)
        train_losses.append(train_loss)
        val_losses.append(val_loss)

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1:3d}/{epochs} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f}")

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            # Save best model
            os.makedirs(output_dir, exist_ok=True)
            torch.save(model.state_dict(), os.path.join(output_dir, "lstm_recovery_best.pt"))
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping at epoch {epoch+1}")
                break

    # Load best model and evaluate on test set
    model.load_state_dict(torch.load(os.path.join(output_dir, "lstm_recovery_best.pt")))
    model.eval()

    all_preds, all_labels = [], []
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(device)
            pred = model(X_batch).cpu().numpy().flatten()
            all_preds.extend(pred)
            all_labels.extend(y_batch.numpy().flatten())

    all_preds = np.array(all_preds)
    all_labels = np.array(all_labels)

    mae = np.mean(np.abs(all_preds - all_labels))
    rmse = np.sqrt(np.mean((all_preds - all_labels) ** 2))
    mape = np.mean(np.abs((all_preds - all_labels) / (all_labels + 1e-6))) * 100

    print(f"\n=== Test Set Evaluation ===")
    print(f"MAE:  {mae:.3f} hours")
    print(f"RMSE: {rmse:.3f} hours")
    print(f"MAPE: {mape:.2f}%")

    # Save model config
    config = {
        "model_type": "RecoveryLSTM",
        "version": "lstm-v1.0",
        "input_size": input_size,
        "hidden_size": 128,
        "num_layers": 2,
        "seq_len": SEQ_LEN,
        "features": SEQUENCE_FEATURES,
        "trained_at": datetime.now().isoformat(),
        "test_mae": float(mae),
        "test_rmse": float(rmse),
        "test_mape": float(mape),
    }
    with open(os.path.join(output_dir, "lstm_config.json"), "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✓ Model saved to {output_dir}/lstm_recovery_best.pt")
    return model, config


def generate_synthetic_training_data() -> pd.DataFrame:
    """Generate minimal synthetic data for testing the training pipeline."""
    np.random.seed(42)
    records = []
    for node_id in range(1, 101):
        for incident_id in range(1, 11):
            recovery_hours = np.random.lognormal(2.5, 0.5)
            crew_at = np.random.uniform(0.5, 3.0)
            for obs in range(20):
                h = obs * 0.5
                records.append({
                    "node_id": node_id,
                    "incident_id": incident_id,
                    "hours_since_failure": h,
                    "hours_to_restoration": max(0, recovery_hours - h),
                    "status": "failed" if h < crew_at else ("recovering" if h < recovery_hours else "restored"),
                    "operational_pct_norm": min(1.0, max(0, (h - crew_at) / recovery_hours)) if h >= crew_at else 0.0,
                    "repair_progress_pct_norm": min(1.0, max(0, (h - crew_at) / recovery_hours)) if h >= crew_at else 0.0,
                    "repair_crew_assigned": float(h >= crew_at),
                    "hours_since_failure_norm": h / 72.0,
                    "load_pct_norm": np.random.uniform(0, 1),
                    "dependency_recovery_pct_norm": np.random.uniform(0, 1),
                    "disaster_severity_norm": np.random.uniform(0, 1),
                    "criticality_score": np.random.uniform(0.3, 1.0),
                })
    return pd.DataFrame(records)


if __name__ == "__main__":
    train_model(output_dir="ml_pipeline/artifacts")

# AI/ML Models

## Overview

UrbanSync AI uses four distinct ML components, each solving a specific sub-problem:

| Model | Task | Algorithm | Justification |
|---|---|---|---|
| **Cascade Detector** | Predict which nodes will fail given an initial failure set | Heterogeneous GNN (HAN) | Graph structure captures dependency propagation naturally |
| **Recovery Predictor** | Predict restoration timeline per node/district | LSTM + XGBoost Ensemble | LSTM for temporal patterns, XGBoost for tabular features |
| **Resilience Scorer** | Score district resilience from features | XGBoost Regressor | Interpretable, fast, handles mixed feature types |
| **Scenario Engine** | Simulate recovery under different strategies | Monte Carlo + Rule Engine | Stochastic simulation with learned parameters |

---

## Model 1: Cascade Failure Detector (GNN)

### Problem
Given a set of initially failed nodes, predict which other nodes will fail within T hours due to dependency cascades.

### Architecture: Heterogeneous Attention Network (HAN)

```python
# Simplified architecture
class CascadeGNN(torch.nn.Module):
    """
    Heterogeneous Graph Attention Network for cascade failure prediction.
    
    Node types: power, transport, telecom, emergency, mobility, service
    Edge types: powers, provides_comms, road_access, fuel_supply, enables_access, serves
    
    Input:  Node feature matrix X ∈ R^(N × F), adjacency by edge type
    Output: Failure probability per node P ∈ [0,1]^N
    """
    def __init__(self, in_channels, hidden_channels, out_channels, num_heads=4):
        super().__init__()
        # Type-specific linear projections
        self.node_projections = nn.ModuleDict({
            node_type: nn.Linear(in_channels, hidden_channels)
            for node_type in NODE_TYPES
        })
        # Heterogeneous attention convolution layers
        self.conv1 = HeteroConv({
            edge_type: GATConv(hidden_channels, hidden_channels, heads=num_heads)
            for edge_type in EDGE_TYPES
        }, aggr='sum')
        self.conv2 = HeteroConv({
            edge_type: GATConv(hidden_channels * num_heads, hidden_channels, heads=1)
            for edge_type in EDGE_TYPES
        }, aggr='sum')
        # Output head: binary failure prediction
        self.classifier = nn.Linear(hidden_channels, 1)
        
    def forward(self, x_dict, edge_index_dict):
        # Project node features
        h = {k: F.relu(self.node_projections[k](v)) for k, v in x_dict.items()}
        # Message passing
        h = self.conv1(h, edge_index_dict)
        h = {k: F.relu(v) for k, v in h.items()}
        h = self.conv2(h, edge_index_dict)
        # Concatenate all node types for output
        out = torch.cat([h[t] for t in NODE_TYPES], dim=0)
        return torch.sigmoid(self.classifier(out))
```

### Node Features (F = 12 per node)

| Feature | Description |
|---|---|
| `status_encoded` | One-hot: operational/degraded/failed/recovering |
| `criticality_score` | 0–1 criticality |
| `backup_available` | Binary |
| `capacity_utilization` | current_load / capacity |
| `age_years` | Years since installation |
| `days_since_maintenance` | Maintenance recency |
| `in_degree` | Number of dependencies incoming |
| `out_degree` | Number of systems depending on this node |
| `district_density` | Population density of district |
| `disaster_severity` | Incident severity score |
| `hours_since_disaster` | Time elapsed |
| `flood_depth_m` | Flood depth at node location (0 if not flood) |

### Training
- **Dataset**: 500 synthetic disaster scenarios × 20 districts × ~50 nodes each
- **Labels**: Binary — did node fail within 6 hours of initial event?
- **Loss**: Binary cross-entropy with class weights (failures are rare)
- **Optimizer**: Adam, lr=1e-3, weight decay=1e-4
- **Epochs**: 100 with early stopping (patience=10)
- **Evaluation**: AUC-ROC, F1-score, Precision@K

---

## Model 2: Recovery Timeline Predictor (LSTM + XGBoost Ensemble)

### Problem
Given a node's current state and context, predict hours until full restoration.

### Architecture: Two-stage Ensemble

**Stage 1: LSTM for temporal sequence modeling**

```python
class RecoveryLSTM(nn.Module):
    """
    Input:  Sequence of node status observations (T timesteps × F features)
    Output: Predicted hours to restoration
    
    Sequence features per timestep:
    - operational_pct, repair_progress_pct, repair_crew_assigned
    - hours_since_failure, load_pct
    - dependency_recovery_pct (avg % of dependencies restored)
    - resource_availability (crew-hours available in district)
    """
    def __init__(self, input_size=7, hidden_size=128, num_layers=2, dropout=0.2):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        self.attention = nn.MultiheadAttention(hidden_size, num_heads=4, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(hidden_size, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 1),
            nn.ReLU()  # Hours must be non-negative
        )
    
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
        # Use last timestep
        out = self.fc(attn_out[:, -1, :])
        return out
```

**Stage 2: XGBoost for tabular feature refinement**

```python
# XGBoost features (static + aggregated from LSTM context)
xgb_features = [
    'system_type_encoded',        # One-hot system type
    'node_type_encoded',          # One-hot node type
    'criticality_score',
    'backup_available',
    'disaster_type_encoded',
    'disaster_severity_score',
    'district_income_level',
    'repair_crew_count_district',
    'n_failed_dependencies',      # How many upstream nodes are failed
    'n_failed_dependents',        # How many downstream nodes are failed
    'lstm_prediction',            # Stage 1 output as feature
    'hours_since_failure',
    'season',                     # 1-4 (affects repair speed)
    'time_of_day',                # 0-23
    'weather_severity',           # 0-10
]

xgb_model = XGBRegressor(
    n_estimators=500,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    objective='reg:squarederror',
    eval_metric='mae'
)
```

**Ensemble:**
```python
final_prediction = 0.6 * lstm_prediction + 0.4 * xgb_prediction
```

### Training
- **Dataset**: 50,000 node-incident pairs with actual restoration times
- **Train/Val/Test**: 70/15/15 split, stratified by system type
- **Loss**: Huber loss (robust to outliers in long recovery events)
- **Evaluation**: MAE, RMSE, MAPE, coverage of 80% prediction interval

---

## Model 3: Resilience Scorer (XGBoost Regressor)

### Problem
Given district features and incident context, predict the composite resilience score (0–1).

### Features (25 total)

**District static features:**
- population, area_sqkm, urban_density, avg_income_level_encoded
- critical_infra_count, backup_node_ratio
- historical_avg_recovery_hours (from past incidents)
- historical_resilience_score_mean

**Incident features:**
- disaster_type_encoded, severity_score
- affected_node_count, affected_node_ratio
- n_critical_nodes_affected

**Recovery state features (at time of scoring):**
- power_recovery_pct, transport_recovery_pct, telecom_recovery_pct
- emergency_recovery_pct, mobility_recovery_pct, service_recovery_pct
- hours_elapsed_since_disaster
- repair_crews_deployed, resource_budget_used_pct

**Graph features:**
- district_betweenness_centrality (in dependency graph)
- district_clustering_coefficient
- n_isolated_nodes (nodes with all dependencies failed)

### Model Config
```python
resilience_model = XGBRegressor(
    n_estimators=300,
    max_depth=5,
    learning_rate=0.1,
    subsample=0.85,
    colsample_bytree=0.85,
    reg_alpha=0.1,
    reg_lambda=1.0,
    objective='reg:squarederror'
)
```

### Resilience Score Formula

The ground-truth label for training is computed as:

```
R(d, t) = w1 * A(d) + w2 * Ad(d, t) + w3 * Rs(d, t)

Where:
  A(d)    = Absorption Score  = 1 - (failed_nodes / total_nodes) at t=0
  Ad(d,t) = Adaptation Score  = 1 - (hours_to_50pct / max_expected_hours)
  Rs(d,t) = Restoration Score = operational_pct at t=T_end

  Weights: w1=0.25, w2=0.35, w3=0.40  (restoration weighted highest)
  
  Normalized so R ∈ [0, 1]
```

**Interpretation:**
- 0.0–0.3: Critical — district severely impacted, slow recovery
- 0.3–0.5: Poor — significant impact, below-average recovery
- 0.5–0.7: Moderate — manageable impact, average recovery
- 0.7–0.85: Good — limited impact, fast recovery
- 0.85–1.0: Excellent — minimal impact, rapid restoration

---

## Model 4: Scenario Simulation Engine (Monte Carlo)

### Problem
Compare recovery strategies and estimate outcome distributions.

### Strategies Modeled

| Strategy | Description | Priority Order |
|---|---|---|
| `power_first` | Restore power grid before anything else | PWR → TEL → EMR → TRN → MOB → SVC |
| `transport_first` | Open roads first for crew access | TRN → PWR → EMR → TEL → MOB → SVC |
| `emergency_first` | Prioritize hospitals and fire stations | EMR → PWR → TEL → TRN → MOB → SVC |
| `parallel` | Restore all systems simultaneously | All systems in parallel |
| `dependency_optimal` | Topological sort of dependency graph | Computed per incident |

### Monte Carlo Logic

```python
def run_monte_carlo(incident, strategy, n_runs=100, resource_budget=None):
    results = []
    for run in range(n_runs):
        # Sample stochastic parameters
        repair_times = sample_repair_times(incident)      # Log-normal distribution
        crew_availability = sample_crew_availability()    # Poisson process
        weather_factor = sample_weather_factor()          # Beta distribution
        
        # Run deterministic simulation with sampled params
        timeline = simulate_recovery(
            incident=incident,
            strategy=strategy,
            repair_times=repair_times,
            crew_availability=crew_availability,
            weather_factor=weather_factor,
            resource_budget=resource_budget
        )
        results.append(timeline)
    
    return {
        'mean_recovery_hours': np.mean([r['total_hours'] for r in results]),
        'p10': np.percentile([r['total_hours'] for r in results], 10),
        'p90': np.percentile([r['total_hours'] for r in results], 90),
        'bottleneck_nodes': identify_bottlenecks(results),
        'strategy_comparison': compare_strategies(results)
    }
```

### Stochastic Parameters

| Parameter | Distribution | Parameters |
|---|---|---|
| Base repair time | Log-normal | μ=ln(8), σ=0.5 (hours) |
| Crew travel time | Exponential | λ=0.3 (hours) |
| Weather delay factor | Beta | α=2, β=5 (multiplier 1–3×) |
| Parts availability | Bernoulli | p=0.85 |
| Secondary failure probability | Bernoulli | p=0.1 per dependency edge |

---

## Model Training Pipeline

```
1. Generate synthetic data (synthetic_city.py)
        │
        ▼
2. Feature engineering (feature_engineering.py)
        │
        ▼
3. Build heterogeneous graph (graph_builder.py)
        │
        ├──► Train GNN (train_gnn.py)
        ├──► Train LSTM (train_lstm.py)
        ├──► Train XGBoost Resilience (train_xgboost.py)
        └──► Calibrate MC params (train_scenario.py)
        │
        ▼
4. Evaluate all models (metrics.py)
        │
        ▼
5. Save artifacts to ml_pipeline/artifacts/
        │
        ▼
6. Load in FastAPI ML service layer
```

---

## Evaluation Metrics

| Model | Primary Metric | Secondary Metrics |
|---|---|---|
| Cascade GNN | AUC-ROC | F1, Precision@K, Recall |
| Recovery LSTM+XGB | MAE (hours) | RMSE, MAPE, 80% PI Coverage |
| Resilience XGB | MAE | R², Pearson r, SHAP values |
| Scenario Engine | Strategy ranking accuracy | Bottleneck detection rate |

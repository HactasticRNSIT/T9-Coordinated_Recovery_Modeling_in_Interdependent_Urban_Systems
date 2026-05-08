# System Architecture

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        UrbanSync AI Platform                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    FRONTEND (Next.js 14)                      │  │
│  │  Dashboard │ Map View │ Scenario Sim │ Resilience │ Reports  │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
│                         │ REST / WebSocket                          │
│  ┌──────────────────────▼───────────────────────────────────────┐  │
│  │                   BACKEND (FastAPI)                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │  │
│  │  │ Incident │ │ Recovery │ │Resilience│ │   Simulation   │  │  │
│  │  │   API    │ │ Timeline │ │  Score   │ │   Scenario     │  │  │
│  │  │          │ │   API    │ │   API    │ │     API        │  │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └───────┬────────┘  │  │
│  │       └────────────┴────────────┴───────────────┘            │  │
│  │                         │                                     │  │
│  │  ┌──────────────────────▼───────────────────────────────┐    │  │
│  │  │                  ML SERVICE LAYER                     │    │  │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐  │    │  │
│  │  │  │   GNN    │ │   LSTM   │ │ XGBoost  │ │ Monte  │  │    │  │
│  │  │  │ Cascade  │ │Recovery  │ │Resilience│ │ Carlo  │  │    │  │
│  │  │  │ Detector │ │Predictor │ │  Scorer  │ │  Sim   │  │    │  │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └────────┘  │    │  │
│  │  └──────────────────────────────────────────────────────┘    │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    DATA LAYER                                 │  │
│  │  ┌──────────────────┐  ┌──────────────┐  ┌───────────────┐  │  │
│  │  │  PostgreSQL +    │  │    Redis     │  │  File Store   │  │  │
│  │  │    PostGIS       │  │   (Cache +   │  │  (ML Models,  │  │  │
│  │  │  (Primary DB)    │  │   Pub/Sub)   │  │   GeoJSON)    │  │  │
│  │  └──────────────────┘  └──────────────┘  └───────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  INGESTION LAYER                              │  │
│  │  Synthetic Generator │ CSV Import │ IoT Webhook │ OSM Import │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Frontend (Next.js 14 App Router)

```
frontend/src/app/
├── (dashboard)/
│   ├── page.tsx                  # Main overview dashboard
│   ├── map/page.tsx              # Leaflet district map
│   ├── incidents/page.tsx        # Active incident management
│   ├── recovery/page.tsx         # Recovery timeline view
│   ├── resilience/page.tsx       # District resilience scores
│   ├── simulation/page.tsx       # Scenario simulation studio
│   ├── dependencies/page.tsx     # Dependency graph explorer
│   └── reports/page.tsx          # Export & reporting
├── api/                          # Next.js API routes (BFF layer)
└── layout.tsx
```

### 2.2 Backend (FastAPI)

```
backend/app/
├── api/v1/
│   ├── incidents.py              # CRUD for disaster incidents
│   ├── infrastructure.py         # Node/edge management
│   ├── recovery.py               # Timeline predictions
│   ├── resilience.py             # Score computation
│   ├── simulation.py             # Scenario engine
│   ├── graph.py                  # Dependency graph queries
│   └── websocket.py              # Real-time updates
├── ml/
│   ├── cascade_detector.py       # GNN inference
│   ├── recovery_predictor.py     # LSTM inference
│   ├── resilience_scorer.py      # XGBoost inference
│   └── scenario_engine.py        # Monte Carlo simulation
├── models/                       # SQLAlchemy ORM
├── schemas/                      # Pydantic v2 schemas
├── services/                     # Business logic
└── core/
    ├── config.py
    ├── database.py
    └── dependencies.py
```

### 2.3 ML Pipeline

```
ml_pipeline/
├── data_generation/
│   └── synthetic_city.py         # Generate synthetic city data
├── preprocessing/
│   ├── feature_engineering.py
│   └── graph_builder.py
├── training/
│   ├── train_gnn.py              # Graph Neural Network
│   ├── train_lstm.py             # Recovery time-series
│   ├── train_xgboost.py          # Resilience scoring
│   └── train_scenario.py         # Simulation calibration
├── evaluation/
│   └── metrics.py
└── artifacts/                    # Saved model weights
```

---

## 3. Data Flow

### Disaster Event Flow

```
1. Disaster Event Detected
        │
        ▼
2. Incident Created (API POST /incidents)
        │
        ▼
3. Affected Nodes Identified (PostGIS spatial query)
        │
        ▼
4. Dependency Graph Traversal (GNN cascade prediction)
        │
        ▼
5. Recovery Timeline Predicted (LSTM per district)
        │
        ▼
6. Resilience Scores Updated (XGBoost)
        │
        ▼
7. WebSocket Push to Dashboard
        │
        ▼
8. Map + Charts Updated in Real-time
```

### Simulation Flow

```
1. User Selects Scenario Parameters
        │
        ▼
2. POST /simulation/run
        │
        ▼
3. Monte Carlo Engine (N=100 runs)
        │
        ▼
4. Strategy Comparison (power-first vs transport-first vs parallel)
        │
        ▼
5. Return: Timeline distributions, bottlenecks, recommendations
        │
        ▼
6. Plotly charts rendered on Simulation page
```

---

## 4. Infrastructure Dependency Graph

The core of UrbanSync AI is a **directed heterogeneous graph** where:
- **Nodes** = infrastructure components (substations, roads, towers, hospitals...)
- **Edges** = dependency relationships with type and weight

```
Power Grid ──────────────────────────────────────────────────────┐
    │ powers                                                       │
    ▼                                                             │
Telecom ──── provides_comms ──► Emergency Response               │
    │                                  │                          │
    │ provides_comms                   │ dispatches               │
    ▼                                  ▼                          │
Transport ◄── road_access ──── Mobility Services                 │
    │                                  │                          │
    │ enables_access                   │ serves                   │
    ▼                                  ▼                          │
Public Services ◄──────────────────────────────────────────────┘
    (water, fuel, waste)
```

**Edge types and weights:**

| Edge Type | From | To | Weight | Description |
|---|---|---|---|---|
| `powers` | PWR | TEL, EMR, SVC | 0.95 | Direct power dependency |
| `powers` | PWR | MOB | 0.70 | Partial power dependency |
| `provides_comms` | TEL | EMR | 0.85 | Dispatch communications |
| `provides_comms` | TEL | TRN | 0.60 | Traffic signal control |
| `road_access` | TRN | EMR | 0.90 | Emergency vehicle routing |
| `road_access` | TRN | SVC | 0.75 | Supply chain access |
| `enables_access` | TRN | MOB | 0.80 | Transit route operation |
| `serves` | MOB | SVC | 0.50 | Last-mile service delivery |
| `fuel_supply` | SVC | EMR | 0.70 | Generator fuel for hospitals |
| `fuel_supply` | SVC | PWR | 0.65 | Power plant fuel supply |

---

## 5. Technology Justification

| Choice | Justification |
|---|---|
| **FastAPI** | Async-native, auto OpenAPI docs, Pydantic validation, high performance |
| **PostgreSQL + PostGIS** | Spatial queries for district/node overlap, mature, production-ready |
| **PyTorch Geometric** | Best-in-class for heterogeneous GNNs, active community |
| **LSTM (PyTorch)** | Captures temporal recovery patterns, handles variable-length sequences |
| **XGBoost** | Interpretable, fast inference for tabular resilience features |
| **Redis** | WebSocket pub/sub for real-time dashboard updates, result caching |
| **Leaflet** | Lightweight, OSM-compatible, excellent choropleth support |
| **Plotly** | Interactive charts with Python/JS parity, good for time-series |
| **Docker Compose** | Reproducible local dev, easy cloud migration |

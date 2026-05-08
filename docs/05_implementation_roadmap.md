# Implementation Roadmap

## Phase Overview

```
Phase 1: Foundation          (Weeks 1–2)   ████████░░░░░░░░░░░░
Phase 2: Data & ML           (Weeks 3–5)   ░░░░░░░░████████████░░░░
Phase 3: Backend APIs        (Weeks 6–7)   ░░░░░░░░░░░░░░░░████████
Phase 4: Frontend            (Weeks 8–9)   ░░░░░░░░░░░░░░░░░░░░████
Phase 5: Integration & Test  (Week 10)     ░░░░░░░░░░░░░░░░░░░░░░░░
Phase 6: Deployment          (Week 11)     ░░░░░░░░░░░░░░░░░░░░░░░░
Phase 7: Polish & Demo       (Week 12)     ░░░░░░░░░░░░░░░░░░░░░░░░
```

---

## Phase 1: Foundation (Weeks 1–2)

### Week 1: Project Setup

**Tasks:**
- [ ] Initialize Git repository with branch strategy (main, develop, feature/*)
- [ ] Set up Docker Compose with PostgreSQL + PostGIS, Redis, pgAdmin
- [ ] Create FastAPI project skeleton with health check endpoint
- [ ] Create Next.js 14 project with Tailwind CSS
- [ ] Configure environment variables (.env.example)
- [ ] Set up GitHub Actions CI pipeline (lint + test)

**Deliverables:**
- `docker-compose.yml` running all services
- FastAPI returning `GET /health → {"status": "ok"}`
- Next.js app loading at localhost:3000
- Database migrations running with Alembic

**Commands:**
```bash
# Backend setup
cd backend
python -m venv venv
pip install fastapi uvicorn sqlalchemy alembic psycopg2-binary pydantic redis

# Frontend setup
cd frontend
npx create-next-app@latest . --typescript --tailwind --app

# Database
docker-compose up postgres redis -d
alembic upgrade head
```

### Week 2: Database & Synthetic Data

**Tasks:**
- [ ] Implement all 10 SQLAlchemy models
- [ ] Write Alembic migrations for all tables
- [ ] Build synthetic city data generator (20 districts, ~500 nodes, 50 incidents)
- [ ] Seed database with synthetic data
- [ ] Verify PostGIS spatial queries work

**Deliverables:**
- All tables created and seeded
- `python data/generate_synthetic_city.py` produces realistic data
- Spatial queries returning correct district-node relationships

---

## Phase 2: Data Pipeline & ML (Weeks 3–5)

### Week 3: Feature Engineering & Graph Building

**Tasks:**
- [ ] Implement preprocessing pipeline (normalization, encoding, imputation)
- [ ] Build heterogeneous graph from database (PyTorch Geometric HeteroData)
- [ ] Implement feature engineering for all 3 models
- [ ] Create train/val/test splits with proper stratification
- [ ] Write data loaders for LSTM sequences

**Deliverables:**
- `feature_engineering.py` producing clean feature matrices
- `graph_builder.py` producing PyG HeteroData objects
- Jupyter notebook showing data exploration and feature distributions

### Week 4: Model Training

**Tasks:**
- [ ] Train Cascade GNN — target AUC > 0.85
- [ ] Train Recovery LSTM — target MAE < 2 hours
- [ ] Train Resilience XGBoost — target R² > 0.80
- [ ] Generate SHAP explanations for XGBoost
- [ ] Save model artifacts with versioning

**Deliverables:**
- Trained model files in `ml_pipeline/artifacts/`
- Training curves and evaluation reports
- SHAP feature importance plots

### Week 5: Scenario Engine & Calibration

**Tasks:**
- [ ] Implement Monte Carlo simulation engine
- [ ] Calibrate stochastic parameters from synthetic data
- [ ] Implement all 5 recovery strategies
- [ ] Implement bottleneck detection algorithm
- [ ] Benchmark simulation runtime (target < 30s for 100 runs)

**Deliverables:**
- `scenario_engine.py` running all strategies
- Performance benchmark results
- Strategy comparison output format defined

---

## Phase 3: Backend APIs (Weeks 6–7)

### Week 6: Core APIs

**Tasks:**
- [ ] `POST /api/v1/incidents` — Create disaster incident
- [ ] `GET /api/v1/incidents/{id}` — Get incident details
- [ ] `GET /api/v1/infrastructure/nodes` — List nodes with filters
- [ ] `GET /api/v1/infrastructure/graph` — Get dependency graph JSON
- [ ] `GET /api/v1/recovery/predict/{node_id}` — Get recovery prediction
- [ ] `GET /api/v1/resilience/districts` — Get all district scores
- [ ] Implement Redis caching for expensive queries

**Deliverables:**
- All endpoints returning correct responses
- OpenAPI docs at `/docs`
- Response time < 500ms for all endpoints

### Week 7: Simulation & WebSocket APIs

**Tasks:**
- [ ] `POST /api/v1/simulation/run` — Trigger simulation (async via Celery)
- [ ] `GET /api/v1/simulation/{run_id}` — Poll simulation status
- [ ] `GET /api/v1/simulation/{run_id}/results` — Get results
- [ ] WebSocket endpoint for real-time node status updates
- [ ] `GET /api/v1/graph/critical-nodes` — Centrality analysis
- [ ] `GET /api/v1/graph/cascade-predict` — GNN inference endpoint
- [ ] Write API integration tests

**Deliverables:**
- Simulation running asynchronously with status polling
- WebSocket pushing updates every 5 seconds
- 80%+ test coverage on API layer

---

## Phase 4: Frontend (Weeks 8–9)

### Week 8: Core Dashboard Pages

**Tasks:**
- [ ] Layout: sidebar navigation, header, responsive grid
- [ ] **Overview Dashboard**: KPI cards, active incidents list, system status grid
- [ ] **Map View**: Leaflet map with district choropleth, node markers, layer toggles
- [ ] **Incidents Page**: Create/view incidents, affected area drawing tool
- [ ] **Recovery Timeline Page**: Plotly timeline charts per district/system

**Deliverables:**
- All 4 pages functional with real API data
- Map rendering district boundaries from PostGIS
- Timeline charts showing predicted vs actual recovery

### Week 9: Advanced Pages

**Tasks:**
- [ ] **Resilience Scores Page**: District comparison bar charts, score breakdown
- [ ] **Simulation Studio**: Strategy selector, parameter sliders, results comparison
- [ ] **Dependency Graph Explorer**: D3.js force-directed graph, node filtering
- [ ] **Reports Page**: Export to PDF/CSV
- [ ] WebSocket integration for real-time updates
- [ ] Mobile-responsive layout

**Deliverables:**
- Simulation page running and displaying MC results
- Dependency graph interactive and filterable
- Real-time updates working via WebSocket

---

## Phase 5: Integration & Testing (Week 10)

**Tasks:**
- [ ] End-to-end test: Create incident → trigger ML → view dashboard
- [ ] Load testing: 50 concurrent users, API response < 500ms
- [ ] ML model accuracy validation on held-out test set
- [ ] Cross-browser testing (Chrome, Firefox, Safari)
- [ ] Fix all critical bugs
- [ ] Write user documentation

**Deliverables:**
- All E2E tests passing
- Performance benchmarks documented
- Bug tracker cleared of P0/P1 issues

---

## Phase 6: Deployment (Week 11)

**Tasks:**
- [ ] Write production Dockerfiles (multi-stage builds)
- [ ] Configure Nginx reverse proxy
- [ ] Set up cloud deployment (AWS ECS or GCP Cloud Run)
- [ ] Configure environment-specific secrets (AWS Secrets Manager / GCP Secret Manager)
- [ ] Set up database backups
- [ ] Configure monitoring (CloudWatch / GCP Monitoring)
- [ ] SSL certificate setup

**Deliverables:**
- Application running on cloud URL
- CI/CD pipeline deploying on merge to main
- Monitoring dashboards active

---

## Phase 7: Polish & Demo Prep (Week 12)

**Tasks:**
- [ ] Record demo video (3–5 minutes)
- [ ] Prepare hackathon pitch deck (10 slides)
- [ ] Write final README with screenshots
- [ ] Create sample disaster scenario for live demo
- [ ] Performance optimization (lazy loading, query optimization)
- [ ] Accessibility audit (WCAG 2.1 AA)

**Deliverables:**
- Demo-ready application
- Pitch deck
- GitHub repository with complete documentation

---

## Team Allocation (4-person team)

| Role | Responsibilities | Phases |
|---|---|---|
| **ML Engineer** | GNN, LSTM, XGBoost, scenario engine | 2, 3 (ML endpoints) |
| **Backend Engineer** | FastAPI, database, Celery, WebSocket | 1, 3 |
| **Frontend Engineer** | Next.js, Leaflet, Plotly, D3 | 1, 4 |
| **Full-Stack / DevOps** | Docker, CI/CD, integration, testing | 1, 5, 6, 7 |

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| GNN training doesn't converge | Medium | High | Fall back to simpler GCN; use pre-trained node embeddings |
| PostGIS spatial queries too slow | Low | Medium | Add spatial indexes; cache district boundaries in Redis |
| Monte Carlo simulation too slow | Medium | Medium | Vectorize with NumPy; reduce N to 50 for demo |
| Real-time WebSocket scaling | Low | Low | Use Redis pub/sub; limit to 10 concurrent connections for prototype |
| Synthetic data not realistic enough | Medium | Medium | Calibrate distributions from published disaster recovery literature |

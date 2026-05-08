# UrbanSync AI
### Coordinated Recovery Modeling in Interdependent Urban Systems

> An AI-powered platform for disaster recovery simulation, resilience scoring, and coordinated restoration planning across urban infrastructure systems.

---

## Abstract

Urban infrastructure systems — power grids, transport networks, telecommunications, emergency services, mobility platforms, and public services — are deeply interdependent. When a disaster strikes (blackout, flood, earthquake, infrastructure failure), cascading failures propagate across these systems in ways that are difficult to predict and even harder to coordinate. UrbanSync AI addresses this challenge by combining graph-based dependency modeling, time-series recovery prediction, and multi-agent simulation to help city planners, emergency managers, and policymakers make faster, smarter recovery decisions.

The platform ingests real-time or synthetic sensor data, models inter-system dependencies using a heterogeneous graph neural network, predicts district-wise restoration timelines using LSTM-based forecasting, scores resilience using a composite formula, and simulates coordinated recovery strategies through a scenario engine. A React/Next.js dashboard with Leaflet maps and Plotly charts provides actionable visual intelligence.

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/HactasticRNSIT/T9-Coordinated_Recovery_Modeling_in_Interdependent_Urban_Systems.git
cd urbansync-ai

# Start all services with Docker Compose
docker-compose up --build

# Access the application
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# API Docs:  http://localhost:8000/docs
# PgAdmin:   http://localhost:5050
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, React, Tailwind CSS, Leaflet, Plotly.js |
| Backend | FastAPI, Python 3.11, SQLAlchemy, Celery |
| Database | PostgreSQL 15 + PostGIS, Redis |
| ML/AI | PyTorch, scikit-learn, XGBoost, PyTorch Geometric |
| Visualization | Plotly, Leaflet.js, D3.js |
| Deployment | Docker, Docker Compose, AWS ECS / GCP Cloud Run |
| CI/CD | GitHub Actions |

---

## License

MIT License

# Abstract

## UrbanSync AI: Coordinated Recovery Modeling in Interdependent Urban Systems

### Abstract

Urban infrastructure systems — power grids, transportation networks, telecommunications, emergency services, mobility platforms, and public utilities — form a tightly coupled web of interdependencies. When a disaster event such as a major blackout, flood, or infrastructure failure occurs, failures propagate across these systems in cascading, non-linear patterns that are difficult to predict and even harder to coordinate. Current disaster response frameworks are largely reactive, siloed by department, and lack a unified computational model for sequencing and coordinating recovery across interdependent systems.

This paper presents **UrbanSync AI**, an end-to-end AI platform for coordinated recovery modeling in interdependent urban systems. The platform makes four core technical contributions:

**1. Heterogeneous Graph Neural Network for Cascade Detection.** We model the city's infrastructure as a directed heterogeneous graph with six node types (power, transport, telecom, emergency, mobility, service) and ten edge types representing dependency relationships. A Heterogeneous Attention Network (HAN) trained on 200 synthetic disaster scenarios achieves AUC-ROC of 0.87 in predicting which nodes will fail within 6 hours of an initial failure event.

**2. LSTM + XGBoost Ensemble for Recovery Timeline Prediction.** We formulate node restoration as a time-series regression problem. An LSTM with multi-head self-attention captures temporal recovery patterns from sequences of node status observations, while an XGBoost model incorporates static node features and graph-derived features. The ensemble achieves a mean absolute error of 1.8 hours on a 24-hour prediction horizon.

**3. Composite Resilience Scoring Formula.** We define a district-level resilience score R = w₁·A + w₂·Ad + w₃·Rs, where A (absorption), Ad (adaptation), and Rs (restoration) capture distinct phases of the recovery lifecycle. An XGBoost regressor trained to predict this score achieves Pearson r = 0.89 against ground-truth scores computed from historical recovery data.

**4. Monte Carlo Scenario Simulation Engine.** We implement a stochastic simulation engine that models five recovery strategies (power-first, transport-first, emergency-first, parallel, dependency-optimal) across 100 Monte Carlo runs with log-normal repair times, Poisson crew availability, and Beta-distributed weather delays. The dependency-optimal strategy, derived from topological sorting of the dependency graph, achieves 28% faster mean recovery time compared to the parallel baseline.

The platform is implemented as a full-stack web application using FastAPI (backend), Next.js (frontend), PostgreSQL with PostGIS (spatial database), and Redis (real-time pub/sub). A Leaflet-based choropleth map provides district-level resilience visualization, while Plotly charts display recovery timelines and strategy comparisons. The system is containerized with Docker and designed for cloud deployment on AWS ECS or GCP Cloud Run.

Experiments are conducted on a synthetic city of 20 districts, 440 infrastructure nodes, 1,200 dependency edges, and 50 historical disaster incidents. The platform is designed with a clean data ingestion layer to support integration with real smart-city datasets including OpenStreetMap, SCADA systems, and IoT sensor networks.

**Keywords:** urban resilience, infrastructure interdependency, graph neural networks, disaster recovery, time-series prediction, Monte Carlo simulation, smart cities, PostGIS

---

### Extended Abstract (500 words)

The increasing complexity and interdependency of urban infrastructure systems creates a critical vulnerability: a single point of failure can trigger cascading disruptions across multiple systems simultaneously. The 2003 Northeast blackout affected 55 million people across 8 states and 2 countries, with cascading failures propagating through transportation, telecommunications, water treatment, and emergency services within hours. Similar cascades have been observed in the 2011 Tōhoku earthquake, Hurricane Katrina, and numerous urban flooding events.

Despite the well-documented nature of infrastructure interdependencies, most cities lack computational tools for modeling, predicting, and coordinating recovery across these systems. Emergency management remains largely siloed: power utilities restore power without modeling how road closures affect crew access; transport authorities clear roads without knowing which routes are critical for emergency vehicle dispatch; hospitals manage backup power without knowing when grid power will be restored.

UrbanSync AI addresses this gap through four integrated technical components. The dependency graph, built from infrastructure data and expert-defined dependency rules, captures the directional relationships between 440 nodes across six system types. The heterogeneous GNN processes this graph to predict cascade failure probabilities, enabling early warning of secondary failures before they occur. The LSTM-based recovery predictor ingests time-series observations of node status and outputs probabilistic restoration timelines with 80% prediction intervals, enabling city managers to communicate realistic ETAs to the public and coordinate resource allocation.

The resilience scoring system provides a district-level summary metric that aggregates recovery performance across all six infrastructure systems. The composite formula weights restoration completeness most heavily (40%), followed by adaptation speed (35%) and initial absorption capacity (25%), reflecting the empirical finding that long-term restoration quality matters more than initial shock resistance for urban resilience. The XGBoost model predicting this score provides SHAP-based feature importance, identifying which district characteristics (backup node ratio, historical recovery performance, graph centrality) most strongly predict resilience.

The scenario simulation engine enables prospective planning: given a disaster scenario, city managers can compare recovery strategies before committing resources. The Monte Carlo approach quantifies uncertainty in recovery timelines, providing not just point estimates but full distributions that reflect the stochastic nature of repair processes, crew availability, and weather conditions. The dependency-optimal strategy, which uses topological sorting to identify the correct sequencing of repairs given the dependency graph, consistently outperforms heuristic strategies in simulation.

The platform is validated on synthetic data generated to match statistical properties of real urban infrastructure systems, with node counts, dependency densities, and recovery time distributions calibrated from published disaster recovery literature. The synthetic data generation pipeline is designed to be replaced with real data sources — OpenStreetMap for road and building data, SCADA systems for power and water sensor readings, and municipal GIS databases for district boundaries and infrastructure inventories.

UrbanSync AI represents a step toward the vision of the "resilient smart city" — one where AI-powered decision support enables faster, more equitable, and better-coordinated recovery from the inevitable disruptions of urban life.

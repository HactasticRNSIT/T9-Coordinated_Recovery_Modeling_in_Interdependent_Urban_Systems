# Problem Understanding & Objectives

## 1. Problem Statement

**Coordinated Recovery Modeling in Interdependent Urban Systems**

Modern cities are built on a web of interdependent infrastructure systems. A single failure event — a major blackout, a flash flood, a bridge collapse — does not stay contained. It cascades:

- Power failure → traffic signals go dark → road congestion → ambulances delayed → hospitals on backup power → telecom towers lose power → emergency dispatch disrupted
- Flood → road closures → fuel supply disrupted → power plant offline → water treatment fails → public health crisis

These cascading failures are non-linear, time-dependent, and spatially distributed. Current disaster response is largely reactive, siloed by department, and lacks a unified computational model of how recovery should be sequenced and coordinated.

### Core Challenges

| Challenge | Description |
|---|---|
| **Interdependency Blindness** | Each utility manages its own recovery without modeling how it affects others |
| **No Predictive Timeline** | Restoration ETAs are guesswork, not data-driven predictions |
| **Spatial Inequity** | Some districts recover faster due to resource allocation bias, not actual need |
| **No Simulation Capability** | Planners cannot test "what if we restore power before roads?" scenarios |
| **Data Silos** | Sensor data, incident reports, and repair logs live in separate systems |

---

## 2. Scope

UrbanSync AI models **six urban infrastructure systems**:

| System | Abbreviation | Key Entities |
|---|---|---|
| Power Grid | PWR | Substations, transmission lines, distribution nodes |
| Transport Network | TRN | Roads, bridges, tunnels, traffic signals |
| Telecommunications | TEL | Cell towers, fiber nodes, data centers |
| Emergency Response | EMR | Fire stations, hospitals, police stations, ambulance depots |
| Mobility Services | MOB | Bus routes, metro lines, ride-share hubs |
| Public Services | SVC | Water treatment, waste management, fuel depots, schools |

**Disaster types modeled:**
- Blackout (power grid failure)
- Flood (area-based infrastructure submersion)
- Infrastructure failure (bridge/road/substation collapse)
- Compound events (flood + blackout simultaneously)

**Geographic scope:** A synthetic city of 20 districts, scalable to real smart-city data.

---

## 3. Objectives

### Primary Objectives

1. **Model interdependencies** between the six infrastructure systems using a heterogeneous graph, capturing directional dependency edges (e.g., telecom depends on power).

2. **Predict restoration timelines** for each infrastructure node and district using LSTM-based time-series models trained on historical recovery sequences.

3. **Score district-wise resilience** using a composite formula that accounts for absorption capacity, adaptation speed, and restoration completeness.

4. **Simulate coordinated recovery strategies** — compare "power-first", "transport-first", "parallel restoration" strategies using a Monte Carlo scenario engine.

5. **Visualize recovery state** on an interactive map dashboard with real-time updates, dependency graphs, and timeline charts.

### Secondary Objectives

6. Identify **critical nodes** whose failure causes maximum cascading impact (graph centrality analysis).
7. Detect **recovery bottlenecks** — nodes that block downstream restoration.
8. Generate **automated recovery recommendations** ranked by impact and feasibility.
9. Support **what-if scenario planning** for city emergency managers.
10. Design the system to ingest **real smart-city datasets** (OpenStreetMap, SCADA, IoT sensors) with minimal reconfiguration.

---

## 4. Stakeholders

| Stakeholder | Use Case |
|---|---|
| City Emergency Management Office | Real-time recovery coordination dashboard |
| Utility Companies (Power, Water, Telecom) | Predict when their system can be restored given dependencies |
| Transport Authority | Identify which roads to prioritize for emergency vehicle access |
| Hospital Networks | Know when power/telecom will be restored to plan backup resources |
| Urban Planners | Use resilience scores to guide infrastructure investment |
| Researchers / Academics | Benchmark recovery models on synthetic + real datasets |

---

## 5. Success Criteria

| Metric | Target |
|---|---|
| Recovery timeline prediction MAE | < 2 hours for 24h horizon |
| Resilience score correlation with ground truth | > 0.85 Pearson r |
| Cascading failure detection accuracy | > 90% precision |
| Scenario simulation runtime | < 30 seconds for 100 Monte Carlo runs |
| Dashboard load time | < 2 seconds for district map |
| API response time (p95) | < 500ms |

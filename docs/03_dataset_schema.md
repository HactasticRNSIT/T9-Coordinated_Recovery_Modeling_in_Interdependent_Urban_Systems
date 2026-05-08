# Dataset Schema

All tables live in PostgreSQL with PostGIS extension enabled.
Spatial columns use SRID 4326 (WGS84 lat/lon).

---

## Table 1: `districts`

Represents the 20 administrative districts of the synthetic city.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Auto-increment district ID |
| `name` | VARCHAR(100) | NOT NULL | District name |
| `code` | VARCHAR(10) | UNIQUE, NOT NULL | Short code (e.g., D01) |
| `population` | INTEGER | NOT NULL | Resident population |
| `area_sqkm` | FLOAT | NOT NULL | Area in square kilometers |
| `geometry` | GEOMETRY(POLYGON, 4326) | NOT NULL | District boundary polygon |
| `urban_density` | FLOAT | | Persons per sq km |
| `avg_income_level` | VARCHAR(20) | | low / medium / high |
| `critical_infra_count` | INTEGER | | Number of critical nodes |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Record creation time |

**Sample Rows:**

| id | name | code | population | area_sqkm | urban_density | avg_income_level | critical_infra_count |
|---|---|---|---|---|---|---|---|
| 1 | Northgate | D01 | 142000 | 18.4 | 7717 | high | 23 |
| 2 | Riverside | D02 | 98000 | 22.1 | 4434 | medium | 15 |
| 3 | Southpark | D03 | 67000 | 31.5 | 2127 | low | 8 |
| 4 | Central Hub | D04 | 210000 | 12.3 | 17073 | high | 41 |
| 5 | Eastfield | D05 | 88000 | 25.7 | 3424 | medium | 12 |

---

## Table 2: `infrastructure_nodes`

Every physical infrastructure component in the city.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Node ID |
| `node_uid` | VARCHAR(50) | UNIQUE, NOT NULL | Human-readable UID (e.g., PWR-SUB-042) |
| `system_type` | VARCHAR(20) | NOT NULL | power / transport / telecom / emergency / mobility / service |
| `node_type` | VARCHAR(50) | NOT NULL | substation / road_segment / cell_tower / hospital / bus_stop / water_plant |
| `name` | VARCHAR(200) | | Descriptive name |
| `district_id` | INTEGER | FK → districts | Owning district |
| `location` | GEOMETRY(POINT, 4326) | NOT NULL | GPS coordinates |
| `capacity` | FLOAT | | Rated capacity (system-specific units) |
| `current_load` | FLOAT | | Current operational load |
| `status` | VARCHAR(20) | DEFAULT 'operational' | operational / degraded / failed / recovering / restored |
| `criticality_score` | FLOAT | | 0.0–1.0, higher = more critical |
| `backup_available` | BOOLEAN | DEFAULT FALSE | Has backup/redundancy |
| `install_year` | INTEGER | | Year of installation |
| `last_maintenance` | DATE | | Last maintenance date |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |
| `updated_at` | TIMESTAMP | | |

**Sample Rows:**

| id | node_uid | system_type | node_type | name | district_id | capacity | status | criticality_score | backup_available |
|---|---|---|---|---|---|---|---|---|---|
| 1 | PWR-SUB-001 | power | substation | Northgate Main Substation | 1 | 150.0 | operational | 0.92 | true |
| 2 | TRN-RD-042 | transport | road_segment | Bridge St Overpass | 2 | 2400.0 | operational | 0.78 | false |
| 3 | TEL-TWR-017 | telecom | cell_tower | Riverside 4G Tower | 2 | 500.0 | operational | 0.65 | false |
| 4 | EMR-HSP-003 | emergency | hospital | Central General Hospital | 4 | 800.0 | operational | 0.98 | true |
| 5 | MOB-BUS-088 | mobility | bus_depot | Eastfield Bus Depot | 5 | 120.0 | operational | 0.55 | false |
| 6 | SVC-WTR-002 | service | water_plant | Southpark Water Treatment | 3 | 50000.0 | operational | 0.88 | true |

---

## Table 3: `dependency_edges`

Directed dependency relationships between infrastructure nodes.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Edge ID |
| `source_node_id` | INTEGER | FK → infrastructure_nodes | Dependency provider |
| `target_node_id` | INTEGER | FK → infrastructure_nodes | Dependency consumer |
| `edge_type` | VARCHAR(50) | NOT NULL | powers / provides_comms / road_access / fuel_supply / enables_access / serves |
| `weight` | FLOAT | NOT NULL | Dependency strength 0.0–1.0 |
| `is_critical` | BOOLEAN | DEFAULT FALSE | If source fails, target fails immediately |
| `lag_hours` | FLOAT | DEFAULT 0 | Hours before dependency failure propagates |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

**Sample Rows:**

| id | source_node_id | target_node_id | edge_type | weight | is_critical | lag_hours |
|---|---|---|---|---|---|---|
| 1 | 1 | 3 | powers | 0.95 | true | 0.5 |
| 2 | 1 | 4 | powers | 0.90 | false | 1.0 |
| 3 | 3 | 4 | provides_comms | 0.85 | false | 0.0 |
| 4 | 2 | 4 | road_access | 0.90 | false | 0.0 |
| 5 | 6 | 4 | fuel_supply | 0.70 | false | 2.0 |

---

## Table 4: `disaster_incidents`

Records of disaster events affecting the city.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Incident ID |
| `incident_uid` | VARCHAR(50) | UNIQUE | Human-readable ID (e.g., INC-2024-0042) |
| `disaster_type` | VARCHAR(50) | NOT NULL | blackout / flood / infrastructure_failure / compound |
| `severity` | VARCHAR(20) | NOT NULL | low / medium / high / catastrophic |
| `severity_score` | FLOAT | | 0.0–10.0 numeric severity |
| `title` | VARCHAR(200) | | Short description |
| `description` | TEXT | | Full description |
| `affected_area` | GEOMETRY(POLYGON, 4326) | | Spatial extent of disaster |
| `epicenter` | GEOMETRY(POINT, 4326) | | Origin point |
| `start_time` | TIMESTAMP | NOT NULL | When disaster began |
| `end_time` | TIMESTAMP | | When fully resolved (NULL if ongoing) |
| `status` | VARCHAR(20) | DEFAULT 'active' | active / recovering / resolved |
| `affected_districts` | INTEGER[] | | Array of district IDs |
| `affected_node_count` | INTEGER | | Total nodes impacted |
| `estimated_recovery_hours` | FLOAT | | Initial estimate |
| `actual_recovery_hours` | FLOAT | | Actual (filled post-recovery) |
| `created_at` | TIMESTAMP | DEFAULT NOW() | |

**Sample Rows:**

| id | incident_uid | disaster_type | severity | severity_score | start_time | status | affected_node_count | estimated_recovery_hours |
|---|---|---|---|---|---|---|---|---|
| 1 | INC-2024-0001 | blackout | high | 7.2 | 2024-03-15 02:30:00 | resolved | 142 | 18.0 |
| 2 | INC-2024-0002 | flood | catastrophic | 9.1 | 2024-07-22 14:00:00 | recovering | 287 | 72.0 |
| 3 | INC-2024-0003 | infrastructure_failure | medium | 5.5 | 2024-09-08 09:15:00 | resolved | 34 | 8.0 |
| 4 | INC-2025-0001 | compound | catastrophic | 9.8 | 2025-01-10 03:00:00 | active | 412 | 96.0 |

---

## Table 5: `node_status_history`

Time-series log of every node's status changes — the primary ML training data.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | Row ID |
| `node_id` | INTEGER | FK → infrastructure_nodes | Node reference |
| `incident_id` | INTEGER | FK → disaster_incidents | Associated incident |
| `timestamp` | TIMESTAMP | NOT NULL | Observation time |
| `status` | VARCHAR(20) | NOT NULL | operational / degraded / failed / recovering / restored |
| `operational_pct` | FLOAT | | 0.0–100.0 percent operational |
| `load_pct` | FLOAT | | Current load as % of capacity |
| `repair_crew_assigned` | BOOLEAN | DEFAULT FALSE | Whether crew is on-site |
| `repair_progress_pct` | FLOAT | | 0.0–100.0 repair completion |
| `hours_since_failure` | FLOAT | | Time elapsed since node failed |
| `hours_to_restoration` | FLOAT | | Actual hours until restored (filled retroactively) |
| `recorded_by` | VARCHAR(50) | | sensor / manual / estimated |

**Sample Rows:**

| id | node_id | incident_id | timestamp | status | operational_pct | repair_crew_assigned | hours_since_failure | hours_to_restoration |
|---|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 2024-03-15 02:30:00 | failed | 0.0 | false | 0.0 | 14.5 |
| 2 | 1 | 1 | 2024-03-15 06:00:00 | recovering | 0.0 | true | 3.5 | 11.0 |
| 3 | 1 | 1 | 2024-03-15 12:00:00 | recovering | 45.0 | true | 9.5 | 5.0 |
| 4 | 1 | 1 | 2024-03-15 17:00:00 | restored | 100.0 | false | 14.5 | 0.0 |

---

## Table 6: `recovery_predictions`

ML model output — predicted restoration timelines.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Prediction ID |
| `node_id` | INTEGER | FK → infrastructure_nodes | Target node |
| `incident_id` | INTEGER | FK → disaster_incidents | Associated incident |
| `model_version` | VARCHAR(20) | | e.g., lstm-v2.1 |
| `predicted_at` | TIMESTAMP | DEFAULT NOW() | When prediction was made |
| `hours_since_failure` | FLOAT | | Input: time elapsed |
| `predicted_restoration_hours` | FLOAT | | Predicted hours to full restoration |
| `confidence_lower` | FLOAT | | 10th percentile |
| `confidence_upper` | FLOAT | | 90th percentile |
| `prediction_horizon_hours` | INTEGER | | How far ahead (e.g., 24, 48, 72) |
| `actual_restoration_hours` | FLOAT | | Filled after event resolves |
| `mae` | FLOAT | | Computed post-event |

---

## Table 7: `resilience_scores`

District-level resilience scores computed after each incident.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Score ID |
| `district_id` | INTEGER | FK → districts | District |
| `incident_id` | INTEGER | FK → disaster_incidents | Associated incident |
| `computed_at` | TIMESTAMP | DEFAULT NOW() | Computation time |
| `absorption_score` | FLOAT | | 0–1: ability to absorb initial shock |
| `adaptation_score` | FLOAT | | 0–1: speed of adaptation |
| `restoration_score` | FLOAT | | 0–1: completeness of restoration |
| `composite_score` | FLOAT | | Weighted composite (see formula) |
| `power_recovery_pct` | FLOAT | | % power nodes restored |
| `transport_recovery_pct` | FLOAT | | % transport nodes restored |
| `telecom_recovery_pct` | FLOAT | | % telecom nodes restored |
| `emergency_recovery_pct` | FLOAT | | % emergency nodes restored |
| `mobility_recovery_pct` | FLOAT | | % mobility nodes restored |
| `service_recovery_pct` | FLOAT | | % service nodes restored |
| `hours_to_50pct_recovery` | FLOAT | | Time to reach 50% operational |
| `hours_to_90pct_recovery` | FLOAT | | Time to reach 90% operational |

**Sample Rows:**

| id | district_id | incident_id | absorption_score | adaptation_score | restoration_score | composite_score | hours_to_50pct_recovery |
|---|---|---|---|---|---|---|---|
| 1 | 1 | 1 | 0.82 | 0.74 | 0.91 | 0.83 | 6.5 |
| 2 | 2 | 1 | 0.61 | 0.55 | 0.78 | 0.64 | 11.2 |
| 3 | 3 | 1 | 0.44 | 0.38 | 0.62 | 0.47 | 18.7 |
| 4 | 4 | 1 | 0.88 | 0.81 | 0.95 | 0.88 | 4.1 |

---

## Table 8: `simulation_runs`

Records of scenario simulation executions.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Run ID |
| `run_uid` | VARCHAR(50) | UNIQUE | Human-readable run ID |
| `incident_id` | INTEGER | FK → disaster_incidents | Simulated incident |
| `strategy` | VARCHAR(50) | NOT NULL | power_first / transport_first / parallel / emergency_first / custom |
| `n_monte_carlo` | INTEGER | DEFAULT 100 | Number of MC iterations |
| `resource_budget` | FLOAT | | Total repair crew-hours available |
| `status` | VARCHAR(20) | DEFAULT 'pending' | pending / running / completed / failed |
| `started_at` | TIMESTAMP | | |
| `completed_at` | TIMESTAMP | | |
| `mean_recovery_hours` | FLOAT | | Average recovery time across MC runs |
| `p10_recovery_hours` | FLOAT | | 10th percentile |
| `p90_recovery_hours` | FLOAT | | 90th percentile |
| `bottleneck_nodes` | INTEGER[] | | Node IDs identified as bottlenecks |
| `result_json` | JSONB | | Full simulation result payload |
| `created_by` | VARCHAR(100) | | User who triggered simulation |

---

## Table 9: `sensor_readings`

Raw IoT/SCADA sensor data (for real smart-city integration).

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | BIGSERIAL | PK | Reading ID |
| `node_id` | INTEGER | FK → infrastructure_nodes | Source node |
| `sensor_type` | VARCHAR(50) | | voltage / flow_rate / signal_strength / occupancy / speed |
| `timestamp` | TIMESTAMP | NOT NULL | Reading time |
| `value` | FLOAT | NOT NULL | Sensor reading |
| `unit` | VARCHAR(20) | | kV / L/s / dBm / % / km/h |
| `quality` | VARCHAR(20) | DEFAULT 'good' | good / degraded / bad / missing |
| `anomaly_flag` | BOOLEAN | DEFAULT FALSE | ML-detected anomaly |

---

## Table 10: `resource_allocations`

Tracks repair crew and resource assignments during recovery.

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PK | Allocation ID |
| `incident_id` | INTEGER | FK → disaster_incidents | Incident context |
| `node_id` | INTEGER | FK → infrastructure_nodes | Target node |
| `resource_type` | VARCHAR(50) | | repair_crew / equipment / fuel / materials |
| `quantity` | FLOAT | | Number of units allocated |
| `assigned_at` | TIMESTAMP | | When assigned |
| `estimated_completion` | TIMESTAMP | | ETA for repair |
| `actual_completion` | TIMESTAMP | | Actual completion |
| `priority_rank` | INTEGER | | Repair priority order |
| `assigned_by` | VARCHAR(100) | | Operator name |

---

## PostGIS Spatial Indexes

```sql
CREATE INDEX idx_nodes_location ON infrastructure_nodes USING GIST(location);
CREATE INDEX idx_districts_geometry ON districts USING GIST(geometry);
CREATE INDEX idx_incidents_affected_area ON disaster_incidents USING GIST(affected_area);
CREATE INDEX idx_status_history_timestamp ON node_status_history(timestamp);
CREATE INDEX idx_status_history_node_incident ON node_status_history(node_id, incident_id);
CREATE INDEX idx_sensor_readings_node_time ON sensor_readings(node_id, timestamp DESC);
```

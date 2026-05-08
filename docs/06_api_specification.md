# API Specification

Base URL: `http://localhost:8000/api/v1`
Auth: Bearer JWT (for production; disabled in dev mode)
Content-Type: `application/json`

---

## Incidents

### POST /incidents
Create a new disaster incident.

**Request Body:**
```json
{
  "disaster_type": "blackout",
  "severity": "high",
  "severity_score": 7.2,
  "title": "Northgate Grid Failure",
  "description": "Major substation failure causing widespread blackout",
  "epicenter": { "lat": 40.7128, "lon": -74.0060 },
  "affected_radius_km": 5.0,
  "start_time": "2025-03-15T02:30:00Z"
}
```

**Response 201:**
```json
{
  "id": 42,
  "incident_uid": "INC-2025-0042",
  "disaster_type": "blackout",
  "severity": "high",
  "status": "active",
  "affected_districts": [1, 2, 4],
  "affected_node_count": 87,
  "estimated_recovery_hours": 18.5,
  "cascade_predictions": {
    "high_risk_nodes": ["PWR-SUB-003", "TEL-TWR-017", "EMR-HSP-002"],
    "cascade_probability": 0.82
  },
  "created_at": "2025-03-15T02:31:00Z"
}
```

---

### GET /incidents
List incidents with filters.

**Query Parameters:**
- `status` — active | recovering | resolved
- `disaster_type` — blackout | flood | infrastructure_failure | compound
- `district_id` — integer
- `from_date` — ISO datetime
- `to_date` — ISO datetime
- `page` — integer (default: 1)
- `page_size` — integer (default: 20, max: 100)

**Response 200:**
```json
{
  "total": 47,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 42,
      "incident_uid": "INC-2025-0042",
      "disaster_type": "blackout",
      "severity": "high",
      "status": "active",
      "start_time": "2025-03-15T02:30:00Z",
      "affected_node_count": 87,
      "estimated_recovery_hours": 18.5
    }
  ]
}
```

---

### GET /incidents/{incident_id}
Get full incident details.

**Response 200:**
```json
{
  "id": 42,
  "incident_uid": "INC-2025-0042",
  "disaster_type": "blackout",
  "severity": "high",
  "severity_score": 7.2,
  "title": "Northgate Grid Failure",
  "status": "active",
  "start_time": "2025-03-15T02:30:00Z",
  "affected_districts": [
    { "id": 1, "name": "Northgate", "resilience_score": 0.72 },
    { "id": 2, "name": "Riverside", "resilience_score": 0.58 }
  ],
  "system_status": {
    "power": { "total": 45, "failed": 23, "recovering": 8, "restored": 14 },
    "transport": { "total": 62, "failed": 5, "recovering": 3, "restored": 54 },
    "telecom": { "total": 28, "failed": 18, "recovering": 4, "restored": 6 },
    "emergency": { "total": 12, "failed": 2, "recovering": 1, "restored": 9 },
    "mobility": { "total": 34, "failed": 11, "recovering": 5, "restored": 18 },
    "service": { "total": 19, "failed": 7, "recovering": 3, "restored": 9 }
  }
}
```

---

## Infrastructure

### GET /infrastructure/nodes
List infrastructure nodes with spatial filtering.

**Query Parameters:**
- `system_type` — power | transport | telecom | emergency | mobility | service
- `status` — operational | degraded | failed | recovering | restored
- `district_id` — integer
- `lat`, `lon`, `radius_km` — spatial filter
- `criticality_min` — float (0–1)

**Response 200:**
```json
{
  "total": 234,
  "items": [
    {
      "id": 1,
      "node_uid": "PWR-SUB-001",
      "system_type": "power",
      "node_type": "substation",
      "name": "Northgate Main Substation",
      "district_id": 1,
      "location": { "lat": 40.7589, "lon": -73.9851 },
      "status": "failed",
      "criticality_score": 0.92,
      "operational_pct": 0.0,
      "hours_since_failure": 3.5
    }
  ]
}
```

---

### GET /infrastructure/graph
Get the full dependency graph for visualization.

**Query Parameters:**
- `incident_id` — highlight affected nodes
- `district_id` — filter to district
- `system_types` — comma-separated list

**Response 200:**
```json
{
  "nodes": [
    {
      "id": "PWR-SUB-001",
      "system_type": "power",
      "node_type": "substation",
      "status": "failed",
      "criticality_score": 0.92,
      "x": 120.5,
      "y": 340.2
    }
  ],
  "edges": [
    {
      "source": "PWR-SUB-001",
      "target": "TEL-TWR-017",
      "edge_type": "powers",
      "weight": 0.95,
      "is_critical": true
    }
  ],
  "metadata": {
    "total_nodes": 487,
    "total_edges": 1243,
    "failed_nodes": 87,
    "critical_path_length": 4
  }
}
```

---

### GET /infrastructure/critical-nodes
Get nodes ranked by criticality (betweenness centrality + criticality score).

**Response 200:**
```json
{
  "critical_nodes": [
    {
      "node_uid": "PWR-SUB-001",
      "name": "Northgate Main Substation",
      "system_type": "power",
      "criticality_score": 0.92,
      "betweenness_centrality": 0.87,
      "dependent_node_count": 34,
      "cascade_risk_score": 0.89
    }
  ]
}
```

---

## Recovery

### GET /recovery/predict/{node_id}
Get recovery timeline prediction for a specific node.

**Query Parameters:**
- `incident_id` — required

**Response 200:**
```json
{
  "node_id": 1,
  "node_uid": "PWR-SUB-001",
  "incident_id": 42,
  "model_version": "lstm-v2.1",
  "predicted_at": "2025-03-15T06:00:00Z",
  "hours_since_failure": 3.5,
  "predicted_restoration_hours": 11.2,
  "estimated_restoration_time": "2025-03-15T17:12:00Z",
  "confidence_interval": {
    "lower_hours": 8.5,
    "upper_hours": 15.8,
    "confidence_level": 0.80
  },
  "key_factors": [
    { "factor": "repair_crew_assigned", "impact": "positive", "weight": 0.32 },
    { "factor": "n_failed_dependencies", "impact": "negative", "weight": 0.28 },
    { "factor": "criticality_score", "impact": "negative", "weight": 0.18 }
  ]
}
```

---

### GET /recovery/district/{district_id}
Get recovery timeline for all systems in a district.

**Response 200:**
```json
{
  "district_id": 1,
  "district_name": "Northgate",
  "incident_id": 42,
  "overall_recovery_pct": 38.5,
  "systems": {
    "power": {
      "recovery_pct": 30.4,
      "predicted_50pct_hours": 8.2,
      "predicted_90pct_hours": 14.5,
      "predicted_full_hours": 18.1
    },
    "transport": {
      "recovery_pct": 87.1,
      "predicted_50pct_hours": 1.2,
      "predicted_90pct_hours": 3.4,
      "predicted_full_hours": 5.0
    }
  },
  "timeline_series": [
    { "hours": 0, "power": 0, "transport": 85, "telecom": 0, "emergency": 75, "mobility": 40, "service": 60 },
    { "hours": 6, "power": 15, "transport": 90, "telecom": 20, "emergency": 80, "mobility": 55, "service": 65 },
    { "hours": 12, "power": 45, "transport": 95, "telecom": 60, "emergency": 90, "mobility": 70, "service": 75 },
    { "hours": 18, "power": 85, "transport": 98, "telecom": 88, "emergency": 95, "mobility": 85, "service": 88 },
    { "hours": 24, "power": 98, "transport": 100, "telecom": 96, "emergency": 100, "mobility": 95, "service": 95 }
  ]
}
```

---

## Resilience

### GET /resilience/districts
Get resilience scores for all districts.

**Query Parameters:**
- `incident_id` — filter to specific incident
- `sort_by` — composite_score | absorption | adaptation | restoration
- `order` — asc | desc

**Response 200:**
```json
{
  "incident_id": 42,
  "computed_at": "2025-03-15T06:00:00Z",
  "districts": [
    {
      "district_id": 4,
      "district_name": "Central Hub",
      "composite_score": 0.88,
      "absorption_score": 0.88,
      "adaptation_score": 0.81,
      "restoration_score": 0.95,
      "rank": 1,
      "hours_to_50pct": 4.1,
      "hours_to_90pct": 9.8
    },
    {
      "district_id": 3,
      "district_name": "Southpark",
      "composite_score": 0.47,
      "absorption_score": 0.44,
      "adaptation_score": 0.38,
      "restoration_score": 0.62,
      "rank": 18,
      "hours_to_50pct": 18.7,
      "hours_to_90pct": 38.2
    }
  ]
}
```

---

## Simulation

### POST /simulation/run
Trigger a scenario simulation (async).

**Request Body:**
```json
{
  "incident_id": 42,
  "strategies": ["power_first", "transport_first", "parallel", "dependency_optimal"],
  "n_monte_carlo": 100,
  "resource_budget": 500.0,
  "custom_priorities": null
}
```

**Response 202:**
```json
{
  "run_id": "SIM-2025-0087",
  "status": "pending",
  "estimated_completion_seconds": 25,
  "poll_url": "/api/v1/simulation/SIM-2025-0087"
}
```

---

### GET /simulation/{run_id}
Poll simulation status.

**Response 200:**
```json
{
  "run_id": "SIM-2025-0087",
  "status": "completed",
  "progress_pct": 100,
  "started_at": "2025-03-15T06:01:00Z",
  "completed_at": "2025-03-15T06:01:22Z"
}
```

---

### GET /simulation/{run_id}/results
Get full simulation results.

**Response 200:**
```json
{
  "run_id": "SIM-2025-0087",
  "incident_id": 42,
  "strategy_comparison": [
    {
      "strategy": "dependency_optimal",
      "mean_recovery_hours": 16.2,
      "p10_hours": 12.1,
      "p90_hours": 21.8,
      "rank": 1,
      "improvement_vs_baseline_pct": 28.4
    },
    {
      "strategy": "power_first",
      "mean_recovery_hours": 19.8,
      "p10_hours": 15.2,
      "p90_hours": 26.4,
      "rank": 2,
      "improvement_vs_baseline_pct": 12.4
    },
    {
      "strategy": "parallel",
      "mean_recovery_hours": 22.6,
      "p10_hours": 17.8,
      "p90_hours": 29.1,
      "rank": 3,
      "improvement_vs_baseline_pct": 0.0
    }
  ],
  "bottleneck_nodes": [
    {
      "node_uid": "PWR-SUB-001",
      "bottleneck_score": 0.94,
      "blocks_n_nodes": 34,
      "recommendation": "Assign 2 additional repair crews immediately"
    }
  ],
  "recommendations": [
    "Prioritize PWR-SUB-001 restoration — unblocks 34 downstream nodes",
    "Deploy backup generator to EMR-HSP-002 within 2 hours",
    "Reroute emergency vehicles via TRN-RD-088 (Bridge St bypass)"
  ]
}
```

---

## WebSocket

### WS /ws/incidents/{incident_id}
Real-time node status updates for an active incident.

**Message format (server → client):**
```json
{
  "type": "node_status_update",
  "timestamp": "2025-03-15T06:05:00Z",
  "updates": [
    {
      "node_uid": "PWR-SUB-001",
      "status": "recovering",
      "operational_pct": 15.0,
      "repair_progress_pct": 22.0
    }
  ],
  "district_summary": {
    "1": { "overall_recovery_pct": 42.1 },
    "2": { "overall_recovery_pct": 67.8 }
  }
}
```

"""
Synthetic City Data Generator for UrbanSync AI.

Generates a realistic synthetic city with:
- 20 districts with PostGIS polygon geometries
- ~500 infrastructure nodes across 6 systems
- ~1200 dependency edges
- 50 historical disaster incidents
- 50,000+ node status history records for ML training
"""
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import json
import random
from typing import List, Dict, Tuple
import psycopg2
from psycopg2.extras import execute_values
import os

# Reproducible seed
np.random.seed(42)
random.seed(42)

# ─── City Configuration ───────────────────────────────────────────────────────

CITY_CENTER = (40.7128, -74.0060)  # NYC-like coordinates
N_DISTRICTS = 20
DISTRICT_NAMES = [
    "Northgate", "Riverside", "Southpark", "Central Hub", "Eastfield",
    "Westbridge", "Harbor View", "Midtown", "Old Quarter", "Tech District",
    "University Hill", "Industrial Zone", "Green Valley", "Airport Corridor",
    "Lakeside", "Uptown", "Downtown Core", "Suburban East", "Suburban West", "Port District"
]

SYSTEM_TYPES = ["power", "transport", "telecom", "emergency", "mobility", "service"]

NODE_TYPES = {
    "power":     ["substation", "transformer", "distribution_node", "power_line_segment"],
    "transport": ["road_segment", "bridge", "tunnel", "traffic_signal", "highway_junction"],
    "telecom":   ["cell_tower", "fiber_node", "data_center", "exchange_point"],
    "emergency": ["hospital", "fire_station", "police_station", "ambulance_depot"],
    "mobility":  ["bus_depot", "metro_station", "bus_stop", "ride_share_hub"],
    "service":   ["water_plant", "fuel_depot", "waste_facility", "school", "community_center"],
}

NODES_PER_SYSTEM = {
    "power": 80,
    "transport": 120,
    "telecom": 60,
    "emergency": 40,
    "mobility": 80,
    "service": 60,
}

DISASTER_TYPES = ["blackout", "flood", "infrastructure_failure", "compound"]
SEVERITY_LEVELS = ["low", "medium", "high", "catastrophic"]
SEVERITY_SCORES = {"low": (1, 3), "medium": (3, 6), "high": (6, 8), "catastrophic": (8, 10)}


# ─── District Generation ──────────────────────────────────────────────────────

def generate_districts() -> List[Dict]:
    """Generate 20 districts with realistic attributes."""
    districts = []
    lat_base, lon_base = CITY_CENTER
    grid_size = 0.05  # ~5km grid cells

    for i, name in enumerate(DISTRICT_NAMES):
        row = i // 5
        col = i % 5
        lat = lat_base + (row - 2) * grid_size + np.random.uniform(-0.01, 0.01)
        lon = lon_base + (col - 2) * grid_size + np.random.uniform(-0.01, 0.01)

        # Create a rough polygon (simplified rectangle with noise)
        half = grid_size * 0.45
        corners = [
            (lon - half + np.random.uniform(-0.005, 0.005), lat - half + np.random.uniform(-0.005, 0.005)),
            (lon + half + np.random.uniform(-0.005, 0.005), lat - half + np.random.uniform(-0.005, 0.005)),
            (lon + half + np.random.uniform(-0.005, 0.005), lat + half + np.random.uniform(-0.005, 0.005)),
            (lon - half + np.random.uniform(-0.005, 0.005), lat + half + np.random.uniform(-0.005, 0.005)),
        ]
        # Close the polygon
        corners.append(corners[0])
        polygon_wkt = "POLYGON((" + ", ".join(f"{c[0]} {c[1]}" for c in corners) + "))"

        income_level = np.random.choice(["low", "medium", "high"], p=[0.3, 0.5, 0.2])
        population = int(np.random.lognormal(11.5, 0.4))  # 50k–300k range
        area = np.random.uniform(10, 40)

        districts.append({
            "name": name,
            "code": f"D{i+1:02d}",
            "population": population,
            "area_sqkm": round(area, 2),
            "geometry_wkt": polygon_wkt,
            "urban_density": round(population / area, 1),
            "avg_income_level": income_level,
            "critical_infra_count": np.random.randint(5, 45),
            "center_lat": lat,
            "center_lon": lon,
        })

    return districts


# ─── Node Generation ──────────────────────────────────────────────────────────

def generate_nodes(districts: List[Dict]) -> List[Dict]:
    """Generate infrastructure nodes distributed across districts."""
    nodes = []
    node_id = 1

    for system_type, count in NODES_PER_SYSTEM.items():
        node_types = NODE_TYPES[system_type]
        for i in range(count):
            # Assign to a district (weighted by population)
            district = random.choices(
                districts,
                weights=[d["population"] for d in districts]
            )[0]
            district_idx = districts.index(district) + 1

            # Position within district
            lat = district["center_lat"] + np.random.uniform(-0.02, 0.02)
            lon = district["center_lon"] + np.random.uniform(-0.02, 0.02)

            node_type = random.choice(node_types)
            uid_prefix = system_type[:3].upper()
            node_uid = f"{uid_prefix}-{node_type[:3].upper()}-{node_id:03d}"

            # Criticality: emergency and power nodes tend to be more critical
            base_criticality = {
                "power": 0.7, "transport": 0.5, "telecom": 0.6,
                "emergency": 0.85, "mobility": 0.4, "service": 0.55
            }[system_type]
            criticality = min(1.0, base_criticality + np.random.uniform(-0.2, 0.2))

            # Capacity (system-specific units)
            capacity_ranges = {
                "power": (10, 500),       # MW
                "transport": (500, 5000), # vehicles/hour
                "telecom": (100, 2000),   # connections
                "emergency": (50, 1000),  # beds/units
                "mobility": (20, 500),    # vehicles
                "service": (1000, 100000) # L/day or similar
            }
            cap_min, cap_max = capacity_ranges[system_type]
            capacity = round(np.random.uniform(cap_min, cap_max), 1)

            install_year = np.random.randint(1980, 2022)
            days_since_maintenance = np.random.randint(0, 730)
            last_maintenance = (datetime.now() - timedelta(days=days_since_maintenance)).date()

            nodes.append({
                "node_uid": node_uid,
                "system_type": system_type,
                "node_type": node_type,
                "name": f"{district['name']} {node_type.replace('_', ' ').title()} {i+1}",
                "district_id": district_idx,
                "lat": lat,
                "lon": lon,
                "capacity": capacity,
                "current_load": round(capacity * np.random.uniform(0.3, 0.9), 1),
                "status": "operational",
                "criticality_score": round(criticality, 3),
                "backup_available": np.random.random() < 0.25,
                "install_year": install_year,
                "last_maintenance": last_maintenance.isoformat(),
            })
            node_id += 1

    return nodes


# ─── Dependency Edge Generation ───────────────────────────────────────────────

def generate_dependency_edges(nodes: List[Dict]) -> List[Dict]:
    """
    Generate realistic dependency edges between nodes.
    
    Dependency rules:
    - Power → Telecom (powers)
    - Power → Emergency (powers)
    - Power → Mobility (powers, partial)
    - Power → Service (powers)
    - Telecom → Emergency (provides_comms)
    - Telecom → Transport (provides_comms, traffic signals)
    - Transport → Emergency (road_access)
    - Transport → Service (road_access)
    - Transport → Mobility (enables_access)
    - Service → Emergency (fuel_supply)
    - Service → Power (fuel_supply, power plant fuel)
    """
    edges = []
    edge_id = 1

    # Index nodes by system type
    by_system = {s: [] for s in SYSTEM_TYPES}
    for i, node in enumerate(nodes):
        by_system[node["system_type"]].append((i + 1, node))  # (db_id, node)

    def add_edges(source_system, target_system, edge_type, weight_range, is_critical_prob, lag_range, n_connections):
        sources = by_system[source_system]
        targets = by_system[target_system]
        if not sources or not targets:
            return

        # Each source connects to a few targets in same/nearby district
        for src_id, src_node in random.sample(sources, min(n_connections, len(sources))):
            # Find nearby targets (same district preferred)
            same_district = [(tid, t) for tid, t in targets if t["district_id"] == src_node["district_id"]]
            candidates = same_district if same_district else targets
            n_targets = min(np.random.randint(1, 4), len(candidates))
            selected_targets = random.sample(candidates, n_targets)

            for tgt_id, tgt_node in selected_targets:
                edges.append({
                    "source_node_id": src_id,
                    "target_node_id": tgt_id,
                    "edge_type": edge_type,
                    "weight": round(np.random.uniform(*weight_range), 3),
                    "is_critical": np.random.random() < is_critical_prob,
                    "lag_hours": round(np.random.uniform(*lag_range), 1),
                })

    # Power → others
    add_edges("power", "telecom",    "powers",         (0.85, 0.98), 0.7, (0.0, 1.0), 40)
    add_edges("power", "emergency",  "powers",         (0.80, 0.95), 0.5, (0.5, 2.0), 30)
    add_edges("power", "mobility",   "powers",         (0.60, 0.80), 0.3, (0.5, 2.0), 30)
    add_edges("power", "service",    "powers",         (0.75, 0.92), 0.5, (0.5, 1.5), 35)

    # Telecom → others
    add_edges("telecom", "emergency",  "provides_comms", (0.75, 0.90), 0.4, (0.0, 0.5), 25)
    add_edges("telecom", "transport",  "provides_comms", (0.50, 0.70), 0.2, (0.0, 0.5), 20)

    # Transport → others
    add_edges("transport", "emergency", "road_access",   (0.80, 0.95), 0.5, (0.0, 0.5), 35)
    add_edges("transport", "service",   "road_access",   (0.65, 0.85), 0.3, (0.0, 1.0), 30)
    add_edges("transport", "mobility",  "enables_access",(0.70, 0.88), 0.3, (0.0, 0.5), 30)

    # Service → others
    add_edges("service", "emergency", "fuel_supply",    (0.60, 0.80), 0.3, (1.0, 3.0), 20)
    add_edges("service", "power",     "fuel_supply",    (0.55, 0.75), 0.2, (2.0, 6.0), 15)

    return edges


# ─── Incident Generation ──────────────────────────────────────────────────────

def generate_incidents(districts: List[Dict], n_incidents: int = 50) -> List[Dict]:
    """Generate historical disaster incidents."""
    incidents = []
    start_date = datetime(2022, 1, 1)

    for i in range(n_incidents):
        disaster_type = random.choice(DISASTER_TYPES)
        severity = random.choices(
            SEVERITY_LEVELS, weights=[0.3, 0.35, 0.25, 0.1]
        )[0]
        sev_min, sev_max = SEVERITY_SCORES[severity]
        severity_score = round(np.random.uniform(sev_min, sev_max), 1)

        # Random date in range
        days_offset = np.random.randint(0, 900)
        start_time = start_date + timedelta(days=int(days_offset), hours=int(np.random.randint(0, 24)))

        # Affected districts (1–8 depending on severity)
        n_affected = {"low": 1, "medium": 2, "high": 4, "catastrophic": 8}[severity]
        affected_districts = random.sample(range(1, N_DISTRICTS + 1), min(n_affected, N_DISTRICTS))

        # Recovery time (hours)
        base_recovery = {"low": 4, "medium": 12, "high": 24, "catastrophic": 72}[severity]
        actual_recovery = round(base_recovery * np.random.lognormal(0, 0.3), 1)
        estimated_recovery = round(actual_recovery * np.random.uniform(0.7, 1.4), 1)

        # Epicenter in one of the affected districts
        epicenter_district = districts[affected_districts[0] - 1]
        epi_lat = epicenter_district["center_lat"] + np.random.uniform(-0.01, 0.01)
        epi_lon = epicenter_district["center_lon"] + np.random.uniform(-0.01, 0.01)

        affected_node_count = int(np.random.uniform(10, 50) * n_affected)

        incidents.append({
            "incident_uid": f"INC-{start_time.year}-{i+1:04d}",
            "disaster_type": disaster_type,
            "severity": severity,
            "severity_score": severity_score,
            "title": f"{severity.title()} {disaster_type.replace('_', ' ').title()} — {epicenter_district['name']}",
            "description": f"Synthetic {disaster_type} event affecting {n_affected} districts.",
            "epi_lat": epi_lat,
            "epi_lon": epi_lon,
            "start_time": start_time.isoformat(),
            "end_time": (start_time + timedelta(hours=actual_recovery)).isoformat(),
            "status": "resolved",
            "affected_districts": affected_districts,
            "affected_node_count": affected_node_count,
            "estimated_recovery_hours": estimated_recovery,
            "actual_recovery_hours": actual_recovery,
        })

    return incidents


# ─── Status History Generation ────────────────────────────────────────────────

def generate_status_history(
    nodes: List[Dict],
    incidents: List[Dict],
    n_records_target: int = 50000
) -> List[Dict]:
    """
    Generate time-series node status history for ML training.
    Each incident affects a subset of nodes with realistic recovery curves.
    """
    records = []

    for incident in incidents:
        affected_node_ids = random.sample(
            range(1, len(nodes) + 1),
            min(incident["affected_node_count"], len(nodes))
        )
        start_time = datetime.fromisoformat(incident["start_time"])
        total_recovery_hours = incident["actual_recovery_hours"]

        for node_id in affected_node_ids:
            node = nodes[node_id - 1]
            # Individual node recovery time (varies around incident average)
            node_recovery_hours = max(0.5, total_recovery_hours * np.random.lognormal(0, 0.4))
            crew_assigned_at = np.random.uniform(0.5, min(4.0, node_recovery_hours * 0.3))

            # Generate hourly observations
            n_obs = max(3, int(node_recovery_hours * 2))  # every 30 min
            for obs_idx in range(n_obs + 1):
                hours_elapsed = obs_idx * 0.5
                timestamp = start_time + timedelta(hours=hours_elapsed)

                if hours_elapsed == 0:
                    status = "failed"
                    operational_pct = 0.0
                    repair_progress = 0.0
                elif hours_elapsed >= node_recovery_hours:
                    status = "restored"
                    operational_pct = 100.0
                    repair_progress = 100.0
                elif hours_elapsed >= crew_assigned_at:
                    # Sigmoid recovery curve
                    progress_ratio = (hours_elapsed - crew_assigned_at) / (node_recovery_hours - crew_assigned_at)
                    repair_progress = 100 * (1 / (1 + np.exp(-8 * (progress_ratio - 0.5))))
                    operational_pct = repair_progress * np.random.uniform(0.85, 1.0)
                    status = "recovering"
                else:
                    status = "failed"
                    operational_pct = 0.0
                    repair_progress = 0.0

                records.append({
                    "node_id": node_id,
                    "incident_id": incidents.index(incident) + 1,
                    "timestamp": timestamp.isoformat(),
                    "status": status,
                    "operational_pct": round(min(100, max(0, operational_pct)), 1),
                    "load_pct": round(operational_pct * np.random.uniform(0.7, 1.0), 1),
                    "repair_crew_assigned": hours_elapsed >= crew_assigned_at,
                    "repair_progress_pct": round(min(100, max(0, repair_progress)), 1),
                    "hours_since_failure": round(hours_elapsed, 2),
                    "hours_to_restoration": round(max(0, node_recovery_hours - hours_elapsed), 2),
                    "recorded_by": "sensor",
                })

        if len(records) >= n_records_target:
            break

    return records


# ─── Database Insertion ───────────────────────────────────────────────────────

def insert_to_database(conn_string: str):
    """Insert all synthetic data into PostgreSQL."""
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()

    print("Generating synthetic city data...")
    districts = generate_districts()
    nodes = generate_nodes(districts)
    edges = generate_dependency_edges(nodes)
    incidents = generate_incidents(districts)
    history = generate_status_history(nodes, incidents)

    print(f"  Districts: {len(districts)}")
    print(f"  Nodes: {len(nodes)}")
    print(f"  Edges: {len(edges)}")
    print(f"  Incidents: {len(incidents)}")
    print(f"  Status history records: {len(history)}")

    # Insert districts
    print("Inserting districts...")
    execute_values(cur, """
        INSERT INTO districts (name, code, population, area_sqkm, geometry, urban_density, avg_income_level, critical_infra_count)
        VALUES %s
    """, [
        (d["name"], d["code"], d["population"], d["area_sqkm"],
         f"SRID=4326;{d['geometry_wkt']}", d["urban_density"],
         d["avg_income_level"], d["critical_infra_count"])
        for d in districts
    ])

    # Insert nodes
    print("Inserting infrastructure nodes...")
    execute_values(cur, """
        INSERT INTO infrastructure_nodes
        (node_uid, system_type, node_type, name, district_id, location, capacity, current_load,
         status, criticality_score, backup_available, install_year, last_maintenance)
        VALUES %s
    """, [
        (n["node_uid"], n["system_type"], n["node_type"], n["name"], n["district_id"],
         f"SRID=4326;POINT({n['lon']} {n['lat']})", n["capacity"], n["current_load"],
         n["status"], n["criticality_score"], n["backup_available"],
         n["install_year"], n["last_maintenance"])
        for n in nodes
    ])

    # Insert edges
    print("Inserting dependency edges...")
    execute_values(cur, """
        INSERT INTO dependency_edges (source_node_id, target_node_id, edge_type, weight, is_critical, lag_hours)
        VALUES %s
    """, [
        (e["source_node_id"], e["target_node_id"], e["edge_type"],
         e["weight"], e["is_critical"], e["lag_hours"])
        for e in edges
    ])

    # Insert incidents
    print("Inserting incidents...")
    execute_values(cur, """
        INSERT INTO disaster_incidents
        (incident_uid, disaster_type, severity, severity_score, title, description,
         epicenter, start_time, end_time, status, affected_districts,
         affected_node_count, estimated_recovery_hours, actual_recovery_hours)
        VALUES %s
    """, [
        (inc["incident_uid"], inc["disaster_type"], inc["severity"], inc["severity_score"],
         inc["title"], inc["description"],
         f"SRID=4326;POINT({inc['epi_lon']} {inc['epi_lat']})",
         inc["start_time"], inc["end_time"], inc["status"],
         inc["affected_districts"], inc["affected_node_count"],
         inc["estimated_recovery_hours"], inc["actual_recovery_hours"])
        for inc in incidents
    ])

    # Insert status history in batches
    print("Inserting status history (this may take a moment)...")
    batch_size = 5000
    for i in range(0, len(history), batch_size):
        batch = history[i:i + batch_size]
        execute_values(cur, """
            INSERT INTO node_status_history
            (node_id, incident_id, timestamp, status, operational_pct, load_pct,
             repair_crew_assigned, repair_progress_pct, hours_since_failure,
             hours_to_restoration, recorded_by)
            VALUES %s
        """, [
            (h["node_id"], h["incident_id"], h["timestamp"], h["status"],
             h["operational_pct"], h["load_pct"], h["repair_crew_assigned"],
             h["repair_progress_pct"], h["hours_since_failure"],
             h["hours_to_restoration"], h["recorded_by"])
            for h in batch
        ])
        print(f"  Inserted {min(i + batch_size, len(history))}/{len(history)} history records")

    conn.commit()
    cur.close()
    conn.close()
    print("✓ Synthetic data generation complete!")


if __name__ == "__main__":
    conn_string = os.getenv(
        "DATABASE_URL",
        "postgresql://urbansync:urbansync_dev_password@localhost:5432/urbansync"
    )
    insert_to_database(conn_string)

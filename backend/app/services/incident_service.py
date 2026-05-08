"""
Incident service — business logic for disaster incident management.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.incidents import DisasterIncident, NodeStatusHistory
from app.models.infrastructure import InfrastructureNode, District
from app.schemas.incidents import IncidentCreate, IncidentListResponse


class IncidentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_incident(self, payload: IncidentCreate) -> DisasterIncident:
        """Create a new incident and identify affected nodes via spatial query."""
        incident_uid = f"INC-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"

        # Find affected nodes within radius using PostGIS
        affected_nodes_query = """
            SELECT id, district_id FROM infrastructure_nodes
            WHERE ST_DWithin(
                location::geography,
                ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                :radius_m
            )
        """
        result = await self.db.execute(
            affected_nodes_query,
            {
                "lat": payload.epicenter.lat,
                "lon": payload.epicenter.lon,
                "radius_m": payload.affected_radius_km * 1000,
            }
        )
        affected_rows = result.fetchall()
        affected_node_count = len(affected_rows)
        affected_district_ids = list(set(row[1] for row in affected_rows if row[1]))

        incident = DisasterIncident(
            incident_uid=incident_uid,
            disaster_type=payload.disaster_type,
            severity=payload.severity,
            severity_score=payload.severity_score,
            title=payload.title,
            description=payload.description,
            start_time=payload.start_time,
            status="active",
            affected_districts=affected_district_ids,
            affected_node_count=affected_node_count,
            estimated_recovery_hours=self._estimate_recovery_hours(
                payload.severity, affected_node_count
            ),
        )
        self.db.add(incident)
        await self.db.flush()
        return incident

    async def get_incident_detail(self, incident_id: int) -> Optional[dict]:
        """Get full incident details with system status breakdown."""
        result = await self.db.execute(
            select(DisasterIncident).where(DisasterIncident.id == incident_id)
        )
        incident = result.scalar_one_or_none()
        if not incident:
            return None

        # Get system status breakdown
        system_status = await self._get_system_status(incident_id)

        return {
            "id": incident.id,
            "incident_uid": incident.incident_uid,
            "disaster_type": incident.disaster_type,
            "severity": incident.severity,
            "severity_score": incident.severity_score,
            "title": incident.title,
            "status": incident.status,
            "start_time": incident.start_time,
            "end_time": incident.end_time,
            "affected_districts": incident.affected_districts,
            "affected_node_count": incident.affected_node_count,
            "estimated_recovery_hours": incident.estimated_recovery_hours,
            "system_status": system_status,
            "cascade_predictions": None,  # Filled by background task
            "created_at": incident.created_at,
        }

    async def list_incidents(
        self,
        status: Optional[str] = None,
        disaster_type: Optional[str] = None,
        district_id: Optional[int] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """List incidents with filters and pagination."""
        query = select(DisasterIncident)
        conditions = []

        if status:
            conditions.append(DisasterIncident.status == status)
        if disaster_type:
            conditions.append(DisasterIncident.disaster_type == disaster_type)
        if from_date:
            conditions.append(DisasterIncident.start_time >= from_date)
        if to_date:
            conditions.append(DisasterIncident.start_time <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        # Count total
        count_result = await self.db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = count_result.scalar()

        # Paginate
        query = query.order_by(DisasterIncident.start_time.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        incidents = result.scalars().all()

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                {
                    "id": inc.id,
                    "incident_uid": inc.incident_uid,
                    "disaster_type": inc.disaster_type,
                    "severity": inc.severity,
                    "status": inc.status,
                    "start_time": inc.start_time,
                    "affected_node_count": inc.affected_node_count,
                    "estimated_recovery_hours": inc.estimated_recovery_hours,
                }
                for inc in incidents
            ],
        }

    async def update_status(self, incident_id: int, status: str) -> bool:
        """Update incident status."""
        result = await self.db.execute(
            select(DisasterIncident).where(DisasterIncident.id == incident_id)
        )
        incident = result.scalar_one_or_none()
        if not incident:
            return False
        incident.status = status
        if status == "resolved":
            incident.end_time = datetime.utcnow()
        return True

    async def get_recovery_timeline(self, incident_id: int) -> dict:
        """Get hourly recovery timeline for all systems."""
        # Query status history grouped by hour and system type
        query = """
            SELECT
                EXTRACT(EPOCH FROM (nsh.timestamp - di.start_time)) / 3600 AS hours_elapsed,
                n.system_type,
                AVG(nsh.operational_pct) AS avg_operational_pct
            FROM node_status_history nsh
            JOIN infrastructure_nodes n ON nsh.node_id = n.id
            JOIN disaster_incidents di ON nsh.incident_id = di.id
            WHERE nsh.incident_id = :incident_id
            GROUP BY hours_elapsed, n.system_type
            ORDER BY hours_elapsed, n.system_type
        """
        result = await self.db.execute(query, {"incident_id": incident_id})
        rows = result.fetchall()

        # Pivot into timeline format
        timeline = {}
        for row in rows:
            hour = round(float(row[0]), 1)
            system = row[1]
            pct = float(row[2])
            if hour not in timeline:
                timeline[hour] = {"hours": hour}
            timeline[hour][system] = round(pct, 1)

        return {"incident_id": incident_id, "timeline": list(timeline.values())}

    async def run_cascade_prediction(self, incident_id: int):
        """Background task: run GNN cascade prediction."""
        from app.ml.model_registry import ModelRegistry
        model = ModelRegistry.get_gnn()
        if model is None:
            return  # Model not loaded, skip
        # In production: build graph from DB, run inference, store results

    async def run_initial_recovery_predictions(self, incident_id: int):
        """Background task: run initial LSTM recovery predictions for all affected nodes."""
        from app.ml.model_registry import ModelRegistry
        model = ModelRegistry.get_lstm()
        if model is None:
            return  # Model not loaded, skip
        # In production: fetch affected nodes, build sequences, run inference, store predictions

    async def _get_system_status(self, incident_id: int) -> dict:
        """Get node count by status for each system type."""
        query = """
            SELECT
                n.system_type,
                n.status,
                COUNT(*) as count
            FROM infrastructure_nodes n
            JOIN node_status_history nsh ON n.id = nsh.node_id
            WHERE nsh.incident_id = :incident_id
            AND nsh.timestamp = (
                SELECT MAX(timestamp) FROM node_status_history
                WHERE node_id = n.id AND incident_id = :incident_id
            )
            GROUP BY n.system_type, n.status
        """
        result = await self.db.execute(query, {"incident_id": incident_id})
        rows = result.fetchall()

        system_status = {}
        for row in rows:
            system = row[0]
            status = row[1]
            count = row[2]
            if system not in system_status:
                system_status[system] = {"total": 0, "failed": 0, "recovering": 0, "restored": 0, "operational": 0}
            system_status[system][status] = system_status[system].get(status, 0) + count
            system_status[system]["total"] += count

        return system_status

    def _estimate_recovery_hours(self, severity: str, affected_node_count: int) -> float:
        """Rough initial estimate of recovery hours."""
        base = {"low": 4, "medium": 12, "high": 24, "catastrophic": 72}.get(severity, 12)
        node_factor = 1 + (affected_node_count / 100) * 0.5
        return round(base * node_factor, 1)

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
from datetime import datetime

from app.core.database import get_async_db
from app.models.incidents import DisasterIncident
from app.schemas.incidents import (
    IncidentCreate, IncidentResponse, IncidentListResponse, IncidentDetail
)
from app.services.incident_service import IncidentService
from app.ml.cascade_detector import CascadeDetector

router = APIRouter()


@router.post("/incidents", response_model=IncidentDetail, status_code=201)
async def create_incident(
    payload: IncidentCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Create a new disaster incident.
    Automatically identifies affected nodes via PostGIS spatial query
    and triggers cascade failure prediction via GNN.
    """
    service = IncidentService(db)
    incident = await service.create_incident(payload)

    # Trigger cascade prediction in background
    background_tasks.add_task(
        service.run_cascade_prediction, incident.id
    )
    # Trigger initial recovery predictions
    background_tasks.add_task(
        service.run_initial_recovery_predictions, incident.id
    )

    return await service.get_incident_detail(incident.id)


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    status: Optional[str] = Query(None, description="active | recovering | resolved"),
    disaster_type: Optional[str] = Query(None),
    district_id: Optional[int] = Query(None),
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """List incidents with optional filters and pagination."""
    service = IncidentService(db)
    return await service.list_incidents(
        status=status,
        disaster_type=disaster_type,
        district_id=district_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get full incident details including system status breakdown."""
    service = IncidentService(db)
    incident = await service.get_incident_detail(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@router.patch("/incidents/{incident_id}/status")
async def update_incident_status(
    incident_id: int,
    status: str = Query(..., description="active | recovering | resolved"),
    db: AsyncSession = Depends(get_async_db),
):
    """Update incident status."""
    valid_statuses = {"active", "recovering", "resolved"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Status must be one of: {valid_statuses}")

    service = IncidentService(db)
    updated = await service.update_status(incident_id, status)
    if not updated:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"id": incident_id, "status": status, "updated_at": datetime.utcnow()}


@router.get("/incidents/{incident_id}/timeline")
async def get_incident_timeline(
    incident_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get hourly recovery timeline for all systems in an incident."""
    service = IncidentService(db)
    return await service.get_recovery_timeline(incident_id)

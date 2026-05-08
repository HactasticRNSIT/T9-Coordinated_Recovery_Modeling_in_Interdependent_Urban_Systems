from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_async_db
from app.services.resilience_service import ResilienceService

router = APIRouter()


@router.get("/resilience/districts")
async def get_district_resilience_scores(
    incident_id: Optional[int] = Query(None),
    sort_by: str = Query("composite_score", description="composite_score | absorption | adaptation | restoration"),
    order: str = Query("desc", description="asc | desc"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get resilience scores for all districts, optionally filtered by incident."""
    service = ResilienceService(db)
    return await service.get_all_district_scores(
        incident_id=incident_id,
        sort_by=sort_by,
        order=order,
    )


@router.get("/resilience/districts/{district_id}")
async def get_district_resilience(
    district_id: int,
    incident_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Get detailed resilience score for a specific district."""
    service = ResilienceService(db)
    score = await service.get_district_score(district_id, incident_id)
    if not score:
        raise HTTPException(status_code=404, detail=f"District {district_id} not found")
    return score


@router.post("/resilience/compute/{incident_id}")
async def compute_resilience_scores(
    incident_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Trigger resilience score computation for all districts in an incident.
    Uses XGBoost model for prediction.
    """
    service = ResilienceService(db)
    return await service.compute_scores_for_incident(incident_id)


@router.get("/resilience/history/{district_id}")
async def get_district_resilience_history(
    district_id: int,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_async_db),
):
    """Get historical resilience scores for a district across past incidents."""
    service = ResilienceService(db)
    return await service.get_district_history(district_id, limit)

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_async_db
from app.services.recovery_service import RecoveryService

router = APIRouter()


@router.get("/recovery/predict/{node_id}")
async def predict_node_recovery(
    node_id: int,
    incident_id: int = Query(..., description="Associated incident ID"),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get ML-predicted recovery timeline for a specific node.
    Uses LSTM + XGBoost ensemble.
    """
    service = RecoveryService(db)
    prediction = await service.predict_node_recovery(node_id, incident_id)
    if not prediction:
        raise HTTPException(status_code=404, detail=f"Node {node_id} or incident {incident_id} not found")
    return prediction


@router.get("/recovery/district/{district_id}")
async def get_district_recovery(
    district_id: int,
    incident_id: int = Query(...),
    db: AsyncSession = Depends(get_async_db),
):
    """Get recovery timeline for all systems in a district."""
    service = RecoveryService(db)
    return await service.get_district_recovery(district_id, incident_id)


@router.get("/recovery/incident/{incident_id}/summary")
async def get_incident_recovery_summary(
    incident_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """Get overall recovery summary for an incident across all districts."""
    service = RecoveryService(db)
    return await service.get_incident_recovery_summary(incident_id)

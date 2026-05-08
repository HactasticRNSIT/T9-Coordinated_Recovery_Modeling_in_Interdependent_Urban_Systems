from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_async_db
from app.services.graph_service import GraphService

router = APIRouter()


@router.get("/graph/cascade-predict")
async def predict_cascade(
    incident_id: int = Query(...),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Run GNN cascade failure prediction for an incident.
    Returns failure probability for each node.
    """
    service = GraphService(db)
    return await service.predict_cascade(incident_id)


@router.get("/graph/critical-path")
async def get_critical_path(
    source_system: str = Query(..., description="Starting system type"),
    target_system: str = Query(..., description="Target system type"),
    db: AsyncSession = Depends(get_async_db),
):
    """Find the critical dependency path between two system types."""
    service = GraphService(db)
    return await service.get_critical_path(source_system, target_system)


@router.get("/graph/centrality")
async def get_centrality_scores(
    metric: str = Query("betweenness", description="betweenness | closeness | pagerank | degree"),
    top_n: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Get node centrality scores for the dependency graph."""
    service = GraphService(db)
    return await service.get_centrality_scores(metric=metric, top_n=top_n)


@router.get("/graph/isolated-nodes/{incident_id}")
async def get_isolated_nodes(
    incident_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Find nodes that are isolated (all dependencies failed) in an incident.
    These are the hardest to restore.
    """
    service = GraphService(db)
    return await service.get_isolated_nodes(incident_id)

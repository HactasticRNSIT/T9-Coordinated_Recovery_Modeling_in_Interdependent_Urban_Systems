from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.core.database import get_async_db
from app.services.infrastructure_service import InfrastructureService

router = APIRouter()


@router.get("/infrastructure/nodes")
async def list_nodes(
    system_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    district_id: Optional[int] = Query(None),
    lat: Optional[float] = Query(None),
    lon: Optional[float] = Query(None),
    radius_km: Optional[float] = Query(None),
    criticality_min: Optional[float] = Query(None, ge=0.0, le=1.0),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    """List infrastructure nodes with optional spatial and attribute filters."""
    service = InfrastructureService(db)
    return await service.list_nodes(
        system_type=system_type,
        status=status,
        district_id=district_id,
        lat=lat, lon=lon, radius_km=radius_km,
        criticality_min=criticality_min,
        page=page, page_size=page_size,
    )


@router.get("/infrastructure/nodes/{node_id}")
async def get_node(node_id: int, db: AsyncSession = Depends(get_async_db)):
    """Get a single infrastructure node by ID."""
    service = InfrastructureService(db)
    node = await service.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return node


@router.get("/infrastructure/graph")
async def get_dependency_graph(
    incident_id: Optional[int] = Query(None),
    district_id: Optional[int] = Query(None),
    system_types: Optional[str] = Query(None, description="Comma-separated system types"),
    db: AsyncSession = Depends(get_async_db),
):
    """Get dependency graph for visualization (nodes + edges)."""
    service = InfrastructureService(db)
    system_type_list = system_types.split(",") if system_types else None
    return await service.get_graph(
        incident_id=incident_id,
        district_id=district_id,
        system_types=system_type_list,
    )


@router.get("/infrastructure/critical-nodes")
async def get_critical_nodes(
    top_n: int = Query(20, ge=1, le=100),
    system_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
):
    """Get top-N critical nodes ranked by cascade risk score."""
    service = InfrastructureService(db)
    return await service.get_critical_nodes(top_n=top_n, system_type=system_type)


@router.get("/infrastructure/districts")
async def list_districts(db: AsyncSession = Depends(get_async_db)):
    """List all districts with basic stats."""
    service = InfrastructureService(db)
    return await service.list_districts()

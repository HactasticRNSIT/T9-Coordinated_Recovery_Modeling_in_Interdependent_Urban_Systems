from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_async_db
from app.schemas.simulation import SimulationRequest, SimulationStatusResponse, SimulationResultResponse
from app.services.simulation_service import SimulationService

router = APIRouter()


@router.post("/simulation/run", response_model=SimulationStatusResponse, status_code=202)
async def run_simulation(
    payload: SimulationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Trigger a Monte Carlo scenario simulation (async).
    Returns a run_id to poll for results.
    """
    service = SimulationService(db)
    run = await service.create_run(payload)

    # Execute simulation in background via Celery
    background_tasks.add_task(service.execute_simulation, run.run_uid)

    estimated_seconds = min(payload.n_monte_carlo * 0.25, 60)
    return {
        "run_id": run.run_uid,
        "status": "pending",
        "estimated_completion_seconds": int(estimated_seconds),
        "poll_url": f"/api/v1/simulation/{run.run_uid}",
    }


@router.get("/simulation/{run_id}", response_model=SimulationStatusResponse)
async def get_simulation_status(
    run_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Poll simulation run status."""
    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Simulation run {run_id} not found")
    return {
        "run_id": run.run_uid,
        "status": run.status,
        "progress_pct": 100 if run.status == "completed" else 50,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


@router.get("/simulation/{run_id}/results", response_model=SimulationResultResponse)
async def get_simulation_results(
    run_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Get full simulation results after completion."""
    service = SimulationService(db)
    run = await service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Simulation run {run_id} not found")
    if run.status != "completed":
        raise HTTPException(
            status_code=202,
            detail=f"Simulation is still {run.status}. Poll {run_id} for status."
        )
    return await service.get_results(run_id)


@router.get("/simulation/strategies/list")
async def list_strategies():
    """List available recovery strategies."""
    return {
        "strategies": [
            {
                "id": "power_first",
                "name": "Power-First",
                "description": "Restore power grid before all other systems",
                "priority_order": ["power", "telecom", "emergency", "transport", "mobility", "service"],
            },
            {
                "id": "transport_first",
                "name": "Transport-First",
                "description": "Open roads first to enable crew access",
                "priority_order": ["transport", "power", "emergency", "telecom", "mobility", "service"],
            },
            {
                "id": "emergency_first",
                "name": "Emergency-First",
                "description": "Prioritize hospitals and emergency services",
                "priority_order": ["emergency", "power", "telecom", "transport", "mobility", "service"],
            },
            {
                "id": "parallel",
                "name": "Parallel Restoration",
                "description": "Restore all systems simultaneously",
                "priority_order": ["all"],
            },
            {
                "id": "dependency_optimal",
                "name": "Dependency-Optimal",
                "description": "Topological sort of dependency graph — computed per incident",
                "priority_order": ["computed"],
            },
        ]
    }

"""
Simulation service — manages simulation run lifecycle.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import uuid

from app.models.incidents import SimulationRun
from app.schemas.simulation import SimulationRequest


class SimulationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_run(self, payload: SimulationRequest) -> SimulationRun:
        """Create a new simulation run record."""
        run_uid = f"SIM-{datetime.utcnow().year}-{str(uuid.uuid4())[:8].upper()}"
        # For multi-strategy runs, create one run per strategy
        # Here we create a single run for the first strategy (extend for multi-strategy)
        strategy = payload.strategies[0] if payload.strategies else "parallel"

        run = SimulationRun(
            run_uid=run_uid,
            incident_id=payload.incident_id,
            strategy=strategy,
            n_monte_carlo=payload.n_monte_carlo,
            resource_budget=payload.resource_budget,
            status="pending",
        )
        self.db.add(run)
        await self.db.flush()
        return run

    async def get_run(self, run_id: str) -> Optional[SimulationRun]:
        """Get simulation run by UID."""
        result = await self.db.execute(
            select(SimulationRun).where(SimulationRun.run_uid == run_id)
        )
        return result.scalar_one_or_none()

    async def execute_simulation(self, run_uid: str):
        """Trigger async simulation via Celery."""
        from app.tasks.simulation_tasks import run_simulation_task
        run_simulation_task.delay(run_uid)

    async def get_results(self, run_id: str) -> dict:
        """Get formatted simulation results."""
        run = await self.get_run(run_id)
        if not run or not run.result_json:
            return {}

        results = run.result_json
        return {
            "run_id": run.run_uid,
            "incident_id": run.incident_id,
            "recommended_strategy": results.get("recommended_strategy", "parallel"),
            "strategy_comparison": results.get("strategy_comparison", []),
            "recommendations": results.get("recommendations", []),
            "detailed_results": results.get("detailed_results"),
        }

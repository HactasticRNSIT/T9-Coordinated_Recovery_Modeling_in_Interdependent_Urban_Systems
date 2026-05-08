from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class SimulationRequest(BaseModel):
    incident_id: int
    strategies: List[str] = Field(
        default=["power_first", "parallel", "dependency_optimal"],
        min_length=1,
        max_length=5,
    )
    n_monte_carlo: int = Field(default=100, ge=10, le=500)
    resource_budget: float = Field(default=500.0, ge=50, le=10000)
    custom_priorities: Optional[List[str]] = None

    model_config = {"json_schema_extra": {
        "example": {
            "incident_id": 1,
            "strategies": ["power_first", "transport_first", "dependency_optimal"],
            "n_monte_carlo": 100,
            "resource_budget": 500.0
        }
    }}


class SimulationStatusResponse(BaseModel):
    run_id: str
    status: str
    progress_pct: Optional[int] = None
    estimated_completion_seconds: Optional[int] = None
    poll_url: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class StrategyResult(BaseModel):
    strategy: str
    rank: int
    mean_recovery_hours: float
    p10_hours: float
    p90_hours: float
    improvement_vs_baseline_pct: float
    bottleneck_nodes: List[Dict[str, Any]]


class SimulationResultResponse(BaseModel):
    run_id: str
    incident_id: int
    recommended_strategy: str
    strategy_comparison: List[StrategyResult]
    recommendations: List[str]
    detailed_results: Optional[Dict[str, Any]] = None

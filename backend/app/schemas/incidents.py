from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class GeoPoint(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class IncidentCreate(BaseModel):
    disaster_type: str = Field(..., pattern="^(blackout|flood|infrastructure_failure|compound)$")
    severity: str = Field(..., pattern="^(low|medium|high|catastrophic)$")
    severity_score: Optional[float] = Field(None, ge=0, le=10)
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    epicenter: GeoPoint
    affected_radius_km: float = Field(5.0, ge=0.1, le=100)
    start_time: datetime

    model_config = {"json_schema_extra": {
        "example": {
            "disaster_type": "blackout",
            "severity": "high",
            "severity_score": 7.2,
            "title": "Northgate Grid Failure",
            "epicenter": {"lat": 40.7128, "lon": -74.0060},
            "affected_radius_km": 5.0,
            "start_time": "2025-03-15T02:30:00Z"
        }
    }}


class IncidentResponse(BaseModel):
    id: int
    incident_uid: str
    disaster_type: str
    severity: str
    status: str
    start_time: datetime
    affected_node_count: int
    estimated_recovery_hours: Optional[float]

    model_config = {"from_attributes": True}


class SystemStatusBreakdown(BaseModel):
    total: int
    failed: int
    recovering: int
    restored: int
    operational: int


class IncidentDetail(BaseModel):
    id: int
    incident_uid: str
    disaster_type: str
    severity: str
    severity_score: Optional[float]
    title: Optional[str]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    affected_districts: Optional[List[int]]
    affected_node_count: int
    estimated_recovery_hours: Optional[float]
    system_status: Optional[Dict[str, SystemStatusBreakdown]]
    cascade_predictions: Optional[Dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[IncidentResponse]

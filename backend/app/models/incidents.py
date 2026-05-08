from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, ARRAY, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base


class DisasterIncident(Base):
    __tablename__ = "disaster_incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_uid = Column(String(50), unique=True, index=True)
    disaster_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    severity_score = Column(Float)
    title = Column(String(200))
    description = Column(Text)
    affected_area = Column(Geometry("POLYGON", srid=4326))
    epicenter = Column(Geometry("POINT", srid=4326))
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime)
    status = Column(String(20), default="active", index=True)
    affected_districts = Column(ARRAY(Integer))
    affected_node_count = Column(Integer, default=0)
    estimated_recovery_hours = Column(Float)
    actual_recovery_hours = Column(Float)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    status_history = relationship("NodeStatusHistory", back_populates="incident")
    recovery_predictions = relationship("RecoveryPrediction", back_populates="incident")
    resilience_scores = relationship("ResilienceScore", back_populates="incident")
    simulation_runs = relationship("SimulationRun", back_populates="incident")


class NodeStatusHistory(Base):
    __tablename__ = "node_status_history"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey("disaster_incidents.id"), index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    status = Column(String(20), nullable=False)
    operational_pct = Column(Float, default=0.0)
    load_pct = Column(Float)
    repair_crew_assigned = Column(Boolean, default=False)
    repair_progress_pct = Column(Float, default=0.0)
    hours_since_failure = Column(Float, default=0.0)
    hours_to_restoration = Column(Float)
    recorded_by = Column(String(50), default="sensor")

    # Relationships
    node = relationship("InfrastructureNode", back_populates="status_history")
    incident = relationship("DisasterIncident", back_populates="status_history")


class RecoveryPrediction(Base):
    __tablename__ = "recovery_predictions"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey("disaster_incidents.id"), index=True)
    model_version = Column(String(20))
    predicted_at = Column(DateTime, server_default=func.now())
    hours_since_failure = Column(Float)
    predicted_restoration_hours = Column(Float)
    confidence_lower = Column(Float)
    confidence_upper = Column(Float)
    prediction_horizon_hours = Column(Integer, default=24)
    actual_restoration_hours = Column(Float)
    mae = Column(Float)

    # Relationships
    node = relationship("InfrastructureNode", back_populates="recovery_predictions")
    incident = relationship("DisasterIncident", back_populates="recovery_predictions")


class ResilienceScore(Base):
    __tablename__ = "resilience_scores"

    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False, index=True)
    incident_id = Column(Integer, ForeignKey("disaster_incidents.id"), index=True)
    computed_at = Column(DateTime, server_default=func.now())
    absorption_score = Column(Float)
    adaptation_score = Column(Float)
    restoration_score = Column(Float)
    composite_score = Column(Float, index=True)
    power_recovery_pct = Column(Float)
    transport_recovery_pct = Column(Float)
    telecom_recovery_pct = Column(Float)
    emergency_recovery_pct = Column(Float)
    mobility_recovery_pct = Column(Float)
    service_recovery_pct = Column(Float)
    hours_to_50pct_recovery = Column(Float)
    hours_to_90pct_recovery = Column(Float)

    # Relationships
    district = relationship("District", back_populates="resilience_scores")
    incident = relationship("DisasterIncident", back_populates="resilience_scores")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_uid = Column(String(50), unique=True, index=True)
    incident_id = Column(Integer, ForeignKey("disaster_incidents.id"), index=True)
    strategy = Column(String(50), nullable=False)
    n_monte_carlo = Column(Integer, default=100)
    resource_budget = Column(Float)
    status = Column(String(20), default="pending", index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    mean_recovery_hours = Column(Float)
    p10_recovery_hours = Column(Float)
    p90_recovery_hours = Column(Float)
    bottleneck_nodes = Column(ARRAY(Integer))
    result_json = Column(JSONB)
    created_by = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    incident = relationship("DisasterIncident", back_populates="simulation_runs")

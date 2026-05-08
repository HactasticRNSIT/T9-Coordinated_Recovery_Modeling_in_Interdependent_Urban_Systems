from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Date,
    ForeignKey, Text, ARRAY, func
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.core.database import Base


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(10), unique=True, nullable=False)
    population = Column(Integer, nullable=False)
    area_sqkm = Column(Float, nullable=False)
    geometry = Column(Geometry("POLYGON", srid=4326), nullable=False)
    urban_density = Column(Float)
    avg_income_level = Column(String(20))  # low / medium / high
    critical_infra_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    nodes = relationship("InfrastructureNode", back_populates="district")
    resilience_scores = relationship("ResilienceScore", back_populates="district")


class InfrastructureNode(Base):
    __tablename__ = "infrastructure_nodes"

    id = Column(Integer, primary_key=True, index=True)
    node_uid = Column(String(50), unique=True, nullable=False, index=True)
    system_type = Column(String(20), nullable=False, index=True)
    node_type = Column(String(50), nullable=False)
    name = Column(String(200))
    district_id = Column(Integer, ForeignKey("districts.id"), index=True)
    location = Column(Geometry("POINT", srid=4326), nullable=False)
    capacity = Column(Float)
    current_load = Column(Float)
    status = Column(String(20), default="operational", index=True)
    criticality_score = Column(Float, default=0.5)
    backup_available = Column(Boolean, default=False)
    install_year = Column(Integer)
    last_maintenance = Column(Date)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    # Relationships
    district = relationship("District", back_populates="nodes")
    outgoing_edges = relationship(
        "DependencyEdge",
        foreign_keys="DependencyEdge.source_node_id",
        back_populates="source_node"
    )
    incoming_edges = relationship(
        "DependencyEdge",
        foreign_keys="DependencyEdge.target_node_id",
        back_populates="target_node"
    )
    status_history = relationship("NodeStatusHistory", back_populates="node")
    recovery_predictions = relationship("RecoveryPrediction", back_populates="node")


class DependencyEdge(Base):
    __tablename__ = "dependency_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=False, index=True)
    target_node_id = Column(Integer, ForeignKey("infrastructure_nodes.id"), nullable=False, index=True)
    edge_type = Column(String(50), nullable=False)
    weight = Column(Float, nullable=False)
    is_critical = Column(Boolean, default=False)
    lag_hours = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    # Relationships
    source_node = relationship("InfrastructureNode", foreign_keys=[source_node_id], back_populates="outgoing_edges")
    target_node = relationship("InfrastructureNode", foreign_keys=[target_node_id], back_populates="incoming_edges")

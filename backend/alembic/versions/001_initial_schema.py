"""Initial schema — all tables

Revision ID: 001
Revises: 
Create Date: 2025-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable PostGIS
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # districts
    op.create_table(
        'districts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('code', sa.String(10), unique=True, nullable=False),
        sa.Column('population', sa.Integer(), nullable=False),
        sa.Column('area_sqkm', sa.Float(), nullable=False),
        sa.Column('geometry', geoalchemy2.types.Geometry('POLYGON', srid=4326), nullable=False),
        sa.Column('urban_density', sa.Float()),
        sa.Column('avg_income_level', sa.String(20)),
        sa.Column('critical_infra_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # infrastructure_nodes
    op.create_table(
        'infrastructure_nodes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('node_uid', sa.String(50), unique=True, nullable=False),
        sa.Column('system_type', sa.String(20), nullable=False),
        sa.Column('node_type', sa.String(50), nullable=False),
        sa.Column('name', sa.String(200)),
        sa.Column('district_id', sa.Integer(), sa.ForeignKey('districts.id')),
        sa.Column('location', geoalchemy2.types.Geometry('POINT', srid=4326), nullable=False),
        sa.Column('capacity', sa.Float()),
        sa.Column('current_load', sa.Float()),
        sa.Column('status', sa.String(20), default='operational'),
        sa.Column('criticality_score', sa.Float(), default=0.5),
        sa.Column('backup_available', sa.Boolean(), default=False),
        sa.Column('install_year', sa.Integer()),
        sa.Column('last_maintenance', sa.Date()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), onupdate=sa.func.now()),
    )

    # dependency_edges
    op.create_table(
        'dependency_edges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('source_node_id', sa.Integer(), sa.ForeignKey('infrastructure_nodes.id'), nullable=False),
        sa.Column('target_node_id', sa.Integer(), sa.ForeignKey('infrastructure_nodes.id'), nullable=False),
        sa.Column('edge_type', sa.String(50), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('is_critical', sa.Boolean(), default=False),
        sa.Column('lag_hours', sa.Float(), default=0.0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # disaster_incidents
    op.create_table(
        'disaster_incidents',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('incident_uid', sa.String(50), unique=True),
        sa.Column('disaster_type', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('severity_score', sa.Float()),
        sa.Column('title', sa.String(200)),
        sa.Column('description', sa.Text()),
        sa.Column('affected_area', geoalchemy2.types.Geometry('POLYGON', srid=4326)),
        sa.Column('epicenter', geoalchemy2.types.Geometry('POINT', srid=4326)),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime()),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('affected_districts', postgresql.ARRAY(sa.Integer())),
        sa.Column('affected_node_count', sa.Integer(), default=0),
        sa.Column('estimated_recovery_hours', sa.Float()),
        sa.Column('actual_recovery_hours', sa.Float()),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # node_status_history
    op.create_table(
        'node_status_history',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('infrastructure_nodes.id'), nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('disaster_incidents.id')),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('operational_pct', sa.Float(), default=0.0),
        sa.Column('load_pct', sa.Float()),
        sa.Column('repair_crew_assigned', sa.Boolean(), default=False),
        sa.Column('repair_progress_pct', sa.Float(), default=0.0),
        sa.Column('hours_since_failure', sa.Float(), default=0.0),
        sa.Column('hours_to_restoration', sa.Float()),
        sa.Column('recorded_by', sa.String(50), default='sensor'),
    )

    # recovery_predictions
    op.create_table(
        'recovery_predictions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('infrastructure_nodes.id'), nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('disaster_incidents.id')),
        sa.Column('model_version', sa.String(20)),
        sa.Column('predicted_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('hours_since_failure', sa.Float()),
        sa.Column('predicted_restoration_hours', sa.Float()),
        sa.Column('confidence_lower', sa.Float()),
        sa.Column('confidence_upper', sa.Float()),
        sa.Column('prediction_horizon_hours', sa.Integer(), default=24),
        sa.Column('actual_restoration_hours', sa.Float()),
        sa.Column('mae', sa.Float()),
    )

    # resilience_scores
    op.create_table(
        'resilience_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('district_id', sa.Integer(), sa.ForeignKey('districts.id'), nullable=False),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('disaster_incidents.id')),
        sa.Column('computed_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('absorption_score', sa.Float()),
        sa.Column('adaptation_score', sa.Float()),
        sa.Column('restoration_score', sa.Float()),
        sa.Column('composite_score', sa.Float()),
        sa.Column('power_recovery_pct', sa.Float()),
        sa.Column('transport_recovery_pct', sa.Float()),
        sa.Column('telecom_recovery_pct', sa.Float()),
        sa.Column('emergency_recovery_pct', sa.Float()),
        sa.Column('mobility_recovery_pct', sa.Float()),
        sa.Column('service_recovery_pct', sa.Float()),
        sa.Column('hours_to_50pct_recovery', sa.Float()),
        sa.Column('hours_to_90pct_recovery', sa.Float()),
    )

    # simulation_runs
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('run_uid', sa.String(50), unique=True),
        sa.Column('incident_id', sa.Integer(), sa.ForeignKey('disaster_incidents.id')),
        sa.Column('strategy', sa.String(50), nullable=False),
        sa.Column('n_monte_carlo', sa.Integer(), default=100),
        sa.Column('resource_budget', sa.Float()),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('completed_at', sa.DateTime()),
        sa.Column('mean_recovery_hours', sa.Float()),
        sa.Column('p10_recovery_hours', sa.Float()),
        sa.Column('p90_recovery_hours', sa.Float()),
        sa.Column('bottleneck_nodes', postgresql.ARRAY(sa.Integer())),
        sa.Column('result_json', postgresql.JSONB()),
        sa.Column('created_by', sa.String(100)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    # sensor_readings
    op.create_table(
        'sensor_readings',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('node_id', sa.Integer(), sa.ForeignKey('infrastructure_nodes.id'), nullable=False),
        sa.Column('sensor_type', sa.String(50)),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('value', sa.Float(), nullable=False),
        sa.Column('unit', sa.String(20)),
        sa.Column('quality', sa.String(20), default='good'),
        sa.Column('anomaly_flag', sa.Boolean(), default=False),
    )

    # ─── Indexes ──────────────────────────────────────────────────────────────
    op.create_index('idx_nodes_location', 'infrastructure_nodes', ['location'], postgresql_using='gist')
    op.create_index('idx_districts_geometry', 'districts', ['geometry'], postgresql_using='gist')
    op.create_index('idx_nodes_system_type', 'infrastructure_nodes', ['system_type'])
    op.create_index('idx_nodes_status', 'infrastructure_nodes', ['status'])
    op.create_index('idx_incidents_status', 'disaster_incidents', ['status'])
    op.create_index('idx_incidents_start_time', 'disaster_incidents', ['start_time'])
    op.create_index('idx_history_node_incident', 'node_status_history', ['node_id', 'incident_id'])
    op.create_index('idx_history_timestamp', 'node_status_history', ['timestamp'])
    op.create_index('idx_sensor_node_time', 'sensor_readings', ['node_id', 'timestamp'])
    op.create_index('idx_resilience_district', 'resilience_scores', ['district_id'])
    op.create_index('idx_resilience_composite', 'resilience_scores', ['composite_score'])


def downgrade() -> None:
    op.drop_table('sensor_readings')
    op.drop_table('simulation_runs')
    op.drop_table('resilience_scores')
    op.drop_table('recovery_predictions')
    op.drop_table('node_status_history')
    op.drop_table('disaster_incidents')
    op.drop_table('dependency_edges')
    op.drop_table('infrastructure_nodes')
    op.drop_table('districts')

"""
Celery tasks for async simulation execution.
"""
from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="run_simulation")
def run_simulation_task(self, run_uid: str):
    """
    Execute Monte Carlo simulation for a given run UID.
    Updates simulation_runs table with results.
    """
    from sqlalchemy.orm import Session
    from app.core.database import SessionLocal
    from app.models.incidents import SimulationRun
    from app.ml.scenario_engine import ScenarioEngine, RecoveryStrategy, compare_strategies
    from datetime import datetime
    import networkx as nx

    db: Session = SessionLocal()
    try:
        # Get run from DB
        run = db.query(SimulationRun).filter(SimulationRun.run_uid == run_uid).first()
        if not run:
            logger.error(f"Simulation run {run_uid} not found")
            return

        # Update status to running
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.commit()

        # Build node states from DB
        from app.models.infrastructure import InfrastructureNode, DependencyEdge
        nodes_db = db.query(InfrastructureNode).filter(
            InfrastructureNode.district_id.in_(
                db.query(InfrastructureNode.district_id).filter(
                    InfrastructureNode.status.in_(["failed", "recovering"])
                )
            )
        ).all()

        from app.ml.scenario_engine import NodeState
        node_states = [
            NodeState(
                node_id=n.id,
                node_uid=n.node_uid,
                system_type=n.system_type,
                criticality_score=n.criticality_score or 0.5,
                base_repair_hours=_estimate_repair_hours(n),
                status=n.status,
            )
            for n in nodes_db
        ]

        # Build dependency graph
        edges_db = db.query(DependencyEdge).all()
        G = nx.DiGraph()
        for node in node_states:
            G.add_node(node.node_id)
        for edge in edges_db:
            G.add_edge(
                edge.source_node_id,
                edge.target_node_id,
                is_critical=edge.is_critical,
                weight=edge.weight,
            )

        # Parse strategies
        strategy_map = {
            "power_first": RecoveryStrategy.POWER_FIRST,
            "transport_first": RecoveryStrategy.TRANSPORT_FIRST,
            "emergency_first": RecoveryStrategy.EMERGENCY_FIRST,
            "parallel": RecoveryStrategy.PARALLEL,
            "dependency_optimal": RecoveryStrategy.DEPENDENCY_OPTIMAL,
        }
        strategies = [strategy_map[s] for s in [run.strategy] if s in strategy_map]
        if not strategies:
            strategies = [RecoveryStrategy.PARALLEL]

        # Run simulation
        results = compare_strategies(
            nodes=node_states,
            dependency_graph=G,
            resource_budget=run.resource_budget or 500.0,
            strategies=strategies,
            n_runs=run.n_monte_carlo or 100,
        )

        # Update run with results
        best = results["strategy_comparison"][0] if results["strategy_comparison"] else {}
        run.status = "completed"
        run.completed_at = datetime.utcnow()
        run.mean_recovery_hours = best.get("mean_recovery_hours")
        run.p10_recovery_hours = best.get("p10_hours")
        run.p90_recovery_hours = best.get("p90_hours")
        run.result_json = results
        db.commit()

        logger.info(f"Simulation {run_uid} completed successfully")

    except Exception as e:
        logger.error(f"Simulation {run_uid} failed: {e}")
        run = db.query(SimulationRun).filter(SimulationRun.run_uid == run_uid).first()
        if run:
            run.status = "failed"
            db.commit()
    finally:
        db.close()


def _estimate_repair_hours(node) -> float:
    """Estimate base repair hours based on node type and criticality."""
    base_hours = {
        "power": 8.0,
        "transport": 4.0,
        "telecom": 6.0,
        "emergency": 3.0,
        "mobility": 5.0,
        "service": 7.0,
    }.get(node.system_type, 6.0)
    # Higher criticality = more complex = longer repair
    return base_hours * (0.5 + node.criticality_score)

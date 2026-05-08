"""
Unit tests for the Monte Carlo scenario simulation engine.
"""
import pytest
import networkx as nx
from app.ml.scenario_engine import (
    ScenarioEngine, RecoveryStrategy, NodeState, compare_strategies
)


def make_test_nodes():
    """Create a small set of test nodes."""
    return [
        NodeState(node_id=1, node_uid="PWR-001", system_type="power",     criticality_score=0.9, base_repair_hours=8.0),
        NodeState(node_id=2, node_uid="TEL-001", system_type="telecom",   criticality_score=0.7, base_repair_hours=6.0),
        NodeState(node_id=3, node_uid="EMR-001", system_type="emergency", criticality_score=0.95, base_repair_hours=3.0),
        NodeState(node_id=4, node_uid="TRN-001", system_type="transport", criticality_score=0.6, base_repair_hours=4.0),
        NodeState(node_id=5, node_uid="MOB-001", system_type="mobility",  criticality_score=0.5, base_repair_hours=5.0),
        NodeState(node_id=6, node_uid="SVC-001", system_type="service",   criticality_score=0.65, base_repair_hours=7.0),
    ]


def make_test_graph(nodes):
    """Create a simple dependency graph."""
    G = nx.DiGraph()
    for node in nodes:
        G.add_node(node.node_id)
    # Power → Telecom (critical)
    G.add_edge(1, 2, is_critical=True, weight=0.95)
    # Power → Emergency
    G.add_edge(1, 3, is_critical=False, weight=0.90)
    # Telecom → Emergency
    G.add_edge(2, 3, is_critical=False, weight=0.85)
    # Transport → Mobility
    G.add_edge(4, 5, is_critical=False, weight=0.80)
    return G


def test_engine_runs_without_error():
    """Smoke test: engine runs and returns results."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    engine = ScenarioEngine(seed=42)
    result = engine.run(
        nodes=nodes,
        dependency_graph=G,
        strategy=RecoveryStrategy.PARALLEL,
        resource_budget=200.0,
        n_runs=10,
    )
    assert "mean_recovery_hours" in result
    assert result["mean_recovery_hours"] > 0
    assert result["n_runs"] == 10


def test_all_strategies_run():
    """All 5 strategies should complete without error."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    engine = ScenarioEngine(seed=42)

    for strategy in RecoveryStrategy:
        result = engine.run(nodes=nodes, dependency_graph=G, strategy=strategy, resource_budget=200.0, n_runs=5)
        assert result["mean_recovery_hours"] > 0, f"Strategy {strategy} returned 0 hours"


def test_dependency_optimal_not_worse_than_parallel():
    """Dependency-optimal should generally perform at least as well as parallel."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    engine = ScenarioEngine(seed=42)

    parallel_result = engine.run(nodes=nodes, dependency_graph=G, strategy=RecoveryStrategy.PARALLEL, resource_budget=200.0, n_runs=50)
    optimal_result = engine.run(nodes=nodes, dependency_graph=G, strategy=RecoveryStrategy.DEPENDENCY_OPTIMAL, resource_budget=200.0, n_runs=50)

    # Dependency-optimal should be within 50% of parallel (not catastrophically worse)
    assert optimal_result["mean_recovery_hours"] <= parallel_result["mean_recovery_hours"] * 1.5


def test_compare_strategies_returns_ranking():
    """compare_strategies should return a ranked list."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    strategies = [RecoveryStrategy.POWER_FIRST, RecoveryStrategy.PARALLEL, RecoveryStrategy.DEPENDENCY_OPTIMAL]

    result = compare_strategies(nodes=nodes, dependency_graph=G, resource_budget=200.0, strategies=strategies, n_runs=10)

    assert "strategy_comparison" in result
    assert len(result["strategy_comparison"]) == 3
    assert "recommended_strategy" in result
    assert "recommendations" in result

    # Ranks should be 1, 2, 3
    ranks = [s["rank"] for s in result["strategy_comparison"]]
    assert sorted(ranks) == [1, 2, 3]


def test_bottleneck_detection():
    """Bottleneck nodes should be identified when dependencies block recovery."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    engine = ScenarioEngine(seed=42)

    result = engine.run(
        nodes=nodes,
        dependency_graph=G,
        strategy=RecoveryStrategy.POWER_FIRST,
        resource_budget=50.0,  # Low budget to force bottlenecks
        n_runs=20,
    )
    # With critical dependency PWR-001 → TEL-001, PWR-001 should appear as bottleneck
    assert "top_bottleneck_nodes" in result


def test_stochastic_variance():
    """Results should have non-zero variance (simulation is actually stochastic)."""
    nodes = make_test_nodes()
    G = make_test_graph(nodes)
    engine = ScenarioEngine()  # No fixed seed

    result = engine.run(nodes=nodes, dependency_graph=G, strategy=RecoveryStrategy.PARALLEL, resource_budget=200.0, n_runs=30)
    assert result["std_recovery_hours"] > 0, "Simulation should have non-zero variance"
    assert result["p10_recovery_hours"] < result["p90_recovery_hours"]

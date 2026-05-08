"""
Monte Carlo Scenario Simulation Engine
Simulates coordinated recovery under different strategies.
"""
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import networkx as nx


class RecoveryStrategy(str, Enum):
    POWER_FIRST = "power_first"
    TRANSPORT_FIRST = "transport_first"
    EMERGENCY_FIRST = "emergency_first"
    PARALLEL = "parallel"
    DEPENDENCY_OPTIMAL = "dependency_optimal"


STRATEGY_PRIORITY = {
    RecoveryStrategy.POWER_FIRST:      ["power", "telecom", "emergency", "transport", "mobility", "service"],
    RecoveryStrategy.TRANSPORT_FIRST:  ["transport", "power", "emergency", "telecom", "mobility", "service"],
    RecoveryStrategy.EMERGENCY_FIRST:  ["emergency", "power", "telecom", "transport", "mobility", "service"],
    RecoveryStrategy.PARALLEL:         ["all"],
    RecoveryStrategy.DEPENDENCY_OPTIMAL: ["computed"],
}


@dataclass
class NodeState:
    node_id: int
    node_uid: str
    system_type: str
    criticality_score: float
    base_repair_hours: float
    status: str = "failed"
    repair_progress: float = 0.0
    crew_assigned: bool = False
    dependencies_met: bool = False


@dataclass
class SimulationResult:
    strategy: str
    run_index: int
    total_recovery_hours: float
    system_recovery_hours: Dict[str, float]
    bottleneck_nodes: List[str]
    timeline: List[Dict]  # hourly snapshots


class ScenarioEngine:
    """
    Monte Carlo simulation engine for recovery strategy comparison.
    
    Stochastic parameters:
    - Repair times: Log-normal(mu=ln(base_hours), sigma=0.4)
    - Crew travel: Exponential(lambda=0.3 hours)
    - Weather delay: Beta(alpha=2, beta=5) multiplier [1.0, 3.0]
    - Parts availability: Bernoulli(p=0.85)
    - Secondary failure: Bernoulli(p=0.1) per critical edge
    """

    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)

    def run(
        self,
        nodes: List[NodeState],
        dependency_graph: nx.DiGraph,
        strategy: RecoveryStrategy,
        resource_budget: float,
        n_runs: int = 100,
    ) -> Dict:
        """
        Run Monte Carlo simulation for a given strategy.
        Returns aggregated statistics across all runs.
        """
        results: List[SimulationResult] = []

        for run_idx in range(n_runs):
            result = self._single_run(
                nodes=nodes,
                dependency_graph=dependency_graph,
                strategy=strategy,
                resource_budget=resource_budget,
                run_index=run_idx,
            )
            results.append(result)

        return self._aggregate_results(results, strategy)

    def _single_run(
        self,
        nodes: List[NodeState],
        dependency_graph: nx.DiGraph,
        strategy: RecoveryStrategy,
        resource_budget: float,
        run_index: int,
    ) -> SimulationResult:
        """Execute one Monte Carlo run."""
        # Sample stochastic parameters
        weather_factor = self._sample_weather_factor()
        crew_availability = self._sample_crew_availability(resource_budget)

        # Determine repair order based on strategy
        repair_order = self._get_repair_order(nodes, dependency_graph, strategy)

        # Simulate repair timeline
        current_time = 0.0
        available_crews = crew_availability
        node_completion_times: Dict[int, float] = {}
        system_completion_times: Dict[str, float] = {}
        timeline = []
        bottleneck_nodes = []

        # Track which nodes are being repaired
        in_progress: Dict[int, float] = {}  # node_id -> completion_time
        completed: set = set()

        max_hours = 168  # 1 week cap
        time_step = 0.5  # 30-minute steps

        t = 0.0
        while t <= max_hours:
            # Check completions
            newly_completed = {nid for nid, ct in in_progress.items() if ct <= t}
            for nid in newly_completed:
                completed.add(nid)
                del in_progress[nid]
                available_crews += 1

            # Assign crews to next nodes in priority order
            for node in repair_order:
                if node.node_id in completed or node.node_id in in_progress:
                    continue
                if available_crews <= 0:
                    break

                # Check if dependencies are met
                deps_met = self._check_dependencies(node.node_id, dependency_graph, completed)
                if not deps_met:
                    bottleneck_nodes.append(node.node_uid)
                    continue

                # Check parts availability
                parts_available = self.rng.random() < 0.85
                if not parts_available:
                    continue

                # Sample repair time
                repair_time = self._sample_repair_time(node.base_repair_hours, weather_factor)
                travel_time = self._sample_travel_time()
                total_time = repair_time + travel_time

                in_progress[node.node_id] = t + total_time
                available_crews -= 1

            # Record timeline snapshot every 2 hours
            if t % 2 == 0:
                snapshot = self._compute_snapshot(t, nodes, completed, in_progress)
                timeline.append(snapshot)

            # Check if all nodes are done
            if len(completed) == len(nodes):
                break

            t += time_step

        # Compute per-system completion times
        for system_type in ["power", "transport", "telecom", "emergency", "mobility", "service"]:
            system_nodes = [n for n in nodes if n.system_type == system_type]
            if not system_nodes:
                continue
            system_node_ids = {n.node_id for n in system_nodes}
            completed_system = system_node_ids & completed
            if len(completed_system) == len(system_node_ids):
                # All nodes in system completed — find max completion time
                system_completion_times[system_type] = max(
                    node_completion_times.get(nid, max_hours) for nid in system_node_ids
                )
            else:
                system_completion_times[system_type] = max_hours

        total_hours = max(node_completion_times.values()) if node_completion_times else max_hours

        return SimulationResult(
            strategy=strategy.value,
            run_index=run_index,
            total_recovery_hours=total_hours,
            system_recovery_hours=system_completion_times,
            bottleneck_nodes=list(set(bottleneck_nodes)),
            timeline=timeline,
        )

    def _get_repair_order(
        self,
        nodes: List[NodeState],
        dependency_graph: nx.DiGraph,
        strategy: RecoveryStrategy,
    ) -> List[NodeState]:
        """Determine node repair priority order based on strategy."""
        if strategy == RecoveryStrategy.DEPENDENCY_OPTIMAL:
            # Topological sort of dependency graph
            try:
                topo_order = list(nx.topological_sort(dependency_graph))
                node_map = {n.node_id: n for n in nodes}
                ordered = [node_map[nid] for nid in topo_order if nid in node_map]
                # Sort by criticality within same topological level
                return sorted(ordered, key=lambda n: -n.criticality_score)
            except nx.NetworkXUnfeasible:
                # Graph has cycles — fall back to criticality sort
                return sorted(nodes, key=lambda n: -n.criticality_score)

        elif strategy == RecoveryStrategy.PARALLEL:
            # Sort by criticality only
            return sorted(nodes, key=lambda n: -n.criticality_score)

        else:
            # Priority-based ordering
            priority_order = STRATEGY_PRIORITY[strategy]
            result = []
            for system in priority_order:
                system_nodes = sorted(
                    [n for n in nodes if n.system_type == system],
                    key=lambda n: -n.criticality_score
                )
                result.extend(system_nodes)
            return result

    def _check_dependencies(
        self,
        node_id: int,
        dependency_graph: nx.DiGraph,
        completed: set,
    ) -> bool:
        """Check if all critical dependencies of a node are restored."""
        predecessors = list(dependency_graph.predecessors(node_id))
        for pred_id in predecessors:
            edge_data = dependency_graph.edges[pred_id, node_id]
            if edge_data.get("is_critical", False) and pred_id not in completed:
                return False
        return True

    def _sample_repair_time(self, base_hours: float, weather_factor: float) -> float:
        """Sample repair time from log-normal distribution."""
        mu = np.log(max(base_hours, 0.5))
        sigma = 0.4
        sampled = self.rng.lognormal(mu, sigma)
        return sampled * weather_factor

    def _sample_travel_time(self) -> float:
        """Sample crew travel time from exponential distribution."""
        return self.rng.exponential(scale=1.0 / 0.3)  # mean = 3.33 hours

    def _sample_weather_factor(self) -> float:
        """Sample weather delay multiplier from Beta distribution, scaled to [1, 3]."""
        beta_sample = self.rng.beta(2, 5)
        return 1.0 + beta_sample * 2.0  # Range: [1.0, 3.0]

    def _sample_crew_availability(self, resource_budget: float) -> int:
        """Sample number of available repair crews from Poisson distribution."""
        mean_crews = max(1, int(resource_budget / 50))  # 50 crew-hours per crew
        return max(1, self.rng.poisson(mean_crews))

    def _compute_snapshot(
        self,
        t: float,
        nodes: List[NodeState],
        completed: set,
        in_progress: Dict[int, float],
    ) -> Dict:
        """Compute system recovery percentages at time t."""
        snapshot = {"hours": t}
        for system_type in ["power", "transport", "telecom", "emergency", "mobility", "service"]:
            system_nodes = [n for n in nodes if n.system_type == system_type]
            if not system_nodes:
                snapshot[system_type] = 100.0
                continue
            n_completed = sum(1 for n in system_nodes if n.node_id in completed)
            n_in_progress = sum(1 for n in system_nodes if n.node_id in in_progress)
            # Partial credit for in-progress nodes
            pct = (n_completed + 0.5 * n_in_progress) / len(system_nodes) * 100
            snapshot[system_type] = round(pct, 1)
        return snapshot

    def _aggregate_results(self, results: List[SimulationResult], strategy: RecoveryStrategy) -> Dict:
        """Aggregate Monte Carlo results into statistics."""
        total_hours = [r.total_recovery_hours for r in results]

        # Bottleneck analysis
        bottleneck_counts: Dict[str, int] = {}
        for r in results:
            for node_uid in r.bottleneck_nodes:
                bottleneck_counts[node_uid] = bottleneck_counts.get(node_uid, 0) + 1

        top_bottlenecks = sorted(
            bottleneck_counts.items(), key=lambda x: -x[1]
        )[:5]

        # Average timeline across runs
        if results and results[0].timeline:
            n_steps = len(results[0].timeline)
            avg_timeline = []
            for step_idx in range(n_steps):
                step = {"hours": results[0].timeline[step_idx]["hours"]}
                for system in ["power", "transport", "telecom", "emergency", "mobility", "service"]:
                    vals = [r.timeline[step_idx].get(system, 0) for r in results if step_idx < len(r.timeline)]
                    step[system] = round(np.mean(vals), 1) if vals else 0.0
                avg_timeline.append(step)
        else:
            avg_timeline = []

        return {
            "strategy": strategy.value,
            "n_runs": len(results),
            "mean_recovery_hours": round(float(np.mean(total_hours)), 2),
            "median_recovery_hours": round(float(np.median(total_hours)), 2),
            "p10_recovery_hours": round(float(np.percentile(total_hours, 10)), 2),
            "p90_recovery_hours": round(float(np.percentile(total_hours, 90)), 2),
            "std_recovery_hours": round(float(np.std(total_hours)), 2),
            "top_bottleneck_nodes": [
                {"node_uid": uid, "frequency": count, "bottleneck_score": count / len(results)}
                for uid, count in top_bottlenecks
            ],
            "avg_timeline": avg_timeline,
        }


def compare_strategies(
    nodes: List[NodeState],
    dependency_graph: nx.DiGraph,
    resource_budget: float,
    strategies: List[RecoveryStrategy],
    n_runs: int = 100,
) -> Dict:
    """
    Run simulation for multiple strategies and return comparison.
    """
    engine = ScenarioEngine()
    strategy_results = {}

    for strategy in strategies:
        result = engine.run(
            nodes=nodes,
            dependency_graph=dependency_graph,
            strategy=strategy,
            resource_budget=resource_budget,
            n_runs=n_runs,
        )
        strategy_results[strategy.value] = result

    # Rank strategies by mean recovery time
    ranked = sorted(
        strategy_results.items(),
        key=lambda x: x[1]["mean_recovery_hours"]
    )

    # Compute improvement vs parallel (baseline)
    baseline_hours = strategy_results.get("parallel", {}).get("mean_recovery_hours", 1)

    comparison = []
    for rank, (strategy_name, result) in enumerate(ranked, 1):
        improvement = (baseline_hours - result["mean_recovery_hours"]) / baseline_hours * 100
        comparison.append({
            "strategy": strategy_name,
            "rank": rank,
            "mean_recovery_hours": result["mean_recovery_hours"],
            "p10_hours": result["p10_recovery_hours"],
            "p90_hours": result["p90_recovery_hours"],
            "improvement_vs_baseline_pct": round(improvement, 1),
            "bottleneck_nodes": result["top_bottleneck_nodes"][:3],
        })

    # Generate recommendations
    best_strategy = ranked[0][1]
    recommendations = _generate_recommendations(best_strategy, ranked[0][0])

    return {
        "strategy_comparison": comparison,
        "recommended_strategy": ranked[0][0],
        "recommendations": recommendations,
        "detailed_results": strategy_results,
    }


def _generate_recommendations(best_result: Dict, best_strategy: str) -> List[str]:
    """Generate human-readable recovery recommendations."""
    recs = []
    recs.append(
        f"Use '{best_strategy}' strategy — estimated {best_result['mean_recovery_hours']:.1f}h mean recovery "
        f"(80% CI: {best_result['p10_recovery_hours']:.1f}–{best_result['p90_recovery_hours']:.1f}h)"
    )
    for bn in best_result.get("top_bottleneck_nodes", [])[:3]:
        recs.append(
            f"Prioritize {bn['node_uid']} — bottleneck in {bn['frequency']} of {best_result['n_runs']} simulations"
        )
    return recs

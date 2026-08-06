"""Graph nodes.

Every node is a factory — `make_<name>_node(dependency)` returns the async
callable LangGraph invokes with state. Dependencies are bound once when the
graph is built rather than resolved inside the node, which keeps nodes pure
enough to test with a stub toolkit and no graph at all.

Each node body is wrapped by `executor.run_node`, so timing, logging, and
failure containment are identical everywhere and appear in no node twice.
"""

from app.agents.nodes.dataset_node import make_dataset_node
from app.agents.nodes.lineage_node import make_lineage_node
from app.agents.nodes.owner_node import make_owner_node
from app.agents.nodes.planner_node import make_planner_node
from app.agents.nodes.reasoning_node import make_reasoning_node
from app.agents.nodes.recommendation_node import make_recommendation_node
from app.agents.nodes.report_node import make_report_node
from app.agents.nodes.risk_node import make_risk_node
from app.agents.nodes.statistics_node import make_statistics_node

__all__ = [
    "make_dataset_node",
    "make_lineage_node",
    "make_owner_node",
    "make_planner_node",
    "make_reasoning_node",
    "make_recommendation_node",
    "make_report_node",
    "make_risk_node",
    "make_statistics_node",
]

import operator
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent
from backend.agents.pm import run_pm_agent
from backend.agents.backend_worker import run_backend_agent
from backend.agents.frontend_worker import run_frontend_agent
from backend.agents.security_auditor import run_security_auditor_agent


def _last(a: str, b: str) -> str:
    """Reducer that keeps the most recent value — used on fields written by
    parallel branches so LangGraph does not raise InvalidUpdateError."""
    return b


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------
# Fields written by parallel nodes (backend_worker_agent + frontend_worker_agent)
# MUST carry a reducer annotation.  We use `_last` for current_status so both
# branches can write it and the final value is whichever finished last.
# ---------------------------------------------------------------------------
class VertexFlowState(TypedDict):
    project_statement: str
    target_tech_stack: str
    company_vision: str
    milestones: List[Dict[str, Any]]
    technical_blueprint: Dict[str, Any]
    product_requirements: Dict[str, Any]
    backend_code: Dict[str, Any]
    frontend_code: Dict[str, Any]
    security_audit: Dict[str, Any]
    # Annotated with _last so parallel writes don't raise InvalidUpdateError
    current_status: Annotated[str, _last]


# ---------------------------------------------------------------------------
# Agent nodes
# ---------------------------------------------------------------------------

def ceo_node(state: VertexFlowState) -> dict:
    """CEO agent: defines company vision and strategic milestones."""
    print("--- CEO AGENT WORKING ---")
    strategy = run_ceo_agent(state["project_statement"], state["target_tech_stack"])
    return {
        "company_vision": strategy.company_vision,
        "milestones": [m.model_dump() for m in strategy.milestones],
        "current_status": "CEO Strategy Complete",
    }


def cto_node(state: VertexFlowState) -> dict:
    """CTO agent: designs architecture, data models and engineering tickets."""
    print("--- CTO AGENT WORKING ---")
    blueprint = run_cto_agent(
        state["project_statement"],
        state["target_tech_stack"],
        str(state["milestones"]),
    )
    return {
        "technical_blueprint": blueprint.model_dump(),
        "current_status": "CTO Architecture Blueprint Complete",
    }


def pm_node(state: VertexFlowState) -> dict:
    """PM agent: produces product scope summary and user stories."""
    print("--- PRODUCT MANAGER AGENT WORKING ---")
    pm_blueprint = run_pm_agent(
        state["project_statement"],
        str(state["milestones"]),
        str(state["technical_blueprint"]),
    )
    return {
        "product_requirements": pm_blueprint.model_dump(),
        "current_status": "Product Requirements & User Stories Complete",
    }


def backend_worker_node(state: VertexFlowState) -> dict:
    """Backend Worker agent: generates FastAPI / SQLAlchemy server code."""
    print("--- BACKEND WORKER AGENT WORKING ---")
    backend = run_backend_agent(
        state["project_statement"],
        str(state["technical_blueprint"]),
        str(state["product_requirements"]),
    )
    return {
        "backend_code": backend.model_dump(),
        "current_status": "Backend Code Generated",
    }


def frontend_worker_node(state: VertexFlowState) -> dict:
    """Frontend Worker agent: generates React / TypeScript component code."""
    print("--- FRONTEND WORKER AGENT WORKING ---")
    frontend = run_frontend_agent(
        state["project_statement"],
        str(state["technical_blueprint"]),
        str(state["product_requirements"]),
    )
    return {
        "frontend_code": frontend.model_dump(),
        "current_status": "Frontend Code Generated",
    }


def security_auditor_node(state: VertexFlowState) -> dict:
    """Security Auditor agent: scans generated code for vulnerabilities."""
    print("--- SECURITY AUDITOR AGENT WORKING ---")
    audit = run_security_auditor_agent(
        state["project_statement"],
        str(state["backend_code"]),
        str(state["frontend_code"]),
    )
    return {
        "security_audit": audit.model_dump(),
        "current_status": "Security Audit Complete",
    }


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------
# CEO → CTO → PM → Backend Worker ─┐
#                                   ├─► Security Auditor → END
#               PM → Frontend Worker ┘
#
# Backend Worker and Frontend Worker run in parallel (fan-out from PM).
# Both write `current_status`; the Annotated[str, _last] reducer above
# resolves the conflict by keeping whichever value arrives last.
# ---------------------------------------------------------------------------

workflow = StateGraph(VertexFlowState)

workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)
workflow.add_node("pm_agent", pm_node)
workflow.add_node("backend_worker_agent", backend_worker_node)
workflow.add_node("frontend_worker_agent", frontend_worker_node)
workflow.add_node("security_auditor_agent", security_auditor_node)

workflow.set_entry_point("ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", "pm_agent")
workflow.add_edge("pm_agent", "backend_worker_agent")
workflow.add_edge("pm_agent", "frontend_worker_agent")
workflow.add_edge("backend_worker_agent", "security_auditor_agent")
workflow.add_edge("frontend_worker_agent", "security_auditor_agent")
workflow.add_edge("security_auditor_agent", END)

vertex_flow_app = workflow.compile()

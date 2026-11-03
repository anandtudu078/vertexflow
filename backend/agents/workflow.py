from typing import List, Dict, Any
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent
from backend.agents.pm import run_pm_agent
from backend.agents.backend_worker import run_backend_agent
from backend.agents.frontend_worker import run_frontend_agent
from backend.agents.security_auditor import run_security_auditor_agent


# Define the shared state structure for the full agent workflow
class VertexFlowState(BaseModel):
    project_statement: str
    target_tech_stack: str
    company_vision: str = ""
    milestones: List[Dict[str, Any]] = []
    technical_blueprint: Dict[str, Any] = {}
    product_requirements: Dict[str, Any] = {}
    backend_code: Dict[str, Any] = {}
    frontend_code: Dict[str, Any] = {}
    security_audit: Dict[str, Any] = {}
    current_status: str = "Initialized"


def ceo_node(state: VertexFlowState) -> dict:
    """Executes the CEO agent: defines vision and strategic milestones."""
    print("--- CEO AGENT WORKING ---")
    strategy = run_ceo_agent(state.project_statement, state.target_tech_stack)
    return {
        "company_vision": strategy.company_vision,
        "milestones": [m.model_dump() for m in strategy.milestones],
        "current_status": "CEO Strategy Complete",
    }


def cto_node(state: VertexFlowState) -> dict:
    """Executes the CTO agent: designs architecture, models and task tickets."""
    print("--- CTO AGENT WORKING ---")
    milestones_str = str(state.milestones)
    blueprint = run_cto_agent(state.project_statement, state.target_tech_stack, milestones_str)
    return {
        "technical_blueprint": blueprint.model_dump(),
        "current_status": "CTO Architecture Blueprint Complete",
    }


def pm_node(state: VertexFlowState) -> dict:
    """Executes the PM agent: produces product scope and user stories."""
    print("--- PRODUCT MANAGER AGENT WORKING ---")
    milestones_str = str(state.milestones)
    blueprint_str = str(state.technical_blueprint)
    pm_blueprint = run_pm_agent(state.project_statement, milestones_str, blueprint_str)
    return {
        "product_requirements": pm_blueprint.model_dump(),
        "current_status": "Product Requirements & User Stories Complete",
    }


def backend_worker_node(state: VertexFlowState) -> dict:
    """Executes the Backend Worker agent: generates FastAPI/SQLAlchemy code."""
    print("--- BACKEND WORKER AGENT WORKING ---")
    blueprint_str = str(state.technical_blueprint)
    pm_str = str(state.product_requirements)
    backend = run_backend_agent(state.project_statement, blueprint_str, pm_str)
    return {
        "backend_code": backend.model_dump(),
        "current_status": "Backend Code Generated",
    }


def frontend_worker_node(state: VertexFlowState) -> dict:
    """Executes the Frontend Worker agent: generates React/TypeScript components."""
    print("--- FRONTEND WORKER AGENT WORKING ---")
    blueprint_str = str(state.technical_blueprint)
    pm_str = str(state.product_requirements)
    frontend = run_frontend_agent(state.project_statement, blueprint_str, pm_str)
    return {
        "frontend_code": frontend.model_dump(),
        "current_status": "Frontend Code Generated",
    }


def security_auditor_node(state: VertexFlowState) -> dict:
    """Executes the Security Auditor agent: audits backend and frontend code."""
    print("--- SECURITY AUDITOR AGENT WORKING ---")
    backend_str = str(state.backend_code)
    frontend_str = str(state.frontend_code)
    audit = run_security_auditor_agent(state.project_statement, backend_str, frontend_str)
    return {
        "security_audit": audit.model_dump(),
        "current_status": "Security Audit Complete",
    }


# Build the LangGraph workflow
workflow = StateGraph(VertexFlowState)

# Register all agent nodes
workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)
workflow.add_node("pm_agent", pm_node)
workflow.add_node("backend_worker_agent", backend_worker_node)
workflow.add_node("frontend_worker_agent", frontend_worker_node)
workflow.add_node("security_auditor_agent", security_auditor_node)

# Execution flow:
# CEO → CTO → PM → Backend Worker ─┐
#                                   ├─► Security Auditor → END
#               PM → Frontend Worker ┘
workflow.set_entry_point("ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", "pm_agent")
workflow.add_edge("pm_agent", "backend_worker_agent")
workflow.add_edge("pm_agent", "frontend_worker_agent")
workflow.add_edge("backend_worker_agent", "security_auditor_agent")
workflow.add_edge("frontend_worker_agent", "security_auditor_agent")
workflow.add_edge("security_auditor_agent", END)

# Compile the graph into an executable app
vertex_flow_app = workflow.compile()

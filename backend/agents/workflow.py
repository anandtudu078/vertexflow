import uuid
import operator
from typing import Annotated, List, Dict, Any, Optional
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent
from backend.agents.pm import run_pm_agent
from backend.agents.backend_worker import run_backend_agent
from backend.agents.frontend_worker import run_frontend_agent
from backend.agents.security_auditor import run_security_auditor_agent
from backend.core.sandbox import scaffold_and_run_project


# Maximum number of self-healing iterations before giving up and finishing anyway.
MAX_HEAL_ITERATIONS = 3


def _last(a: str, b: str) -> str:
    """Reducer that keeps the most recent value — used on fields written by
    parallel branches so LangGraph does not raise InvalidUpdateError."""
    return b


# ---------------------------------------------------------------------------
# Shared state
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
    sandbox_result: Dict[str, Any]
    current_status: Annotated[str, _last]
    # Self-healing tracking fields
    heal_iteration: int     # how many refactor loops have run so far
    security_feedback: str  # serialised audit findings forwarded to workers
    project_id: str         # stable ID so re-scaffolds overwrite the same folder


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
        # Assign a stable project_id once at the start of the pipeline
        "project_id": state.get("project_id") or str(uuid.uuid4())[:8],
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
    """Backend Worker agent: generates FastAPI / SQLAlchemy server code.

    On self-healing passes the security audit findings are forwarded so the
    agent can explicitly address the identified vulnerabilities.
    NOTE: Does NOT call the sandbox directly — scaffold_node does that after
    both parallel workers (backend + frontend) have finished.
    """
    print("--- BACKEND WORKER AGENT WORKING ---")
    security_notes = state.get("security_feedback", "")

    result = run_backend_agent(
        state["project_statement"],
        str(state["technical_blueprint"]),
        str(state["product_requirements"]),
        security_notes=security_notes,
    )
    return {
        "backend_code": result.blueprint.model_dump(),
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


def scaffold_node(state: VertexFlowState) -> dict:
    """Scaffold node: called after both workers finish.

    Writes all generated files to disk, installs pip dependencies, launches
    the FastAPI backend as a subprocess, and scaffolds the React/Vite frontend.
    Uses the stable project_id so re-scaffolds on heal cycles overwrite the
    same output folder rather than creating duplicate directories.
    """
    print("--- SCAFFOLD NODE: WRITING FILES & STARTING SERVERS ---")
    project_id = state.get("project_id") or str(uuid.uuid4())[:8]

    sandbox = scaffold_and_run_project(
        project_id=project_id,
        backend_code=state["backend_code"],
        frontend_code=state.get("frontend_code"),
    )
    return {
        "sandbox_result": sandbox,
        "current_status": "Project Scaffolded & Backend Server Running",
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
# Conditional Routing Logic (Self-Healing Loop)
# ---------------------------------------------------------------------------
def should_loop_back_to_workers(state: VertexFlowState) -> str:
    """
    Evaluates the Security Audit report.
    - Loops back to workers if issues found AND iteration cap not reached.
    - Finishes (with a warning) once MAX_HEAL_ITERATIONS is hit.
    - Finishes immediately on a passing audit.
    """
    audit = state.get("security_audit", {})
    status = audit.get("overall_status", "Passed")
    score = audit.get("security_score", 100)
    current_iteration = state.get("heal_iteration", 0)

    needs_fix = (status != "Passed") or (score < 80)

    if needs_fix and current_iteration < MAX_HEAL_ITERATIONS:
        print(
            f"--- SECURITY AUDIT FAILED (iteration {current_iteration + 1}/{MAX_HEAL_ITERATIONS}): "
            "LOOPING BACK TO WORKERS FOR REFACTORING ---"
        )
        return "refactor"

    if needs_fix:
        print(
            f"--- SECURITY AUDIT FAILED but max heal iterations ({MAX_HEAL_ITERATIONS}) reached. "
            "Finishing pipeline. ---"
        )
    else:
        print("--- SECURITY AUDIT PASSED: PIPELINE FINISHED ---")

    return "finish"


def increment_heal_iteration(state: VertexFlowState) -> dict:
    """Prep node before the refactor loop.

    Increments the heal counter and serialises audit findings into a
    human-readable string that the worker agents use to patch their output.
    """
    audit = state.get("security_audit", {})
    vulnerabilities = audit.get("vulnerabilities", [])

    lines = [
        f"  [{v.get('severity', 'Unknown')}] {v.get('vulnerability_id', '')}: "
        f"{v.get('description', '')} — Remediation: {v.get('remediation', '')}"
        for v in vulnerabilities
    ]
    feedback_text = "\n".join(lines) if lines else "General security issues found; harden the code."

    iteration = state.get("heal_iteration", 0) + 1
    return {
        "heal_iteration": iteration,
        "security_feedback": feedback_text,
        "current_status": f"Self-Healing Iteration {iteration} Starting",
    }


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------
workflow = StateGraph(VertexFlowState)

workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)
workflow.add_node("pm_agent", pm_node)
workflow.add_node("backend_worker_agent", backend_worker_node)
workflow.add_node("frontend_worker_agent", frontend_worker_node)
workflow.add_node("scaffold_agent", scaffold_node)          # NEW: scaffold after both workers
workflow.add_node("security_auditor_agent", security_auditor_node)
workflow.add_node("heal_prep", increment_heal_iteration)

workflow.set_entry_point("ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", "pm_agent")

# Fan out to both workers in parallel
workflow.add_edge("pm_agent", "backend_worker_agent")
workflow.add_edge("pm_agent", "frontend_worker_agent")

# Both workers must finish before scaffolding
workflow.add_edge("backend_worker_agent", "scaffold_agent")
workflow.add_edge("frontend_worker_agent", "scaffold_agent")

# Scaffold then audit
workflow.add_edge("scaffold_agent", "security_auditor_agent")

# Conditional: pass → finish, fail → heal_prep
workflow.add_conditional_edges(
    "security_auditor_agent",
    should_loop_back_to_workers,
    {
        "refactor": "heal_prep",
        "finish": END,
    },
)

# heal_prep fans back out to both workers, then scaffold again with patched code
workflow.add_edge("heal_prep", "backend_worker_agent")
workflow.add_edge("heal_prep", "frontend_worker_agent")

vertex_flow_app = workflow.compile()

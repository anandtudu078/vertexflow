import uuid
from typing import Annotated, List, Dict, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END

from backend.agents.research_agent import run_research_agent
from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent
from backend.agents.pm import run_pm_agent
from backend.agents.ui_ux_agent import run_ui_ux_agent
from backend.agents.backend_worker import run_backend_agent
from backend.agents.frontend_worker import run_frontend_agent
from backend.agents.code_reviewer_agent import run_code_reviewer_agent
from backend.agents.qa_agent import run_qa_agent
from backend.agents.security_auditor import run_security_auditor_agent
from backend.core.sandbox import scaffold_and_run_project


# Maximum number of self-healing iterations before giving up and finishing anyway.
MAX_HEAL_ITERATIONS = 3


def _last(a: str, b: str) -> str:
    """Reducer that keeps the most recent value on parallel writes."""
    return b


# ---------------------------------------------------------------------------
# Shared state (Added qa_report)
# ---------------------------------------------------------------------------
class VertexFlowState(TypedDict):
    project_statement: str
    target_tech_stack: str
    research_findings: Dict[str, Any]
    company_vision: str
    milestones: List[Dict[str, Any]]
    technical_blueprint: Dict[str, Any]
    product_requirements: Dict[str, Any]
    ui_ux_blueprint: Dict[str, Any]
    backend_code: Dict[str, Any]
    frontend_code: Dict[str, Any]
    code_review: Dict[str, Any]
    qa_report: Dict[str, Any]
    security_audit: Dict[str, Any]
    sandbox_result: Dict[str, Any]
    current_status: Annotated[str, _last]
    # Self-healing tracking fields
    heal_iteration: int     # how many refactor loops have run so far
    security_feedback: str  # serialised audit / build findings forwarded to workers
    project_id: str         # stable ID so re-scaffolds overwrite the same folder


# ---------------------------------------------------------------------------
# Agent nodes
# ---------------------------------------------------------------------------

def research_node(state: VertexFlowState) -> dict:
    """Research agent: gathers modern patterns, library docs, and pitfalls."""
    print("--- RESEARCH AGENT WORKING ---")
    findings = run_research_agent(state["project_statement"], state["target_tech_stack"])
    return {
        "research_findings": findings.model_dump(),
        "current_status": "Technical Research Complete",
    }


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


def ui_ux_node(state: VertexFlowState) -> dict:
    """UI/UX Stylist agent: defines color palettes, typography, and design systems."""
    print("--- UI/UX STYLIST AGENT WORKING ---")
    ui_blueprint = run_ui_ux_agent(
        state["project_statement"],
        str(state["product_requirements"]),
    )
    return {
        "ui_ux_blueprint": ui_blueprint.model_dump(),
        "current_status": "UI/UX Design System Complete",
    }


def backend_worker_node(state: VertexFlowState) -> dict:
    """Backend Worker agent: generates FastAPI / SQLAlchemy server code.

    On self-healing passes the audit findings (and any build error from the
    previous scaffold) are forwarded so the agent can address them explicitly.
    NOTE: does NOT scaffold — scaffold_node does that once both workers finish.
    """
    print("--- BACKEND WORKER AGENT WORKING ---")
    result = run_backend_agent(
        state["project_statement"],
        str(state["technical_blueprint"]),
        str(state["product_requirements"]),
        security_notes=state.get("security_feedback", ""),
    )
    return {
        "backend_code": result.blueprint.model_dump(),
        "current_status": "Backend Code Generated",
    }


def frontend_worker_node(state: VertexFlowState) -> dict:
    """Frontend Worker agent: generates React / TypeScript component code using UI/UX design specs."""
    print("--- FRONTEND WORKER AGENT WORKING ---")
    frontend = run_frontend_agent(
        state["project_statement"],
        str(state["technical_blueprint"]),
        str(state["product_requirements"]),
        security_notes=state.get("security_feedback", ""),
        ui_ux_notes=str(state.get("ui_ux_blueprint", {})),
    )
    return {
        "frontend_code": frontend.model_dump(),
        "current_status": "Frontend Code Generated with Design System",
    }


def code_reviewer_node(state: VertexFlowState) -> dict:
    """Code Reviewer agent: performs static analysis and clean code reviews."""
    print("--- CODE REVIEWER AGENT WORKING ---")
    review = run_code_reviewer_agent(
        state["project_statement"],
        str(state["backend_code"]),
        str(state["frontend_code"]),
    )
    return {
        "code_review": review.model_dump(),
        "current_status": "Code Review & Static Analysis Complete",
    }


def qa_node(state: VertexFlowState) -> dict:
    """QA Test Engineer agent: designs unit tests and verifies test pass rates."""
    print("--- QA TEST ENGINEER AGENT WORKING ---")
    report = run_qa_agent(
        state["project_statement"],
        str(state["backend_code"]),
        str(state["frontend_code"]),
    )
    return {
        "qa_report": report.model_dump(),
        "current_status": "QA Testing & Verification Complete",
    }


def scaffold_node(state: VertexFlowState) -> dict:
    """Scaffold node: called once both workers finish.

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
def backend_failed_to_boot(state: VertexFlowState) -> bool:
    """True when the scaffold reported a backend that never came up.

    A generated app that fails its import check never serves a request, yet the
    audit only reads the code and can still pass — so the pipeline used to end
    "successfully" with a dead backend. Such a build error earns a heal cycle
    just like a security finding.
    """
    backend = (state.get("sandbox_result") or {}).get("backend") or {}
    status = backend.get("status")
    return bool(status) and status != "Running"


def should_loop_back_to_workers(state: VertexFlowState) -> str:
    """
    Evaluates the Security Audit report and the scaffold result.
    - Loops back to workers if issues found AND iteration cap not reached.
    - Finishes (with a warning) once MAX_HEAL_ITERATIONS is hit.
    - Finishes immediately on a passing audit with a running backend.
    """
    audit = state.get("security_audit", {})
    status = audit.get("overall_status", "Passed")
    score = audit.get("security_score", 100)
    current_iteration = state.get("heal_iteration", 0)

    audit_failed = (status != "Passed") or (score < 80)
    needs_fix = audit_failed or backend_failed_to_boot(state)
    reason = "SECURITY AUDIT FAILED" if audit_failed else "BACKEND FAILED TO BOOT"

    if needs_fix and current_iteration < MAX_HEAL_ITERATIONS:
        print(
            f"--- {reason} (iteration {current_iteration + 1}/{MAX_HEAL_ITERATIONS}): "
            "LOOPING BACK TO WORKERS FOR REFACTORING ---"
        )
        return "refactor"

    if needs_fix:
        print(
            f"--- {reason} but max heal iterations ({MAX_HEAL_ITERATIONS}) reached. "
            "Finishing pipeline. ---"
        )
    else:
        print("--- SECURITY AUDIT PASSED: PIPELINE FINISHED ---")

    return "finish"


def increment_heal_iteration(state: VertexFlowState) -> dict:
    """Prep node before the refactor loop.

    Increments the heal counter and serialises audit findings plus any build
    error into a human-readable string the workers use to patch their output.
    """
    audit = state.get("security_audit", {})
    vulnerabilities = audit.get("vulnerabilities", [])

    lines = [
        f"  [{v.get('severity', 'Unknown')}] {v.get('vulnerability_id', '')}: "
        f"{v.get('description', '')} — Remediation: {v.get('remediation', '')}"
        for v in vulnerabilities
    ]

    # A build error is not a security finding: the workers need the traceback
    # so the regenerated code imports and boots, otherwise the loop burns its
    # iterations on an app that never starts.
    backend = (state.get("sandbox_result") or {}).get("backend") or {}
    if backend_failed_to_boot(state):
        boot_error = backend.get("import_error") or "\n".join(backend.get("startup_error") or [])
        lines.append(
            "  [Build] The scaffolded backend failed to start"
            f" ({backend.get('status')}). The new code MUST import cleanly and boot."
        )
        if boot_error:
            lines.append(f"  [Build] Error: {boot_error}")

    feedback_text = "\n".join(lines) if lines else "General security issues found; harden the code."

    iteration = state.get("heal_iteration", 0) + 1
    return {
        "heal_iteration": iteration,
        "security_feedback": feedback_text,
        "current_status": f"Self-Healing Iteration {iteration} Starting",
    }


# ---------------------------------------------------------------------------
# Graph wiring with QA Agent integrated
# ---------------------------------------------------------------------------
workflow = StateGraph(VertexFlowState)

workflow.add_node("research_agent", research_node)
workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)
workflow.add_node("pm_agent", pm_node)
workflow.add_node("ui_ux_agent", ui_ux_node)
workflow.add_node("backend_worker_agent", backend_worker_node)
workflow.add_node("frontend_worker_agent", frontend_worker_node)
workflow.add_node("code_reviewer_agent", code_reviewer_node)
workflow.add_node("qa_agent", qa_node)
workflow.add_node("scaffold_agent", scaffold_node)
workflow.add_node("security_auditor_agent", security_auditor_node)
workflow.add_node("heal_prep", increment_heal_iteration)

# Linear flow up to PM
workflow.set_entry_point("research_agent")
workflow.add_edge("research_agent", "ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", "pm_agent")

# Parallel fan-out from PM to Backend Worker and UI/UX Agent
workflow.add_edge("pm_agent", "backend_worker_agent")
workflow.add_edge("pm_agent", "ui_ux_agent")

# UI/UX feeds into Frontend Worker
workflow.add_edge("ui_ux_agent", "frontend_worker_agent")

# Both workers feed into Code Reviewer. This must be one join edge: the two
# branches are different depths (ui_ux -> frontend), so separate edges made the
# reviewer fire once the backend finished, before frontend_code existed.
workflow.add_edge(["backend_worker_agent", "frontend_worker_agent"], "code_reviewer_agent")

# Code Reviewer -> QA Agent -> Scaffold -> Security Auditor
workflow.add_edge("code_reviewer_agent", "qa_agent")
workflow.add_edge("qa_agent", "scaffold_agent")
workflow.add_edge("scaffold_agent", "security_auditor_agent")

workflow.add_conditional_edges(
    "security_auditor_agent",
    should_loop_back_to_workers,
    {
        "refactor": "heal_prep",
        "finish": END,
    },
)

# heal_prep fans back out to the workers (and the UI/UX agent that feeds the
# frontend), then the pipeline re-scaffolds with the patched code
workflow.add_edge("heal_prep", "backend_worker_agent")
workflow.add_edge("heal_prep", "ui_ux_agent")

vertex_flow_app = workflow.compile()
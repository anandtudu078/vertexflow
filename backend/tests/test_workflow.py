"""Graph-level tests for the VertexFlow pipeline.

Every agent call and the sandbox launch are stubbed, so these tests exercise the
wiring, the self-healing loop and the state reducers; they never touch Gemini or
start a server.
"""

import pytest

from backend.agents import workflow
from backend.agents.workflow import (
    MAX_HEAL_ITERATIONS,
    _last,
    increment_heal_iteration,
    should_loop_back_to_workers,
)

PROJECT_STATEMENT = "Build a todo app"
TARGET_STACK = "FastAPI + React"


class _Payload:
    """Stand-in for the pydantic objects the agents return."""

    def __init__(self, **fields):
        self._fields = fields

    def model_dump(self):
        return dict(self._fields)

    def __getattr__(self, item):
        try:
            return self._fields[item]
        except KeyError:
            raise AttributeError(item) from None


FAILING_AUDIT = {
    "security_score": 78,
    "overall_status": "Passed",
    "vulnerabilities": [
        {
            "vulnerability_id": "SEC-001",
            "severity": "High",
            "description": "Hardcoded SECRET_KEY",
            "remediation": "Load the secret from the environment",
        }
    ],
}


class _StubPipeline:
    """Records what the graph asked of each agent."""

    def __init__(self):
        self.backend_calls: list[str] = []
        self.frontend_calls = 0
        self.frontend_notes: list[str] = []
        self.audit_calls = 0
        self.scaffolds: list[tuple[str, dict, dict | None]] = []
        self.audit_report = {
            "security_score": 100,
            "overall_status": "Passed",
            "vulnerabilities": [],
        }

    @property
    def backend_passes(self) -> int:
        return len(self.backend_calls)


@pytest.fixture
def pipeline(monkeypatch):
    stub = _StubPipeline()

    def research(project_statement, target_tech_stack):
        return _Payload(
            recommended_libraries=["fastapi", "react"],
            architecture_insights="Split API and UI",
            potential_pitfalls=["Storing secrets in code"],
        )

    def ui_ux(project_statement, product_requirements):
        return _Payload(primary_color="#2563eb", typography="Inter")

    def code_reviewer(project_statement, backend_code, frontend_code):
        return _Payload(summary="Readable code")

    def qa_agent(project_statement, backend_code, frontend_code):
        return _Payload(test_plan="Cover auth and CRUD")

    def ceo(project_statement, target_tech_stack):
        return _Payload(
            company_vision="Ship the todo app",
            milestones=[
                _Payload(
                    milestone_id=1,
                    title="MVP",
                    description="Auth plus CRUD",
                    assigned_department="engineering",
                )
            ],
        )

    def cto(project_statement, target_tech_stack, milestones):
        return _Payload(architecture="FastAPI + SQLModel + React")

    def pm(project_statement, milestones, cto_blueprint):
        return _Payload(scope="Todo CRUD with JWT auth")

    def backend_agent(project_statement, cto_blueprint, pm_requirements, security_notes=""):
        stub.backend_calls.append(security_notes)
        return _Payload(
            blueprint=_Payload(
                module_name="todos",
                database_models_code="class Task: ...",
                api_endpoints_code="router = APIRouter()",
                dependencies_required=["fastapi"],
            )
        )

    def frontend_agent(
        project_statement, cto_blueprint, pm_requirements, security_notes="", ui_ux_notes=""
    ):
        stub.frontend_calls += 1
        stub.frontend_notes.append(security_notes)
        return _Payload(module_name="App", components_code="export default App")

    def auditor(project_statement, backend_code, frontend_code):
        stub.audit_calls += 1
        return _Payload(**stub.audit_report)

    def scaffold(project_id, backend_code, frontend_code=None):
        stub.scaffolds.append((project_id, backend_code, frontend_code))
        return {
            "backend": {"status": "Running", "url": "http://127.0.0.1:1234"},
            "status": "Backend Running. Frontend scaffolded.",
        }

    monkeypatch.setattr(workflow, "run_research_agent", research)
    monkeypatch.setattr(workflow, "run_ui_ux_agent", ui_ux)
    monkeypatch.setattr(workflow, "run_code_reviewer_agent", code_reviewer)
    monkeypatch.setattr(workflow, "run_qa_agent", qa_agent)
    monkeypatch.setattr(workflow, "run_ceo_agent", ceo)
    monkeypatch.setattr(workflow, "run_cto_agent", cto)
    monkeypatch.setattr(workflow, "run_pm_agent", pm)
    monkeypatch.setattr(workflow, "run_backend_agent", backend_agent)
    monkeypatch.setattr(workflow, "run_frontend_agent", frontend_agent)
    monkeypatch.setattr(workflow, "run_security_auditor_agent", auditor)
    monkeypatch.setattr(workflow, "scaffold_and_run_project", scaffold)
    return stub


def _run(**overrides):
    state = {"project_statement": PROJECT_STATEMENT, "target_tech_stack": TARGET_STACK}
    state.update(overrides)
    return workflow.vertex_flow_app.invoke(state)


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------

def test_graph_wires_parallel_workers_scaffold_and_heal_loop():
    edges = {(edge.source, edge.target) for edge in workflow.vertex_flow_app.get_graph().edges}

    assert ("__start__", "research_agent") in edges
    assert ("research_agent", "ceo_agent") in edges
    assert ("ceo_agent", "cto_agent") in edges
    assert ("cto_agent", "pm_agent") in edges
    assert ("pm_agent", "backend_worker_agent") in edges
    assert ("pm_agent", "ui_ux_agent") in edges
    assert ("ui_ux_agent", "frontend_worker_agent") in edges
    # Both branches must join before review, scaffold and audit, not run through
    # them in sequence.
    assert ("backend_worker_agent", "code_reviewer_agent") in edges
    assert ("frontend_worker_agent", "code_reviewer_agent") in edges
    assert ("code_reviewer_agent", "qa_agent") in edges
    assert ("qa_agent", "scaffold_agent") in edges
    assert ("scaffold_agent", "security_auditor_agent") in edges
    assert ("security_auditor_agent", "heal_prep") in edges
    assert ("security_auditor_agent", "__end__") in edges
    assert ("heal_prep", "backend_worker_agent") in edges
    assert ("heal_prep", "ui_ux_agent") in edges


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_passing_audit_finishes_after_a_single_pass(pipeline):
    result = _run()

    assert pipeline.backend_passes == 1
    assert pipeline.frontend_calls == 1
    assert pipeline.audit_calls == 1
    assert len(pipeline.scaffolds) == 1
    assert result.get("heal_iteration", 0) == 0
    assert result["current_status"] == "Security Audit Complete"
    assert result["sandbox_result"]["backend"]["status"] == "Running"


def test_scaffold_receives_both_worker_outputs_and_the_stable_project_id(pipeline):
    result = _run()

    project_id, backend_code, frontend_code = pipeline.scaffolds[0]

    assert project_id == result["project_id"]
    assert backend_code["module_name"] == "todos"
    assert frontend_code["module_name"] == "App"


def test_ceo_assigns_an_eight_character_project_id(pipeline):
    result = _run()

    assert len(result["project_id"]) == 8


def test_supplied_project_id_is_reused(pipeline):
    result = _run(project_id="fixed123")

    assert result["project_id"] == "fixed123"
    assert [scaffold[0] for scaffold in pipeline.scaffolds] == ["fixed123"]


# ---------------------------------------------------------------------------
# Self-healing loop
# ---------------------------------------------------------------------------

def test_failing_audit_heals_until_the_iteration_cap(pipeline):
    pipeline.audit_report = FAILING_AUDIT

    result = _run()

    expected_passes = MAX_HEAL_ITERATIONS + 1  # initial generation plus each retry
    assert pipeline.backend_passes == expected_passes
    assert pipeline.frontend_calls == expected_passes
    assert pipeline.audit_calls == expected_passes
    assert len(pipeline.scaffolds) == expected_passes
    assert result["heal_iteration"] == MAX_HEAL_ITERATIONS
    assert result["current_status"] == "Security Audit Complete"


def test_heal_feedback_is_forwarded_to_the_workers(pipeline):
    pipeline.audit_report = FAILING_AUDIT

    _run()

    assert pipeline.backend_calls[0] == ""  # first pass has no findings yet
    assert "SEC-001" in pipeline.backend_calls[1]
    assert "Load the secret from the environment" in pipeline.backend_calls[1]
    # The frontend worker must receive the same findings; it used to be skipped.
    assert pipeline.frontend_notes[0] == ""
    assert "SEC-001" in pipeline.frontend_notes[1]


def test_heal_cycles_reuse_one_output_folder(pipeline):
    pipeline.audit_report = FAILING_AUDIT

    _run()

    project_ids = {scaffold[0] for scaffold in pipeline.scaffolds}
    assert len(project_ids) == 1


# ---------------------------------------------------------------------------
# Reducers and routing helpers
# ---------------------------------------------------------------------------

def test_last_reducer_keeps_the_newest_value():
    assert _last("Backend Code Generated", "Frontend Code Generated") == "Frontend Code Generated"


@pytest.mark.parametrize(
    "state,expected",
    [
        ({}, "finish"),
        ({"security_audit": {}}, "finish"),
        ({"security_audit": {"overall_status": "Passed", "security_score": 100}}, "finish"),
        ({"security_audit": {"overall_status": "Passed", "security_score": 80}}, "finish"),
        # A "Passed" verdict alone does not finish while the score gate fails.
        ({"security_audit": {"overall_status": "Passed", "security_score": 79}}, "refactor"),
        ({"security_audit": {"overall_status": "Requires Fixes", "security_score": 95}}, "refactor"),
        (
            {
                "security_audit": {"overall_status": "Requires Fixes", "security_score": 40},
                "heal_iteration": MAX_HEAL_ITERATIONS,
            },
            "finish",
        ),
    ],
)
def test_should_loop_back_to_workers(state, expected):
    assert should_loop_back_to_workers(state) == expected


FAILED_BUILD = {
    "assigned_port": None,
    "backend": {
        "status": "Import error — see import_error field",
        "import_error": "ModuleNotFoundError: No module named 'todo_app'",
    },
}


def test_backend_boot_failure_triggers_a_heal_cycle():
    state = {
        "security_audit": {"overall_status": "Passed", "security_score": 100},
        "sandbox_result": FAILED_BUILD,
    }

    assert should_loop_back_to_workers(state) == "refactor"


def test_backend_boot_failure_stops_at_the_iteration_cap():
    state = {
        "security_audit": {"overall_status": "Passed", "security_score": 100},
        "sandbox_result": FAILED_BUILD,
        "heal_iteration": MAX_HEAL_ITERATIONS,
    }

    assert should_loop_back_to_workers(state) == "finish"


def test_running_backend_with_a_passing_audit_finishes():
    state = {
        "security_audit": {"overall_status": "Passed", "security_score": 100},
        "sandbox_result": {"backend": {"status": "Running"}},
    }

    assert should_loop_back_to_workers(state) == "finish"


def test_heal_feedback_carries_the_build_error_to_the_workers():
    update = increment_heal_iteration(
        {"security_audit": {"overall_status": "Passed", "security_score": 100},
         "sandbox_result": FAILED_BUILD}
    )

    assert "[Build] The scaffolded backend failed to start" in update["security_feedback"]
    assert "No module named 'todo_app'" in update["security_feedback"]


def test_increment_heal_iteration_serialises_findings():
    update = increment_heal_iteration({"security_audit": FAILING_AUDIT})

    assert update["heal_iteration"] == 1
    assert update["current_status"] == "Self-Healing Iteration 1 Starting"
    assert "[High] SEC-001: Hardcoded SECRET_KEY" in update["security_feedback"]
    assert "Remediation: Load the secret from the environment" in update["security_feedback"]


def test_increment_heal_iteration_counts_up_and_falls_back_without_findings():
    assert increment_heal_iteration({"heal_iteration": 2}).get("heal_iteration") == 3

    update = increment_heal_iteration({"security_audit": {"vulnerabilities": []}})
    assert update["security_feedback"] == "General security issues found; harden the code."

"""Tests for the Backend Worker agent.

The Gemini client is stubbed, so these tests only cover the worker's own logic:
what it returns and — importantly — that it does not scaffold a project itself.
"""

import json
from types import SimpleNamespace

import pytest

from backend.agents import backend_worker

BLUEPRINT = {
    "module_name": "todos",
    "database_models_code": "class Task: ...",
    "api_endpoints_code": "router = APIRouter()",
    "dependencies_required": ["fastapi"],
}


class _Response:
    def __init__(self, payload: dict):
        self.text = json.dumps(payload)


@pytest.fixture
def stubbed_client(monkeypatch):
    """Replace the Gemini client and record the prompt the agent sends."""
    captured: dict = {}
    scaffold_calls: list = []

    def generate_content(**kwargs):
        captured["prompt"] = kwargs.get("contents", "")
        return _Response(BLUEPRINT)

    fake_client = SimpleNamespace(models=SimpleNamespace(generate_content=generate_content))
    monkeypatch.setattr(
        backend_worker,
        "get_agent_llm_config",
        lambda role: {"provider": "gemini", "client": fake_client, "model": "test-model"},
    )
    # raising=False: after the fix the module should not even import the sandbox.
    monkeypatch.setattr(
        backend_worker,
        "scaffold_and_run_project",
        lambda *args, **kwargs: scaffold_calls.append(args),
        raising=False,
    )
    return SimpleNamespace(prompt=captured, scaffolds=scaffold_calls)


def test_backend_agent_returns_the_blueprint(stubbed_client):
    result = backend_worker.run_backend_agent("Build a todo app", "cto blueprint", "pm stories")

    assert result.blueprint.module_name == "todos"
    assert result.blueprint.dependencies_required == ["fastapi"]


def test_backend_agent_leaves_scaffolding_to_the_graph(stubbed_client):
    backend_worker.run_backend_agent("Build a todo app", "cto blueprint", "pm stories")

    # The graph's scaffold_agent runs once after both workers; scaffolding here
    # used to launch a duplicate server for every generation.
    assert stubbed_client.scaffolds == []
    assert "sandbox" not in backend_worker.BackendWorkerResult.model_fields


def test_backend_agent_forwards_security_findings_to_the_prompt(stubbed_client):
    backend_worker.run_backend_agent(
        "Build a todo app",
        "cto blueprint",
        "pm stories",
        security_notes="[High] SEC-001: Hardcoded SECRET_KEY",
    )

    prompt = stubbed_client.prompt["prompt"]
    assert "Self-Healing Pass" in prompt
    assert "SEC-001" in prompt


def test_backend_agent_omits_the_healing_section_on_the_first_pass(stubbed_client):
    backend_worker.run_backend_agent("Build a todo app", "cto blueprint", "pm stories")

    assert "Self-Healing Pass" not in stubbed_client.prompt["prompt"]

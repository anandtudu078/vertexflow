"""Backend Worker agent: turns the blueprint into FastAPI code.

Scaffolding is deliberately left to the graph's scaffold node, which runs once
after both workers finish; doing it here launched a second server and wrote a
second project folder for every generation.
"""

from typing import List

from pydantic import BaseModel

from backend.agents.llm import generate_json, get_agent_llm_config


class BackendCodeBlueprint(BaseModel):
    module_name: str
    database_models_code: str
    api_endpoints_code: str
    dependencies_required: List[str]


class BackendWorkerResult(BaseModel):
    blueprint: BackendCodeBlueprint


def run_backend_agent(
    project_statement: str,
    cto_blueprint: str,
    pm_requirements: str,
    security_notes: str = "",
) -> BackendWorkerResult:
    """Generate the server-side blueprint.

    If `security_notes` is provided the agent is instructed to address those
    vulnerabilities in the regenerated code (self-healing loop).
    """
    healing_section = ""
    if security_notes:
        healing_section = f"""
    IMPORTANT – Self-Healing Pass:
    A previous version of your code was rejected by the Security Auditor.
    You MUST address every vulnerability listed below before producing new code.
    Do NOT reproduce any of the flaws described here.

    Security Audit Findings:
    {security_notes}
    """

    prompt = f"""
    You are the Senior Backend Engineering Agent of VertexFlow.

    Project Statement: "{project_statement}"

    CTO Architecture Blueprint:
    {cto_blueprint}

    Product Manager User Stories:
    {pm_requirements}
    {healing_section}
    Generate production-ready Python server code. Provide:
    1. The module name.
    2. SQLModel/SQLAlchemy database models code.
    3. FastAPI endpoint router code implementing the core features.
    4. The required Python pip dependencies.

    Return your output strictly as a JSON object matching this schema:
    {{
      "module_name": "string",
      "database_models_code": "string",
      "api_endpoints_code": "string",
      "dependencies_required": ["fastapi", "uvicorn", "sqlmodel"]
    }}
    """

    config = get_agent_llm_config("backend_worker")
    blueprint = BackendCodeBlueprint.model_validate_json(generate_json(config, prompt))
    return BackendWorkerResult(blueprint=blueprint)

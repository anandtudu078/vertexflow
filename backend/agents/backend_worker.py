import uuid
from google.genai import types
from pydantic import BaseModel
from typing import List, Dict, Any

from backend.agents.llm import get_client
from backend.config import GEMINI_MODEL
from backend.core.sandbox import scaffold_and_run_project


class BackendCodeBlueprint(BaseModel):
    module_name: str
    database_models_code: str
    api_endpoints_code: str
    dependencies_required: List[str]


class BackendWorkerResult(BaseModel):
    blueprint: BackendCodeBlueprint
    sandbox: Dict[str, Any]


def run_backend_agent(
    project_statement: str,
    cto_blueprint: str,
    pm_requirements: str,
    security_notes: str = "",
) -> BackendWorkerResult:
    """
    The Backend Worker Agent generates production-ready server-side code
    (FastAPI/SQLAlchemy) based on the architectural blueprint and user stories,
    then scaffolds the output to disk via the sandbox.

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
    Your job is to generate production-ready Python backend code. Provide:
    1. The module name.
    2. SQLAlchemy/SQLModel or Pydantic database models code.
    3. FastAPI endpoint router code implementing the core features.
    4. A list of required Python pip dependencies (e.g., fastapi, sqlalchemy, pydantic).
    """

    response = get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BackendCodeBlueprint,
            temperature=0.2,
        ),
    )

    blueprint = BackendCodeBlueprint.model_validate_json(response.text)

    project_id = str(uuid.uuid4())[:8]
    sandbox = scaffold_and_run_project(project_id, blueprint.model_dump())

    return BackendWorkerResult(blueprint=blueprint, sandbox=sandbox)
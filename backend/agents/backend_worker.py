from google.genai import types
from pydantic import BaseModel
from typing import List

from backend.agents.llm import get_client
from backend.config import GEMINI_MODEL


class BackendCodeBlueprint(BaseModel):
    module_name: str
    database_models_code: str
    api_endpoints_code: str
    dependencies_required: List[str]


def run_backend_agent(project_statement: str, cto_blueprint: str, pm_requirements: str) -> BackendCodeBlueprint:
    """
    The Backend Worker Agent generates production-ready server-side code
    (FastAPI/SQLAlchemy) based on the architectural blueprint and user stories.
    """
    prompt = f"""
    You are the Senior Backend Engineering Agent of VertexFlow.

    Project Statement: "{project_statement}"

    CTO Architecture Blueprint:
    {cto_blueprint}

    Product Manager User Stories:
    {pm_requirements}

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

    return BackendCodeBlueprint.model_validate_json(response.text)
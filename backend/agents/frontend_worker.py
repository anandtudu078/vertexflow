from google.genai import types
from pydantic import BaseModel
from typing import List

from backend.agents.llm import get_client
from backend.config import GEMINI_MODEL


class FrontendCodeBlueprint(BaseModel):
    component_name: str
    react_tsx_code: str
    tailwind_styles_used: List[str]
    state_management_summary: str


def run_frontend_agent(project_statement: str, cto_blueprint: str, pm_requirements: str) -> FrontendCodeBlueprint:
    """
    The Frontend Worker Agent generates production-ready React/TypeScript components
    and Tailwind styling based on the architectural blueprint and user stories.
    """
    prompt = f"""
    You are the Senior Frontend Engineering Agent of VertexFlow.

    Project Statement: "{project_statement}"

    CTO Architecture Blueprint:
    {cto_blueprint}

    Product Manager User Stories:
    {pm_requirements}

    Your job is to generate production-ready React + TypeScript frontend code using Tailwind CSS. Provide:
    1. The main component name.
    2. The complete React TSX code implementation for the UI component.
    3. A list of key Tailwind CSS utility styles or classes used.
    4. A brief summary of how local state or data fetching is managed.
    """

    response = get_client().models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FrontendCodeBlueprint,
            temperature=0.2,
        ),
    )

    return FrontendCodeBlueprint.model_validate_json(response.text)
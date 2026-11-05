import json
from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import get_agent_llm_config, generate_json


class CodeReviewReport(BaseModel):
    clean_code_score: int
    refactoring_suggestions: List[str]
    is_approved: bool


def run_code_reviewer_agent(project_statement: str, backend_code: str, frontend_code: str) -> CodeReviewReport:
    # Fetch model config (routes to Gemini for meticulous code analysis)
    config = get_agent_llm_config("code_reviewer_agent")

    prompt = f"""
    You are an elite Principal Software Engineer and Code Reviewer.
    Project Statement: {project_statement}

    Backend Code Snippet:
    {backend_code}

    Frontend Code Snippet:
    {frontend_code}

    Review the code for clean architecture, type hinting compliance, readability, and structural best practices.
    Return your output strictly as a JSON object matching this schema:
    {{
      "clean_code_score": 90,
      "refactoring_suggestions": ["suggestion 1", "suggestion 2"],
      "is_approved": true
    }}
    """

    response_text = generate_json(
        config,
        prompt,
        system_prompt="You are a precise JSON code reviewer and static analysis expert."
    )

    data = json.loads(response_text)
    return CodeReviewReport(**data)
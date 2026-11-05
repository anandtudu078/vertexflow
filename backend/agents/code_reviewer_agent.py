from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import generate_model


class CodeReviewReport(BaseModel):
    clean_code_score: int
    refactoring_suggestions: List[str]
    is_approved: bool


def run_code_reviewer_agent(project_statement: str, backend_code: str, frontend_code: str) -> CodeReviewReport:
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

    return generate_model(prompt, CodeReviewReport, "code_reviewer_agent")
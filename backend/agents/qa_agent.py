from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import generate_model


class QATestReport(BaseModel):
    tests_generated: List[str]
    pass_rate_estimate: float
    qa_feedback: str
    is_passing: bool


def run_qa_agent(project_statement: str, backend_code: str, frontend_code: str) -> QATestReport:
    prompt = f"""
    You are an expert QA and Test Automation Engineer.
    Project Statement: {project_statement}

    Backend Code:
    {backend_code}

    Frontend Code:
    {frontend_code}

    Design unit and integration test suites for this codebase (e.g. pytest for backend, React testing components).
    Return your output strictly as a JSON object matching this schema:
    {{
      "tests_generated": ["test_api_endpoints.py", "test_ui_components.tsx"],
      "pass_rate_estimate": 95.5,
      "qa_feedback": "string describing test results and edge cases covered",
      "is_passing": true
    }}
    """

    return generate_model(prompt, QATestReport, "qa_agent")
import json
from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import get_agent_llm_config, generate_json


class QATestReport(BaseModel):
    tests_generated: List[str]
    pass_rate_estimate: float
    qa_feedback: str
    is_passing: bool


def run_qa_agent(project_statement: str, backend_code: str, frontend_code: str) -> QATestReport:
    # Fetch model config (routes to Gemini for test planning & logic verification)
    config = get_agent_llm_config("qa_agent")

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

    response_text = generate_json(
        config,
        prompt,
        system_prompt="You are a precise JSON QA automation engineer."
    )

    data = json.loads(response_text)
    return QATestReport(**data)
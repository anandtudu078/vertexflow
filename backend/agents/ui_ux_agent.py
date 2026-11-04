import json
from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import get_agent_llm_config, generate_json


class UIUXBlueprint(BaseModel):
    design_system_name: str
    color_palette: dict
    typography: str
    component_styling_guidelines: List[str]
    tailwind_theme_extensions: str


def run_ui_ux_agent(project_statement: str, product_requirements: str) -> UIUXBlueprint:
    # Fetch model config (routes to Gemini for creative design reasoning)
    config = get_agent_llm_config("ui_ux_agent")

    prompt = f"""
    You are an expert Lead UI/UX Designer and Design Systems Architect.
    Project Statement: {project_statement}
    Product Requirements: {product_requirements}

    Design a comprehensive, modern UI/UX design system for this project using Tailwind CSS.
    Return your output strictly as a JSON object matching this schema:
    {{
      "design_system_name": "string",
      "color_palette": {{"primary": "string", "secondary": "string", "background": "string", "text": "string"}},
      "typography": "string",
      "component_styling_guidelines": ["guideline 1", "guideline 2"],
      "tailwind_theme_extensions": "string"
    }}
    """

    response_text = generate_json(
        config,
        prompt,
        system_prompt="You are a precise JSON UI/UX design architect."
    )

    data = json.loads(response_text)
    return UIUXBlueprint(**data)
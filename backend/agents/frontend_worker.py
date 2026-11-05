"""Frontend Worker agent: turns the blueprint into React/TypeScript code."""

from typing import List

from pydantic import BaseModel

from backend.agents.llm import generate_json, get_agent_llm_config


class FrontendCodeBlueprint(BaseModel):
    component_name: str
    html_structure: str
    react_code: str
    styling_css: str
    dependencies_required: List[str]


def run_frontend_agent(
    project_statement: str,
    cto_blueprint: str,
    pm_requirements: str,
    security_notes: str = "",
    ui_ux_notes: str = "",
) -> FrontendCodeBlueprint:
    """Generate the client-side blueprint.

    If `security_notes` is provided the agent is instructed to address those
    vulnerabilities in the regenerated code (self-healing loop). `ui_ux_notes`
    carries the design system the UI/UX agent produced for this project.
    """
    design_section = ""
    if ui_ux_notes:
        design_section = f"""
    Design System (follow it for colours, typography and spacing):
    {ui_ux_notes}
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
    You are an expert Frontend Engineer specializing in React, TypeScript, and modern UI/UX design.
    Project Statement: {project_statement}
    CTO Architecture Blueprint: {cto_blueprint}
    Product Requirements: {pm_requirements}
    {design_section}
    {healing_section}
    Generate clean, production-ready frontend code (React component, CSS styling, and dependencies).
    Return your output strictly as a JSON object matching this schema:
    {{
      "component_name": "string",
      "html_structure": "string",
      "react_code": "string",
      "styling_css": "string",
      "dependencies_required": ["react", "lucide-react"]
    }}
    """

    config = get_agent_llm_config("frontend_worker")
    return FrontendCodeBlueprint.model_validate_json(generate_json(config, prompt))

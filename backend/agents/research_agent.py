from pydantic import BaseModel, Field
from typing import List
from backend.agents.llm import generate_model


class ResearchFindings(BaseModel):
    recommended_libraries: List[str]
    architecture_insights: str
    potential_pitfalls: List[str]


def run_research_agent(project_statement: str, target_tech_stack: str) -> ResearchFindings:
    prompt = f"""
    You are an expert Technical Researcher and Developer Advocate.
    Project Statement: {project_statement}
    Target Tech Stack: {target_tech_stack}

    Research the best practices, required libraries, modern architecture patterns, and potential integration pitfalls for this project.
    Return your output strictly as a JSON object matching this schema:
    {{
      "recommended_libraries": ["fastapi", "react", "tailwindcss"],
      "architecture_insights": "string describing modern approach",
      "potential_pitfalls": ["pitfall 1", "pitfall 2"]
    }}
    """

    return generate_model(prompt, ResearchFindings, "research_agent")
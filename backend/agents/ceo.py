from typing import List

from pydantic import BaseModel

from backend.agents.llm import generate_structured


class Milestone(BaseModel):
    milestone_id: int
    title: str
    description: str
    assigned_department: str


class CEOStrategyResponse(BaseModel):
    company_vision: str
    milestones: List[Milestone]


def run_ceo_agent(project_statement: str, target_tech_stack: str) -> CEOStrategyResponse:
    """
    The CEO Agent ingests the project statement and decomposes it into high-level milestones.
    """
    prompt = f"""
    You are the CEO AI Agent of VertexFlow, an autonomous virtual software enterprise.
    A user has submitted the following project brief:

    Project Statement: "{project_statement}"
    Target Tech Stack: "{target_tech_stack}"

    Your job is to act as the Chief Executive Officer. Define the company vision for this project 
    and break down the execution into 3 to 5 clear, sequential milestones that can be passed down 
    to the CTO and engineering departments.
    """

    return CEOStrategyResponse.model_validate_json(
        generate_structured(prompt, CEOStrategyResponse, "ceo")
    )

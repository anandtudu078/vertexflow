from pydantic import BaseModel
from typing import List

from backend.agents.llm import generate_structured


class UserStory(BaseModel):
    story_id: int
    user_role: str
    feature_goal: str
    acceptance_criteria: List[str]


class ProductManagerBlueprint(BaseModel):
    product_scope_summary: str
    user_stories: List[UserStory]


def run_pm_agent(project_statement: str, ceo_milestones: str, cto_blueprint: str) -> ProductManagerBlueprint:
    """
    The Product Manager Agent translates strategy and architecture into
    actionable user stories and acceptance criteria.
    """
    prompt = f"""
    You are the Lead Product Manager AI Agent of VertexFlow.

    Project Statement: "{project_statement}"

    The CEO provided these milestones:
    {ceo_milestones}

    The CTO provided this technical architecture:
    {cto_blueprint}

    Your job is to define the product scope summary and break down the requirements into 3 to 5 detailed user stories, 
    complete with user roles, feature goals, and explicit acceptance criteria.
    """

    return ProductManagerBlueprint.model_validate_json(
        generate_structured(prompt, ProductManagerBlueprint, "pm")
    )
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydantic import BaseModel
from typing import List

# Load environment variables from the .env file
load_dotenv()

# Initialize the Gemini client securely from environment variables
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))


class TaskTicket(BaseModel):
    task_id: int
    title: str
    description: str
    difficulty: str


class CTOTechnicalBlueprint(BaseModel):
    architecture_overview: str
    database_models: List[str]
    tasks: List[TaskTicket]


def run_cto_agent(project_statement: str, target_tech_stack: str, ceo_milestones: str) -> CTOTechnicalBlueprint:
    """
    The CTO Agent takes the project brief and the CEO's milestones,
    then designs the technical blueprint and engineering task tickets.
    """
    prompt = f"""
    You are the CTO AI Agent of VertexFlow, an autonomous virtual software enterprise.

    Project Statement: "{project_statement}"
    Target Tech Stack: "{target_tech_stack}"

    The CEO has provided the following strategic milestones:
    {ceo_milestones}

    Your job as Chief Technology Officer is to design the technical architecture, list required database models, 
    and break down the execution into actionable developer task tickets.
    """

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CTOTechnicalBlueprint,
            temperature=0.2,
        ),
    )

    return CTOTechnicalBlueprint.model_validate_json(response.text)
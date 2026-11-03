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

    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CEOStrategyResponse,
            temperature=0.2,
        ),
    )

    return CEOStrategyResponse.model_validate_json(response.text)
from typing import List, Dict, Any
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent
from backend.agents.pm import run_pm_agent  # <--- 1. Import the PM agent


# Define the shared state structure for our agent workflow
class VertexFlowState(BaseModel):
    project_statement: str
    target_tech_stack: str
    company_vision: str = ""
    milestones: List[Dict[str, Any]] = []
    technical_blueprint: Dict[str, Any] = {}
    product_requirements: Dict[str, Any] = {}  # <--- 2. Add field for PM output
    current_status: str = "Initialized"


def ceo_node(state: VertexFlowState) -> dict:
    """Executes the CEO agent step and updates state."""
    print("--- CEO AGENT WORKING ---")
    strategy = run_ceo_agent(state.project_statement, state.target_tech_stack)
    return {
        "company_vision": strategy.company_vision,
        "milestones": [m.model_dump() for m in strategy.milestones],
        "current_status": "CEO Strategy Complete"
    }


def cto_node(state: VertexFlowState) -> dict:
    """Executes the CTO agent step using the CEO's milestones."""
    print("--- CTO AGENT WORKING ---")
    milestones_str = str(state.milestones)
    blueprint = run_cto_agent(state.project_statement, state.target_tech_stack, milestones_str)
    return {
        "technical_blueprint": blueprint.model_dump(),
        "current_status": "CTO Architecture Blueprint Complete"
    }


def pm_node(state: VertexFlowState) -> dict:
    """Executes the PM agent step using CEO milestones and CTO blueprint."""
    print("--- PRODUCT MANAGER AGENT WORKING ---")
    milestones_str = str(state.milestones)
    blueprint_str = str(state.technical_blueprint)

    pm_blueprint = run_pm_agent(state.project_statement, milestones_str, blueprint_str)
    return {
        "product_requirements": pm_blueprint.model_dump(),  # <--- 3. Return PM data update
        "current_status": "Product Requirements & User Stories Complete"
    }


# Build the LangGraph workflow
workflow = StateGraph(VertexFlowState)

# Add agent nodes
workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)
workflow.add_node("pm_agent", pm_node)  # <--- 4. Add PM node to graph

# Define the execution flow: Start -> CEO -> CTO -> PM -> END
workflow.set_entry_point("ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", "pm_agent")  # <--- 5. Connect CTO to PM
workflow.add_edge("pm_agent", END)  # <--- 6. Connect PM to END

# Compile the graph into an executable app
vertex_flow_app = workflow.compile()
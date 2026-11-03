from typing import List, Dict, Any
from pydantic import BaseModel
from langgraph.graph import StateGraph, END

from backend.agents.ceo import run_ceo_agent
from backend.agents.cto import run_cto_agent

# Define the shared state structure for our agent workflow
class VertexFlowState(BaseModel):
    project_statement: str
    target_tech_stack: str
    company_vision: str = ""
    milestones: List[Dict[str, Any]] = []
    technical_blueprint: Dict[str, Any] = {}
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
    # Convert milestones back to string/json format for the CTO prompt
    milestones_str = str(state.milestones)
    blueprint = run_cto_agent(state.project_statement, state.target_tech_stack, milestones_str)
    return {
        "technical_blueprint": blueprint.model_dump(),
        "current_status": "CTO Architecture Blueprint Complete"
    }

# Build the LangGraph workflow
workflow = StateGraph(VertexFlowState)

# Add agent nodes
workflow.add_node("ceo_agent", ceo_node)
workflow.add_node("cto_agent", cto_node)

# Define the execution flow: Start -> CEO -> CTO -> END
workflow.set_entry_point("ceo_agent")
workflow.add_edge("ceo_agent", "cto_agent")
workflow.add_edge("cto_agent", END)

# Compile the graph into an executable app
vertex_flow_app = workflow.compile()
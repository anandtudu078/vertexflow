import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import our LangGraph compiled application
from backend.agents.workflow import vertex_flow_app
from backend.auth import UserOut, init_db, require_user
from backend.auth import router as auth_router
from backend.config import ConfigurationError, has_gemini_api_key

logger = logging.getLogger("vertexflow")

MISSING_KEY_DETAIL = (
    "The agent pipeline is not configured: GEMINI_API_KEY is missing. "
    "Add it to backend/.env or export it in your shell, then restart the API."
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    logger.info("Account database ready.")

    if has_gemini_api_key():
        logger.info("GEMINI_API_KEY detected; the CEO -> CTO -> PM -> Backend/Frontend -> Security pipeline is ready.")
    else:
        logger.warning(
            "GEMINI_API_KEY is not set. /api/projects/launch will return 503 until it is configured."
        )
    yield


# Initialize FastAPI application
app = FastAPI(title="VertexFlow Core Engine", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)

# Configure CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for incoming project requests
class ProjectBrief(BaseModel):
    project_statement: str
    target_tech_stack: str


@app.get("/")
async def root():
    return {"status": "online", "message": "VertexFlow Orchestration Engine is running."}


@app.post("/api/projects/launch")
def launch_project(brief: ProjectBrief, current_user: UserOut = Depends(require_user)):
    """
    Triggers the VertexFlow multi-agent StateGraph workflow:
    CEO Agent -> CTO Agent -> Product Manager Agent -> Final Output State
    """
    if not has_gemini_api_key():
        raise HTTPException(status_code=503, detail=MISSING_KEY_DETAIL)

    try:
        initial_state = {
            "project_statement": brief.project_statement,
            "target_tech_stack": brief.target_tech_stack,
            "company_vision": "",
            "milestones": [],
            "technical_blueprint": {},
            "product_requirements": {},
            "backend_code": {},
            "frontend_code": {},
            "security_audit": {},
            "current_status": "Starting Pipeline",
        }

        logger.info("Running the agent pipeline for %s", current_user.email)
        final_state = vertex_flow_app.invoke(initial_state)

        return {
            "status": "success",
            "current_status": final_state.get("current_status"),
            "vision": final_state.get("company_vision"),
            "milestones": final_state.get("milestones"),
            "technical_blueprint": final_state.get("technical_blueprint"),
            "product_requirements": final_state.get("product_requirements"),
            "backend_code": final_state.get("backend_code"),
            "frontend_code": final_state.get("frontend_code"),
            "security_audit": final_state.get("security_audit"),
        }

    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception as e:
        logger.exception("Agent pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/monitor/{project_id}")
async def websocket_monitor(websocket: WebSocket, project_id: str):
    await websocket.accept()
    try:
        await websocket.send_json({"role": "System", "status": "Connected to VertexFlow telemetry stream."})
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"echo": data})

    except WebSocketDisconnect:
        print(f"Client disconnected from project monitor: {project_id}")
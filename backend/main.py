import logging
import os
import uuid
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
        logger.info("GEMINI_API_KEY detected; the CEO -> CTO -> PM -> Backend/Frontend -> Security -> Sandbox pipeline is ready.")
    else:
        logger.warning(
            "GEMINI_API_KEY is not set. /api/projects/launch will return 503 until it is configured."
        )
    yield


# Initialize FastAPI application
app = FastAPI(title="VertexFlow Core Engine", version="1.0.0", lifespan=lifespan)
app.include_router(auth_router)


# Configure CORS for frontend communication - restricted origins for security*
# See: https://fastapi.tiangolo.com/tutorial/cors/#web-browser-same-origin
# WARNING: browsers reject wildcards with credentials (allow_credentials=True)
# so we use explicit origins rather than ["*"]
def _cors_origins() -> list[str]:
    origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    if os.getenv("VERTEXFLOW_CORS_ALLOW_ALL", "false").lower() == "true":
        origins.append("*")
    return origins


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# In-memory project state store for background polling.
# In production this would be a database (Redis, Postgres, etc.).
_PROJECT_STATES: dict[str, dict] = {}


# Pydantic models for incoming project requests
class ProjectBrief(BaseModel):
    project_statement: str
    target_tech_stack: str


@app.get("/")
async def root():
    return {"status": "online", "message": "VertexFlow Orchestration Engine is running."}


@app.get("/api/projects/{project_id}/status")
async def project_status(project_id: str) -> dict:
    """Poll the status of a background pipeline run."""
    state = _PROJECT_STATES.get(project_id)
    if not state:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "project_id": project_id,
        "status": state.get("status", "unknown"),
        "current_status": state.get("current_status"),
        "vision": state.get("vision"),
        "milestones": state.get("milestones"),
        "technical_blueprint": state.get("technical_blueprint"),
        "product_requirements": state.get("product_requirements"),
        "research_findings": state.get("research_findings"),
        "ui_ux_blueprint": state.get("ui_ux_blueprint"),
        "backend_code": state.get("backend_code"),
        "frontend_code": state.get("frontend_code"),
        "code_review": state.get("code_review"),
        "qa_report": state.get("qa_report"),
        "security_audit": state.get("security_audit"),
        "sandbox_result": state.get("sandbox_result"),
    }


@app.post("/api/projects/launch")
def launch_project(brief: ProjectBrief, current_user: UserOut = Depends(require_user)):
    """Triggers the VertexFlow multi-agent StateGraph workflow.

    CEO Agent -> CTO Agent -> Product Manager Agent -> Final Output State.
    Starts the pipeline in a background thread so the HTTP request returns
    immediately. The project_id can be used with /api/projects/{id}/status
    to poll for completion, or via the WebSocket monitor endpoint.
    """
    if not has_gemini_api_key():
        raise HTTPException(status_code=503, detail=MISSING_KEY_DETAIL)

    try:
        project_id = str(uuid.uuid4())[:8]
        initial_state = {
            "project_statement": brief.project_statement,
            "target_tech_stack": brief.target_tech_stack,
            "company_vision": "",
            "milestones": [],
            "technical_blueprint": {},
            "product_requirements": {},
            "ui_ux_blueprint": {},
            "research_findings": {},
            "backend_code": {},
            "frontend_code": {},
            "code_review": {},
            "qa_report": {},
            "security_audit": {},
            "sandbox_result": {},
            "current_status": "Starting Pipeline",
            "heal_iteration": 0,
            "security_feedback": "",
            "project_id": project_id,
        }

        logger.info("Running the agent pipeline for %s", current_user.email)
        # Store initial state so status endpoint can return something meaningful
        _PROJECT_STATES[project_id] = {
            "status": "pending",
            "current_status": "Starting Pipeline",
            "project_id": project_id,
        }
        # Run pipeline in background thread so the HTTP request returns right away
        import threading as _threading
        import json, os
        from pathlib import Path

        def _run_pipeline():
            try:
                final_state = vertex_flow_app.invoke(initial_state)
                # Persist final state so the status endpoint can return it
                marker_dir = Path("./output") / f"project_{project_id}"
                marker_dir.mkdir(parents=True, exist_ok=True)
                (marker_dir / "final_state.json").write_text(
                    json.dumps(final_state), encoding="utf-8"
                )
                _PROJECT_STATES[project_id].update(
                    {
                        "status": "success",
                        "current_status": final_state.get("current_status"),
                        "vision": final_state.get("company_vision"),
                        "milestones": final_state.get("milestones"),
                        "technical_blueprint": final_state.get("technical_blueprint"),
                        "product_requirements": final_state.get("product_requirements"),
                        "research_findings": final_state.get("research_findings"),
                        "ui_ux_blueprint": final_state.get("ui_ux_blueprint"),
                        "backend_code": final_state.get("backend_code"),
                        "frontend_code": final_state.get("frontend_code"),
                        "code_review": final_state.get("code_review"),
                        "qa_report": final_state.get("qa_report"),
                        "security_audit": final_state.get("security_audit"),
                        "sandbox_result": final_state.get("sandbox_result"),
                    }
                )
            except Exception as e:
                logger.exception("Background pipeline worker failed")
                _PROJECT_STATES[project_id].update(
                    {
                        "status": "error",
                        "current_status": "Pipeline failed",
                        "error": str(e),
                    }
                )

        _thread = _threading.Thread(target=_run_pipeline, daemon=True)
        _thread.start()

        return {
            "status": "pending",
            "project_id": project_id,
            "message": "Pipeline launched in background. Poll /api/projects/{project_id}/status or use WebSocket monitor.",
        }
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    except Exception as e:
        logger.exception("Agent pipeline failed")
        # Mask generic error to client; full traceback logged server-side
        raise HTTPException(status_code=500, detail="An unexpected error occurred.")


@app.websocket("/ws/monitor/{project_id}")
async def websocket_monitor(websocket: WebSocket, project_id: str):
    await websocket.accept()
  

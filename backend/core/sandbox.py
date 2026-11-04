import os
import sys
import subprocess
import socket
import time
from pathlib import Path
import logging

logger = logging.getLogger("vertexflow")

# Template for the React + Vite frontend app
_VITE_INDEX_HTML = """\
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>VertexFlow App</title>
    <script src="https://cdn.tailwindcss.com"></script>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

_VITE_MAIN_TSX = """\
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

_VITE_CONFIG = """\
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: FRONTEND_PORT,
    proxy: {
      '/api': 'http://127.0.0.1:BACKEND_PORT'
    }
  }
})
"""

_PACKAGE_JSON = """\
{
  "name": "vertexflow-generated-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@vitejs/plugin-react": "^4.0.0",
    "typescript": "^5.0.0",
    "vite": "^4.4.0"
  }
}
"""


def find_free_port() -> int:
    """Finds an available local port for running generated projects."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """Return True if something is already listening on host:port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def _wait_for_port(port: int, host: str = "127.0.0.1", retries: int = 15, delay: float = 1.0) -> bool:
    """Poll until the port is open or retries are exhausted."""
    for _ in range(retries):
        if _is_port_open(port, host):
            return True
        time.sleep(delay)
    return False


def scaffold_and_run_project(
    project_id: str,
    backend_code: dict,
    frontend_code: dict | None = None,
) -> dict:
    """
    1. Scaffolds backend (FastAPI) and frontend (React/Vite) files to disk.
    2. Installs Python dependencies.
    3. Launches the FastAPI server via uvicorn as a background subprocess.
    4. Scaffolds a Vite + React frontend wired to the backend via proxy.

    Returns a dict with project paths, ports, process PIDs, and run status.
    """
    base_dir = Path(f"./output/project_{project_id}")
    base_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1. Write backend files
    # ------------------------------------------------------------------
    module_name = backend_code.get("module_name", "main_router")
    models_code = backend_code.get("database_models_code", "# No models")
    endpoints_code = backend_code.get("api_endpoints_code", "# No endpoints")
    requirements: list[str] = backend_code.get("dependencies_required", ["fastapi", "uvicorn"])

    # Ensure uvicorn is always in the requirements list
    if "uvicorn" not in requirements:
        requirements.append("uvicorn")

    (base_dir / "models.py").write_text(models_code, encoding="utf-8")
    (base_dir / f"{module_name}.py").write_text(endpoints_code, encoding="utf-8")

    entrypoint_code = f"""\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from {module_name} import router as app_router

app = FastAPI(title="Generated VertexFlow App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(app_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
"""
    (base_dir / "app.py").write_text(entrypoint_code, encoding="utf-8")
    (base_dir / "requirements.txt").write_text("\n".join(requirements), encoding="utf-8")

    # ------------------------------------------------------------------
    # 2. Install Python dependencies
    # ------------------------------------------------------------------
    backend_port = find_free_port()

    pip_result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=str(base_dir),
        capture_output=True,
        text=True,
    )
    if pip_result.returncode != 0:
        logger.warning(f"pip install warnings for project {project_id}: {pip_result.stderr}")

    # ------------------------------------------------------------------
    # 3. Launch the FastAPI backend as a background subprocess
    # ------------------------------------------------------------------
    backend_log = open(base_dir / "backend.log", "w")
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(backend_port)],
        cwd=str(base_dir),
        stdout=backend_log,
        stderr=backend_log,
    )

    backend_ready = _wait_for_port(backend_port)
    backend_status = "Running" if backend_ready else "Failed to start (check backend.log)"

    logger.info(f"Backend for project {project_id} on port {backend_port}: {backend_status}")

    # ------------------------------------------------------------------
    # 4. Scaffold frontend (React + Vite)
    # ------------------------------------------------------------------
    frontend_port = find_free_port()
    frontend_dir = base_dir / "frontend"
    src_dir = frontend_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    # Write Vite config with port substitution
    vite_cfg = _VITE_CONFIG.replace("FRONTEND_PORT", str(frontend_port)).replace("BACKEND_PORT", str(backend_port))
    (frontend_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")
    (frontend_dir / "index.html").write_text(_VITE_INDEX_HTML, encoding="utf-8")
    (frontend_dir / "package.json").write_text(_PACKAGE_JSON, encoding="utf-8")
    (src_dir / "main.tsx").write_text(_VITE_MAIN_TSX, encoding="utf-8")

    # Use the LLM-generated component if available, otherwise write a default
    if frontend_code and frontend_code.get("react_tsx_code"):
        component_name = frontend_code.get("component_name", "App")
        app_tsx = frontend_code["react_tsx_code"]
        # If the generated code doesn't export a default, wrap it
        if "export default" not in app_tsx:
            app_tsx += f"\nexport default {component_name};"
    else:
        component_name = "App"
        app_tsx = f"""\
import React from 'react'

export default function App() {{
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl shadow p-8 max-w-lg w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">VertexFlow App</h1>
        <p className="text-gray-500 mb-4">
          Backend API is running at{' '}
          <a className="text-blue-600 underline" href="http://127.0.0.1:{backend_port}/docs" target="_blank">
            http://127.0.0.1:{backend_port}/docs
          </a>
        </p>
        <p className="text-sm text-gray-400">
          Replace this component with your generated UI.
        </p>
      </div>
    </div>
  )
}}
"""

    (src_dir / "App.tsx").write_text(app_tsx, encoding="utf-8")

    logger.info(f"Frontend scaffolded for project {project_id} at {frontend_dir.resolve()}")

    # ------------------------------------------------------------------
    # 5. Return full sandbox result
    # ------------------------------------------------------------------
    return {
        "project_path": str(base_dir.resolve()),
        "backend": {
            "port": backend_port,
            "pid": backend_proc.pid,
            "status": backend_status,
            "url": f"http://127.0.0.1:{backend_port}",
            "docs_url": f"http://127.0.0.1:{backend_port}/docs",
            "log": str((base_dir / "backend.log").resolve()),
        },
        "frontend": {
            "port": frontend_port,
            "status": "Scaffolded — run `npm install && npm run dev` to start",
            "path": str(frontend_dir.resolve()),
            "url": f"http://127.0.0.1:{frontend_port}",
        },
        "status": f"Backend {backend_status}. Frontend scaffolded.",
    }

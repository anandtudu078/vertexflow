import re
import os
import secrets
import sys
import subprocess
import socket
import time
from pathlib import Path
import logging

logger = logging.getLogger("vertexflow")

# ---------------------------------------------------------------------------
# Frontend templates
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def find_free_port() -> int:
    """Find an available local TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def _is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        return s.connect_ex((host, port)) == 0


def _wait_for_port(port: int, host: str = "127.0.0.1", retries: int = 20, delay: float = 1.0) -> bool:
    for _ in range(retries):
        if _is_port_open(port, host):
            return True
        time.sleep(delay)
    return False


# Fallback router module name when the agent's answer is unusable.
_DEFAULT_MODULE_NAME = "main_router"

# Filenames the scaffold writes itself: a router module with either name would
# overwrite models.py or app.py.
_RESERVED_MODULE_NAMES = {"app", "models"}


def _normalise_module_name(raw: str | None) -> str:
    """Turn an LLM-supplied module name into one importable flat module name.

    The backend agent sometimes answers with a path-like name ("app.main",
    "app/main.py", "src.routers.todos"). Written as-is that produced a file
    literally named `app.main.py` while app.py did `from app.main import ...`,
    so the import check failed with "'app' is not a package" and the backend
    never booted. Only the final segment survives, since the scaffold writes
    every module into one flat directory.
    """
    name = (raw or "").strip().strip("'\"")
    if name.endswith(".py"):
        name = name[: -len(".py")]
    name = re.split(r"[.\\/]", name)[-1]
    name = re.sub(r"\W", "_", name)
    if name[:1].isdigit():
        name = f"_{name}"

    if not name or not name.isidentifier() or name in _RESERVED_MODULE_NAMES:
        return _DEFAULT_MODULE_NAME
    return name


# Records "<pid> <port>" of the backend this scaffold started, so the next pass
# can stop it instead of leaking one uvicorn per self-healing iteration.
_PID_FILE = "backend.pid"

_ENV_FILE = ".env"


def _sandbox_env(base_dir: Path) -> dict[str, str]:
    """Environment for the generated app, including a dev signing secret.

    Generated routers routinely abort at import time when SECRET_KEY is unset
    (`raise RuntimeError('SECRET_KEY ... required')`), which failed the import
    check and left the pipeline reporting a backend that never booted. The
    secret is written to the project's .env for `load_dotenv()` and passed in
    the environment for code that reads os.environ directly. An existing .env
    is reused so heal cycles do not invalidate tokens from the previous pass.
    """
    env_path = base_dir / _ENV_FILE
    secret = ""
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            if key.strip() == "SECRET_KEY" and value.strip():
                secret = value.strip()
                break

    if not secret:
        secret = secrets.token_hex(32)
        header = "" if env_path.exists() else (
            "# VertexFlow sandbox dev settings — replace before deploying.\n"
        )
        with open(env_path, "a", encoding="utf-8") as env_fh:
            env_fh.write(f"{header}SECRET_KEY={secret}\n")

    return {
        **os.environ,
        "PYTHONPATH": str(base_dir.resolve()),
        "SECRET_KEY": secret,
    }


def _stop_previous_backend(base_dir: Path) -> None:
    """Stop the backend a previous scaffold of this project started, if any.

    Heal cycles re-scaffold into the same folder. Without this, every iteration
    left its server running on a new port. The recorded port is checked first so
    a stale PID file whose process already exited (and whose PID may have been
    reused by an unrelated process) is never signalled.
    """
    pid_path = base_dir / _PID_FILE
    if not pid_path.exists():
        return

    try:
        raw_pid, raw_port = pid_path.read_text(encoding="utf-8").split()
        pid, port = int(raw_pid), int(raw_port)
    except (OSError, ValueError):
        pid_path.unlink(missing_ok=True)
        return

    if _is_port_open(port):
        if sys.platform == "win32":
            # /T: uvicorn runs the app in a child process on Windows; killing only
            # the parent leaves the child holding the port.
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
        else:
            subprocess.run(["kill", "-TERM", str(pid)], capture_output=True)
        logger.info("Stopped previous backend pid %s on :%s for %s", pid, port, base_dir.name)

    pid_path.unlink(missing_ok=True)


# Names the scaffold runtime can provide when the generated models module omits them.
_RUNTIME_HELPER_NAMES = (
    "get_session",
    "SessionLocal",
    "engine",
    "init_db",
    "create_db_and_tables",
)

# Module names the LLM uses when referring to the models/database file. The
# `*_code` spellings are the blueprint's own field names, which the router used
# to import as if a module by that name existed on disk.
_MODEL_MODULE_ALIASES = {
    "models",
    "model",
    "database",
    "db",
    "schemas",
    "orm",
    "database_models",
    "db_models",
    "data_models",
    "database_models_code",
    "db_models_code",
    "data_models_code",
    "models_code",
}


def _local_package_prefixes(raw_module_name: str | None) -> tuple[str, ...]:
    """Leading segments of the package path the agent used for its own modules.

    The backend agent sometimes describes its code as a package ("todo_app.main"
    with `from todo_app.database_models import Task`). The scaffold writes flat
    files, so every import under that prefix has to be reduced to its last
    segment — otherwise app import dies with `No module named 'todo_app'`.
    """
    name = (raw_module_name or "").strip().strip("'\"")
    if name.endswith(".py"):
        name = name[: -len(".py")]
    parts = [part for part in re.split(r"[.\\/]", name) if part]
    return tuple(parts[:-1])


def _fix_imports(
    code: str,
    models_module: str,
    module_name: str | None = None,
    local_packages: tuple[str, ...] = (),
) -> str:
    """
    Rewrite LLM-generated code so it works as a flat (non-package) script.

    Problems fixed:
    1. Relative imports like `from .database import X` or `from .models import X`
       are rewritten to absolute: `from models import X` (or the actual module name).
    2. Common alias patterns the LLM uses for the models file
       (database, db, schemas, orm) are all remapped to the real module name —
       including *absolute* imports such as `from database import get_session`.
    3. Self-imports of the router module (`from todos import Task` inside todos.py)
       are remapped to the models module as well.
    4. The agent's own package prefix is dropped: `from todo_app.database_models
       import Task` becomes `from models import Task`, since only models.py and
       the router module exist on disk.
    5. Any remaining leading dot on an import is stripped.
    """
    local_modules = set(_MODEL_MODULE_ALIASES)
    if module_name:
        # The router module importing from itself is always meant to be the models
        local_modules.add(module_name)

    def replace_module(match: re.Match) -> str:
        indent, from_part = match.group(1), match.group(2).strip()
        bare = from_part.lstrip(".")

        # Duck typing the agent's package: anything below that prefix is one of
        # its own modules, and the only local module besides the router is models.
        is_local = False
        for prefix in local_packages:
            if bare == prefix or bare.startswith(f"{prefix}."):
                bare = bare[len(prefix):].lstrip(".")
                is_local = True
                break

        # Everything that points at the generated models file (directly, through
        # a common alias, as a self-import, or as a submodule of the agent's own
        # package) collapses onto models_module.
        if (
            not bare
            or is_local
            or bare in local_modules
            or bare in _MODEL_MODULE_ALIASES
        ):
            target = models_module
        else:
            target = bare
        return f"{indent}from {target} import "

    # Matches `from <module> import ...` on any line (also indented / multi-line
    # parenthesised imports, since only the module token is rewritten).
    code = re.sub(
        r"(?m)^(\s*)from\s+(\.*[\w.]+)\s+import\s+",
        replace_module,
        code,
    )

    return code


# `session: Session = Depends()` — an empty Depends() whose annotation is a SQLModel type.
_EMPTY_SESSION_DEPENDENCY = re.compile(r":\s*(?:sqlmodel\.)?Session\s*=\s*Depends\(\s*\)")

# camelCase spellings the LLM uses for SQLModel/SQLAlchemy field options.
_MODEL_FIELD_ALIASES = {
    "foreignKey": "foreign_key",
    "primaryKey": "primary_key",
}


# Column kwargs the agent puts in `sa_column_kwargs` that SQLAlchemy rejects
# there (it raises "Additional arguments should be named <dialect>_<arg>").
_UNSUPPORTED_COLUMN_KWARGS = ("ondelete", "onupdate")

_SA_COLUMN_KWARGS = re.compile(r"sa_column_kwargs\s*=\s*\{([^{}]*)\}")


def _fix_sa_column_kwargs(code: str) -> str:
    """Drop Column kwargs SQLAlchemy does not accept on a mapped column.

    `Field(foreign_key="users.id", sa_column_kwargs={"ondelete": "CASCADE"})`
    parses, but building the mapper raises
    "Additional arguments should be named <dialectname>_<argument>, got 'ondelete'"
    and the whole app fails to import. ON DELETE belongs on the ForeignKey, which
    SQLModel's Field does not expose, so the honest repair is to drop it and keep
    the rest of the kwargs (stripping `ondelete`/`onupdate` only).
    """
    def repair(match: re.Match) -> str:
        entries = [entry.strip() for entry in match.group(1).split(",") if entry.strip()]
        kept: list[str] = []
        for entry in entries:
            key = re.match(r"^['\"]?(\w+)['\"]?\s*[:=]", entry)
            if key and key.group(1) in _UNSUPPORTED_COLUMN_KWARGS:
                continue
            kept.append(entry)
        body = ", ".join(kept)
        if body == match.group(1).strip():
            return match.group(0)
        logger.info("Dropped unsupported column kwargs from sa_column_kwargs: %s", ", ".join(
            entry for entry in entries if entry not in kept
        ))
        return f"sa_column_kwargs={{{body}}}"

    return _SA_COLUMN_KWARGS.sub(repair, code)


def _fix_models_code(code: str) -> str:
    """Normalise the field keyword spellings SQLModel actually accepts."""
    for wrong, right in _MODEL_FIELD_ALIASES.items():
        code = re.sub(rf"\b{wrong}\b", right, code)
    return _fix_sa_column_kwargs(code)


def _apply_requirement_pins(requirements: list[str]) -> list[str]:
    """Pin transitive dependencies that generated code routinely pairs incompatibly.

    passlib 1.7.4 (unmaintained) breaks against bcrypt >= 4.1: its backend probe
    hashes a >72-byte secret and newer bcrypt raises ValueError, so every password
    hash returns 500. Generated code that imports passlib therefore gets a bcrypt pin.
    """
    if not any(r.lower().startswith("passlib") for r in requirements):
        return requirements

    pinned: list[str] = []
    for requirement in requirements:
        if requirement.lower().startswith("bcrypt") and not re.search(r"[<>=!~]", requirement):
            requirement = "bcrypt<4.1"
        pinned.append(requirement)

    if not any(r.lower().startswith("bcrypt") for r in pinned):
        pinned.append("bcrypt<4.1")
    return pinned


def _fix_session_dependencies(code: str, models_module: str = "models") -> tuple[str, bool]:
    """Give `session: Session = Depends()` a real source of sessions.

    With no callable, FastAPI uses the *annotation* as the dependency, so it
    introspects SQLModel's `Session` as a Pydantic model and OpenAPI generation
    dies with `_SessionBind is not fully defined` — a 500 on /docs and
    /openapi.json while the server still reports itself as running.

    Returns the rewritten code and whether the models module must supply
    `get_session`. `Depends()` on a class (OAuth2PasswordRequestForm) is valid
    FastAPI usage and is deliberately left alone.
    """
    fixed, replacements = _EMPTY_SESSION_DEPENDENCY.subn(": Session = Depends(get_session)", code)
    if not replacements:
        return code, False

    already_available = _defines(fixed, "get_session") or "get_session" in _imported_from_module(
        fixed, models_module
    )
    if not already_available:
        fixed = f"from {models_module} import get_session\n{fixed}"
    return fixed, True


def _imported_from_module(code: str, module_name: str) -> set[str]:
    """Collect the names a module imports from `module_name`."""
    imported: set[str] = set()
    # Handles both `from models import A, B` and parenthesised multi-line imports.
    pattern = rf"(?ms)^\s*from\s+{re.escape(module_name)}\s+import\s+(\([^)]*\)|[^\n(]+)"
    for match in re.finditer(pattern, code):
        raw = match.group(1).replace("(", " ").replace(")", " ")
        for part in raw.split(","):
            # Strip inline comments so "get_session  # comment" becomes "get_session"
            name = part.strip().split(" as ")[0].strip()
            name = name.split("#")[0].strip()
            if name and name != "*":
                imported.add(name)
    return imported


def _defines(models_code: str, name: str) -> bool:
    """True when the models module already defines `name`."""
    return re.search(rf"(?m)^\s*(?:def\s+{re.escape(name)}\b|{re.escape(name)}\s*=)", models_code) is not None


def _ensure_model_runtime(
    models_code: str,
    endpoints_code: str,
    models_module: str = "models",
    required: tuple[str, ...] = (),
) -> str:
    """Append the database plumbing the generated router imports but the models module omits.

    Gemini frequently writes `from database import get_session` (or similar) while only
    emitting model classes, so the scaffolded app would raise ImportError on boot.
    `required` forces helpers that the router needs but never imports by name (it
    writes `Depends()` instead, see `_fix_session_dependencies`).
    """
    imported = _imported_from_module(endpoints_code, models_module)
    wanted = imported | set(required)
    missing = {n for n in _RUNTIME_HELPER_NAMES if n in wanted and not _defines(models_code, n)}
    if not missing:
        return models_code

    use_sqlmodel = "SQLModel" in models_code and "declarative_base" not in models_code
    lines = ["", "", "# --- VertexFlow scaffold runtime: database plumbing imported by the router ---"]

    if use_sqlmodel:
        lines.append("from sqlmodel import Session, SQLModel, create_engine")
        lines.append("")
        lines.append('DATABASE_URL = "sqlite:///./app.db"')
        if "engine" in missing or not _defines(models_code, "engine"):
            lines.append(
                "engine = create_engine(DATABASE_URL, connect_args={\"check_same_thread\": False})"
            )
        lines.append("")
        if "create_db_and_tables" in missing:
            lines.append("")
            lines.append("def create_db_and_tables() -> None:")
            lines.append("    SQLModel.metadata.create_all(engine)")
            lines.append("")
        if "get_session" in missing:
            lines.append("")
            lines.append("def get_session():")
            lines.append("    with Session(engine) as session:")
            lines.append("        yield session")
            lines.append("")
        if "SessionLocal" in missing:
            lines.append("")
            lines.append("def SessionLocal():")
            lines.append("    return Session(engine)")
            lines.append("")
    else:
        lines.append("from sqlalchemy import create_engine")
        lines.append("from sqlalchemy.orm import sessionmaker")
        lines.append("")
        lines.append('DATABASE_URL = "sqlite:///./app.db"')
        if "engine" in missing or not _defines(models_code, "engine"):
            lines.append(
                "engine = create_engine(DATABASE_URL, connect_args={\"check_same_thread\": False})"
            )
        lines.append("")
        if "SessionLocal" in missing:
            lines.append(
                "SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)"
            )
            lines.append("")
        if "get_session" in missing:
            lines.append("")
            lines.append("def get_session():")
            lines.append("    session = SessionLocal()")
            lines.append("    try:")
            lines.append("        yield session")
            lines.append("    finally:")
            lines.append("        session.close()")
            lines.append("")
        if "init_db" in missing:
            lines.append("")
            lines.append("def init_db() -> None:")
            lines.append("    Base.metadata.create_all(engine)")
            lines.append("")

    logger.info("Added scaffold runtime helpers to %s.py: %s", models_module, ", ".join(sorted(missing)))
    return models_code.rstrip() + "\n" + "\n".join(lines) + "\n"


def _router_export_name(router_code: str) -> str:
    """Name under which the generated module exposes its routes.

    The agent usually returns an `APIRouter` called `router`, but it sometimes
    returns a finished `FastAPI` app called `app` — importing `router` from that
    module fails at startup with `cannot import name 'router'`.
    """
    if re.search(r"(?m)^\s*router\s*(?::[^=\n]+)?=", router_code):
        return "router"
    if re.search(r"(?m)^\s*app\s*(?::[^=\n]+)?=", router_code):
        return "app"
    return "router"


def _build_entrypoint(
    module_name: str,
    models_code: str,
    models_module: str,
    router_code: str = "",
) -> str:
    """Generate app.py that boots the FastAPI app correctly.

    The startup hook only imports helpers that the models module actually defines,
    so a missing `create_db_and_tables` / `SQLModel` symbol cannot break app import.
    It is also emitted *after* `app` exists, because the decorator evaluates eagerly.
    """
    export = _router_export_name(router_code)
    if export == "app":
        # A complete FastAPI app: borrow its routes instead of expecting a router.
        include_line = "app.include_router(app_router.router)"
    else:
        include_line = "app.include_router(app_router)"
    startup_imports: list[str] = []
    startup_lines: list[str] = []

    if "create_db_and_tables" in models_code:
        startup_imports.append("create_db_and_tables")
        startup_lines.append("    create_db_and_tables()")
    elif _defines(models_code, "init_db"):
        startup_imports.append("init_db")
        startup_lines.append("    init_db()")
    elif "SQLModel" in models_code and _defines(models_code, "engine"):
        startup_imports += ["SQLModel", "engine"]
        startup_lines.append("    SQLModel.metadata.create_all(engine)")
    elif _defines(models_code, "Base") and _defines(models_code, "engine"):
        startup_imports += ["Base", "engine"]
        startup_lines.append("    Base.metadata.create_all(engine)")

    db_init_block = ""
    if startup_lines:
        db_init_block = (
            f"\nfrom {models_module} import {', '.join(startup_imports)}\n"
            "\n\n@app.on_event(\"startup\")\ndef on_startup():\n"
            "    # Create database tables on first boot\n"
            + "\n".join(startup_lines)
            + "\n"
        )

    return f"""\
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from {module_name} import {export} as app_router

app = FastAPI(title="Generated VertexFlow App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

{include_line}
{db_init_block}
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
"""


# ---------------------------------------------------------------------------
# Main scaffolding function
# ---------------------------------------------------------------------------

def scaffold_and_run_project(
    project_id: str,
    backend_code: dict,
    frontend_code: dict | None = None,
) -> dict:
    """
    1. Write backend files, fixing relative imports so flat scripts work.
    2. Install Python dependencies using the current interpreter.
    3. Launch the FastAPI server via uvicorn as a background subprocess.
    4. Scaffold a Vite + React frontend wired to the backend via proxy.
    """
    base_dir = Path(f"./output/project_{project_id}")
    base_dir.mkdir(parents=True, exist_ok=True)
    _stop_previous_backend(base_dir)

    # Heal cycles re-scaffold into this folder and the LLM picks a different
    # module name each pass, so drop stale router modules instead of leaving
    # dead (sometimes unparsable) files next to the one app.py imports.
    for stale in base_dir.glob("*.py"):
        if stale.name not in {"app.py", "models.py"}:
            stale.unlink()

    # ------------------------------------------------------------------
    # 1. Extract generated code
    # ------------------------------------------------------------------
    raw_module_name = backend_code.get("module_name")
    module_name   = _normalise_module_name(raw_module_name)
    local_packages = _local_package_prefixes(raw_module_name)
    models_code   = backend_code.get("database_models_code", "# No models")
    endpoints_code = backend_code.get("api_endpoints_code", "# No endpoints")
    requirements: list[str] = backend_code.get("dependencies_required", [])

    # Always ensure these core deps are present
    for dep in ("fastapi", "uvicorn", "sqlmodel"):
        if not any(dep in r.lower() for r in requirements):
            requirements.append(dep)

    requirements = _apply_requirement_pins(requirements)

    # The models file is always written as models.py; fix any alias the LLM used
    models_module = "models"

    # Normalise every reference to the models file (relative, absolute alias,
    # self-import) and backfill DB helpers the router expects.
    models_code    = _fix_imports(models_code, models_module, module_name, local_packages)
    endpoints_code = _fix_imports(endpoints_code, models_module, module_name, local_packages)
    endpoints_code, needs_session_helper = _fix_session_dependencies(endpoints_code, models_module)
    models_code    = _fix_models_code(models_code)
    models_code    = _ensure_model_runtime(
        models_code,
        endpoints_code,
        models_module,
        required=("get_session",) if needs_session_helper else (),
    )

    # ------------------------------------------------------------------
    # 2. Write files to disk
    # ------------------------------------------------------------------
    (base_dir / "models.py").write_text(models_code, encoding="utf-8")
    (base_dir / f"{module_name}.py").write_text(endpoints_code, encoding="utf-8")
    (base_dir / "app.py").write_text(
        _build_entrypoint(module_name, models_code, models_module, endpoints_code),
        encoding="utf-8",
    )
    (base_dir / "requirements.txt").write_text("\n".join(requirements), encoding="utf-8")
    sandbox_env = _sandbox_env(base_dir)

    logger.info(f"Scaffolded project {project_id} at {base_dir.resolve()}")

    # ------------------------------------------------------------------
    # 3. Install Python dependencies in an isolated per-project venv.
    #    This prevents generated dependencies from mutating the host environment.
    # ------------------------------------------------------------------
    venv_dir = base_dir / ".venv"
    if not venv_dir.exists():
        import venv as _mod_venv
        venv_dir.mkdir(parents=True, exist_ok=True)
        _mod_venv.cli_main(["--without-pip", "--clear", "create", str(venv_dir)])

    pip_path = str(venv_dir / "bin" if hasattr(venv_dir, "joinpath") else "Scripts")
    pip = [os.path.join(pip_path, "python") if hasattr(venv_dir, "joinpath") else os.path.join(pip_path, "python.exe")]
    pip_result = subprocess.run(
        pip + ["-m", "pip", "install", "-r", "requirements.txt", "-q"],
        cwd=str(base_dir.resolve()),
        capture_output=True,
        text=True,
    )
    if pip_result.returncode != 0:
        logger.warning(f"pip install stderr for {project_id}:\n{pip_result.stderr}")
    else:
        logger.info(f"pip install OK for {project_id}")

    # ------------------------------------------------------------------
    # 4. Quick import-check before spawning the server
    #    Catches syntax errors and bad imports without waiting for uvicorn
    # ------------------------------------------------------------------
    check = subprocess.run(
        [sys.executable, "-c", "import app"],
        cwd=str(base_dir.resolve()),
        capture_output=True,
        text=True,
        env=sandbox_env,
    )
    if check.returncode != 0:
        import_error = check.stderr.strip()
        logger.error(f"Import check failed for {project_id}:\n{import_error}")
        return {
            "project_path": str(base_dir.resolve()),
            "assigned_port": None,
            "backend": {
                "port": None,
                "pid": None,
                "status": "Import error — see import_error field",
                "import_error": import_error,
                "url": None,
                "docs_url": None,
            },
            "frontend": _scaffold_frontend(base_dir, frontend_code, 0, find_free_port()),
            "status": f"Backend failed import check: {import_error.splitlines()[-1]}",
        }

    # ------------------------------------------------------------------
    # 5. Launch FastAPI backend
    # ------------------------------------------------------------------
    backend_port = find_free_port()
    log_path = base_dir / "backend.log"

    with open(log_path, "w", encoding="utf-8") as log_fh:
        backend_proc = subprocess.Popen(
            [
                sys.executable, "-m", "uvicorn", "app:app",
                "--host", "127.0.0.1",
                "--port", str(backend_port),
            ],
            cwd=str(base_dir.resolve()),
            stdout=log_fh,
            stderr=log_fh,
            env=sandbox_env,
        )

    backend_ready = _wait_for_port(backend_port)
    if not backend_ready:
        # Read the log to surface the real error
        try:
            log_tail = log_path.read_text(encoding="utf-8").strip()
        except Exception:
            log_tail = "(log unreadable)"
        backend_status = "Failed to start"
        logger.error(f"Backend failed for {project_id}:\n{log_tail}")
    else:
        backend_status = "Running"
        log_tail = ""

    logger.info(f"Backend for project {project_id} on :{backend_port} → {backend_status}")
    if backend_ready:
        (base_dir / _PID_FILE).write_text(f"{backend_proc.pid} {backend_port}", encoding="utf-8")

    # ------------------------------------------------------------------
    # 6. Scaffold frontend
    # ------------------------------------------------------------------
    frontend_port = find_free_port()
    frontend_info = _scaffold_frontend(base_dir, frontend_code, backend_port, frontend_port)

    # ------------------------------------------------------------------
    # 7. Return result
    # ------------------------------------------------------------------
    result: dict = {
        "project_path": str(base_dir.resolve()),
        # Flat alias kept for the UI contract (frontend `SandboxResult`), which
        # reads `assigned_port` rather than `backend.port`.
        "assigned_port": backend_port,
        "backend": {
            "port": backend_port,
            "pid": backend_proc.pid,
            "status": backend_status,
            "url": f"http://127.0.0.1:{backend_port}",
            "docs_url": f"http://127.0.0.1:{backend_port}/docs",
            "log": str(log_path.resolve()),
        },
        "frontend": frontend_info,
        "status": f"Backend {backend_status}. Frontend scaffolded.",
    }

    if log_tail:
        result["backend"]["startup_error"] = log_tail.splitlines()[-5:]  # last 5 lines

    return result


def _scaffold_frontend(
    base_dir: Path,
    frontend_code: dict | None,
    backend_port: int,
    frontend_port: int,
) -> dict:
    """Write Vite + React frontend files and return info dict."""
    frontend_dir = base_dir / "frontend"
    src_dir = frontend_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)

    vite_cfg = (
        _VITE_CONFIG
        .replace("FRONTEND_PORT", str(frontend_port))
        .replace("BACKEND_PORT", str(backend_port))
    )
    (frontend_dir / "vite.config.ts").write_text(vite_cfg, encoding="utf-8")
    (frontend_dir / "index.html").write_text(_VITE_INDEX_HTML, encoding="utf-8")
    (frontend_dir / "package.json").write_text(_PACKAGE_JSON, encoding="utf-8")

    # The frontend blueprint calls the component field `react_code`; older
    # payloads used `react_tsx_code`. Reading only the latter meant generated
    # UI was silently dropped in favour of the placeholder below.
    component_source = ""
    styling_css = ""
    if frontend_code:
        component_source = (
            frontend_code.get("react_tsx_code") or frontend_code.get("react_code") or ""
        )
        styling_css = frontend_code.get("styling_css") or ""

    main_tsx = _VITE_MAIN_TSX
    if styling_css:
        (src_dir / "styles.css").write_text(styling_css, encoding="utf-8")
        main_tsx = "import './styles.css'\n" + main_tsx
    (src_dir / "main.tsx").write_text(main_tsx, encoding="utf-8")

    if component_source:
        component_name = frontend_code.get("component_name") or "App"
        app_tsx = component_source
        if "export default" not in app_tsx:
            app_tsx += f"\nexport default {component_name};\n"
    else:
        app_tsx = f"""\
import React from 'react'

export default function App() {{
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8">
      <div className="bg-white rounded-2xl shadow p-8 max-w-lg w-full">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">VertexFlow App</h1>
        <p className="text-gray-500 mb-4">
          Backend API →{{' '}}
          <a className="text-blue-600 underline"
             href="http://127.0.0.1:{backend_port}/docs"
             target="_blank" rel="noreferrer">
            http://127.0.0.1:{backend_port}/docs
          </a>
        </p>
      </div>
    </div>
  )
}}
"""

    (src_dir / "App.tsx").write_text(app_tsx, encoding="utf-8")

    return {
        "port": frontend_port,
        "status": "Scaffolded — run `npm install && npm run dev` to start",
        "path": str(frontend_dir.resolve()),
        "url": f"http://127.0.0.1:{frontend_port}",
    }

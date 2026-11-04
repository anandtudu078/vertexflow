"""Tests for the scaffold repair layer in `backend.core.sandbox`.

The fixtures mirror code Gemini actually emitted for a todo app — the run that
produced `ModuleNotFoundError: No module named 'database'` and a backend that
never booted. Each test pins one repair step, so a regression shows up here
instead of as a pipeline that reports success while shipping a dead backend.
"""

import ast

import pytest

from backend.core.sandbox import (
    _apply_requirement_pins,
    _build_entrypoint,
    _ensure_model_runtime,
    _fix_imports,
    _fix_models_code,
    _fix_sa_column_kwargs,
    _fix_session_dependencies,
    _normalise_module_name,
    _sandbox_env,
    _stop_previous_backend,
)

ROUTER_MODULE = "todos"
MODELS_MODULE = "models"

# Abridged from output/project_a914d251/todos.py: absolute alias import plus a
# self-referential import of the models it defines itself.
GENERATED_ROUTER = """\
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlmodel import Session, select

from database import get_session
from models import Task, TaskCreate, User

router = APIRouter()
"""

# Abridged from output/project_a914d251/models.py: model classes only, no engine
# and no session helper, plus the camelCase field option SQLModel rejects.
GENERATED_MODELS = """\
from typing import Optional

from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)


class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    user_id: int = Field(foreignKey="user.id")
"""

# `scaffold_and_run_project` repairs imports before backfilling helpers, so the
# runtime step only ever sees imports that already point at the models module.
FIXED_ROUTER = _fix_imports(GENERATED_ROUTER, MODELS_MODULE, ROUTER_MODULE)


# ---------------------------------------------------------------------------
# Import repair
# ---------------------------------------------------------------------------

def test_fix_imports_remaps_absolute_alias_import():
    fixed = _fix_imports(GENERATED_ROUTER, MODELS_MODULE, ROUTER_MODULE)

    assert "from models import get_session" in fixed
    assert "from database import" not in fixed


def test_fix_imports_remaps_router_self_import():
    code = "from todos import Task, User\n"

    fixed = _fix_imports(code, MODELS_MODULE, ROUTER_MODULE)

    assert fixed.strip() == "from models import Task, User"


def test_fix_imports_remaps_relative_parenthesised_import():
    code = "from .database import (\n    SessionLocal,\n    init_db,\n)\n"

    fixed = _fix_imports(code, MODELS_MODULE)

    assert fixed == "from models import (\n    SessionLocal,\n    init_db,\n)\n"


def test_fix_imports_remaps_bare_relative_package_import():
    fixed = _fix_imports("from . import Base\n", MODELS_MODULE)

    assert fixed.strip() == "from models import Base"


def test_fix_imports_rewrites_indented_imports():
    code = "def get_db():\n    from database import get_session\n    return get_session\n"

    assert "from models import get_session" in _fix_imports(code, MODELS_MODULE)


def test_fix_imports_flattens_imports_under_the_agents_own_package():
    code = "from todo_app.database_models import SQLModel, Task, User, engine\n"

    fixed = _fix_imports(code, MODELS_MODULE, "main", local_packages=("todo_app",))

    assert fixed.strip() == "from models import SQLModel, Task, User, engine"


def test_fix_imports_leaves_third_party_imports_untouched():
    fixed = _fix_imports(GENERATED_ROUTER, MODELS_MODULE, ROUTER_MODULE)

    assert "from fastapi import APIRouter, Depends, HTTPException" in fixed
    assert "from sqlmodel import Session, select" in fixed
    assert "from passlib.context import CryptContext" in fixed
    assert "from datetime import datetime" in fixed


# ---------------------------------------------------------------------------
# Module naming
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "raw,expected",
    [
        ("todos", "todos"),
        ("  todos  ", "todos"),
        # The regression from _verify.log: the agent answered "app.main", the
        # scaffold wrote app.main.py and app.py imported "app.main".
        ("app.main", "main"),
        ("app/main.py", "main"),
        ("src.routers.todos", "todos"),
        ("main.py", "main"),
    ],
)
def test_normalise_module_name_reduces_to_a_flat_module(raw, expected):
    assert _normalise_module_name(raw) == expected


@pytest.mark.parametrize("raw", [None, "", "   ", "app", "models", "2fa"])
def test_normalise_module_name_falls_back_when_unusable(raw):
    name = _normalise_module_name(raw)

    assert name.isidentifier()
    assert name not in {"app", "models"}


def test_nested_module_name_still_yields_an_importable_entrypoint():
    name = _normalise_module_name("app.main")

    app_code = _build_entrypoint(name, "class Foo:\n    pass\n", MODELS_MODULE)

    ast.parse(app_code)
    assert f"from {name} import router as app_router" in app_code
    assert "from app.main import" not in app_code


# ---------------------------------------------------------------------------
# Model normalisation
# ---------------------------------------------------------------------------

def test_fix_models_code_normalises_camel_case_field_kwargs():
    fixed = _fix_models_code(GENERATED_MODELS)

    assert 'Field(foreign_key="user.id")' in fixed
    assert "foreignKey" not in fixed


def test_fix_models_code_leaves_lookalike_identifiers_alone():
    code = "myForeignKey = 1\nprimary_keys = []\n"

    assert _fix_models_code(code) == code


def test_fix_sa_column_kwargs_drops_ondelete_that_sqlalchemy_rejects():
    # From the live run: import died with "Additional arguments should be named
    # <dialectname>_<argument>, got 'ondelete'" while building the mapper.
    code = "    user_id: int = Field(foreign_key='users.id', sa_column_kwargs={'ondelete': 'CASCADE'})\n"

    fixed = _fix_sa_column_kwargs(code)

    ast.parse("class Task:\n" + fixed)
    assert "ondelete" not in fixed
    assert "sa_column_kwargs={}" in fixed


def test_fix_sa_column_kwargs_keeps_supported_kwargs():
    code = "    a: int = Field(sa_column_kwargs={'index': True, 'onupdate': 'now()'})\n"

    fixed = _fix_sa_column_kwargs(code)

    ast.parse("class Task:\n" + fixed)
    assert "sa_column_kwargs={'index': True}" in fixed


def test_fix_sa_column_kwargs_is_a_noop_without_the_keyword():
    code = "    title: str = Field(max_length=200)\n"

    assert _fix_sa_column_kwargs(code) == code


# ---------------------------------------------------------------------------
# Session dependencies
# ---------------------------------------------------------------------------

def test_fix_session_dependencies_replaces_empty_depends_on_session():
    code = "def read_tasks(session: Session = Depends()):\n    return session\n"

    fixed, needs_helper = _fix_session_dependencies(code)

    assert needs_helper is True
    assert "session: Session = Depends(get_session)" in fixed
    assert fixed.startswith("from models import get_session\n")


def test_fix_session_dependencies_leaves_class_dependencies_alone():
    # A no-argument Depends() on a class is valid FastAPI usage.
    code = "def login(form_data: OAuth2PasswordRequestForm = Depends()):\n    return form_data\n"

    assert _fix_session_dependencies(code) == (code, False)


def test_fix_session_dependencies_does_not_duplicate_the_models_import():
    code = "from models import get_session\n\ndef read(session: Session = Depends()): ...\n"

    fixed, _ = _fix_session_dependencies(code)

    assert fixed.count("from models import get_session") == 1


def test_fix_session_dependencies_handles_qualified_session_annotation():
    code = "def read(session: sqlmodel.Session = Depends()): ...\n"

    fixed, needs_helper = _fix_session_dependencies(code)

    assert needs_helper is True
    assert "Depends(get_session)" in fixed


# ---------------------------------------------------------------------------
# Sandbox environment
# ---------------------------------------------------------------------------

def test_sandbox_env_provisions_a_dev_secret_key(tmp_path):
    env = _sandbox_env(tmp_path)

    secret = env["SECRET_KEY"]
    assert len(secret) >= 32
    assert f"SECRET_KEY={secret}" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_sandbox_env_reuses_the_secret_of_an_existing_env_file(tmp_path):
    (tmp_path / ".env").write_text("SECRET_KEY=existing-secret\n", encoding="utf-8")

    assert _sandbox_env(tmp_path)["SECRET_KEY"] == "existing-secret"
    assert (tmp_path / ".env").read_text(encoding="utf-8") == "SECRET_KEY=existing-secret\n"


def test_sandbox_env_appends_the_secret_to_an_env_file_that_lacks_one(tmp_path):
    (tmp_path / ".env").write_text("DATABASE_URL=sqlite:///./app.db\n", encoding="utf-8")

    secret = _sandbox_env(tmp_path)["SECRET_KEY"]

    contents = (tmp_path / ".env").read_text(encoding="utf-8")
    assert contents.startswith("DATABASE_URL=sqlite:///./app.db\n")
    assert f"SECRET_KEY={secret}" in contents


# ---------------------------------------------------------------------------
# Runtime helper backfill
# ---------------------------------------------------------------------------


def test_ensure_model_runtime_adds_session_helpers_the_router_imports():
    models = _ensure_model_runtime(GENERATED_MODELS, FIXED_ROUTER)

    ast.parse(models)  # the appended block must stay valid Python
    assert "def get_session():" in models
    assert "engine = create_engine(" in models
    assert "class Task(SQLModel, table=True):" in models


def test_ensure_model_runtime_handles_declarative_models():
    declarative_models = """\
from sqlalchemy import Column, Integer
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Task(Base):
    __tablename__ = "task"
    id = Column(Integer, primary_key=True)
"""

    models = _ensure_model_runtime(declarative_models, "from models import SessionLocal, init_db\n")

    ast.parse(models)
    assert "SessionLocal = sessionmaker(" in models
    assert "def init_db() -> None:" in models
    assert "Base.metadata.create_all(engine)" in models


def test_ensure_model_runtime_adds_helpers_that_are_required_but_never_imported():
    models = _ensure_model_runtime(GENERATED_MODELS, "endpoints = []\n", required=("get_session",))

    ast.parse(models)
    assert "def get_session():" in models
    assert "engine = create_engine(" in models


def test_ensure_model_runtime_is_noop_when_helpers_exist():
    models_with_plumbing = (
        GENERATED_MODELS
        + "\nengine = create_engine(DATABASE_URL)\n"
        + "\ndef get_session():\n    yield None\n"
    )

    assert _ensure_model_runtime(models_with_plumbing, FIXED_ROUTER) == models_with_plumbing


# ---------------------------------------------------------------------------
# Entrypoint generation
# ---------------------------------------------------------------------------

def test_build_entrypoint_creates_tables_after_app_is_defined():
    models = _ensure_model_runtime(GENERATED_MODELS, FIXED_ROUTER)

    app_code = _build_entrypoint(ROUTER_MODULE, models, MODELS_MODULE)

    ast.parse(app_code)
    assert app_code.index("app = FastAPI(") < app_code.index("@app.on_event")
    assert "from models import SQLModel, engine" in app_code
    assert "SQLModel.metadata.create_all(engine)" in app_code


def test_build_entrypoint_prefers_create_db_and_tables_when_present():
    models = GENERATED_MODELS + (
        "\n\ndef create_db_and_tables() -> None:\n"
        "    SQLModel.metadata.create_all(engine)\n"
    )

    app_code = _build_entrypoint(ROUTER_MODULE, models, MODELS_MODULE)

    assert "from models import create_db_and_tables" in app_code
    assert "    create_db_and_tables()" in app_code
    assert "import SQLModel" not in app_code


def test_build_entrypoint_skips_startup_hook_without_a_database_layer():
    app_code = _build_entrypoint(ROUTER_MODULE, "class Foo:\n    pass\n", MODELS_MODULE)

    ast.parse(app_code)
    assert "@app.on_event" not in app_code
    assert "from models import" not in app_code


# ---------------------------------------------------------------------------
# Dependency pins
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "requirements",
    [
        ["fastapi", "passlib", "bcrypt"],
        ["fastapi", "passlib[bcrypt]"],
    ],
)
def test_apply_requirement_pins_pins_bcrypt_with_passlib(requirements):
    pinned = _apply_requirement_pins(requirements)

    assert "bcrypt<4.1" in pinned
    assert not any(r.startswith("bcrypt") and r != "bcrypt<4.1" for r in pinned)


def test_apply_requirement_pins_keeps_other_requirements():
    pinned = _apply_requirement_pins(["fastapi", "passlib", "python-jose[cryptography]"])

    assert pinned == ["fastapi", "passlib", "python-jose[cryptography]", "bcrypt<4.1"]


def test_apply_requirement_pins_ignores_projects_without_passlib():
    requirements = ["fastapi", "uvicorn", "sqlmodel"]

    assert _apply_requirement_pins(requirements) == requirements


def test_apply_requirement_pins_respects_explicit_bcrypt_constraint():
    requirements = ["passlib", "bcrypt==4.0.1"]

    assert _apply_requirement_pins(requirements) == requirements


# ---------------------------------------------------------------------------
# Backend process cleanup
# ---------------------------------------------------------------------------

def test_stop_previous_backend_discards_stale_pid_file(tmp_path):
    pid_file = tmp_path / "backend.pid"
    pid_file.write_text("999999 1", encoding="utf-8")  # port 1 is not listening

    _stop_previous_backend(tmp_path)

    assert not pid_file.exists()


def test_stop_previous_backend_discards_malformed_pid_file(tmp_path):
    pid_file = tmp_path / "backend.pid"
    pid_file.write_text("not a pid", encoding="utf-8")

    _stop_previous_backend(tmp_path)

    assert not pid_file.exists()


def test_stop_previous_backend_is_a_noop_without_a_pid_file(tmp_path):
    _stop_previous_backend(tmp_path)  # must not raise


# ---------------------------------------------------------------------------
# Full assembly
# ---------------------------------------------------------------------------

def test_generated_bundle_has_no_dangling_local_imports():
    endpoints = FIXED_ROUTER
    models = _ensure_model_runtime(_fix_models_code(GENERATED_MODELS), endpoints, MODELS_MODULE)
    app_code = _build_entrypoint(ROUTER_MODULE, models, MODELS_MODULE)

    for source in (app_code, endpoints, models):
        ast.parse(source)

    imported_modules = {
        node.module.split(".")[-1]
        for source in (endpoints, models)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom) and node.module and node.level == 0
    }
    assert "database" not in imported_modules
    assert "db" not in imported_modules
    assert "todos" not in imported_modules
    assert "models" in imported_modules

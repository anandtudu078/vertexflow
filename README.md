# VertexFlow

**An autonomous virtual software enterprise.** Submit a project brief and a swarm of six AI agents
run a pipeline — from company strategy all the way to scaffolded code and a security audit — and
render everything in a web dashboard you can export.

```
 project brief
      │
      ▼
 CEO agent          → company vision + strategic milestones
      │
      ▼
 CTO agent          → architecture overview, database models, task tickets
      │
      ▼
 PM agent           → product scope summary, user stories + acceptance criteria
      │
      ├──────────────────────────────────────────┐
      ▼                                          ▼
 Backend worker                           Frontend worker
 FastAPI + SQLAlchemy code                React + TypeScript component
 (+ sandbox scaffold)                     (parallel with Backend)
      │                                          │
      └───────────────────┬──────────────────────┘
                          ▼
                  Security auditor   → vulnerability scan, score, remediation
                          │
                          ▼
                       dashboard
```

Built with **FastAPI + LangGraph + Gemini** on the backend and **React + TypeScript + Tailwind** on
the frontend.

---

## What it does

1. You describe a product and the stack you want to build it with.
2. **`run_ceo_agent`** — sets a company vision and breaks execution into 3–5 sequential milestones
   with owning departments.
3. **`run_cto_agent`** — reads the brief plus those milestones and returns an architecture overview,
   the required database models and actionable engineering tickets with difficulty ratings.
4. **`run_pm_agent`** — reads the brief, milestones and technical blueprint and produces a product
   scope summary plus 3–5 user stories each with explicit acceptance criteria.
5. **`run_backend_agent`** — generates FastAPI / SQLAlchemy server code (models, endpoints,
   dependencies) and scaffolds the files to disk via `scaffold_and_run_project`.
6. **`run_frontend_agent`** — generates a React / TypeScript component, Tailwind classes and a
   state management summary. Runs in **parallel** with the Backend worker.
7. **`run_security_auditor_agent`** — audits the generated backend and frontend code for
   vulnerabilities (hardcoded secrets, missing auth, injection flaws) and returns a 1–100 score,
   findings list and compliance notes.
8. The dashboard presents vision, milestones, architecture, models, tickets, user stories, backend
   code, frontend component, security audit and sandbox output, with **Markdown** and **JSON**
   export of the full result.

All agents are LangGraph nodes wired as a `StateGraph`. The Backend and Frontend workers fan out in
parallel from the PM agent and both feed the Security Auditor:

```
ceo_agent → cto_agent → pm_agent → backend_worker_agent ─┐
                                 ↘ frontend_worker_agent  ├─► security_auditor_agent → END
```

Each agent calls Gemini with a `response_schema`, so responses deserialize straight into Pydantic
models without any post-processing.

---

## Tech stack

| Layer     | Tools                                                                             |
| --------- | --------------------------------------------------------------------------------- |
| Backend   | Python 3.14, FastAPI, LangGraph, `google-genai` (Gemini 3.5 Flash Lite), Uvicorn |
| Frontend  | React 19, TypeScript, Vite 8, Tailwind CSS 4                                     |
| Auth      | SQLite (scrypt-hashed passwords, server-side cookie sessions)                    |
| Sandbox   | `scaffold_and_run_project` writes files to `./output/project_<id>/`              |
| Packaging | `uv` (backend), `npm` (frontend)                                                 |

---

## Quick start

### Prerequisites

- **Python 3.14+** and [`uv`](https://docs.astral.sh/uv/)
- **Node.js 20.19+** (Vite 8's engine requirement; 22.12+ also works)
- A **Gemini API key** from [Google AI Studio](https://aistudio.google.com/apikey)

### 1. Backend

```bash
# from the repository root
uv sync
```

Create `backend/.env` with your key:

```dotenv
GEMINI_API_KEY=your-key-here
```

Start the API:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

| Check | Expected |
| --- | --- |
| <http://127.0.0.1:8000/> | `{"status":"online","message":"VertexFlow Orchestration Engine is running."}` |
| <http://127.0.0.1:8000/docs> | Interactive OpenAPI docs |

A missing key does **not** crash the server: it logs a warning at startup and
`POST /api/projects/launch` returns `503` explaining how to fix it.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

The dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`, so the browser only ever
talks to its own origin — no CORS setup needed during development.

---

## Configuration

| Variable | App | Required | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | backend | yes | Gemini credentials, read from `backend/.env` or the environment |
| `GEMINI_MODEL` | backend | no | Model id, default `gemini-3.5-flash-lite` |
| `VERTEXFLOW_DB` | backend | no | SQLite file for accounts and sessions, default `backend/vertexflow.db` |
| `VERTEXFLOW_COOKIE_SECURE` | backend | no | Set to `true` when served over HTTPS so the session cookie gets `Secure` |
| `VITE_BACKEND_URL` | frontend dev | no | Dev proxy target, default `http://127.0.0.1:8000` |
| `VITE_API_BASE_URL` | frontend build | no | Absolute backend origin; leave unset to use the same-origin proxy |

For a production build with a separate API origin, set `VITE_API_BASE_URL` **and** allow that origin
in the backend CORS config (currently `allow_origins=["*"]`).

---

## Authentication

The dashboard is gated behind an account; `POST /api/projects/launch` requires a valid session.

- **Accounts** live in SQLite (`users` table). Passwords are hashed with **scrypt** from the
  standard library, with a per-user salt and a self-describing hash format — no extra dependency.
- **Sessions** are server-side rows (`sessions` table) referenced by a random token in an `HttpOnly`
  cookie (`SameSite=Lax`, `Secure` when `VERTEXFLOW_COOKIE_SECURE=true`). Sessions last 7 days and
  are revoked on logout.
- **Registration is open** to whoever can reach the API. Create the first account, then keep the
  port private (or put a proxy in front of it) if you expose it publicly.
- There is no password reset, email verification or rate limiting yet.

| Endpoint | Body | Behaviour |
| --- | --- | --- |
| `POST /api/auth/register` | `{email, password}` | `201` and a session cookie; `409` if the email exists; `422` for an invalid email or password under 8 characters |
| `POST /api/auth/login` | `{email, password}` | `200` and a session cookie; `401` on bad credentials |
| `POST /api/auth/logout` | — | `204`, deletes the session row and clears the cookie |
| `GET /api/auth/me` | — | `200` with the user, or `401` when the session is missing/expired |

---

## API

All `/api/projects/*` routes require a session; unauthenticated calls return `401`.

### `POST /api/projects/launch`

Runs the full six-agent pipeline synchronously. The call blocks until the entire graph finishes
(up to 180 seconds).

```json
{
  "project_statement": "An AI-powered code review platform that flags risky diffs.",
  "target_tech_stack": "Python, FastAPI, React, PostgreSQL"
}
```

Response:

```json
{
  "status": "success",
  "current_status": "Security Audit Complete",
  "vision": "Become the fastest way for teams to ship safe code.",
  "milestones": [
    {
      "milestone_id": 1,
      "title": "Ship the review engine",
      "description": "Detect risky diffs and surface inline suggestions.",
      "assigned_department": "Engineering"
    }
  ],
  "technical_blueprint": {
    "architecture_overview": "FastAPI service, Postgres, React dashboard.",
    "database_models": ["User", "Repository", "Review", "Suggestion"],
    "tasks": [
      {
        "task_id": 1,
        "title": "Diff ingestion endpoint",
        "description": "Accept webhooks and persist parsed diffs.",
        "difficulty": "Medium"
      }
    ]
  },
  "product_requirements": {
    "product_scope_summary": "A developer tool that automatically reviews pull requests...",
    "user_stories": [
      {
        "story_id": 1,
        "user_role": "Developer",
        "feature_goal": "See inline suggestions on my pull request",
        "acceptance_criteria": [
          "Suggestions appear within 30 seconds of opening a PR",
          "Each suggestion links to the relevant diff line"
        ]
      }
    ]
  },
  "backend_code": {
    "module_name": "reviews_router",
    "database_models_code": "from sqlalchemy import ...",
    "api_endpoints_code": "from fastapi import APIRouter ...",
    "dependencies_required": ["fastapi", "sqlalchemy", "uvicorn"]
  },
  "frontend_code": {
    "component_name": "ReviewDashboard",
    "react_tsx_code": "import React from 'react' ...",
    "tailwind_styles_used": ["flex", "gap-4", "rounded-xl"],
    "state_management_summary": "Uses useState for review list and useEffect to fetch on mount."
  },
  "security_audit": {
    "security_score": 72,
    "overall_status": "Requires Fixes",
    "vulnerabilities": [
      {
        "vulnerability_id": "VULN-001",
        "severity": "Warning",
        "description": "No input validation on the diff ingestion endpoint.",
        "remediation": "Add a Pydantic model to validate the webhook payload."
      }
    ],
    "compliance_notes": "No sensitive data stored in plaintext."
  },
  "sandbox_result": {
    "project_path": "/abs/path/to/output/project_abc12345",
    "assigned_port": 54321,
    "status": "Scaffolded successfully"
  }
}
```

| Status | Meaning |
| --- | --- |
| `401` | No valid session — sign in |
| `422` | Request body failed validation |
| `503` | `GEMINI_API_KEY` is not configured |
| `500` | An agent or the graph failed (the upstream model error is returned as `detail`) |

### `GET /`

Liveness check used by the dashboard's connection indicator.

### `WS /ws/monitor/{project_id}`

Accepts a connection and currently echoes any messages sent back. **Not yet wired to the agent
run** — the dashboard narrates progress locally. Real streaming is a follow-up item.

---

## Project layout

```
.
├── backend/
│   ├── main.py              # FastAPI app, /api/projects/launch endpoint, WebSocket stub
│   ├── auth.py              # Accounts, scrypt hashing, cookie sessions, auth routes
│   ├── config.py            # Environment loading, API key validation, model id
│   ├── core/
│   │   └── sandbox.py       # scaffold_and_run_project: writes files, allocates port
│   └── agents/
│       ├── llm.py           # Lazily created, shared Gemini client
│       ├── ceo.py           # Vision + milestones
│       ├── cto.py           # Architecture + models + tickets
│       ├── pm.py            # Product scope + user stories + acceptance criteria
│       ├── backend_worker.py # FastAPI/SQLAlchemy code + sandbox invocation
│       ├── frontend_worker.py # React/TypeScript component
│       ├── security_auditor.py # Vulnerability scan
│       └── workflow.py      # LangGraph StateGraph wiring all nodes
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Session gate, run state machine and layout
│   │   ├── components/      # Auth screen, brief form, header, telemetry panel,
│   │   │                    # pipeline stages, results view, milestone board,
│   │   │                    # blueprint panel, PM requirements panel, backend/frontend
│   │   │                    # code panels, security audit panel, sandbox panel
│   │   ├── lib/             # API client, auth client, export helpers, utilities
│   │   └── types/           # TypeScript types mirrored from Pydantic models
│   └── README.md            # Frontend-specific documentation
├── pyproject.toml
└── uv.lock
```

---

## Commands

### Backend (repository root)

| Command | Description |
| --- | --- |
| `uv sync` | Install dependencies from `uv.lock` |
| `uv run uvicorn backend.main:app --reload --port 8000` | Run the API with auto-reload |
| `uv lock --check` | Verify the lock file is up to date |

### Frontend (`cd frontend`)

| Command | Description |
| --- | --- |
| `npm run dev` | Dev server with HMR and the API proxy |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Preview the production build |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run lint` | ESLint over TypeScript sources |

---

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Dashboard says "Backend offline" | The API is not running on port 8000, or the proxy target is wrong |
| "Incorrect email or password" | No account exists yet — create one on the sign-in screen |
| `401` on launch | The session expired (7 days) — sign in again |
| `503` on launch | `GEMINI_API_KEY` missing from `backend/.env` or the environment |
| `500` with a model message | The upstream model failed. Retry or set `GEMINI_MODEL` to a different model id |
| Network tab shows `502` | The proxy forwarded the request but the backend refused the connection |
| Blank page | Build/runtime error — check the browser console |
| Run takes >120 s with no feedback | Normal — the full pipeline can take 60–180 s. The request has a 180 s client-side timeout |

---

## Known limitations

This project is functional but not production-ready:

- **No persistence.** There is no project history; refreshing the page discards the result.
- **Synthetic telemetry.** The WebSocket endpoint is a stub; agent progress is narrated
  client-side with pre-scripted log messages rather than real events from the pipeline.
- **Blocking HTTP.** The entire pipeline runs synchronously inside the `/api/projects/launch`
  request handler. Long runs tie up a server thread and will hit proxy timeouts if the full
  graph exceeds 180 s.
- **Sandbox does not start the generated app.** Files are scaffolded and a port is allocated,
  but dependencies are not installed and the generated FastAPI server is never launched.
- **Unhardened input.** The brief is interpolated directly into agent prompts, and `500`
  responses echo the underlying exception text.
- **No tests, CI or container configuration.**
- **No rate limiting or login throttling**, and registration is open to anyone who can reach the API.
- **No password reset or email verification.**
- **CORS is wide-open** (`allow_origins=["*"]`). Restrict allowed origins before any public deployment.

## Roadmap

1. Restricted CORS origins, model timeouts/retries and sanitized error responses.
2. Tests (mocked agent client) plus a CI workflow running lint, typecheck, build and pytest.
3. Real event streaming over `/ws/monitor`, replacing the narrated telemetry.
4. Project persistence with a `project_id`, enabling history, sharing and refinement loops.
5. Background task execution so the server thread is freed immediately and the client polls or
   subscribes for results.
6. Actually boot the scaffolded app: install deps in an isolated venv and launch via subprocess.

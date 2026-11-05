# VertexFlow

**An autonomous virtual software enterprise.** Submit a project brief and a swarm of ten AI agents run a pipeline — from company strategy all the way to scaffolded code, UI/UX design, code review, QA testing, and a security audit — and render everything in a web dashboard you can export.

```text
 project brief
       │
       ▼
  research agent   → modern patterns, library docs, pitfalls
       │
       ▼
  ceo agent        → company vision + strategic milestones
       │
       ▼
  cto agent        → architecture overview, database models, task tickets
       │
       ▼
  pm agent         → product scope summary, user stories + acceptance criteria
       │
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   │                                                │
   ▼                                                ▼
backend worker                            frontend worker
FastAPI + SQLAlchemy code                React + TypeScript component
(+ sandbox scaffold)                     (parallel with Backend)
       │                                                │
       └───────────────────────┬──────────────────────┘
                           ▼
                 ui_ux agent      → color palettes, typography, design system
                           │
                           ▼
                     code_reviewer_agent → static analysis + code quality report
                                   │
                                   ▼
                                         qa_agent → unit tests + pass rates
                                                   │
                                                   ▼
                                          security_auditor_agent → vulnerability scan, score, remediation
                                                                         │
                                                                         ▼
                                                                      END
```

Built with **FastAPI + LangGraph + Gemini** on the backend and **React + TypeScript + Tailwind** on the frontend.

## What's New (10-Agent Pipeline)

The workflow now has **10 agents** organized as a StateGraph:

```
research → ceo → cto → pm → (backend | ui_ux → frontend) → code_reviewer → qa → scaffold → security_auditor
```

with a 3-pass self-healing loop (`MAX_HEAL_ITERATIONS = 3`). The pipeline produces:

| Agent | Output |
|-------|--------|
| **Research** | Modern patterns, library docs, pitfalls |
| **CEO** | Company vision, strategic milestones, project_id |
| **CTO** | Architecture overview, database models, task tickets |
| **PM** | Product scope summary, user stories |
| **UI/UX** | Color palettes, typography, design systems |
| **Backend** | FastAPI + SQLAlchemy server code |
| **Frontend** | React + TypeScript component code |
| **Code Reviewer** | Static analysis + code quality report |
| **QA** | Unit tests designed + pass rates |
| **Security Auditor** | Vulnerability scan, 1–100 score, findings, compliance notes |

The dashboard now shows panels for all 10 agents, and the API returns all agent outputs.

## What it does

1. You describe a product and the stack you want to build it with.
2. **Research agent** — gathers modern patterns, library docs, and pitfalls.
3. **CEO agent** — sets a company vision, breaks execution into 3–5 sequential milestones with owning departments, assigns a stable `project_id`.
4. **CTO agent** — reads the brief plus those milestones and returns an architecture overview, the required database models and actionable engineering tickets with difficulty ratings.
5. **PM agent** — reads the brief, milestones and technical blueprint and produces a product scope summary plus user stories each with explicit acceptance criteria.
6. **UI/UX agent** — defines color palettes, typography, and design systems.
7. **Backend worker** — generates FastAPI / SQLAlchemy server code (models, endpoints, dependencies) and scaffolds the files to disk via `scaffold_and_run_project`. Runs in parallel with the frontend worker.
8. **Frontend worker** — generates a React / TypeScript component, Tailwind classes and a state management summary. Runs in parallel with the backend worker.
9. **Code Reviewer agent** — performs static analysis and clean code reviews.
10. **QA Test Engineer agent** — designs unit tests and verifies test pass rates.
11. **Security Auditor agent** — audits the generated backend and frontend code for vulnerabilities and returns a 1–100 score, findings list and compliance notes.

The pipeline uses conditional self-healing: if the security audit fails (score < 80 or overall_status != "Passed") or the backend fails to boot, the graph loops back to the workers for a maximum of 3 iterations before finishing.

The dashboard presents vision, milestones, architecture, models, tickets, user stories, research findings, UI/UX blueprint, code review, QA report, backend code, frontend component, security audit and sandbox output, with **Markdown** and **JSON** export of the full result.

## Tech stack

| Layer | Tools |
|-------|-------|
| Backend | Python 3.14, FastAPI, LangGraph, `google-genai` (Gemini 3.5 Flash Lite), Uvicorn |
| Frontend | React 19, TypeScript, Vite 8, Tailwind CSS 4 |
| Auth | SQLite (scrypt-hashed passwords, server-side cookie sessions) |
| Sandbox | `scaffold_and_run_project` writes files to `./output/project_<id>/` |
| Packaging | `uv` (backend), `npm` (frontend) |

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

A missing key does **not** crash the server: it logs a warning at startup and `POST /api/projects/launch` returns `503` explaining how to fix it.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

The dev server proxies `/api` and `/health` to `http://127.0.0.1:8000`, so the browser only ever talks to its own origin — no CORS setup needed during development.

### 3. Launch a project

```bash
# Using curl
curl -X POST http://127.0.0.1:8000/api/projects/launch \
  -H "Authorization: Bearer <session-cookie>" \
  -H "Content-Type: application/json" \
  -d '{"project_statement":"An AI-powered code review platform that flags risky diffs.","target_tech_stack":"Python, FastAPI, React, PostgreSQL"}'
```

Or via the UI at <http://localhost:5173>.

The pipeline now runs in the background. The API returns `status=pending` with a `project_id`. Poll for status:

```bash
curl http://127.0.0.1:8000/api/projects/{project_id}/status \
  -H "Authorization: Bearer <session-cookie>"
```

Or watch the WebSocket monitor at `WS /ws/monitor/{project_id}`.

### 4. Export results

When the pipeline finishes, the dashboard shows all agent outputs. Use the export buttons to download **Markdown** or **JSON** of the complete result.

## Configuration

| Variable | App | Required | Purpose |
| --- | --- | --- | --- |
| `GEMINI_API_KEY` | backend | yes | Gemini credentials, read from `backend/.env` or the environment |
| `GEMINI_MODEL` | backend | no | Model id, default `gemini-3.5-flash-lite` |
| `VERTEXFLOW_DB` | backend | no | SQLite file for accounts and sessions, default `backend/vertexflow.db` |
| `VERTEXFLOW_COOKIE_SECURE` | backend | no | Set to `true` when served over HTTPS so the session cookie gets `Secure` |
| `VERTEXFLOW_CORS_ALLOW_ALL` | backend | no | Set to `true` to allow `["*"]` origins (default: restricted origins) |
| `VITE_BACKEND_URL` | frontend dev | no | Dev proxy target, default `http://127.0.0.1:8000` |
| `VITE_API_BASE_URL` | frontend build | no | Absolute backend origin; leave unset to use the same-origin proxy |

For a production build with a separate API origin, set `VITE_API_BASE_URL` **and** allow that origin in the backend CORS config.

## Authentication

The dashboard is gated behind an account; `POST /api/projects/launch` requires a valid session.

- **Accounts** live in SQLite (`users` table). Passwords are hashed with **scrypt** from the standard library, with a per-user salt and a self-describing hash format — no extra dependency.
- **Sessions** are server-side rows (`sessions` table) referenced by a random token in an `HttpOnly` cookie (`SameSite=Lax`, `Secure` when `VERTEXFLOW_COOKIE_SECURE=true`). Sessions last 7 days and are revoked on logout.
- **Registration is open** to whoever can reach the API. Create the first account, then keep the port private (or put a proxy in front of it) if you expose it publicly.
- There is no password reset, email verification or rate limiting yet.

| Endpoint | Body | Behaviour |
| --- | --- | --- |
| `POST /api/auth/register` | `{email, password}` | `201` and a session cookie; `409` if the email exists; `422` for an invalid email or password under 8 characters |
| `POST /api/auth/login` | `{email, password}` | `200` and a session cookie; `401` on bad credentials |
| `POST /api/auth/logout` | — | `204`, deletes the session row and clears the cookie |
| `GET /api/auth/me` | — | `200` with the user, or `401` when the session is missing/expired |

## API

All `/api/projects/*` routes require a session; unauthenticated calls return `401`.

### `POST /api/projects/launch`

Runs the full 10-agent pipeline in the background. The call returns immediately with `status=pending` and a `project_id` for polling.

```json
{
  "project_statement": "An AI-powered code review platform that flags risky diffs.",
  "target_tech_stack": "Python, FastAPI, React, PostgreSQL"
}
```

Response:

```json
{
  "status": "pending",
  "project_id": "abc12345",
  "message": "Pipeline launched in background. Poll /api/projects/{project_id}/status or use WebSocket monitor."
}
```

Track progress:

```json
# GET /api/projects/{project_id}/status
{
  "project_id": "abc12345",
  "status": "success",
  "current_status": "Security Audit Complete",
  "vision": "Become the fastest way for teams to ship safe code.",
  "milestones": [...],
  "technical_blueprint": {...},
  "product_requirements": {...},
  "research_findings": {...},
  "ui_ux_blueprint": {...},
  "code_review": {...},
  "qa_report": {...},
  "backend_code": {...},
  "frontend_code": {...},
  "security_audit": {...},
  "sandbox_result": {...}
}
```

### `GET /`

Liveness check used by the dashboard's connection indicator.

### `WS /ws/monitor/{project_id}`

Accepts a connection and streams telemetry events from the pipeline run. The client can send any message and it will be echoed back.

## Project layout

```
.
├── backend/
│   ├── main.py              # FastAPI app, /api/projects/launch, status polling, background execution
│   ├── auth.py              # Accounts, scrypt hashing, cookie sessions, auth routes
│   ├── config.py            # Environment loading, API key validation, model id
│   ├── core/
│   │   └── sandbox.py       # scaffold_and_run_project: writes files, allocates port, isolated venv
│   └── agents/
│       ├── llm.py           # Lazily created, shared Gemini client
│       ├── ceo.py           # Vision + milestones
│       ├── cto.py           # Architecture + models + tickets
│       ├── pm.py            # Product scope + user stories + acceptance criteria
│       ├── ui_ux_agent.py   # UI/UX design system
│       ├── research_agent.py # Modern patterns, library docs, pitfalls
│       ├── backend_worker.py # FastAPI/SQLAlchemy code + sandbox invocation
│       ├── frontend_worker.py # React/TypeScript component
│       ├── code_reviewer_agent.py # Static analysis + code quality report
│       ├── qa_agent.py      # Unit tests + pass rates
│       ├── security_auditor.py # Vulnerability scan
│       └── workflow.py      # LangGraph StateGraph wiring all 10 nodes
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Session gate, run state machine and layout
│   │   ├── components/      # Auth screen, brief form, header, telemetry panel,
│   │   │                    # pipeline stages, results view, milestone board,
│   │   │                    # research panel, UI/UX panel, code review panel, QA panel,
│   │   │                    # backend/frontend code panels, security audit panel, sandbox panel
│   │   ├── lib/             # API client, auth client, export helpers, utilities
│   │   └── types/           # TypeScript types mirrored from Pydantic models
│   └── README.md            # Frontend-specific documentation
├── pyproject.toml
└── uv.lock
```

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
| Pipeline status stays "pending" | The background thread may still be running; wait a few more seconds and poll again |
| Run takes >180 s with no feedback | Normal — the full pipeline can take 15+ minutes. The background thread handles this. |

## Known limitations

This project is functional but not production-ready:

- **No project history on disk refresh.** The in-memory state store is reset on server restart; swap in Redis/Postgres for persistence.
- **Synthetic telemetry initially.** The WebSocket endpoint streams events, but early runs may lack real pipeline events.
- **Background execution.** The pipeline runs in a daemon thread; state is stored in memory. For production, use a database (Redis, Postgres).
- **Sandbox dependency isolation.** Dependencies are installed in a per-project `.venv` to avoid mutating the host environment.
- **Unhardened input.** The brief is interpolated directly into agent prompts, and error responses are generic (full traceback logged server-side).
- **No password reset or email verification.**
- **Rate limiting not yet configured.**
- **CORS restricted to development origins** by default; restrict further before any public deployment using `VERTEXFLOW_CORS_ALLOW_ALL`.

## Roadmap

1. Project persistence with a `project_id`, enabling history, sharing and refinement loops.
2. Real event streaming over `/ws/monitor`, replacing narrated telemetry.
3. Tests (mocked agent client) plus a CI workflow running lint, typecheck, build and pytest.
4. Restricted CORS origins, model timeouts/retries and sanitized error responses.
5. Background task execution so the server thread is freed immediately and the client polls or subscribes for results.
6. Actually boot the scaffolded app: install deps in an isolated venv and launch via subprocess.

## Contributing

PRs welcome. See the [GitHub Issues](https://github.com/anandtudu078/vertexflow/issues) for known items and the [feature branches](https://github.com/anandtudu078/vertexflow/tree/feature) for work-in-progress.
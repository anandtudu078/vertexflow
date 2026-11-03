# VertexFlow — Frontend

Single-page dashboard for the VertexFlow multi-agent orchestrator. You submit a project
brief, the **CEO agent** turns it into a company vision and strategic milestones, and the
**CTO agent** turns those into an architecture overview, database models and developer
task tickets.

The UI shows the run as it happens: form validation, agent telemetry, pipeline progress,
loading skeletons, and the generated blueprint with copy/export actions.

## Stack

- **React 19** + **TypeScript**
- **Vite 8** (dev server, proxy, build)
- **Tailwind CSS 4** via `@tailwindcss/vite`
- No router, state library or HTTP client — plain `fetch` and React state

## Requirements

- Node.js 20+
- The VertexFlow FastAPI backend running on `http://127.0.0.1:8000`
  (it needs `GEMINI_API_KEY` in `backend/.env` and the FastAPI, LangGraph and
  `google-genai` packages installed)

## Getting started

```bash
cd frontend
npm install
npm run dev
```

The app is served at http://localhost:5173.

Start the backend from the repository root:

```bash
uv run uvicorn backend.main:app --reload --port 8000
```

## Connecting to the backend

The backend sends no CORS headers, so the frontend never calls port 8000 directly:

- **Development** — Vite proxies `/api` and `/health` to `http://127.0.0.1:8000`
  (see `vite.config.js`). The UI's connection pill turns green once the proxy
  reaches the backend. Point the proxy somewhere else with
  `VITE_BACKEND_URL=http://host:port npm run dev`.
- **Production** — serve the built `dist/` behind a reverse proxy that forwards
  `/api` to the backend, or set `VITE_API_BASE_URL` at build time to call the backend
  origin directly (in that case the backend must allow CORS from the frontend origin).

| Variable            | Used by        | Purpose                                                   |
| ------------------- | -------------- | --------------------------------------------------------- |
| `VITE_BACKEND_URL`  | `vite.config.js` | Dev proxy target (default `http://127.0.0.1:8000`)      |
| `VITE_API_BASE_URL` | app bundle     | Absolute backend origin; unset to use the same-origin proxy |

## Scripts

| Command             | Description                                     |
| ------------------- | ----------------------------------------------- |
| `npm run dev`       | Dev server with HMR and the backend proxy       |
| `npm run build`     | Production build into `dist/`                   |
| `npm run preview`   | Preview the production build                    |
| `npm run typecheck` | `tsc --noEmit` over `src/`                      |
| `npm run lint`      | ESLint (TypeScript, hooks and refresh rules)    |

## Project structure

```
src/
├── App.tsx                 # Run state machine, telemetry, layout
├── main.tsx                # React root
├── index.css               # Tailwind entry, theme tokens, custom utilities
├── components/
│   ├── Header.tsx          # Brand + backend status pill
│   ├── BriefForm.tsx       # Brief editor, stack presets, submit/cancel
│   ├── TelemetryPanel.tsx  # Live agent log
│   ├── PipelineStages.tsx  # Brief → CEO → CTO progress
│   ├── ResultsView.tsx     # Summary stats, vision, export actions
│   ├── MilestoneBoard.tsx  # CEO milestones timeline
│   ├── BlueprintPanel.tsx  # Architecture, DB models, task tickets
│   ├── EmptyState.tsx      # Idle onboarding
│   ├── ResultsSkeleton.tsx # Loading placeholders
│   ├── Icons.tsx           # Inline SVG icon set
│   └── ui.tsx              # Card, Badge, SectionHeading primitives
├── lib/
│   ├── api.ts              # Typed API client, timeouts, error normalisation
│   ├── export.ts           # JSON download and Markdown export
│   ├── tone.ts             # Badge tones, difficulty mapping
│   └── cn.ts               # className helper
└── types/index.ts          # Request/response contract mirrored from Pydantic
```

## API contract

**`POST /api/projects/launch`**

```json
{ "project_statement": "...", "target_tech_stack": "..." }
```

Returns `status`, `current_status`, `vision`, `milestones[]` and
`technical_blueprint` (`architecture_overview`, `database_models[]`, `tasks[]`).
Responses are normalised before rendering, so a partial agent result still shows
what was produced instead of crashing.

`GET /` on the backend is used for the header health check; in development it is
reached through the `/health` proxy entry.

### Client behaviour

- Statements need 12+ characters and a tech stack 2+ characters before launch.
  `Ctrl`/`⌘` + `Enter` submits from the textarea.
- A run can be cancelled; the request is aborted and the UI returns to idle.
- Requests time out after 180 seconds (health checks after 5), since two LLM calls
  run synchronously server-side.
- Errors surface the backend's `detail`, FastAPI validation messages, or a
  "could not reach the backend" hint — including when a proxy returns HTML instead
  of JSON.
- Results can be exported as Markdown (clipboard) or as a JSON file.

## Styling

Tailwind CSS 4 is configured directly in `src/index.css` (`@theme` tokens for the
`ink` palette, animations and fonts, plus `panel`, `field` and `skeleton`
utilities). There is no `tailwind.config.js`. The dark palette is fixed — the
dashboard is designed for dark mode only.

## Troubleshooting

| Symptom                                   | Likely cause                                                              |
| ----------------------------------------- | ------------------------------------------------------------------------- |
| Blank page                                | `index.html` entry point or a runtime error — check the browser console   |
| Header pill says "Backend offline"        | FastAPI is not running on port 8000, or the proxy target is wrong         |
| "Could not reach the backend" on launch   | Dev proxy target unreachable; run the backend or set `VITE_BACKEND_URL`   |
| 500 from the API                          | Backend error — usually a missing/invalid `GEMINI_API_KEY`                |
| Network tab shows 502                     | The Vite proxy forwarded the request but the backend refused the connection |

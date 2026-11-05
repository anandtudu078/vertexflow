import type {
  BackendCodeBlueprint,
  FrontendCodeBlueprint,
  HealthResponse,
  Milestone,
  ProjectBrief,
  ProjectExecutionResponse,
  SandboxResult,
  SecurityAuditReport,
  TaskTicket,
  UserStory,
  VulnerabilityItem,
} from '../types';

/**
 * When unset, requests are relative so the Vite dev proxy (or a reverse proxy in
 * production) forwards them to the FastAPI backend on port 8000.
 */
export const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').trim().replace(/\/+$/, '');

export const API_ORIGIN_LABEL = API_BASE || 'same origin (/api proxy)';

const LAUNCH_PATH = '/api/projects/launch';
const HEALTH_PATH = API_BASE ? '/' : '/health';
const LAUNCH_TIMEOUT_MS = 180_000;
const HEALTH_TIMEOUT_MS = 5_000;

export class ApiError extends Error {
  readonly status?: number;

  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

/** Turns any FastAPI/HTML/network failure into a human readable sentence. */
export async function readErrorDetail(response: Response): Promise<string> {
  const raw = await response.text().catch(() => '');

  if (!raw.trim()) {
    return `The backend responded with status ${response.status}.`;
  }

  try {
    const parsed = JSON.parse(raw) as { detail?: unknown };

    if (typeof parsed.detail === 'string' && parsed.detail.trim()) {
      return parsed.detail;
    }

    // FastAPI validation errors: [{ loc: [...], msg: "..." }]
    if (Array.isArray(parsed.detail)) {
      const lines = parsed.detail
        .map((item) => {
          if (typeof item !== 'object' || item === null) return null;
          const { loc, msg } = item as { loc?: unknown; msg?: unknown };
          if (typeof msg !== 'string') return null;
          const field = Array.isArray(loc) ? loc.filter((part) => part !== 'body').join('.') : '';
          return field ? `${field}: ${msg}` : msg;
        })
        .filter((line): line is string => Boolean(line));
      if (lines.length > 0) return lines.join(' · ');
    }
  } catch {
    // Not JSON — fall through to the text cleanup below.
  }

  const cleaned = raw
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();

  return cleaned.slice(0, 280) || `The backend responded with status ${response.status}.`;
}

interface TimedSignal {
  signal: AbortSignal;
  cancel: () => void;
}

function createTimedSignal(timeoutMs: number, external?: AbortSignal): TimedSignal {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort(new DOMException(`Request timed out after ${timeoutMs} ms`, 'TimeoutError'));
  }, timeoutMs);

  const forwardAbort = () => controller.abort(external?.reason);
  if (external) {
    if (external.aborted) forwardAbort();
    else external.addEventListener('abort', forwardAbort, { once: true });
  }

  return {
    signal: controller.signal,
    cancel: () => {
      clearTimeout(timer);
      external?.removeEventListener('abort', forwardAbort);
    },
  };
}

function toNetworkError(error: unknown, timeoutMs: number, cancelled: boolean): ApiError {
  if (error instanceof ApiError) return error;

  const name = error instanceof Error ? error.name : '';
  if (name === 'TimeoutError') {
    return new ApiError(`The agents took longer than ${Math.round(timeoutMs / 1000)}s to respond.`);
  }
  if (cancelled) {
    return new ApiError('Run cancelled.');
  }
  if (name === 'AbortError') {
    return new ApiError('The request was aborted before the agents finished.');
  }

  return new ApiError(
    'Could not reach the backend. Make sure the FastAPI server is running on port 8000, then try again.',
  );
}

const asArray = <T,>(value: unknown): T[] => (Array.isArray(value) ? (value as T[]) : []);
const asText = (value: unknown, fallback = ''): string =>
  typeof value === 'string' ? value : fallback;

/** Fills in missing fields so a partial agent result can still be rendered. */
function normalizeResponse(payload: unknown): ProjectExecutionResponse {
  if (typeof payload !== 'object' || payload === null) {
    throw new ApiError('The backend returned an unexpected response.');
  }

  const data = payload as Record<string, unknown>;

  const blueprint =
    typeof data.technical_blueprint === 'object' && data.technical_blueprint !== null
      ? (data.technical_blueprint as Record<string, unknown>)
      : {};

  const pmRaw =
    typeof data.product_requirements === 'object' && data.product_requirements !== null
      ? (data.product_requirements as Record<string, unknown>)
      : {};

  const backendRaw =
    typeof data.backend_code === 'object' && data.backend_code !== null
      ? (data.backend_code as Record<string, unknown>)
      : {};

  const frontendRaw =
    typeof data.frontend_code === 'object' && data.frontend_code !== null
      ? (data.frontend_code as Record<string, unknown>)
      : {};

  const auditRaw =
    typeof data.security_audit === 'object' && data.security_audit !== null
      ? (data.security_audit as Record<string, unknown>)
      : {};

  const sandboxRaw =
    typeof data.sandbox_result === 'object' && data.sandbox_result !== null
      ? (data.sandbox_result as Record<string, unknown>)
      : {};

  const researchRaw =
    typeof data.research_findings === 'object' && data.research_findings !== null
      ? (data.research_findings as Record<string, unknown>)
      : {};

  const uiRaw =
    typeof data.ui_ux_blueprint === 'object' && data.ui_ux_blueprint !== null
      ? (data.ui_ux_blueprint as Record<string, unknown>)
      : {};

  const reviewRaw =
    typeof data.code_review === 'object' && data.code_review !== null
      ? (data.code_review as Record<string, unknown>)
      : {};

  const qaRaw =
    typeof data.qa_report === 'object' && data.qa_report !== null
      ? (data.qa_report as Record<string, unknown>)
      : {};

  return {
    status: asText(data.status, 'unknown'),
    current_status: asText(data.current_status, 'Pipeline finished'),
    vision: asText(data.vision),
    milestones: asArray<Milestone>(data.milestones),
    technical_blueprint: {
      architecture_overview: asText(blueprint.architecture_overview),
      database_models: asArray<unknown>(blueprint.database_models).filter(
        (model): model is string => typeof model === 'string',
      ),
      tasks: asArray<TaskTicket>(blueprint.tasks),
    },
    product_requirements: {
      product_scope_summary: asText(pmRaw.product_scope_summary),
      user_stories: asArray<UserStory>(pmRaw.user_stories),
    },
    research_findings: {
      raw: researchRaw,
    },
    ui_ux_blueprint: {
      raw: uiRaw,
    },
    code_review: {
      raw: reviewRaw,
    },
    qa_report: {
      raw: qaRaw,
    },
    backend_code: {
      module_name: asText(backendRaw.module_name),
      database_models_code: asText(backendRaw.database_models_code),
      api_endpoints_code: asText(backendRaw.api_endpoints_code),
      dependencies_required: asArray<unknown>(backendRaw.dependencies_required).filter(
        (d): d is string => typeof d === 'string',
      ),
    } satisfies BackendCodeBlueprint,
    frontend_code: {
      component_name: asText(frontendRaw.component_name),
      react_tsx_code: asText(frontendRaw.react_tsx_code),
      tailwind_styles_used: asArray<unknown>(frontendRaw.tailwind_styles_used).filter(
        (s): s is string => typeof s === 'string',
      ),
      state_management_summary: asText(frontendRaw.state_management_summary),
    } satisfies FrontendCodeBlueprint,
    security_audit: {
      security_score: typeof auditRaw.security_score === 'number' ? auditRaw.security_score : 0,
      overall_status: asText(auditRaw.overall_status),
      vulnerabilities: asArray<VulnerabilityItem>(auditRaw.vulnerabilities),
      compliance_notes: asText(auditRaw.compliance_notes),
    } satisfies SecurityAuditReport,
    sandbox_result: {
      project_path: asText(sandboxRaw.project_path),
      assigned_port:
        typeof sandboxRaw.assigned_port === 'number' ? sandboxRaw.assigned_port : undefined,
      status: asText(sandboxRaw.status),
    } satisfies Partial<SandboxResult>,
  } as ProjectExecutionResponse;
}

/** Runs the full CEO → CTO → PM → Backend/Frontend → Security agent pipeline. */
export async function launchProject(
  brief: ProjectBrief,
  signal?: AbortSignal,
): Promise<ProjectExecutionResponse> {
  const timed = createTimedSignal(LAUNCH_TIMEOUT_MS, signal);

  try {
    const response = await fetch(`${API_BASE}${LAUNCH_PATH}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      body: JSON.stringify({
        project_statement: brief.project_statement.trim(),
        target_tech_stack: brief.target_tech_stack.trim(),
      }),
      signal: timed.signal,
    });

    if (!response.ok) {
      throw new ApiError(await readErrorDetail(response), response.status);
    }

    return normalizeResponse(await response.json());
  } catch (error) {
    throw toNetworkError(error, LAUNCH_TIMEOUT_MS, Boolean(signal?.aborted));
  } finally {
    timed.cancel();
  }
}

/** Lightweight ping used for the header connection indicator. */
export async function checkBackendHealth(signal?: AbortSignal): Promise<boolean> {
  const timed = createTimedSignal(HEALTH_TIMEOUT_MS, signal);

  try {
    const response = await fetch(`${API_BASE}${HEALTH_PATH}`, {
      headers: { Accept: 'application/json' },
      signal: timed.signal,
    });
    if (!response.ok) return false;
    const payload = (await response.json()) as HealthResponse;
    return typeof payload.status === 'string';
  } catch {
    return false;
  } finally {
    timed.cancel();
  }
}

/** Account returned by the auth endpoints (`backend.auth.UserOut`). */
export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

/** Login and registration payload. */
export interface Credentials {
  email: string;
  password: string;
}

export type AuthState = 'checking' | 'anonymous' | 'authenticated' | 'unreachable';

/** Payload accepted by `POST /api/projects/launch` (backend `ProjectBrief`). */
export interface ProjectBrief {
  project_statement: string;
  target_tech_stack: string;
}

/** Raw milestone returned by the CEO agent. */
export interface Milestone {
  milestone_id: number;
  title: string;
  description: string;
  assigned_department: string;
}

/** Raw developer ticket returned by the CTO agent. */
export interface TaskTicket {
  task_id: number;
  title: string;
  description: string;
  /** Free-form label from the model, typically Easy | Medium | Hard. */
  difficulty: string;
}

/** Raw blueprint returned by the CTO agent. */
export interface CTOTechnicalBlueprint {
  architecture_overview: string;
  database_models: string[];
  tasks: TaskTicket[];
}

/** A single user story produced by the PM agent. */
export interface UserStory {
  story_id: number;
  user_role: string;
  feature_goal: string;
  acceptance_criteria: string[];
}

/** Product requirements blueprint returned by the PM agent. */
export interface ProductManagerBlueprint {
  product_scope_summary: string;
  user_stories: UserStory[];
}

/** Backend Worker agent output. */
export interface BackendCodeBlueprint {
  module_name: string;
  database_models_code: string;
  api_endpoints_code: string;
  dependencies_required: string[];
}

/** Frontend Worker agent output. */
export interface FrontendCodeBlueprint {
  component_name: string;
  react_tsx_code: string;
  tailwind_styles_used: string[];
  state_management_summary: string;
}

/** A single vulnerability found by the Security Auditor. */
export interface VulnerabilityItem {
  vulnerability_id: string;
  /** Free-form severity label, e.g. "Critical", "Warning", "Info". */
  severity: string;
  description: string;
  remediation: string;
}

/** Security Auditor agent output. */
export interface SecurityAuditReport {
  /** Score from 1–100. */
  security_score: number;
  /** e.g. "Passed", "Requires Fixes", "Rejected". */
  overall_status: string;
  vulnerabilities: VulnerabilityItem[];
  compliance_notes: string;
}

/** Sandbox scaffold result returned by backend/core/sandbox.py */
export interface SandboxResult {
  /** Absolute path on the server where the project was scaffolded. */
  project_path: string;
  /** Dynamically allocated port for the generated FastAPI app. */
  assigned_port: number;
  /** Human-readable outcome, e.g. "Scaffolded successfully". */
  status: string;
}

/** Response of `POST /api/projects/launch`. Fields can be empty if a node fails. */
export interface ProjectExecutionResponse {
  status: string;
  current_status: string;
  vision: string;
  milestones: Milestone[];
  technical_blueprint: Partial<CTOTechnicalBlueprint>;
  product_requirements: Partial<ProductManagerBlueprint>;
  backend_code: Partial<BackendCodeBlueprint>;
  frontend_code: Partial<FrontendCodeBlueprint>;
  security_audit: Partial<SecurityAuditReport>;
  sandbox_result: Partial<SandboxResult>;
}

/** Response of the backend root route, reachable through the `/health` proxy. */
export interface HealthResponse {
  status: string;
  message?: string;
}

export type ApiStatus = 'checking' | 'online' | 'offline';

export type LogLevel = 'info' | 'success' | 'error';

export interface LogEntry {
  id: number;
  at: Date;
  role: 'CEO' | 'CTO' | 'PM' | 'Backend' | 'Frontend' | 'Security' | 'System' | 'Error';
  message: string;
  level: LogLevel;
}

export type Phase = 'idle' | 'running' | 'success' | 'error';

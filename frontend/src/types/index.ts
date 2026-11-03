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

/** Response of `POST /api/projects/launch`. Fields can be empty if a node fails. */
export interface ProjectExecutionResponse {
  status: string;
  current_status: string;
  vision: string;
  milestones: Milestone[];
  technical_blueprint: Partial<CTOTechnicalBlueprint>;
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
  role: 'CEO' | 'CTO' | 'System' | 'Error';
  message: string;
  level: LogLevel;
}

export type Phase = 'idle' | 'running' | 'success' | 'error';

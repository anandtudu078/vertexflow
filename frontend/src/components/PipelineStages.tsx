import { cn } from '../lib/cn';
import type { Phase } from '../types';

type StageState = 'pending' | 'active' | 'done' | 'error';

const STAGES = [
  { key: 'brief',    label: 'Brief',            detail: 'Submitted' },
  { key: 'ceo',      label: 'CEO agent',         detail: 'Vision + milestones' },
  { key: 'cto',      label: 'CTO agent',         detail: 'Architecture + tickets' },
  { key: 'pm',       label: 'PM agent',          detail: 'User stories' },
  { key: 'workers',  label: 'Backend / Frontend', detail: 'Code generation' },
  { key: 'security', label: 'Security auditor',  detail: 'Vulnerability scan' },
  { key: 'sandbox',  label: 'Sandbox',           detail: 'Scaffold + port alloc' },
] as const;

const DOT_CLASSES: Record<StageState, string> = {
  pending: 'border-slate-700 bg-slate-900 text-slate-600',
  active:  'border-indigo-400/60 bg-indigo-500/20 text-indigo-200',
  done:    'border-emerald-400/50 bg-emerald-500/15 text-emerald-300',
  error:   'border-rose-400/50 bg-rose-500/15 text-rose-300',
};

function statesFor(phase: Phase): StageState[] {
  // 7 stages: brief, ceo, cto, pm, workers, security, sandbox
  switch (phase) {
    case 'running':
      return ['done', 'active', 'active', 'active', 'active', 'active', 'active'];
    case 'success':
      return ['done', 'done', 'done', 'done', 'done', 'done', 'done'];
    case 'error':
      return ['done', 'error', 'error', 'error', 'error', 'error', 'error'];
    case 'idle':
    default:
      return ['pending', 'pending', 'pending', 'pending', 'pending', 'pending', 'pending'];
  }
}

export function PipelineStages({ phase }: { phase: Phase }) {
  const states = statesFor(phase);

  return (
    <div className="panel px-4 py-3">
      <ol className="flex flex-col gap-3 sm:flex-row sm:items-center sm:gap-1">
        {STAGES.map((stage, index) => {
          const state = states[index] ?? 'pending';

          return (
            <li key={stage.key} className="flex flex-1 items-center gap-2">
              <span
                className={cn(
                  'flex h-7 w-7 shrink-0 items-center justify-center rounded-full border font-mono text-[11px]',
                  DOT_CLASSES[state],
                  state === 'active' && 'animate-pulse',
                )}
                aria-hidden="true"
              >
                {index + 1}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    'block text-xs font-medium',
                    state === 'pending' ? 'text-slate-500' : 'text-white',
                  )}
                >
                  {stage.label}
                </span>
                <span className="block truncate text-[10px] text-slate-500">
                  {state === 'error' ? 'Halted' : stage.detail}
                </span>
              </span>
              {index < STAGES.length - 1 ? (
                <span
                  className={cn(
                    'hidden h-px flex-1 sm:block',
                    state === 'done' ? 'bg-emerald-500/40' : 'bg-slate-800',
                  )}
                  aria-hidden="true"
                />
              ) : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

import { API_ORIGIN_LABEL } from '../lib/api';
import { cn } from '../lib/cn';
import type { ApiStatus, AuthUser } from '../types';

const STATUS_META: Record<ApiStatus, { label: string; classes: string; dot: string }> = {
  checking: {
    label: 'Checking backend',
    classes: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    dot: 'bg-amber-400 animate-pulse',
  },
  online: {
    label: 'Backend online',
    classes: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    dot: 'bg-emerald-400',
  },
  offline: {
    label: 'Backend offline',
    classes: 'border-rose-500/30 bg-rose-500/10 text-rose-300',
    dot: 'bg-rose-400',
  },
};

export function Header({
  status,
  onRefresh,
  user = null,
  onSignOut,
}: {
  status: ApiStatus;
  onRefresh: () => void;
  user?: AuthUser | null;
  onSignOut?: () => void;
}) {
  const meta = STATUS_META[status];

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/70 bg-ink-950/80 backdrop-blur-lg">
      <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center justify-between gap-4 px-4 sm:px-6">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-indigo-500/30 bg-indigo-500/10">
            <svg viewBox="0 0 32 32" className="h-5 w-5" fill="none" aria-hidden="true">
              <path
                d="M8 9l8 14 8-14"
                stroke="#818cf8"
                strokeWidth="2.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="7.5" r="2.2" fill="#34d399" />
            </svg>
          </span>
          <div className="leading-tight">
            <h1 className="text-base font-semibold tracking-tight text-white">
              Vertex<span className="text-indigo-400">Flow</span>
            </h1>
            <p className="hidden text-[11px] tracking-wide text-slate-500 sm:block">
              Autonomous software enterprise
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="hidden rounded-full border border-slate-800 bg-slate-900/60 px-3 py-1 text-[11px] text-slate-400 md:inline">
            CEO · CTO agent swarm
          </span>
          <button
            type="button"
            onClick={onRefresh}
            title={`Backend target: ${API_ORIGIN_LABEL} — click to re-check`}
            className={cn(
              'inline-flex cursor-pointer items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-medium transition hover:brightness-125',
              meta.classes,
            )}
          >
            <span className={cn('h-1.5 w-1.5 rounded-full', meta.dot)} />
            {meta.label}
          </button>

          {user && onSignOut ? (
            <div className="flex items-center gap-2 border-l border-slate-800 pl-2">
              <span
                className="hidden max-w-[160px] truncate text-[11px] text-slate-400 sm:inline"
                title={user.email}
              >
                {user.email}
              </span>
              <button
                type="button"
                onClick={onSignOut}
                className="cursor-pointer rounded-lg border border-slate-800 px-2.5 py-1 text-[11px] font-medium text-slate-400 transition hover:border-rose-500/40 hover:text-rose-300"
              >
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}

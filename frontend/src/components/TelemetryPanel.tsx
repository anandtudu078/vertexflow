import { useEffect, useRef } from 'react';
import { cn } from '../lib/cn';
import type { LogEntry } from '../types';
import { SparkIcon } from './Icons';
import { Card, SectionHeading } from './ui';

const ROLE_CLASSES: Record<LogEntry['role'], string> = {
  CEO: 'text-indigo-300',
  CTO: 'text-emerald-300',
  System: 'text-slate-400',
  Error: 'text-rose-400',
};

const timeFormatter = new Intl.DateTimeFormat(undefined, {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
});

export function TelemetryPanel({
  entries,
  running,
}: {
  entries: LogEntry[];
  running: boolean;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const node = scrollRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [entries]);

  return (
    <Card>
      <SectionHeading
        icon={<SparkIcon />}
        title="Live agent telemetry"
        hint="Stream of orchestration events"
        action={
          <span
            className={cn(
              'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] tracking-wide uppercase',
              running
                ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                : 'border-slate-800 bg-slate-900/60 text-slate-500',
            )}
          >
            <span
              className={cn(
                'h-1.5 w-1.5 rounded-full',
                running ? 'animate-pulse bg-emerald-400' : 'bg-slate-600',
              )}
            />
            {running ? 'live' : 'idle'}
          </span>
        }
      />

      <div
        ref={scrollRef}
        className="h-52 overflow-y-auto rounded-xl border border-slate-800/80 bg-ink-950/80 p-3 font-mono text-[11px] leading-relaxed"
        role="log"
        aria-live="polite"
        aria-label="Agent telemetry"
      >
        {entries.length === 0 ? (
          <p className="text-slate-600">Waiting for the next run…</p>
        ) : (
          <ul className="space-y-1.5">
            {entries.map((entry) => (
              <li key={entry.id} className="flex gap-2">
                <span className="shrink-0 text-slate-600 tabular-nums">
                  {timeFormatter.format(entry.at)}
                </span>
                <span className={cn('shrink-0 font-semibold', ROLE_CLASSES[entry.role])}>
                  [{entry.role}]
                </span>
                <span
                  className={cn(
                    'text-slate-400',
                    entry.level === 'success' && 'text-slate-300',
                    entry.level === 'error' && 'text-rose-300',
                  )}
                >
                  {entry.message}
                </span>
              </li>
            ))}
            {running ? (
              <li className="flex gap-2 text-indigo-400">
                <span className="shrink-0 text-slate-600 tabular-nums">
                  {timeFormatter.format(new Date())}
                </span>
                <span className="animate-pulse">▍</span>
              </li>
            ) : null}
          </ul>
        )}
      </div>
    </Card>
  );
}

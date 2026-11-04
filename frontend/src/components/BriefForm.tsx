import type { FormEvent, KeyboardEvent } from 'react';
import { cn } from '../lib/cn';
import { RefreshIcon, RocketIcon, StopIcon } from './Icons';
import { Card, SectionHeading } from './ui';

const MIN_STATEMENT_LENGTH = 12;
const MIN_STACK_LENGTH = 2;
const MAX_STATEMENT_LENGTH = 800;

const STACK_PRESETS = [
  ['React', 'FastAPI', 'PostgreSQL'],
  ['Next.js', 'TypeScript', 'Prisma'],
  ['Flutter', 'Firebase'],
  ['Django', 'Redis', 'Celery'],
];

interface BriefFormProps {
  statement: string;
  techStack: string;
  running: boolean;
  onStatementChange: (value: string) => void;
  onTechStackChange: (value: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
  onUseExample: () => void;
}

export function BriefForm({
  statement,
  techStack,
  running,
  onStatementChange,
  onTechStackChange,
  onSubmit,
  onCancel,
  onUseExample,
}: BriefFormProps) {
  const statementReady = statement.trim().length >= MIN_STATEMENT_LENGTH;
  const stackReady = techStack.trim().length >= MIN_STACK_LENGTH;
  const canSubmit = statementReady && stackReady && !running;
  const remaining = MAX_STATEMENT_LENGTH - statement.length;

  const addPreset = (preset: string[]) => {
    const current = techStack
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    const lower = current.map((item) => item.toLowerCase());
    const merged = [...current];

    for (const tech of preset) {
      if (!lower.includes(tech.toLowerCase())) merged.push(tech);
    }

    onTechStackChange(merged.join(', '));
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (canSubmit) onSubmit();
  };

  const handleStatementKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if ((event.metaKey || event.ctrlKey) && event.key === 'Enter' && canSubmit) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <Card>
      <SectionHeading
        icon={<RocketIcon />}
        title="Launch project brief"
        hint="Tell the swarm what to build"
        action={
          <button
            type="button"
            onClick={onUseExample}
            disabled={running}
            className="cursor-pointer rounded-lg px-2 py-1 text-[11px] font-medium text-indigo-300 transition hover:bg-indigo-500/10 hover:text-indigo-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Use an example
          </button>
        }
      />

      <form onSubmit={handleSubmit} className="space-y-5" noValidate>
        <div>
          <div className="mb-2 flex items-baseline justify-between gap-2">
            <label
              htmlFor="project-statement"
              className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase"
            >
              Project statement
            </label>
            <span
              className={cn(
                'font-mono text-[10px]',
                remaining < 60 ? 'text-amber-400' : 'text-slate-600',
              )}
            >
              {statement.length}/{MAX_STATEMENT_LENGTH}
            </span>
          </div>
          <textarea
            id="project-statement"
            rows={5}
            maxLength={MAX_STATEMENT_LENGTH}
            value={statement}
            disabled={running}
            onChange={(event) => onStatementChange(event.target.value)}
            onKeyDown={handleStatementKeyDown}
            placeholder="e.g. An AI-powered code review platform that flags risky diffs and writes fix suggestions..."
            className="field resize-y leading-relaxed disabled:cursor-not-allowed disabled:opacity-60"
            aria-describedby="project-statement-hint"
          />
          <p
            id="project-statement-hint"
            className={cn(
              'mt-2 text-[11px]',
              statement.length > 0 && !statementReady ? 'text-amber-400' : 'text-slate-500',
            )}
          >
            {statementReady
              ? 'Ctrl / ⌘ + Enter launches the pipeline.'
              : `Add at least ${MIN_STATEMENT_LENGTH} characters so the CEO has something to work with.`}
          </p>
        </div>

        <div>
          <label
            htmlFor="tech-stack"
            className="mb-2 block text-[11px] font-semibold tracking-wider text-slate-400 uppercase"
          >
            Target tech stack
          </label>
          <input
            id="tech-stack"
            type="text"
            value={techStack}
            disabled={running}
            onChange={(event) => onTechStackChange(event.target.value)}
            placeholder="e.g. Python, FastAPI, React, PostgreSQL"
            className="field disabled:cursor-not-allowed disabled:opacity-60"
            aria-describedby="tech-stack-hint"
          />
          <p id="tech-stack-hint" className="mt-2 text-[11px] text-slate-500">
            Comma separated. The CTO agent designs the architecture around these tools.
          </p>

          <div className="mt-3 flex flex-wrap gap-1.5">
            {STACK_PRESETS.map((preset) => (
              <button
                key={preset.join('-')}
                type="button"
                onClick={() => addPreset(preset)}
                disabled={running}
                className="cursor-pointer rounded-lg border border-slate-800 bg-slate-900/60 px-2 py-1 text-[11px] text-slate-400 transition hover:border-indigo-500/40 hover:text-indigo-300 disabled:cursor-not-allowed disabled:opacity-40"
              >
                + {preset.join(' · ')}
              </button>
            ))}
          </div>
        </div>

        <div className="flex flex-col gap-2 pt-1">
          <button
            type="submit"
            disabled={!canSubmit}
            className={cn(
              'inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition',
              canSubmit
                ? 'cursor-pointer bg-indigo-600 shadow-lg shadow-indigo-600/25 hover:bg-indigo-500 active:scale-[0.99]'
                : 'cursor-not-allowed bg-indigo-600/40 text-indigo-100/60',
            )}
          >
            {running ? (
              <>
                <RefreshIcon className="h-4 w-4 animate-spin" />
                Agents collaborating…
              </>
            ) : (
              <>
                <RocketIcon className="h-4 w-4" />
                Initialize swarm execution
              </>
            )}
          </button>

          {running ? (
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex cursor-pointer items-center justify-center gap-2 rounded-xl border border-slate-800 px-4 py-2 text-xs font-medium text-slate-400 transition hover:border-rose-500/40 hover:text-rose-300"
            >
              <StopIcon className="h-3.5 w-3.5" />
              Stop run
            </button>
          ) : (
            <p className="text-center text-[10px] text-slate-600">
              Runs all 6 agents — usually 30–120 seconds.
            </p>
          )}
        </div>
      </form>
    </Card>
  );
}

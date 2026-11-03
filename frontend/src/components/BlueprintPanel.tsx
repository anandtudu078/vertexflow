import { difficultyTone } from '../lib/tone';
import type { CTOTechnicalBlueprint } from '../types';
import { DatabaseIcon, LayersIcon, TicketIcon } from './Icons';
import { Badge, Card, SectionHeading } from './ui';

export function BlueprintPanel({
  blueprint,
}: {
  blueprint: Partial<CTOTechnicalBlueprint>;
}) {
  const models = blueprint.database_models ?? [];
  const tasks = blueprint.tasks ?? [];

  return (
    <Card>
      <SectionHeading
        icon={<LayersIcon />}
        title="CTO architecture blueprint"
        hint="Design produced by the CTO agent"
        action={
          tasks.length > 0 ? (
            <Badge tone="amber">
              {tasks.length} {tasks.length === 1 ? 'ticket' : 'tickets'}
            </Badge>
          ) : undefined
        }
      />

      <div className="rounded-xl border border-slate-800/80 bg-ink-950/60 p-4">
        <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          Architecture overview
        </h3>
        {blueprint.architecture_overview ? (
          <p className="text-sm leading-relaxed whitespace-pre-line text-slate-300">
            {blueprint.architecture_overview}
          </p>
        ) : (
          <p className="text-sm text-slate-500 italic">
            No architecture overview was returned for this brief.
          </p>
        )}
      </div>

      <div className="mt-4">
        <h3 className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          <DatabaseIcon className="h-3.5 w-3.5" />
          Database models
        </h3>
        {models.length > 0 ? (
          <ul className="flex flex-wrap gap-1.5">
            {models.map((model, index) => (
              <li
                key={`${model}-${index}`}
                className="rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1 font-mono text-[11px] text-slate-300"
              >
                {model}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-xs text-slate-500 italic">No database models were proposed.</p>
        )}
      </div>

      <div className="mt-5">
        <h3 className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          <TicketIcon className="h-3.5 w-3.5" />
          Task tickets
        </h3>
        {tasks.length > 0 ? (
          <ul className="space-y-2">
            {tasks.map((task, index) => (
              <li
                key={`${task.task_id}-${index}`}
                className="flex flex-col gap-2 rounded-xl border border-slate-800/80 bg-ink-950/60 p-3.5 transition hover:border-amber-500/25 sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="min-w-0">
                  <span className="font-mono text-[10px] tracking-wide text-slate-500">
                    TASK #{task.task_id}
                  </span>
                  <h4 className="mt-0.5 text-sm font-medium text-white">{task.title}</h4>
                  <p className="mt-1 text-xs leading-relaxed text-slate-400">
                    {task.description}
                  </p>
                </div>
                <Badge tone={difficultyTone(task.difficulty)} className="self-start">
                  {task.difficulty || 'unrated'}
                </Badge>
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-slate-800 bg-ink-950/40 p-4 text-sm text-slate-500 italic">
            The CTO agent did not return any task tickets.
          </p>
        )}
      </div>
    </Card>
  );
}

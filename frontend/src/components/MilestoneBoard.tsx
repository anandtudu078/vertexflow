import type { Milestone } from '../types';
import { MilestoneIcon } from './Icons';
import { Badge, Card, SectionHeading } from './ui';

export function MilestoneBoard({ milestones }: { milestones: Milestone[] }) {
  return (
    <Card>
      <SectionHeading
        icon={<MilestoneIcon />}
        title="Strategic milestones"
        hint="Sequenced by the CEO agent"
        action={
          <Badge tone="indigo">
            {milestones.length} {milestones.length === 1 ? 'milestone' : 'milestones'}
          </Badge>
        }
      />

      {milestones.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-800 bg-ink-950/40 p-4 text-sm text-slate-500 italic">
          The CEO agent did not return any milestones for this brief.
        </p>
      ) : (
        <ol className="relative space-y-3">
          {milestones.map((milestone, index) => (
            <li
              key={`${milestone.milestone_id}-${index}`}
              className="relative flex gap-3 rounded-xl border border-slate-800/80 bg-ink-950/60 p-4 transition hover:border-indigo-500/30"
            >
              <div className="flex flex-col items-center">
                <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/10 font-mono text-[11px] font-semibold text-indigo-300">
                  {milestone.milestone_id}
                </span>
                {index < milestones.length - 1 ? (
                  <span className="mt-1 w-px flex-1 bg-gradient-to-b from-indigo-500/30 to-transparent" />
                ) : null}
              </div>

              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3 className="text-sm font-medium text-white">{milestone.title}</h3>
                  {milestone.assigned_department ? (
                    <Badge tone="slate">{milestone.assigned_department}</Badge>
                  ) : null}
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                  {milestone.description}
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

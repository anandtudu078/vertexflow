import { API_ORIGIN_LABEL } from '../lib/api';
import { BriefcaseIcon, CompassIcon, LayersIcon } from './Icons';
import { Card } from './ui';

const STEPS = [
  {
    icon: <BriefcaseIcon className="h-4 w-4" />,
    title: 'You write the brief',
    body: 'Describe the product and the stack you want to build it with.',
  },
  {
    icon: <CompassIcon className="h-4 w-4" />,
    title: 'The CEO sets direction',
    body: 'A company vision plus 3–5 sequential strategic milestones.',
  },
  {
    icon: <LayersIcon className="h-4 w-4" />,
    title: 'The CTO designs the build',
    body: 'Architecture overview, database models and developer task tickets.',
  },
];

export function EmptyState() {
  return (
    <Card className="animate-fade-in">
      <div className="flex flex-col items-center px-2 py-6 text-center">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
          <CompassIcon className="h-6 w-6" />
        </span>
        <h2 className="text-lg font-semibold text-white">Your virtual company is idle</h2>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-400">
          Fill in the brief on the left and the agent swarm will take it from strategy to
          engineering tickets in a single run.
        </p>
      </div>

      <ol className="mt-2 grid gap-3 sm:grid-cols-3">
        {STEPS.map((step, index) => (
          <li
            key={step.title}
            className="rounded-xl border border-slate-800/80 bg-ink-950/60 p-4 transition hover:border-indigo-500/30"
          >
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg border border-slate-800 bg-slate-900 text-indigo-300">
                {step.icon}
              </span>
              <span className="font-mono text-[10px] text-slate-600">STEP {index + 1}</span>
            </div>
            <h3 className="mt-3 text-sm font-medium text-white">{step.title}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-500">{step.body}</p>
          </li>
        ))}
      </ol>

      <p className="mt-5 border-t border-slate-800/80 pt-4 text-center text-[11px] text-slate-600">
        Orchestration engine: FastAPI on <span className="font-mono">{API_ORIGIN_LABEL}</span>
      </p>
    </Card>
  );
}

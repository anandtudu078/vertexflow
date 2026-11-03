import { Card } from './ui';

function Bar({ className = '' }: { className?: string }) {
  return <div className={`skeleton rounded-md ${className}`} />;
}

export function ResultsSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-live="polite">
      <Card>
        <div className="flex items-center gap-3">
          <span className="h-2 w-2 animate-pulse rounded-full bg-indigo-400" />
          <p className="text-sm font-medium text-slate-300">
            The agents are collaborating on your brief…
          </p>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          {[0, 1, 2].map((index) => (
            <div key={index} className="rounded-xl border border-slate-800/60 p-3">
              <Bar className="h-2.5 w-16" />
              <Bar className="mt-2 h-2 w-full" />
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <Bar className="h-3 w-32" />
        <Bar className="mt-4 h-3 w-full" />
        <Bar className="mt-2 h-3 w-11/12" />
        <Bar className="mt-2 h-3 w-8/12" />
      </Card>

      <Card>
        <Bar className="h-3 w-40" />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {[0, 1, 2, 3].map((index) => (
            <div key={index} className="rounded-xl border border-slate-800/60 p-4">
              <Bar className="h-2.5 w-24" />
              <Bar className="mt-3 h-3 w-full" />
              <Bar className="mt-2 h-2.5 w-10/12" />
              <Bar className="mt-3 h-2 w-16" />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

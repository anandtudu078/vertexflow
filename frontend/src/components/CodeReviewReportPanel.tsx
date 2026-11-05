import { Card, SectionHeading } from './ui';

/** Panel displaying the Code Reviewer agent's report (raw record). */
export function CodeReviewReportPanel({ review }: { review?: { raw?: Record<string, unknown> } }) {
  const raw = review?.raw ?? {};

  const keys = Object.keys(raw).filter(k => raw[k] !== undefined && raw[k] !== null);

  return (
    <Card>
      <SectionHeading
        icon={<ShieldIcon />}

        title="Code review & static analysis"
        hint="Code quality findings and style issues"
        tone="indigo"
      />

      {keys.length === 0 ? (
        <p className="text-sm text-slate-500 italic">No code review captured.</p>
      ) : (
        <div className="space-y-2 text-sm text-slate-300">
          {keys.map((key) => {
            const value = raw[key];
            const valueStr =
              typeof value === 'string'
                ? value.length > 200
                  ? value.slice(0, 200) + '...'
                  : value
                : typeof value === 'object'
                  ? JSON.stringify(value).slice(0, 200) + '...'
                  : String(value);

            return (
              <div key={key} className="flex flex-col gap-1">
                <span className="font-medium text-white">{key}</span>
                <span className="text-[10px] text-slate-500 truncate">{valueStr}</span>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

import { ShieldIcon } from './Icons';
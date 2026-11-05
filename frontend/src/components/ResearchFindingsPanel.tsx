import { Card, SectionHeading } from './ui';
import { CompassIcon } from './Icons';

/** Panel displaying the Research agent's findings (raw record). */
export function ResearchFindingsPanel({ findings }: { findings?: { raw?: Record<string, unknown> } }) {
  const raw = findings?.raw ?? {};

  const keys = Object.keys(raw).filter(k => raw[k] !== undefined && raw[k] !== null);

  return (
    <Card>
      <SectionHeading
        icon={<CompassIcon />}

        title="Research findings"
        hint="Modern patterns, library docs, and pitfalls gathered by the research agent"
        tone="indigo"
      />

      {keys.length === 0 ? (
        <p className="text-sm text-slate-500 italic">No research findings captured.</p>
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
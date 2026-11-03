import { scoreTone, severityTone } from '../lib/tone';
import type { SecurityAuditReport } from '../types';
import { ShieldIcon } from './Icons';
import { Badge, Card, SectionHeading } from './ui';

export function SecurityAuditPanel({
  audit,
}: {
  audit: Partial<SecurityAuditReport>;
}) {
  const vulnerabilities = audit.vulnerabilities ?? [];
  const score = audit.security_score ?? 0;
  const hasData = audit.overall_status || vulnerabilities.length > 0 || score > 0;

  return (
    <Card>
      <SectionHeading
        icon={<ShieldIcon />}
        title="Security audit report"
        hint="Vulnerability scan by the Security Auditor agent"
        action={
          audit.overall_status ? (
            <Badge tone={scoreTone(score)}>{audit.overall_status}</Badge>
          ) : undefined
        }
      />

      {!hasData ? (
        <p className="text-sm text-slate-500 italic">
          The Security Auditor agent did not return a report.
        </p>
      ) : (
        <div className="space-y-4">
          {/* Score bar */}
          {score > 0 ? (
            <div>
              <div className="mb-1.5 flex items-center justify-between">
                <span className="text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
                  Security score
                </span>
                <span className="font-mono text-lg font-semibold text-white">{score} / 100</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                <div
                  className={`h-full rounded-full transition-all ${
                    score >= 80
                      ? 'bg-emerald-500'
                      : score >= 50
                        ? 'bg-amber-500'
                        : 'bg-rose-500'
                  }`}
                  style={{ width: `${score}%` }}
                />
              </div>
            </div>
          ) : null}

          {/* Vulnerabilities */}
          {vulnerabilities.length > 0 ? (
            <div>
              <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
                Vulnerabilities ({vulnerabilities.length})
              </h3>
              <ul className="space-y-2">
                {vulnerabilities.map((vuln, index) => (
                  <li
                    key={`${vuln.vulnerability_id}-${index}`}
                    className="rounded-xl border border-slate-800/80 bg-ink-950/60 p-3.5"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <span className="font-mono text-[10px] tracking-wide text-slate-500">
                        {vuln.vulnerability_id}
                      </span>
                      <Badge tone={severityTone(vuln.severity)}>{vuln.severity}</Badge>
                    </div>
                    <p className="mt-1.5 text-sm font-medium text-white">{vuln.description}</p>
                    {vuln.remediation ? (
                      <p className="mt-1.5 text-xs leading-relaxed text-slate-400">
                        <span className="text-emerald-400 font-medium">Fix: </span>
                        {vuln.remediation}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="rounded-xl border border-dashed border-emerald-800/40 bg-emerald-500/5 p-4 text-sm text-emerald-400">
              No vulnerabilities detected.
            </p>
          )}

          {/* Compliance notes */}
          {audit.compliance_notes ? (
            <div>
              <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
                Compliance notes
              </h3>
              <p className="text-sm leading-relaxed whitespace-pre-line text-slate-300">
                {audit.compliance_notes}
              </p>
            </div>
          ) : null}
        </div>
      )}
    </Card>
  );
}

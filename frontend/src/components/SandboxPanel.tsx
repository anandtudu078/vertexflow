import type { SandboxResult } from '../types';
import { TerminalIcon } from './Icons';
import { Badge, Card, SectionHeading } from './ui';

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5 sm:flex-row sm:items-baseline sm:gap-3">
      <span className="w-28 shrink-0 text-[11px] font-semibold tracking-wider text-slate-500 uppercase">
        {label}
      </span>
      <span className="break-all font-mono text-xs text-slate-300">{value}</span>
    </div>
  );
}

export function SandboxPanel({
  sandbox,
}: {
  sandbox: Partial<SandboxResult>;
}) {
  const isReady = Boolean(sandbox.status);

  return (
    <Card>
      <SectionHeading
        icon={<TerminalIcon />}
        title="Sandbox scaffold"
        hint="Generated project written to disk and assigned a run port"
        tone="amber"
        action={
          isReady ? (
            <Badge tone="emerald">{sandbox.status ?? 'Ready'}</Badge>
          ) : (
            <Badge tone="slate">Not run</Badge>
          )
        }
      />

      {isReady ? (
        <div className="space-y-3 rounded-xl border border-slate-800/80 bg-black/30 px-4 py-4">
          {sandbox.project_path ? (
            <InfoRow label="Project path" value={sandbox.project_path} />
          ) : null}
          {sandbox.assigned_port !== undefined ? (
            <InfoRow label="Assigned port" value={String(sandbox.assigned_port)} />
          ) : null}
          {sandbox.status ? (
            <InfoRow label="Status" value={sandbox.status} />
          ) : null}
        </div>
      ) : (
        <p className="text-sm text-slate-500 italic">
          The sandbox did not return a result for this run.
        </p>
      )}

      {sandbox.assigned_port !== undefined && (
        <p className="mt-3 text-xs text-slate-500">
          To boot the generated app:{' '}
          <code className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-slate-300">
            cd {sandbox.project_path ?? '<project_path>'} &amp;&amp; uvicorn app:app --port{' '}
            {sandbox.assigned_port}
          </code>
        </p>
      )}
    </Card>
  );
}

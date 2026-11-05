import { useCallback, useState } from 'react';
import { blueprintToMarkdown, downloadBlueprintJson } from '../lib/export';
import type { ProjectBrief, ProjectExecutionResponse } from '../types';
import { BackendCodePanel } from './BackendCodePanel';
import { BlueprintPanel } from './BlueprintPanel';
import { FrontendCodePanel } from './FrontendCodePanel';
import { CheckIcon, CompassIcon, CopyIcon, DownloadIcon } from './Icons';
import { MilestoneBoard } from './MilestoneBoard';
import { ProductRequirementsPanel } from './ProductRequirementsPanel';
import { QaReportPanel } from './QaReportPanel';
import { ResearchFindingsPanel } from './ResearchFindingsPanel';
import { UiUxBlueprintPanel } from './UiUxBlueprintPanel';
import { CodeReviewReportPanel } from './CodeReviewReportPanel';
import { SandboxPanel } from './SandboxPanel';
import { SecurityAuditPanel } from './SecurityAuditPanel';
import { Badge, Card, SectionHeading } from './ui';

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-xl border border-slate-800/80 bg-ink-950/60 px-3 py-2.5">
      <p className="font-mono text-lg leading-none font-semibold text-white">{value}</p>
      <p className="mt-1 text-[10px] tracking-wider text-slate-500 uppercase">{label}</p>
    </div>
  );
}

export function ResultsView({
  result,
  brief,
  onNewProject,
}: {
  result: ProjectExecutionResponse;
  brief: ProjectBrief;
  onNewProject: () => void;
}) {
  const [copied, setCopied] = useState<boolean>(false);
  const blueprint = result.technical_blueprint;
  const tasks = blueprint.tasks ?? [];
  const models = blueprint.database_models ?? [];
  const userStories = result.product_requirements?.user_stories ?? [];
  const vulnCount = result.security_audit?.vulnerabilities?.length ?? 0;
  const securityScore = result.security_audit?.security_score ?? 0;
  const sandboxPort = result.sandbox_result?.assigned_port;

  const stack = brief.target_tech_stack
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(blueprintToMarkdown(result, brief));
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  }, [result, brief]);

  return (
    <div className="animate-rise space-y-4">
      {/* Header card */}
      <Card className="bg-gradient-to-br from-indigo-500/10 via-ink-900/80 to-ink-900/80">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Badge tone="emerald">
              <CheckIcon className="h-3 w-3" />
              Run complete
            </Badge>
            <span className="text-[11px] text-slate-500">{result.current_status}</span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCopy}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-[11px] font-medium text-slate-300 transition hover:border-indigo-500/40 hover:text-white"
            >
              {copied ? (
                <CheckIcon className="h-3.5 w-3.5 text-emerald-400" />
              ) : (
                <CopyIcon className="h-3.5 w-3.5" />
              )}
              {copied ? 'Copied' : 'Copy Markdown'}
            </button>
            <button
              type="button"
              onClick={() => downloadBlueprintJson(result, brief)}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-slate-800 bg-slate-900/60 px-2.5 py-1.5 text-[11px] font-medium text-slate-300 transition hover:border-indigo-500/40 hover:text-white"
            >
              <DownloadIcon className="h-3.5 w-3.5" />
              JSON
            </button>
          </div>
        </div>

        <p className="mt-4 line-clamp-3 text-base leading-relaxed font-medium text-white">
          {brief.project_statement}
        </p>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {stack.map((tech) => (
            <Badge key={tech} tone="indigo">
              {tech}
            </Badge>
          ))}
          <button
            type="button"
            onClick={onNewProject}
            className="ml-auto cursor-pointer rounded-lg px-2 py-1 text-[11px] font-medium text-slate-400 transition hover:text-indigo-300"
          >
            Start a new brief →
          </button>
        </div>

        {/* Stats strip */}
        <div className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-7">
          <Stat label="Milestones" value={result.milestones.length} />
          <Stat label="Tickets" value={tasks.length} />
          <Stat label="DB models" value={models.length} />
          <Stat label="User stories" value={userStories.length} />
          <Stat label="Vulns" value={vulnCount} />
          <Stat label="Sec score" value={securityScore > 0 ? `${securityScore}/100` : '—'} />
          <Stat label="Port" value={sandboxPort !== undefined ? String(sandboxPort) : '—'} />
        </div>
      </Card>

      {/* CEO vision */}
      <Card>
        <SectionHeading
          icon={<CompassIcon />}
          title="CEO company vision"
          hint="Strategic direction for the product"
          tone="emerald"
        />
        {result.vision ? (
          <p className="text-sm leading-relaxed whitespace-pre-line text-slate-300">
            {result.vision}
          </p>
        ) : (
          <p className="text-sm text-slate-500 italic">
            The CEO agent did not return a vision statement.
          </p>
        )}
      </Card>

      {/* Strategy + architecture */}
      <MilestoneBoard milestones={result.milestones} />
      <BlueprintPanel blueprint={blueprint} />

      {/* PM requirements */}
      <ProductRequirementsPanel requirements={result.product_requirements ?? {}} />

      {/* Worker code outputs */}
      <BackendCodePanel backendCode={result.backend_code ?? {}} />
      <FrontendCodePanel frontendCode={result.frontend_code ?? {}} />

      {/* Security audit */}
      <SecurityAuditPanel audit={result.security_audit ?? {}} />

      {/* Research findings */}
      <ResearchFindingsPanel findings={result.research_findings ?? {}} />

      {/* UI/UX blueprint */}
      <UiUxBlueprintPanel blueprint={result.ui_ux_blueprint ?? {}} />

      {/* Code review */}
      <CodeReviewReportPanel review={result.code_review ?? {}} />

      {/* QA report */}
      <QaReportPanel qa={result.qa_report ?? {}} />

      {/* Sandbox scaffold */}
      <SandboxPanel sandbox={result.sandbox_result ?? {}} />
    </div>
  );
}

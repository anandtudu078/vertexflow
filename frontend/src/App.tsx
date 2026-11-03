import { useCallback, useEffect, useRef, useState } from 'react';
import { BriefForm } from './components/BriefForm';
import { EmptyState } from './components/EmptyState';
import { Header } from './components/Header';
import { AlertIcon, RefreshIcon } from './components/Icons';
import { PipelineStages } from './components/PipelineStages';
import { ResultsSkeleton } from './components/ResultsSkeleton';
import { ResultsView } from './components/ResultsView';
import { TelemetryPanel } from './components/TelemetryPanel';
import { ApiError, checkBackendHealth, launchProject } from './lib/api';
import type {
  ApiStatus,
  LogEntry,
  Phase,
  ProjectBrief,
  ProjectExecutionResponse,
} from './types';

const EXAMPLES: ProjectBrief[] = [
  {
    project_statement:
      'An AI-powered code review platform that inspects pull requests, flags risky diffs and writes fix suggestions developers can apply with one click.',
    target_tech_stack: 'Python, FastAPI, React, PostgreSQL, Redis',
  },
  {
    project_statement:
      'A habit tracking mobile app with streak gamification, shared challenges between friends and daily reminder notifications.',
    target_tech_stack: 'Flutter, Firebase, Cloud Functions',
  },
  {
    project_statement:
      'A marketplace for independent coffee roasters where shops manage inventory, subscriptions and order fulfilment.',
    target_tech_stack: 'Next.js, TypeScript, Prisma, Stripe, PostgreSQL',
  },
];

const WELCOME_LOG: LogEntry = {
  id: 0,
  at: new Date(),
  role: 'System',
  message: 'Orchestration engine ready. Waiting for a project brief.',
  level: 'info',
};

export default function App() {
  const [statement, setStatement] = useState<string>('');
  const [techStack, setTechStack] = useState<string>('');
  const [phase, setPhase] = useState<Phase>('idle');
  const [logs, setLogs] = useState<LogEntry[]>(() => [WELCOME_LOG]);
  const [result, setResult] = useState<ProjectExecutionResponse | null>(null);
  const [submittedBrief, setSubmittedBrief] = useState<ProjectBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<ApiStatus>('checking');

  const logId = useRef<number>(1);
  const abortRef = useRef<AbortController | null>(null);
  const exampleIndex = useRef<number>(0);

  const pushLog = useCallback(
    (role: LogEntry['role'], message: string, level: LogEntry['level'] = 'info') => {
      const entry: LogEntry = { id: logId.current++, at: new Date(), role, message, level };
      setLogs((previous) => [...previous, entry]);
    },
    [],
  );

  const refreshHealth = useCallback(async (showChecking = false) => {
    if (showChecking) setHealth('checking');
    const online = await checkBackendHealth();
    setHealth(online ? 'online' : 'offline');
  }, []);

  useEffect(() => {
    const tick = () => {
      void refreshHealth();
    };
    const initial = window.setTimeout(tick, 0);
    const interval = window.setInterval(tick, 20_000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(interval);
    };
  }, [refreshHealth]);

  useEffect(() => {
    return () => abortRef.current?.abort();
  }, []);

  const handleLaunch = useCallback(async () => {
    if (phase === 'running') return;

    const brief: ProjectBrief = {
      project_statement: statement.trim(),
      target_tech_stack: techStack.trim(),
    };

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setPhase('running');
    setError(null);
    setResult(null);
    setSubmittedBrief(brief);
    setLogs([]);
    pushLog('System', 'Brief dispatched to the orchestration engine.');
    pushLog('CEO', 'Analyzing the project brief and defining strategy…');

    const startedAt = performance.now();

    try {
      const data = await launchProject(brief, controller.signal);
      const seconds = ((performance.now() - startedAt) / 1000).toFixed(1);

      setResult(data);
      setPhase('success');
      setHealth('online');
      setLogs((previous) => [
        ...previous,
        {
          id: logId.current++,
          at: new Date(),
          role: 'CEO',
          message: `Vision and ${data.milestones.length} milestone${
            data.milestones.length === 1 ? '' : 's'
          } received.`,
          level: 'success',
        },
        {
          id: logId.current++,
          at: new Date(),
          role: 'CTO',
          message: `Blueprint complete: ${data.technical_blueprint.tasks?.length ?? 0} task tickets, ${
            data.technical_blueprint.database_models?.length ?? 0
          } data models.`,
          level: 'success',
        },
        {
          id: logId.current++,
          at: new Date(),
          role: 'System',
          message: `Pipeline finished in ${seconds}s.`,
          level: 'success',
        },
      ]);
    } catch (caught) {
      if (controller.signal.aborted) {
        setPhase('idle');
        pushLog('System', 'Run cancelled before the agents finished.', 'error');
        return;
      }

      const message =
        caught instanceof ApiError
          ? caught.message
          : 'An unexpected error occurred while running the pipeline.';

      setError(message);
      setPhase('error');
      pushLog('Error', message, 'error');
      if (message.toLowerCase().includes('could not reach')) setHealth('offline');
    }
  }, [phase, statement, techStack, pushLog]);

  const handleCancel = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const handleUseExample = useCallback(() => {
    const example = EXAMPLES[exampleIndex.current % EXAMPLES.length];
    exampleIndex.current += 1;
    if (!example) return;
    setStatement(example.project_statement);
    setTechStack(example.target_tech_stack);
    setError(null);
    pushLog('System', 'Example brief loaded into the editor.');
  }, [pushLog]);

  const handleNewProject = useCallback(() => {
    abortRef.current?.abort();
    setResult(null);
    setSubmittedBrief(null);
    setError(null);
    setPhase('idle');
    setLogs([{ ...WELCOME_LOG, at: new Date() }]);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const handleRetry = useCallback(() => {
    void handleLaunch();
  }, [handleLaunch]);

  return (
    <div className="flex min-h-screen flex-col">
      <Header status={health} onRefresh={() => void refreshHealth(true)} />

      <main className="mx-auto w-full max-w-[1400px] flex-1 px-4 py-6 sm:px-6 lg:py-8">
        <div className="grid gap-5 lg:grid-cols-[minmax(320px,380px)_minmax(0,1fr)] lg:items-start">
          <div className="space-y-5 lg:sticky lg:top-20">
            <BriefForm
              statement={statement}
              techStack={techStack}
              running={phase === 'running'}
              onStatementChange={setStatement}
              onTechStackChange={setTechStack}
              onSubmit={() => void handleLaunch()}
              onCancel={handleCancel}
              onUseExample={handleUseExample}
            />
            <TelemetryPanel entries={logs} running={phase === 'running'} />
          </div>

          <div className="space-y-5">
            <PipelineStages phase={phase} />

            {error ? (
              <div
                role="alert"
                className="animate-fade-in flex flex-col gap-3 rounded-2xl border border-rose-500/30 bg-rose-500/10 p-4 sm:flex-row sm:items-start sm:justify-between"
              >
                <div className="flex gap-3">
                  <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                  <div>
                    <p className="text-sm font-medium text-rose-200">Pipeline failed</p>
                    <p className="mt-1 text-xs leading-relaxed text-rose-200/80">{error}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={handleRetry}
                  className="inline-flex shrink-0 cursor-pointer items-center gap-1.5 self-start rounded-lg border border-rose-500/40 bg-rose-500/10 px-2.5 py-1.5 text-[11px] font-medium text-rose-200 transition hover:bg-rose-500/20"
                >
                  <RefreshIcon className="h-3.5 w-3.5" />
                  Retry
                </button>
              </div>
            ) : null}

            {phase === 'running' ? (
              <ResultsSkeleton />
            ) : phase === 'success' && result && submittedBrief ? (
              <ResultsView
                result={result}
                brief={submittedBrief}
                onNewProject={handleNewProject}
              />
            ) : phase === 'idle' || phase === 'error' ? (
              <EmptyState />
            ) : null}
          </div>
        </div>
      </main>

      <footer className="border-t border-slate-800/70 px-4 py-5 sm:px-6">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col items-center justify-between gap-2 text-[11px] text-slate-600 sm:flex-row">
          <p>VertexFlow · CEO + CTO multi-agent orchestration</p>
          <p className="font-mono">FastAPI · LangGraph · Gemini</p>
        </div>
      </footer>
    </div>
  );
}

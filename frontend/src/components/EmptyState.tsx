import { API_ORIGIN_LABEL } from '../lib/api';
import { CompassIcon } from './Icons';
import { Card } from './ui';

// ─── node definitions ───────────────────────────────────────────────────────

interface AgentNode {
  id: string;
  label: string;
  sublabel: string;
  color: string;         // Tailwind color token used for accent
  borderColor: string;   // inline stroke colour for SVG connector
  iconPath: string;      // SVG path(s) inside a 24×24 viewBox
}

const AGENTS: AgentNode[] = [
  {
    id: 'ceo',
    label: 'CEO',
    sublabel: 'Vision · Milestones',
    color: 'indigo',
    borderColor: '#818cf8',
    iconPath: 'M12 3 3 8.5v5C3 18.5 7 21.5 12 22c5-0.5 9-3.5 9-8.5v-5L12 3Z M9 12l2 2 4-4',
  },
  {
    id: 'cto',
    label: 'CTO',
    sublabel: 'Architecture · Tickets',
    color: 'emerald',
    borderColor: '#34d399',
    iconPath:
      'm12 3 8 4.5-8 4.5-8-4.5L12 3Z m-8 9 8 4.5 8-4.5 M4 16.5 12 21l8-4.5',
  },
  {
    id: 'pm',
    label: 'PM',
    sublabel: 'Scope · User stories',
    color: 'sky',
    borderColor: '#38bdf8',
    iconPath:
      'M4.5 5h15A1.5 1.5 0 0 1 21 6.5v13A1.5 1.5 0 0 1 19.5 21h-15A1.5 1.5 0 0 1 3 19.5v-13A1.5 1.5 0 0 1 4.5 5Z M8 10h8 M8 14h5',
  },
  {
    id: 'backend',
    label: 'Backend',
    sublabel: 'FastAPI · SQLAlchemy',
    color: 'amber',
    borderColor: '#fbbf24',
    iconPath: 'm7 8-4 4 4 4 M17 8l4 4-4 4 M14 4l-4 16',
  },
  {
    id: 'frontend',
    label: 'Frontend',
    sublabel: 'React · TypeScript',
    color: 'violet',
    borderColor: '#a78bfa',
    iconPath:
      'm12 3 8 4.5v9L12 21l-8-4.5v-9L12 3Z M12 3v18 M4 7.5l8 4.5 8-4.5',
  },
  {
    id: 'security',
    label: 'Security',
    sublabel: 'Audit · Score',
    color: 'rose',
    borderColor: '#fb7185',
    iconPath:
      'M12 3 4 6.5v5C4 16 7.6 20.2 12 21c4.4-.8 8-5 8-9.5v-5L12 3Z m-3 9 2 2 4-4',
  },
  {
    id: 'sandbox',
    label: 'Sandbox',
    sublabel: 'Scaffold · Port alloc',
    color: 'slate',
    borderColor: '#94a3b8',
    iconPath:
      'M3 3.5h18v17H3z M7 9l3.5 3L7 15 M13 15h4',
  },
];

// ─── colour maps ─────────────────────────────────────────────────────────────

const BG: Record<string, string> = {
  indigo: 'bg-indigo-500/10',
  emerald: 'bg-emerald-500/10',
  sky: 'bg-sky-500/10',
  amber: 'bg-amber-500/10',
  violet: 'bg-violet-500/10',
  rose: 'bg-rose-500/10',
  slate: 'bg-slate-500/10',
};

const BORDER: Record<string, string> = {
  indigo: 'border-indigo-500/40',
  emerald: 'border-emerald-500/40',
  sky: 'border-sky-500/40',
  amber: 'border-amber-500/40',
  violet: 'border-violet-500/40',
  rose: 'border-rose-500/40',
  slate: 'border-slate-600/60',
};

const TEXT: Record<string, string> = {
  indigo: 'text-indigo-300',
  emerald: 'text-emerald-300',
  sky: 'text-sky-300',
  amber: 'text-amber-300',
  violet: 'text-violet-300',
  rose: 'text-rose-300',
  slate: 'text-slate-400',
};

const SUB: Record<string, string> = {
  indigo: 'text-indigo-400/70',
  emerald: 'text-emerald-400/70',
  sky: 'text-sky-400/70',
  amber: 'text-amber-400/70',
  violet: 'text-violet-400/70',
  rose: 'text-rose-400/70',
  slate: 'text-slate-500',
};

// ─── small agent card ─────────────────────────────────────────────────────────

function AgentCard({ agent }: { agent: AgentNode }) {
  return (
    <div
      className={`flex flex-col items-center gap-1.5 rounded-2xl border px-4 py-3 shadow-lg backdrop-blur transition-transform hover:scale-105 ${BG[agent.color]} ${BORDER[agent.color]}`}
      style={{ minWidth: 110 }}
    >
      {/* icon */}
      <span
        className={`flex h-9 w-9 items-center justify-center rounded-xl border ${BG[agent.color]} ${BORDER[agent.color]}`}
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={1.7}
          strokeLinecap="round"
          strokeLinejoin="round"
          className={`h-4 w-4 ${TEXT[agent.color]}`}
          aria-hidden="true"
        >
          {agent.iconPath.split(' M').map((segment, i) => (
            <path key={i} d={i === 0 ? segment : `M${segment}`} />
          ))}
        </svg>
      </span>
      <span className={`text-sm font-semibold tracking-wide ${TEXT[agent.color]}`}>
        {agent.label}
      </span>
      <span className={`text-center text-[10px] leading-tight ${SUB[agent.color]}`}>
        {agent.sublabel}
      </span>
    </div>
  );
}

// ─── connector SVG overlay ────────────────────────────────────────────────────
// Drawn as a pure SVG using fixed proportions; the layout is described in
// percentage terms so it scales with the container width.

function TreeConnectors() {
  // All coordinates are in a 1000×420 user-space that maps onto the container.
  // Nodes are centred at these x positions (matches the flex layout below):
  //   CEO               → 500
  //   CTO               → 500
  //   PM                → 500
  //   Backend           → 270
  //   Frontend          → 500   (hidden — PM fans out to Backend & Frontend)
  //                             actually: Backend=270, Frontend=730
  //   Security          → 500
  //   Sandbox           → 500
  //
  // Row y-centres (approximate, matching node height + gap):
  //   CEO row  → 40
  //   CTO row  → 145
  //   PM row   → 250
  //   workers  → 355
  //   Security → 460
  //   Sandbox  → 565
  //
  // We only draw the lines — the nodes sit on top inside the HTML.

  const stroke = 'rgba(148,163,184,0.25)';
  const sw = 1.5;

  return (
    <svg
      viewBox="0 0 1000 560"
      preserveAspectRatio="xMidYMid meet"
      className="pointer-events-none absolute inset-0 h-full w-full"
      aria-hidden="true"
    >
      {/* CEO → CTO */}
      <line x1={500} y1={68} x2={500} y2={118} stroke={stroke} strokeWidth={sw} />

      {/* CTO → PM */}
      <line x1={500} y1={174} x2={500} y2={224} stroke={stroke} strokeWidth={sw} />

      {/* PM → Backend (left) */}
      <line x1={500} y1={278} x2={500} y2={300} stroke={stroke} strokeWidth={sw} />
      <line x1={500} y1={300} x2={270} y2={300} stroke={stroke} strokeWidth={sw} />
      <line x1={270} y1={300} x2={270} y2={328} stroke={stroke} strokeWidth={sw} />

      {/* PM → Frontend (right) */}
      <line x1={500} y1={300} x2={730} y2={300} stroke={stroke} strokeWidth={sw} />
      <line x1={730} y1={300} x2={730} y2={328} stroke={stroke} strokeWidth={sw} />

      {/* Backend → Security */}
      <line x1={270} y1={408} x2={270} y2={432} stroke={stroke} strokeWidth={sw} />
      <line x1={270} y1={432} x2={500} y2={432} stroke={stroke} strokeWidth={sw} />
      <line x1={500} y1={432} x2={500} y2={458} stroke={stroke} strokeWidth={sw} />

      {/* Frontend → Security */}
      <line x1={730} y1={408} x2={730} y2={432} stroke={stroke} strokeWidth={sw} />
      <line x1={730} y1={432} x2={500} y2={432} stroke={stroke} strokeWidth={sw} />

      {/* Security → Sandbox */}
      <line x1={500} y1={516} x2={500} y2={544} stroke={stroke} strokeWidth={sw} />

      {/* "parallel" label between Backend and Frontend */}
      <text
        x={500}
        y={316}
        textAnchor="middle"
        fill="rgba(148,163,184,0.4)"
        fontSize={22}
        fontFamily="monospace"
      >
        parallel
      </text>
    </svg>
  );
}

// ─── main component ───────────────────────────────────────────────────────────

export function EmptyState() {
  const [ceo, cto, pm, backend, frontend, security, sandbox] = AGENTS as [
    AgentNode, AgentNode, AgentNode, AgentNode, AgentNode, AgentNode, AgentNode
  ];

  return (
    <Card className="animate-fade-in">
      {/* header */}
      <div className="flex flex-col items-center px-2 py-6 text-center">
        <span className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/30 bg-indigo-500/10 text-indigo-300">
          <CompassIcon className="h-6 w-6" />
        </span>
        <h2 className="text-lg font-semibold text-white">Your virtual company is idle</h2>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-slate-400">
          Fill in the brief on the left and the agent swarm will run this pipeline automatically.
        </p>
      </div>

      {/* tree diagram */}
      <div className="relative mx-auto w-full max-w-2xl py-4 select-none" aria-label="Agent pipeline diagram">
        <TreeConnectors />

        {/* Row 1 — CEO */}
        <div className="flex justify-center">
          <AgentCard agent={ceo} />
        </div>

        {/* Row 2 — CTO */}
        <div className="mt-12 flex justify-center">
          <AgentCard agent={cto} />
        </div>

        {/* Row 3 — PM */}
        <div className="mt-12 flex justify-center">
          <AgentCard agent={pm} />
        </div>

        {/* Row 4 — Backend + Frontend (parallel) */}
        <div className="mt-12 flex justify-around px-8">
          <AgentCard agent={backend} />
          <AgentCard agent={frontend} />
        </div>

        {/* Row 5 — Security */}
        <div className="mt-12 flex justify-center">
          <AgentCard agent={security} />
        </div>

        {/* Row 6 — Sandbox */}
        <div className="mt-12 flex justify-center">
          <AgentCard agent={sandbox} />
        </div>
      </div>

      <p className="mt-6 border-t border-slate-800/80 pt-4 text-center text-[11px] text-slate-600">
        Orchestration engine: FastAPI on{' '}
        <span className="font-mono">{API_ORIGIN_LABEL}</span>
      </p>
    </Card>
  );
}

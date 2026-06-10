// Shared presentational primitives for the console.
import {
  AGENTIC_CATEGORIES,
  type AttackCategory,
  type AttackMode,
  type CampaignStatus,
  type Severity,
  type ToolCall,
  type Verdict,
} from "@/lib/api";

export function Panel({
  title,
  right,
  children,
  className = "",
}: {
  title?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`border border-line bg-panel/70 backdrop-blur-[1px] ${className}`}
    >
      {title && (
        <header className="flex items-center justify-between border-b border-line px-3.5 py-2">
          <h2 className="text-[11px] font-600 tracking-[0.18em] text-dim">
            {title}
          </h2>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

const SEV_CLS: Record<Severity, string> = {
  LOW: "border-line text-muted",
  MED: "border-warn/40 text-warn",
  HIGH: "border-fail/45 text-fail",
};

export function SeverityChip({ severity }: { severity: Severity }) {
  return (
    <span
      className={`inline-flex items-center border px-1.5 py-px text-[10px] font-600 tracking-[0.12em] ${SEV_CLS[severity]}`}
    >
      {severity}
    </span>
  );
}

export function VerdictGlyph({ verdict }: { verdict: Verdict }) {
  const fail = verdict === "FAIL";
  return (
    <span
      className={`inline-flex items-center gap-1 text-[11px] font-700 tracking-[0.1em] ${
        fail ? "text-fail" : "text-pass"
      }`}
    >
      <span aria-hidden>{fail ? "✗" : "✓"}</span>
      {fail ? "BREACH" : "HELD"}
    </span>
  );
}

export function CategoryTag({ category }: { category: string }) {
  return (
    <span className="inline-flex items-center border border-line bg-base2 px-1.5 py-px text-[10px] tracking-[0.1em] text-dim">
      {category}
    </span>
  );
}

const STATUS_META: Record<
  CampaignStatus | "idle",
  { label: string; cls: string; led: string }
> = {
  idle: { label: "IDLE", cls: "text-muted border-line", led: "bg-muted" },
  created: { label: "CREATED", cls: "text-dim border-line", led: "bg-dim" },
  running: {
    label: "RUNNING",
    cls: "text-warn border-warn/40",
    led: "bg-warn led-live",
  },
  awaiting_approval: {
    label: "AWAITING APPROVAL",
    cls: "text-warn border-warn/40",
    led: "bg-warn led-live",
  },
  done: { label: "DONE", cls: "text-pass border-pass/40", led: "bg-pass" },
};

export function StatusPill({ status }: { status: CampaignStatus | "idle" }) {
  const m = STATUS_META[status];
  return (
    <span
      className={`inline-flex items-center gap-2 border px-2.5 py-1 text-[11px] font-600 tracking-[0.14em] ${m.cls}`}
    >
      <span className={`size-2 ${m.led}`} aria-hidden />
      {m.label}
    </span>
  );
}

export function StatusLed({ status }: { status: CampaignStatus | "idle" }) {
  return <span className={`size-2.5 ${STATUS_META[status].led}`} aria-hidden />;
}

export function pct(n: number): string {
  return `${Math.round(n * 100)}%`;
}

// Attack delivery mode — crescendo is the multi-turn differentiator.
export function ModeBadge({
  mode,
  category,
}: {
  mode: AttackMode;
  category: AttackCategory;
}) {
  const agentic = AGENTIC_CATEGORIES.has(category);
  const label = agentic ? "AGENTIC" : mode === "crescendo" ? "CRESCENDO" : "SINGLE";
  const cls = agentic
    ? "border-fail/40 text-fail"
    : mode === "crescendo"
      ? "border-warn/40 text-warn"
      : "border-line text-muted";
  return (
    <span
      className={`inline-flex items-center border px-1.5 py-px text-[10px] tracking-[0.1em] ${cls}`}
    >
      {label}
    </span>
  );
}

// OWASP mapping — id (e.g. LLM07) + framework lane (LLM / AGENTIC / CUSTOM).
export function OwaspTag({
  id,
  framework,
}: {
  id: string | null;
  framework: string;
}) {
  if (!id) {
    return (
      <span className="text-[10px] tracking-[0.1em] text-muted/70">UNMAPPED</span>
    );
  }
  const agentic = framework === "AGENTIC";
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] tracking-[0.1em] ${
        agentic ? "text-fail/80" : "text-dim"
      }`}
    >
      <span className="text-muted">{framework}</span>
      <span className="font-600">{id}</span>
    </span>
  );
}

// Agentic evidence — the strongest visual: machine-readable proof a tool fired.
export function formatToolCall(tc: ToolCall): string {
  const args = Object.entries(tc.args || {})
    .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
    .join(", ");
  return `${tc.name}{ ${args} }`;
}

export function ToolEvidence({ calls }: { calls: ToolCall[] }) {
  if (!calls?.length) return null;
  return (
    <div className="flex flex-col gap-1.5 border-l-2 border-l-fail bg-faildim/40 px-3 py-2">
      <span className="text-[10px] tracking-[0.16em] text-fail/80">
        ⚠ TOOL CALLS EXECUTED — AGENTIC BREACH EVIDENCE
      </span>
      {calls.map((tc, i) => (
        <code
          key={i}
          className="break-words text-[12px] font-600 leading-relaxed text-fail"
        >
          {formatToolCall(tc)}
        </code>
      ))}
    </div>
  );
}

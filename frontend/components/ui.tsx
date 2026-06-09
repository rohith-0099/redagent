// Shared presentational primitives for the console.
import type { CampaignStatus, Severity, Verdict } from "@/lib/api";

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
    cls: "text-accent border-accent/40",
    led: "bg-accent led-live",
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

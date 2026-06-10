import {
  CATEGORY_ORDER,
  type VerificationReport,
} from "@/lib/api";
import { pct } from "./ui";

const VERDICT_META: Record<string, { label: string; cls: string }> = {
  fix_effective: { label: "FIX EFFECTIVE", cls: "border-pass/45 text-pass" },
  partial: { label: "PARTIAL", cls: "border-warn/45 text-warn" },
  ineffective: { label: "INEFFECTIVE", cls: "border-fail/45 text-fail" },
};

export function VerifierPanel({ v }: { v: VerificationReport }) {
  const meta = VERDICT_META[v.verdict] ?? {
    label: v.verdict.toUpperCase(),
    cls: "border-line text-dim",
  };
  const cats = CATEGORY_ORDER.filter((c) => v.per_category[c]).map(
    (c) => [c, v.per_category[c]!] as const,
  );

  return (
    <section className="reveal mt-4 border border-line bg-panel/70">
      <header className="flex items-center justify-between border-b border-line px-3.5 py-2.5">
        <h2 className="text-[11px] font-600 tracking-[0.18em] text-dim">
          VERIFIER · RE-TEST PROOF
        </h2>
        <span
          className={`inline-flex items-center border px-2 py-0.5 text-[10px] font-700 tracking-[0.16em] ${meta.cls}`}
        >
          {meta.label}
        </span>
      </header>

      <div className="flex flex-wrap items-center gap-x-8 gap-y-2 border-b border-line px-3.5 py-3 text-[12px]">
        <Stat label="ORIGINAL BREACHES" value={v.original_breaches} tone="fail" />
        <span className="text-muted" aria-hidden>
          →
        </span>
        <Stat
          label="AFTER FIX"
          value={v.breaches_after_fix}
          tone={v.breaches_after_fix === 0 ? "pass" : "fail"}
        />
        <Stat label="FIXED" value={v.fixed} tone="pass" />
      </div>

      <div className="p-3.5">
        <span className="text-[10px] tracking-[0.16em] text-muted">
          PER-CATEGORY · BREACH RATE BEFORE → AFTER
        </span>
        <ul className="mt-2.5 flex flex-col gap-2.5">
          {cats.map(([cat, ba]) => {
            const held = ba.after === 0;
            return (
              <li key={cat} className="flex items-center gap-3 text-[12px]">
                <span className="w-36 shrink-0 text-fg">{cat}</span>
                <span className="font-600 tabular-nums text-fail">
                  {pct(ba.before)}
                </span>
                <span className="text-muted" aria-hidden>
                  →
                </span>
                <span
                  className={
                    "font-600 tabular-nums " + (held ? "text-pass" : "text-fail")
                  }
                >
                  {pct(ba.after)}
                </span>
                <span
                  className={
                    "ml-auto text-[11px] tracking-[0.12em] " +
                    (held ? "text-pass" : "text-fail")
                  }
                >
                  {held ? "✓ HELD" : "✗ STILL BREACHING"}
                </span>
              </li>
            );
          })}
        </ul>

        {v.still_breaching.length > 0 && (
          <div className="mt-3 border-l-2 border-l-fail bg-faildim/30 px-3 py-2">
            <span className="text-[10px] tracking-[0.16em] text-fail/80">
              {v.still_breaching.length} ATTACK
              {v.still_breaching.length === 1 ? "" : "S"} STILL BREACHING
            </span>
            <ul className="mt-1.5 flex flex-col gap-1">
              {v.still_breaching.map((r, i) => (
                <li
                  key={i}
                  className="truncate text-[11.5px] text-fail/90"
                  title={r.prompt}
                >
                  {r.category} · {r.prompt}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: "pass" | "fail";
}) {
  return (
    <span className="flex items-baseline gap-2">
      <span
        className={
          "text-[22px] font-700 tabular-nums " +
          (tone === "pass" ? "text-pass" : "text-fail")
        }
      >
        {value}
      </span>
      <span className="text-[10px] tracking-[0.14em] text-muted">{label}</span>
    </span>
  );
}

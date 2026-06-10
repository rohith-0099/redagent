import {
  CATEGORY_ORDER,
  type FixProposal,
  type VulnReport,
} from "@/lib/api";
import { pct } from "./ui";

export function FixPanel({
  report,
  fix,
  onVerify,
  verifying,
  verified,
  exportHref,
}: {
  report: VulnReport | null;
  fix: FixProposal;
  onVerify: () => void;
  verifying: boolean;
  verified: boolean;
  exportHref: string;
}) {
  const breached = report
    ? CATEGORY_ORDER.filter(
        (c) => (report.per_category[c]?.success_rate ?? 0) > 0,
      ).map((c) => [c, report.per_category[c]!] as const)
    : [];

  return (
    <section className="reveal mt-4 border border-line bg-panel/70">
      <header className="flex items-center justify-between border-b border-line px-3.5 py-2.5">
        <h2 className="text-[11px] font-600 tracking-[0.18em] text-dim">
          DEFENSE APPLIED
        </h2>
        <span className="inline-flex items-center gap-1.5 border border-pass/45 px-2 py-0.5 text-[10px] font-700 tracking-[0.16em] text-pass">
          <span aria-hidden>✓</span> HARDENED
        </span>
      </header>

      <div className="grid gap-px bg-line md:grid-cols-2">
        {/* BEFORE — breaches */}
        <div className="bg-panel p-4">
          <h3 className="mb-3 text-[10px] tracking-[0.18em] text-fail">
            ◂ BEFORE — BREACHES FOUND
          </h3>
          {breached.length === 0 ? (
            <p className="text-[12px] text-muted">No breaches recorded.</p>
          ) : (
            <ul className="flex flex-col gap-2">
              {breached.map(([cat, rep]) => (
                <li
                  key={cat}
                  className="flex items-center justify-between border border-fail/20 bg-faildim/40 px-2.5 py-1.5 text-[12px]"
                >
                  <span className="text-fg">{cat}</span>
                  <span className="font-600 tabular-nums text-fail">
                    {pct(rep.success_rate)} breached
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="mt-3 text-[10.5px] leading-relaxed text-muted">
            Naive system prompt, no input guards — attacks landed.
          </p>
        </div>

        {/* AFTER — hardened */}
        <div className="bg-panel p-4">
          <h3 className="mb-3 text-[10px] tracking-[0.18em] text-pass">
            AFTER — HARDENED DEFENSE ▸
          </h3>

          <span className="text-[10px] tracking-[0.16em] text-muted">
            NEW_SYSTEM_PROMPT
          </span>
          <pre className="mt-1.5 max-h-52 overflow-auto whitespace-pre-wrap break-words border border-pass/20 bg-base2 p-2.5 text-[11.5px] leading-relaxed text-fg/90">
            {fix.new_system_prompt}
          </pre>

          <span className="mt-3 block text-[10px] tracking-[0.16em] text-muted">
            GUARDS · {fix.guards.length}
          </span>
          <ul className="mt-1.5 flex flex-col gap-1.5">
            {fix.guards.map((g, i) => (
              <li key={i} className="flex gap-2 text-[12px] leading-relaxed">
                <span className="mt-px shrink-0 text-pass" aria-hidden>
                  ✓
                </span>
                <span className="text-dim">{g}</span>
              </li>
            ))}
          </ul>

          {fix.rationale && (
            <p className="mt-3 border-l-2 border-pass/30 pl-2.5 text-[11px] leading-relaxed text-muted">
              {fix.rationale}
            </p>
          )}
        </div>
      </div>

      {/* Action bar: prove the fix (Verifier) + export a CI regression suite. */}
      <div className="flex flex-wrap items-center gap-3 border-t border-line px-3.5 py-3">
        <button
          onClick={onVerify}
          disabled={verifying}
          className={
            "border px-3 py-2 text-[11px] font-600 tracking-[0.14em] transition-colors " +
            (verifying
              ? "cursor-not-allowed border-line text-muted"
              : verified
                ? "border-pass/45 text-pass hover:bg-pass/10"
                : "border-accent/50 text-accent hover:bg-accent/10 active:bg-accent/15")
          }
        >
          {verifying ? (
            <span className="caret">RE-TESTING BREACHES</span>
          ) : verified ? (
            "↻ RE-VERIFY FIX"
          ) : (
            "▶ VERIFY FIX — RE-TEST BREACHES"
          )}
        </button>

        <a
          href={exportHref}
          className="border border-line px-3 py-2 text-[11px] font-600 tracking-[0.14em] text-dim transition-colors hover:border-accent/50 hover:text-accent"
        >
          ⤓ DOWNLOAD REGRESSION SUITE
        </a>
        <span className="text-[10.5px] leading-relaxed text-muted">
          pytest suite — breaches become CI tests that must never pass again.
        </span>
      </div>
    </section>
  );
}

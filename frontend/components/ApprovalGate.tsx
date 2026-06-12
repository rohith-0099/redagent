import { ShieldCheck } from "./icons";

export function ApprovalGate({
  onApprove,
  approving,
}: {
  onApprove: () => void;
  approving: boolean;
}) {
  return (
    <section className="reveal border border-warn/35 bg-warndim/50">
      <div className="flex items-center gap-2 border-b border-warn/25 px-3.5 py-2">
        <span className="icon-chip size-5 border-warn/30 bg-warndim text-[12px] text-warn">
          <ShieldCheck />
        </span>
        <h2 className="text-[11px] font-600 tracking-[0.18em] text-warn">
          HUMAN APPROVAL REQUIRED
        </h2>
      </div>
      <div className="flex flex-col gap-3 p-3.5">
        <p className="text-[12px] leading-relaxed text-dim">
          The pipeline paused before applying any change. The Defender will
          harden the target&apos;s system prompt against the breaches found
          above. Nothing is applied until you approve.
        </p>
        <button
          onClick={onApprove}
          disabled={approving}
          className={
            "inline-flex items-center gap-2 border px-3 py-2.5 text-[12px] font-600 tracking-[0.16em] transition-colors " +
            (approving
              ? "cursor-not-allowed border-line text-muted"
              : "border-warn/50 text-warn hover:bg-warn/10 active:bg-warn/15")
          }
        >
          {approving ? (
            <span className="caret">DEFENDER WORKING</span>
          ) : (
            <>
              <ShieldCheck className="text-[14px]" />
              APPROVE &amp; APPLY FIX
            </>
          )}
        </button>
      </div>
    </section>
  );
}

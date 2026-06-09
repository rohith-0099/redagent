import type { CampaignStatus } from "@/lib/api";
import { Panel } from "./ui";

export function CampaignConfig({
  targetUrl,
  setTargetUrl,
  description,
  setDescription,
  onLaunch,
  launching,
  status,
}: {
  targetUrl: string;
  setTargetUrl: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  onLaunch: () => void;
  launching: boolean;
  status: CampaignStatus | "idle";
}) {
  const active = status === "running";
  const disabled = launching || active;

  const inputCls =
    "w-full border border-line bg-base2 px-3 py-2 text-[13px] text-fg placeholder:text-muted/70 " +
    "transition-colors focus:border-accent focus:outline-none";

  return (
    <Panel title="◢ CONFIG">
      <form
        className="flex flex-col gap-4 p-3.5"
        onSubmit={(e) => {
          e.preventDefault();
          if (!disabled) onLaunch();
        }}
      >
        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="target-url"
            className="text-[10px] tracking-[0.16em] text-muted"
          >
            TARGET_URL
          </label>
          <input
            id="target-url"
            className={inputCls}
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="http://localhost:8001"
            spellCheck={false}
            autoComplete="off"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label
            htmlFor="target-desc"
            className="text-[10px] tracking-[0.16em] text-muted"
          >
            TARGET_DESCRIPTION
          </label>
          <input
            id="target-desc"
            className={inputCls}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="TechCo customer-support bot"
            spellCheck={false}
            autoComplete="off"
          />
          <p className="text-[10.5px] leading-relaxed text-muted">
            Briefs the Strategist on what the target is, so it can pick attack
            categories.
          </p>
        </div>

        <button
          type="submit"
          disabled={disabled}
          className={
            "group relative mt-0.5 border px-3 py-2.5 text-[12px] font-600 tracking-[0.16em] transition-colors " +
            (disabled
              ? "cursor-not-allowed border-line text-muted"
              : "border-accent/50 text-accent hover:bg-accent/10 active:bg-accent/15")
          }
        >
          {launching ? (
            <span className="caret">DEPLOYING AGENTS</span>
          ) : active ? (
            "CAMPAIGN ACTIVE"
          ) : (
            "▶ LAUNCH CAMPAIGN"
          )}
        </button>
      </form>
    </Panel>
  );
}

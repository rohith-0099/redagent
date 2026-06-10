import type { CampaignStatus } from "@/lib/api";
import { StatusPill } from "./ui";

export function StatusBar({
  status,
  campaignId,
  target,
  breaches,
  probes,
  memory,
}: {
  status: CampaignStatus | "idle";
  campaignId: string | null;
  target: string;
  breaches: number;
  probes: number;
  memory: number;
}) {
  return (
    <header className="sticky top-0 z-20 border-b border-line bg-base/85 backdrop-blur-md">
      <div className="mx-auto flex h-13 w-full max-w-[1500px] items-center gap-3 px-4 lg:px-6">
        {/* brand */}
        <div className="flex items-center gap-2.5">
          <span className="size-2.5 bg-fail" aria-hidden />
          <span className="text-[15px] font-700 tracking-[0.22em] text-fg">
            RED<span className="text-fail">·</span>AGENT
          </span>
        </div>

        <span className="hidden text-line sm:inline" aria-hidden>
          │
        </span>

        {/* target + campaign id */}
        <div className="hidden min-w-0 flex-1 items-center gap-4 text-[12px] sm:flex">
          <span className="truncate text-muted">
            <span className="text-dim">target</span>{" "}
            <span className="text-fg">{target || "—"}</span>
          </span>
          {campaignId && (
            <span className="truncate text-muted">
              <span className="text-dim">id</span>{" "}
              <span className="text-fg">{campaignId.slice(0, 8)}</span>
            </span>
          )}
        </div>

        <div className="flex flex-1 items-center justify-end gap-3 sm:flex-none">
          {/* live counters */}
          <div className="flex items-center gap-3 text-[11px] tracking-[0.12em]">
            <span className="text-muted">
              PROBES <span className="text-fg tabular-nums">{probes}</span>
            </span>
            <span
              className={breaches > 0 ? "text-fail" : "text-muted"}
              aria-live="polite"
            >
              BREACH{" "}
              <span className="tabular-nums">
                {String(breaches).padStart(2, "0")}
              </span>
            </span>
            {memory > 0 && (
              <span className="hidden text-accent sm:inline">
                MEM <span className="tabular-nums">{memory}</span>
              </span>
            )}
          </div>
          <StatusPill status={status} />
        </div>
      </div>
    </header>
  );
}

import {
  CATEGORY_ORDER,
  type CampaignStatus,
  type VulnReport as VulnReportT,
} from "@/lib/api";
import { OwaspTag, Panel, SeverityChip, pct } from "./ui";
import { Check, FileBug } from "./icons";

export function VulnReport({
  report,
  status,
}: {
  report: VulnReportT | null;
  status: CampaignStatus | "idle";
}) {
  const entries = report
    ? CATEGORY_ORDER.filter((c) => report.per_category[c]).map(
        (c) => [c, report.per_category[c]!] as const,
      )
    : [];
  const breached = entries.filter(([, r]) => r.success_rate > 0).length;

  return (
    <Panel
      title="VULN REPORT"
      icon={<FileBug />}
      right={
        report ? (
          <span className="text-[11px] tracking-[0.12em] text-muted">
            <span className={breached > 0 ? "text-fail" : "text-pass"}>
              {breached}
            </span>
            /{entries.length} BREACHED
          </span>
        ) : null
      }
    >
      <div className="p-3.5">
        {!report ? (
          <p
            className={
              "text-[12px] " +
              (status === "running" ? "text-warn caret" : "text-muted")
            }
          >
            {status === "running"
              ? "analysing traces"
              : "// awaiting campaign results"}
          </p>
        ) : entries.length === 0 ? (
          <p className="flex items-center gap-1.5 text-[12px] text-pass">
            <Check className="text-[13px]" />
            no categories breached
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {entries.map(([cat, rep]) => {
              const breach = rep.success_rate > 0;
              return (
                <li key={cat} className="flex flex-col gap-1.5">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-[12px] text-fg">{cat}</span>
                    <div className="flex items-center gap-2">
                      <SeverityChip severity={rep.severity} />
                      <span
                        className={
                          "w-9 text-right text-[12px] font-600 tabular-nums " +
                          (breach ? "text-fail" : "text-pass")
                        }
                      >
                        {pct(rep.success_rate)}
                      </span>
                    </div>
                  </div>
                  {/* breach-rate track */}
                  <div className="h-1.5 w-full overflow-hidden rounded-[2px] bg-base2">
                    <div
                      className={
                        breach
                          ? "h-full bg-fail led-fail transition-[width] duration-500"
                          : "h-full bg-pass transition-[width] duration-500"
                      }
                      style={{
                        width: `${Math.max(rep.success_rate * 100, breach ? 4 : 2)}%`,
                      }}
                    />
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <OwaspTag id={rep.owasp_id} framework={rep.framework} />
                    <span className="truncate text-[10.5px] text-muted">
                      {rep.owasp_title !== "Unmapped" ? rep.owasp_title : ""}
                    </span>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </Panel>
  );
}

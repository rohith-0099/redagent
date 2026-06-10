import type { CampaignStatus, ReconReport } from "@/lib/api";
import { Panel } from "./ui";

export function ReconPanel({
  recon,
  status,
}: {
  recon: ReconReport | null;
  status: CampaignStatus | "idle";
}) {
  return (
    <Panel
      title="RECON"
      right={
        recon ? (
          <span className="text-[10px] tracking-[0.12em] text-accent">
            SELF-DISCOVERED
          </span>
        ) : null
      }
    >
      <div className="p-3.5">
        {!recon ? (
          <p
            className={
              "text-[12px] " +
              (status === "running" ? "text-warn caret" : "text-muted")
            }
          >
            {status === "running"
              ? "probing target surface"
              : "// recon runs first, before any attack"}
          </p>
        ) : (
          <div className="flex flex-col gap-3 text-[12px]">
            {recon.target_purpose && (
              <Line label="PURPOSE">{recon.target_purpose}</Line>
            )}
            <div className="flex flex-col gap-1.5">
              <span className="text-[10px] tracking-[0.16em] text-muted">
                TOOLS DISCOVERED
              </span>
              {recon.discovered_tools.length ? (
                <div className="flex flex-wrap gap-1.5">
                  {recon.discovered_tools.map((t) => (
                    <span
                      key={t}
                      className="border border-fail/30 bg-faildim/30 px-1.5 py-px text-[11px] text-fail/90"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-[11px] text-muted">none exposed</span>
              )}
            </div>
            {recon.refusal_style && (
              <Line label="REFUSAL STYLE">{recon.refusal_style}</Line>
            )}
            {recon.exploitable_surface?.length > 0 && (
              <div className="flex flex-col gap-1.5">
                <span className="text-[10px] tracking-[0.16em] text-muted">
                  EXPLOITABLE SURFACE
                </span>
                <ul className="flex flex-col gap-1">
                  {recon.exploitable_surface.map((s, i) => (
                    <li key={i} className="text-[11.5px] leading-relaxed text-dim">
                      <span className="text-muted">›</span> {s}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {recon.discovered_context &&
              Object.keys(recon.discovered_context).length > 0 && (
                <div className="flex flex-col gap-1.5">
                  <span className="text-[10px] tracking-[0.16em] text-muted">
                    REVEALED IDENTIFIERS
                  </span>
                  <code className="block whitespace-pre-wrap break-words border-l border-line pl-2 text-[11px] leading-relaxed text-dim">
                    {JSON.stringify(recon.discovered_context, null, 2)}
                  </code>
                </div>
              )}
          </div>
        )}
      </div>
    </Panel>
  );
}

function Line({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] tracking-[0.16em] text-muted">{label}</span>
      <p className="leading-relaxed text-fg/90">{children}</p>
    </div>
  );
}

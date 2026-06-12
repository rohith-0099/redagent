"use client";

import { useState } from "react";
import { type CampaignStatus, testConnection } from "@/lib/api";
import { Panel } from "./ui";
import { Check, Play, Sliders, X, Zap } from "./icons";

type TestState =
  | { kind: "idle" }
  | { kind: "testing" }
  | { kind: "ok"; reply: string }
  | { kind: "err"; msg: string };

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
  const [test, setTest] = useState<TestState>({ kind: "idle" });

  const inputCls =
    "w-full border border-line bg-base2 px-3 py-2 text-[13px] text-fg placeholder:text-muted/70 " +
    "transition-colors focus:border-accent focus:outline-none";

  async function runTest() {
    setTest({ kind: "testing" });
    try {
      const r = await testConnection(targetUrl);
      if (r.ok) setTest({ kind: "ok", reply: r.sample_reply || "(empty reply)" });
      else setTest({ kind: "err", msg: r.error || "target did not answer" });
    } catch (e) {
      setTest({
        kind: "err",
        msg: e instanceof Error ? e.message : "request failed",
      });
    }
  }

  return (
    <Panel title="CONFIG" icon={<Sliders />}>
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
            onChange={(e) => {
              setTargetUrl(e.target.value);
              setTest({ kind: "idle" });
            }}
            placeholder="http://localhost:8000"
            spellCheck={false}
            autoComplete="off"
          />
          <div className="flex items-center gap-2">
            <span className="border border-line bg-base2 px-1.5 py-px text-[10px] tracking-[0.1em] text-muted">
              ADAPTER simple_json
            </span>
            <button
              type="button"
              onClick={runTest}
              disabled={test.kind === "testing"}
              className="inline-flex items-center gap-1.5 text-[10.5px] tracking-[0.12em] text-accent transition-colors hover:text-fg disabled:text-muted"
            >
              {test.kind === "testing" ? (
                <span className="caret">TESTING</span>
              ) : (
                <>
                  <Play className="text-[11px]" />
                  TEST CONNECTION
                </>
              )}
            </button>
          </div>
          {test.kind === "ok" && (
            <p className="flex items-start gap-1.5 border-l-2 border-l-pass bg-passdim/40 px-2 py-1 text-[11px] leading-relaxed text-pass/90">
              <Check className="mt-0.5 shrink-0 text-[12px]" />
              reachable — &ldquo;{truncate(test.reply, 90)}&rdquo;
            </p>
          )}
          {test.kind === "err" && (
            <p className="flex items-start gap-1.5 border-l-2 border-l-fail bg-faildim/40 px-2 py-1 text-[11px] leading-relaxed text-fail/90">
              <X className="mt-0.5 shrink-0 text-[12px]" />
              {test.msg}. Check the URL and that the target is running.
            </p>
          )}
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
            "group relative mt-0.5 inline-flex items-center justify-center gap-2 border px-3 py-2.5 text-[12px] font-600 tracking-[0.16em] transition-colors " +
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
            <>
              <Zap className="text-[14px]" />
              LAUNCH CAMPAIGN
            </>
          )}
        </button>
      </form>
    </Panel>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

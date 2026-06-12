"use client";

import { useEffect, useRef, useState } from "react";
import {
  AGENTIC_CATEGORIES,
  type AttackResult,
  type CampaignStatus,
  type TranscriptTurn,
} from "@/lib/api";
import {
  CategoryTag,
  formatToolCall,
  ModeBadge,
  Panel,
  SeverityChip,
  ToolEvidence,
  VerdictGlyph,
} from "./ui";
import { ChevronDown, CornerDownRight, Crosshair, Terminal } from "./icons";

export interface StreamRow {
  result: AttackResult;
  t: string; // arrival timestamp HH:MM:SS
  owasp?: string | null; // resolved from the vuln report when ready
}

export function AttackStream({
  rows,
  status,
}: {
  rows: StreamRow[];
  status: CampaignStatus | "idle";
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState<Set<number>>(new Set());

  const running = status === "running";
  const breaches = rows.filter((r) => r.result.verdict === "FAIL").length;

  // Auto-scroll to the newest line as attacks arrive.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [rows.length]);

  function toggle(i: number) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  }

  return (
    <Panel
      title="ATTACK STREAM"
      icon={<Crosshair />}
      className="flex h-[60vh] flex-col lg:sticky lg:top-[68px] lg:h-[calc(100dvh-96px)]"
      right={
        <div className="flex items-center gap-3 text-[11px] tracking-[0.12em]">
          <span className="text-muted">
            PROBES <span className="text-fg tabular-nums">{rows.length}</span>
          </span>
          <span className={breaches > 0 ? "text-fail" : "text-muted"}>
            BREACH{" "}
            <span className="tabular-nums">
              {String(breaches).padStart(2, "0")}
            </span>
          </span>
          {running && <span className="caret text-warn" aria-hidden />}
        </div>
      }
    >
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 overflow-y-auto scroll-smooth"
        role="log"
        aria-label="Live attack stream"
        aria-live="polite"
      >
        {rows.length === 0 ? (
          <EmptyState status={status} />
        ) : (
          <ul>
            {rows.map((row, i) => (
              <Row
                key={i}
                index={i}
                row={row}
                open={open.has(i)}
                onToggle={() => toggle(i)}
              />
            ))}
            {running && (
              <li className="px-3.5 py-2 text-[12px] text-muted caret" aria-hidden>
                <span className="text-dim">probing</span>
              </li>
            )}
          </ul>
        )}
      </div>
    </Panel>
  );
}

function Row({
  index,
  row,
  open,
  onToggle,
}: {
  index: number;
  row: StreamRow;
  open: boolean;
  onToggle: () => void;
}) {
  const { result, t, owasp } = row;
  const fail = result.verdict === "FAIL";
  const agentic = AGENTIC_CATEGORIES.has(result.category);
  const hasEvidence = fail && agentic && result.tool_calls?.length > 0;

  return (
    <li className={"border-b border-line/60 " + (fail ? "bg-faildim/30" : "")}>
      <button
        onClick={onToggle}
        aria-expanded={open}
        className={
          "flex w-full items-center gap-2.5 px-3.5 py-1.5 text-left text-[12px] transition-colors hover:bg-panel2 " +
          (fail
            ? "border-l-2 border-l-fail row-flash"
            : "border-l-2 border-l-transparent")
        }
      >
        <span className="w-7 shrink-0 text-right text-[11px] tabular-nums text-muted/70">
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className="hidden shrink-0 text-[11px] tabular-nums text-muted sm:block">
          {t}
        </span>
        <span className="shrink-0">
          <CategoryTag category={result.category} />
        </span>
        <span className="hidden shrink-0 md:block">
          <ModeBadge mode={result.attack_mode} category={result.category} />
        </span>
        <span className="min-w-0 flex-1 truncate text-dim">{result.prompt}</span>
        {owasp && (
          <span className="hidden shrink-0 text-[10px] tracking-[0.1em] text-muted lg:block">
            {owasp}
          </span>
        )}
        <span className="shrink-0">
          <VerdictGlyph verdict={result.verdict} />
        </span>
        <ChevronDown
          className={"shrink-0 text-[14px] text-muted chev" + (open ? " open" : "")}
        />
      </button>

      {/* Agentic breach: surface the money-shot evidence even when collapsed. */}
      {hasEvidence && !open && (
        <div className="flex items-start gap-1.5 px-3.5 pb-2 pl-12">
          <CornerDownRight className="mt-0.5 shrink-0 text-[12px]" />
          <code className="break-words text-[11.5px] font-600 text-fail">
            {formatToolCall(result.tool_calls[0])}
            {result.tool_calls.length > 1
              ? `  +${result.tool_calls.length - 1} more`
              : ""}
          </code>
        </div>
      )}

      <div className={"expander" + (open ? " open" : "")}>
        <div className="expander-clip">
          <div className="expander-body space-y-3 border-t border-line/60 bg-base2/60 px-3.5 py-3 pl-12 text-[12px]">
            {result.attack_mode === "crescendo" && result.transcript?.length ? (
              <Crescendo
                transcript={result.transcript}
                breachTurn={result.breach_turn}
              />
            ) : (
              <>
                <Field label="PROMPT">{result.prompt}</Field>
                <Field label="RESPONSE" tone={fail ? "fail" : "default"}>
                  {result.response}
                </Field>
              </>
            )}
            {result.tool_calls?.length > 0 && (
              <ToolEvidence calls={result.tool_calls} />
            )}
            <Field label="JUDGE">{result.reason}</Field>
          </div>
        </div>
      </div>
    </li>
  );
}

function Crescendo({
  transcript,
  breachTurn,
}: {
  transcript: TranscriptTurn[];
  breachTurn: number | null;
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] tracking-[0.16em] text-muted">
        MULTI-TURN TRANSCRIPT · {transcript.length} turns
        {breachTurn ? ` · breach at turn ${breachTurn}` : ""}
      </span>
      <ol className="flex flex-col gap-2.5 border-l border-line pl-3">
        {transcript.map((turn) => {
          const isBreach = turn.turn_index === breachTurn;
          return (
            <li key={turn.turn_index} className="relative flex flex-col gap-1.5">
              <span
                className={
                  "absolute -left-[15px] top-1 size-1.5 " +
                  (isBreach ? "bg-fail" : "bg-line")
                }
                aria-hidden
              />
              <span
                className={
                  "text-[10px] tracking-[0.14em] " +
                  (isBreach ? "text-fail" : "text-muted")
                }
              >
                TURN {turn.turn_index}
                {isBreach ? " · BREACH" : ""}
              </span>
              <p className="whitespace-pre-wrap break-words leading-relaxed text-dim">
                <span className="text-muted">→ </span>
                {turn.attacker_msg}
              </p>
              <p
                className={
                  "whitespace-pre-wrap break-words leading-relaxed " +
                  (isBreach ? "text-fail/90" : "text-fg/80")
                }
              >
                <span className="text-muted">← </span>
                {turn.target_response}
              </p>
              {turn.tool_calls && turn.tool_calls.length > 0 && (
                <code className="flex items-center gap-1.5 break-words text-[11.5px] font-600 text-fail">
                  <Terminal className="shrink-0 text-[13px]" />
                  {turn.tool_calls.map(formatToolCall).join("  ")}
                </code>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

function Field({
  label,
  children,
  tone = "default",
}: {
  label: string;
  children: React.ReactNode;
  tone?: "default" | "fail";
}) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[10px] tracking-[0.16em] text-muted">{label}</span>
      <p
        className={
          "whitespace-pre-wrap break-words leading-relaxed " +
          (tone === "fail" ? "text-fail/90" : "text-fg/90")
        }
      >
        {children}
      </p>
    </div>
  );
}

function EmptyState({ status }: { status: CampaignStatus | "idle" }) {
  const running = status === "running";
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center">
      <Crosshair
        className={"text-[34px] " + (running ? "text-warn/70 led-live" : "text-line")}
      />
      <p className={"text-[13px] " + (running ? "text-warn caret" : "text-muted")}>
        {running ? "awaiting first probe" : "// no active campaign"}
      </p>
      {!running && (
        <p className="max-w-xs text-[11.5px] leading-relaxed text-muted/80">
          Configure a target and launch a campaign. Every attack the agents fire —
          single-shot, crescendo, and agentic — logs here in real time.
        </p>
      )}
    </div>
  );
}

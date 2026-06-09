"use client";

import { useEffect, useRef, useState } from "react";
import type { AttackResult, CampaignStatus } from "@/lib/api";
import { CategoryTag, Panel, SeverityChip, VerdictGlyph } from "./ui";

export interface StreamRow {
  result: AttackResult;
  t: string; // arrival timestamp HH:MM:SS
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
      next.has(i) ? next.delete(i) : next.add(i);
      return next;
    });
  }

  return (
    <Panel
      title="ATTACK STREAM"
      className="flex h-[58vh] flex-col lg:sticky lg:top-[68px] lg:h-[calc(100dvh-92px)]"
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
              <li
                className="px-3.5 py-2 text-[12px] text-muted caret"
                aria-hidden
              >
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
  const { result, t } = row;
  const fail = result.verdict === "FAIL";

  return (
    <li
      className={
        "border-b border-line/60 " +
        (fail ? "bg-faildim/40 row-flash" : "")
      }
    >
      <button
        onClick={onToggle}
        aria-expanded={open}
        className={
          "flex w-full items-center gap-2.5 px-3.5 py-1.5 text-left text-[12px] transition-colors hover:bg-panel2 " +
          (fail ? "border-l-2 border-l-fail" : "border-l-2 border-l-transparent")
        }
      >
        <span className="w-7 shrink-0 text-right text-[11px] tabular-nums text-muted/70">
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className="shrink-0 text-[11px] tabular-nums text-muted">{t}</span>
        <span className="shrink-0">
          <CategoryTag category={result.category} />
        </span>
        <span className="hidden shrink-0 sm:block">
          <SeverityChip severity={result.severity} />
        </span>
        <span className="min-w-0 flex-1 truncate text-dim">
          {result.prompt}
        </span>
        <span className="shrink-0">
          <VerdictGlyph verdict={result.verdict} />
        </span>
        <span
          className="w-3 shrink-0 text-center text-muted"
          aria-hidden
        >
          {open ? "−" : "+"}
        </span>
      </button>

      {open && (
        <div className="space-y-3 border-t border-line/60 bg-base2/60 px-3.5 py-3 pl-12 text-[12px]">
          <Field label="PROMPT">{result.prompt}</Field>
          <Field label="RESPONSE" tone={fail ? "fail" : "default"}>
            {result.response}
          </Field>
          <Field label="JUDGE">{result.reason}</Field>
        </div>
      )}
    </li>
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
    <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
      <p
        className={
          "text-[13px] " + (running ? "text-warn caret" : "text-muted")
        }
      >
        {running ? "awaiting first probe" : "// no active campaign"}
      </p>
      {!running && (
        <p className="max-w-xs text-[11.5px] leading-relaxed text-muted/80">
          Configure a target and launch a campaign. Each attack the agents fire
          will log here in real time.
        </p>
      )}
    </div>
  );
}

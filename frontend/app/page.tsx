"use client";

import { useEffect, useRef, useState } from "react";
import {
  API_BASE,
  approveCampaign,
  type CampaignStatus,
  type FixProposal,
  getCampaign,
  launchCampaign,
  type StreamEvent,
  streamUrl,
  type VulnReport as VulnReportT,
} from "@/lib/api";
import { ApprovalGate } from "@/components/ApprovalGate";
import { AttackStream, type StreamRow } from "@/components/AttackStream";
import { CampaignConfig } from "@/components/CampaignConfig";
import { FixPanel } from "@/components/FixPanel";
import { StatusBar } from "@/components/StatusBar";
import { VulnReport } from "@/components/VulnReport";

function now(): string {
  return new Date().toLocaleTimeString("en-GB", { hour12: false });
}

export default function Console() {
  const [targetUrl, setTargetUrl] = useState("http://localhost:8001");
  const [description, setDescription] = useState("TechCo customer-support bot");

  const [campaignId, setCampaignId] = useState<string | null>(null);
  const [status, setStatus] = useState<CampaignStatus | "idle">("idle");
  const [rows, setRows] = useState<StreamRow[]>([]);
  const [report, setReport] = useState<VulnReportT | null>(null);
  const [fix, setFix] = useState<FixProposal | null>(null);

  const [launching, setLaunching] = useState(false);
  const [approving, setApproving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const esRef = useRef<EventSource | null>(null);
  const doneRef = useRef(false);

  // Close any open stream when the component unmounts.
  useEffect(() => () => esRef.current?.close(), []);

  function openStream(id: string) {
    esRef.current?.close();
    doneRef.current = false;
    const es = new EventSource(streamUrl(id));
    esRef.current = es;

    es.onmessage = (ev) => {
      let data: StreamEvent;
      try {
        data = JSON.parse(ev.data) as StreamEvent;
      } catch {
        return;
      }
      if (data.type === "attack_result") {
        setRows((prev) => [...prev, { result: data.result, t: now() }]);
      } else if (data.type === "report_ready") {
        setReport(data.report);
        setStatus("awaiting_approval");
        doneRef.current = true;
        es.close();
      }
    };

    es.onerror = () => {
      es.close();
      if (doneRef.current) return; // normal end after report — ignore
      recover(id); // dropped early — try to recover from stored state
    };
  }

  async function recover(id: string) {
    try {
      const c = await getCampaign(id);
      setStatus(c.status);
      if (c.results?.length) {
        setRows(c.results.map((result) => ({ result, t: "--:--:--" })));
      }
      if (c.report) {
        setReport(c.report);
        doneRef.current = true;
      }
      if (c.fix) setFix(c.fix);
      if (!c.report && c.status !== "done") {
        setError(
          "Live stream interrupted before the report was ready. Reload to retry.",
        );
      }
    } catch (e) {
      setError(
        `Lost connection to the backend at ${API_BASE}. Is it running? ` +
          `(${e instanceof Error ? e.message : "unknown error"})`,
      );
    }
  }

  async function launch() {
    setError(null);
    setLaunching(true);
    setRows([]);
    setReport(null);
    setFix(null);
    setCampaignId(null);
    setStatus("idle");
    try {
      const { campaign_id } = await launchCampaign(targetUrl, description);
      setCampaignId(campaign_id);
      setStatus("running");
      openStream(campaign_id);
    } catch (e) {
      setStatus("idle");
      setError(
        `Could not launch campaign against ${API_BASE}. ` +
          `Check the backend is up and the target URL is reachable. ` +
          `(${e instanceof Error ? e.message : "unknown error"})`,
      );
    } finally {
      setLaunching(false);
    }
  }

  async function approve() {
    if (!campaignId) return;
    setApproving(true);
    setError(null);
    try {
      const proposal = await approveCampaign(campaignId);
      setFix(proposal);
      setStatus("done");
    } catch (e) {
      setError(
        `Approval failed. ${e instanceof Error ? e.message : "unknown error"}`,
      );
    } finally {
      setApproving(false);
    }
  }

  const breaches = rows.filter((r) => r.result.verdict === "FAIL").length;

  return (
    <div className="flex min-h-dvh flex-col">
      <StatusBar
        status={status}
        campaignId={campaignId}
        target={targetUrl}
        breaches={breaches}
        probes={rows.length}
      />

      <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-5 lg:px-6">
        {error && (
          <div
            role="alert"
            className="reveal mb-4 flex items-start justify-between gap-4 border border-fail/40 bg-faildim/50 px-3.5 py-2.5"
          >
            <p className="text-[12px] leading-relaxed text-fail/95">{error}</p>
            <button
              onClick={() => setError(null)}
              className="shrink-0 text-[12px] text-muted hover:text-fg"
              aria-label="Dismiss error"
            >
              ✕
            </button>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-[360px_minmax(0,1fr)]">
          {/* control rail */}
          <div className="flex flex-col gap-4">
            <CampaignConfig
              targetUrl={targetUrl}
              setTargetUrl={setTargetUrl}
              description={description}
              setDescription={setDescription}
              onLaunch={launch}
              launching={launching}
              status={status}
            />
            <VulnReport report={report} status={status} />
            {status === "awaiting_approval" && (
              <ApprovalGate onApprove={approve} approving={approving} />
            )}
          </div>

          {/* hero: live attack stream */}
          <AttackStream rows={rows} status={status} />
        </div>

        {fix && <FixPanel report={report} fix={fix} />}

        <footer className="mt-6 flex items-center justify-between border-t border-line/60 pt-3 text-[10.5px] tracking-[0.1em] text-muted">
          <span>REDAGENT // DEFENSIVE RED-TEAM CONSOLE</span>
          <span className="truncate">api: {API_BASE}</span>
        </footer>
      </main>
    </div>
  );
}

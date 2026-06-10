"use client";

import { useMemo } from "react";
import type { TimelineEvent } from "../types/api";

interface AgentTimelineProps {
  timeline: TimelineEvent[];
}

type NodeStatus = "waiting" | "running" | "completed" | "error";

const AGENT_ORDER = [
  { id: "claim_extractor", label: "Extractor" },
  { id: "retriever", label: "Retriever" },
  { id: "verifier", label: "Verifier" },
  { id: "critic", label: "Critic" },
  { id: "judge", label: "Judge" },
];

const AGENT_ALIASES: Record<string, string> = {
  extractor: "claim_extractor",
  claim_extractor: "claim_extractor",
  retriever: "retriever",
  evidence_retriever: "retriever",
  verifier: "verifier",
  critic: "critic",
  scorer: "judge",
  judge: "judge",
};

function normalizeAgentKey(agent: string): string {
  const normalized = agent.toLowerCase().replace(/\s+/g, "_");
  return AGENT_ALIASES[normalized] ?? normalized;
}

function getDurationMs(startedAt: string, completedAt: string): string {
  try {
    const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
    if (isNaN(ms) || ms < 0) return "--";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  } catch {
    return "--";
  }
}

function getStatus(event: TimelineEvent | undefined): NodeStatus {
  if (!event) return "waiting";
  if (event.completedAt) return "completed";
  if (/failed|error/i.test(event.outputSummary ?? "")) return "error";
  if (event.startedAt) return "running";
  return "waiting";
}

function statusStyles(status: NodeStatus): { label: string; color: string; background: string; border: string } {
  if (status === "completed") {
    return {
      label: "Done",
      color: "var(--color-verified)",
      background: "rgba(34,197,94,0.10)",
      border: "rgba(34,197,94,0.35)",
    };
  }

  if (status === "error") {
    return {
      label: "Error",
      color: "var(--color-refuted)",
      background: "rgba(239,68,68,0.10)",
      border: "rgba(239,68,68,0.35)",
    };
  }

  if (status === "running") {
    return {
      label: "Running",
      color: "var(--color-uncertain)",
      background: "rgba(245,158,11,0.10)",
      border: "rgba(245,158,11,0.35)",
    };
  }

  return {
    label: "Waiting",
    color: "var(--color-unverified)",
    background: "rgba(107,114,128,0.10)",
    border: "rgba(107,114,128,0.35)",
  };
}

function buildTimelineMap(timeline: TimelineEvent[]) {
  const map = new Map<string, TimelineEvent>();
  for (const item of timeline) {
    map.set(normalizeAgentKey(item.agent), item);
  }
  return map;
}

function formatTimestamp(value: string | undefined): string {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(date);
}

export function AgentTimeline({ timeline }: AgentTimelineProps) {
  const completedCount = timeline.filter((item) => Boolean(item.completedAt)).length;
  const timelineByAgent = useMemo(() => buildTimelineMap(timeline), [timeline]);

  if (timeline.length === 0) {
    return (
      <div className="card p-6">
        <p className="label">Agent Timeline</p>
        <p className="mt-3 rounded-md border border-border bg-surface-high p-4 text-sm text-text-muted">
          Timeline data not available for this analysis.
        </p>
      </div>
    );
  }

  return (
    <div className="card space-y-5 p-6">
      <div>
        <p className="label">Agent Timeline</p>
        <p className="mt-0.5 text-xs text-text-muted">
          {completedCount} of {AGENT_ORDER.length} agent{AGENT_ORDER.length !== 1 ? "s" : ""} completed
        </p>
      </div>

      <div className="overflow-x-auto rounded-md border border-border bg-surface p-4" aria-label="agent-timeline-flow">
        <ol className="grid min-w-[780px] grid-cols-5 gap-0">
          {AGENT_ORDER.map((agent, index) => {
            const event = timelineByAgent.get(agent.id);
            const status = getStatus(event);
            const styles = statusStyles(status);
            const duration = event?.startedAt && event?.completedAt
              ? getDurationMs(event.startedAt, event.completedAt)
              : "--";

            return (
              <li key={agent.id} className="relative px-2">
                {index > 0 ? (
                  <span className="absolute left-0 top-5 h-px w-1/2 bg-border" aria-hidden="true" />
                ) : null}
                {index < AGENT_ORDER.length - 1 ? (
                  <span className="absolute right-0 top-5 h-px w-1/2 bg-border" aria-hidden="true" />
                ) : null}
                <div className="relative z-10 mx-auto flex w-full max-w-[150px] flex-col items-center text-center">
                  <span
                    className="flex h-10 w-10 items-center justify-center rounded-full border text-xs font-semibold"
                    style={{ color: styles.color, background: styles.background, borderColor: styles.border }}
                    aria-label={`${agent.label} status`}
                  >
                    {index + 1}
                  </span>
                  <p className="mt-2 text-sm font-medium text-text-primary">{agent.label}</p>
                  <span
                    className="mt-1 rounded-full border px-2 py-0.5 text-[11px]"
                    style={{ color: styles.color, background: styles.background, borderColor: styles.border }}
                  >
                    {styles.label}
                  </span>
                  <p className="mt-1 text-xs text-text-muted">{duration}</p>
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {AGENT_ORDER.map((agent) => {
          const event = timelineByAgent.get(agent.id);
          const duration = event?.startedAt && event?.completedAt
            ? getDurationMs(event.startedAt, event.completedAt)
            : "--";

          return (
            <div key={agent.id} className="rounded-md border border-border bg-surface-high p-3">
              <div className="flex items-center justify-between gap-2">
                <p className="text-sm font-medium text-text-primary">{agent.label}</p>
                <span className="text-xs text-text-muted">{duration}</span>
              </div>
              <dl className="mt-2 grid gap-1 text-xs text-text-secondary">
                <div className="grid grid-cols-[76px_1fr] gap-2">
                  <dt className="text-text-muted">Start</dt>
                  <dd className="break-words">{formatTimestamp(event?.startedAt)}</dd>
                </div>
                <div className="grid grid-cols-[76px_1fr] gap-2">
                  <dt className="text-text-muted">End</dt>
                  <dd className="break-words">{formatTimestamp(event?.completedAt)}</dd>
                </div>
                <div className="grid grid-cols-[76px_1fr] gap-2">
                  <dt className="text-text-muted">Input</dt>
                  <dd className="break-words">{event?.inputSummary || "--"}</dd>
                </div>
                <div className="grid grid-cols-[76px_1fr] gap-2">
                  <dt className="text-text-muted">Output</dt>
                  <dd className="break-words">{event?.outputSummary || "--"}</dd>
                </div>
              </dl>
            </div>
          );
        })}
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import {
  Background,
  ReactFlow,
  ReactFlowProvider,
  type Edge,
  type Node,
} from "@xyflow/react";
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
  if (/failed|error/i.test(event.outputSummary ?? "")) return "error";
  if (event.completedAt) return "completed";
  if (event.startedAt) return "running";
  return "waiting";
}

function statusVisual(status: NodeStatus): { icon: string; color: string; bg: string; border: string } {
  if (status === "completed") {
    return {
      icon: "OK",
      color: "var(--color-verified)",
      bg: "rgba(34,197,94,0.10)",
      border: "rgba(34,197,94,0.35)",
    };
  }

  if (status === "error") {
    return {
      icon: "!",
      color: "var(--color-refuted)",
      bg: "rgba(239,68,68,0.10)",
      border: "rgba(239,68,68,0.35)",
    };
  }

  if (status === "running") {
    return {
      icon: "...",
      color: "var(--color-uncertain)",
      bg: "rgba(245,158,11,0.10)",
      border: "rgba(245,158,11,0.35)",
    };
  }

  return {
    icon: "--",
    color: "var(--color-unverified)",
    bg: "rgba(107,114,128,0.10)",
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

function TimelineCanvas({ timeline }: AgentTimelineProps) {
  const timelineByAgent = useMemo(() => buildTimelineMap(timeline), [timeline]);

  const nodes = useMemo<Array<Node>>(() => {
    return AGENT_ORDER.map((agent, index) => {
      const event = timelineByAgent.get(agent.id);
      const status = getStatus(event);
      const visual = statusVisual(status);
      const duration = event?.startedAt && event?.completedAt
        ? getDurationMs(event.startedAt, event.completedAt)
        : "waiting";

      const tooltip = event
        ? `Input: ${event.inputSummary || "n/a"}\nOutput: ${event.outputSummary || "n/a"}`
        : "Waiting for this agent to run";

      return {
        id: agent.id,
        type: "default",
        position: { x: index * 210, y: 25 },
        draggable: false,
        selectable: false,
        connectable: false,
        data: {
          label: (
            <div className="min-w-[150px]" title={tooltip}>
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-medium text-text-primary">{agent.label}</span>
                <span
                  aria-label={`${agent.label} status`}
                  className="inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[10px] font-semibold"
                  style={{
                    color: visual.color,
                    background: visual.bg,
                    border: `1px solid ${visual.border}`,
                  }}
                >
                  {visual.icon}
                </span>
              </div>
              <div className="mt-1 text-xs text-text-secondary">{duration}</div>
            </div>
          ),
        },
        style: {
          borderRadius: 8,
          border: `1px solid ${visual.border}`,
          background: "var(--color-surface-high)",
          boxShadow: "none",
          color: "var(--color-text-primary)",
          padding: 8,
        },
      };
    });
  }, [timelineByAgent]);

  const edges = useMemo<Array<Edge>>(() => {
    return AGENT_ORDER.slice(0, -1).map((agent, index) => ({
      id: `${agent.id}->${AGENT_ORDER[index + 1].id}`,
      source: agent.id,
      target: AGENT_ORDER[index + 1].id,
      animated: false,
      style: {
        stroke: "var(--color-border)",
        strokeWidth: 1.5,
      },
    }));
  }, []);

  return (
    <div className="h-[220px] w-full rounded-md border border-border bg-surface" aria-label="agent-timeline-flow">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
      >
        <Background color="var(--color-border-subtle)" gap={20} size={1} />
      </ReactFlow>
    </div>
  );
}

function TimelineDetails({ timeline }: AgentTimelineProps) {
  const timelineByAgent = useMemo(() => buildTimelineMap(timeline), [timeline]);

  return (
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
                <dd className="break-words">{event?.startedAt || "--"}</dd>
              </div>
              <div className="grid grid-cols-[76px_1fr] gap-2">
                <dt className="text-text-muted">End</dt>
                <dd className="break-words">{event?.completedAt || "--"}</dd>
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
  );
}

export function AgentTimeline({ timeline }: AgentTimelineProps) {
  const completedCount = timeline.filter((item) => Boolean(item.completedAt)).length;

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
    <div className="card p-6 space-y-4">
      <div>
        <p className="label">Agent Timeline</p>
        <p className="text-xs text-text-muted mt-0.5">
          {completedCount} of {AGENT_ORDER.length} agent{AGENT_ORDER.length !== 1 ? "s" : ""} completed
        </p>
      </div>
      <ReactFlowProvider>
        <TimelineCanvas timeline={timeline} />
      </ReactFlowProvider>
      <TimelineDetails timeline={timeline} />
    </div>
  );
}

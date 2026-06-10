"use client";

import type { TimelineEvent } from "../types/api";

interface AgentTimelineProps {
  timeline: TimelineEvent[];
}

const AGENT_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  claim_extractor:    { label: "Claim Extractor",     icon: "⬡", color: "var(--color-accent)"    },
  evidence_retriever: { label: "Evidence Retriever",  icon: "⬡", color: "var(--color-uncertain)" },
  verifier:           { label: "Verifier",            icon: "⬡", color: "var(--color-verified)"  },
  critic:             { label: "Critic",              icon: "⬡", color: "var(--color-refuted)"   },
  scorer:             { label: "Scorer",              icon: "⬡", color: "var(--color-accent)"    },
};

function getDurationMs(startedAt: string, completedAt: string): string {
  try {
    const ms = new Date(completedAt).getTime() - new Date(startedAt).getTime();
    if (isNaN(ms) || ms < 0) return "—";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  } catch {
    return "—";
  }
}

function getAgentConfig(agent: string) {
  const key = agent.toLowerCase().replace(/\s+/g, "_");
  return (
    AGENT_CONFIG[key] ?? {
      label: agent,
      icon:  "⬡",
      color: "var(--color-text-muted)",
    }
  );
}

export function AgentTimeline({ timeline }: AgentTimelineProps) {
  if (timeline.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Agent Timeline</p>
        <p className="text-sm text-text-muted">No timeline data available.</p>
      </div>
    );
  }

  return (
    <div className="card p-6 space-y-4">
      <div>
        <p className="label">Agent Timeline</p>
        <p className="text-xs text-text-muted mt-0.5">
          {timeline.length} agent{timeline.length !== 1 ? "s" : ""} executed
        </p>
      </div>

      {/* Timeline track */}
      <div className="relative">
        {/* Vertical connecting line */}
        <div
          className="absolute left-[19px] top-6 bottom-6 w-px"
          style={{ background: "linear-gradient(to bottom, var(--color-border), var(--color-border-subtle))" }}
        />

        <div className="space-y-2">
          {timeline.map((event, index) => {
            const cfg      = getAgentConfig(event.agent);
            const duration = getDurationMs(event.startedAt, event.completedAt);

            return (
              <div key={index} className="relative flex gap-4 group">

                {/* Node dot */}
                <div
                  className="relative z-10 flex-shrink-0 w-10 h-10 rounded-full flex items-center
                             justify-center border transition-all duration-300
                             group-hover:scale-110"
                  style={{
                    background: `${cfg.color}14`,
                    borderColor: `${cfg.color}66`,
                    boxShadow:   `0 0 12px ${cfg.color}22`,
                    color:       cfg.color,
                    fontSize:    "1rem",
                  }}
                >
                  {cfg.icon}
                </div>

                {/* Card */}
                <div
                  className="flex-1 rounded-md border border-border bg-surface-high p-3 space-y-2
                             mb-2 transition-colors hover:border-accent/30"
                >
                  {/* Agent name + duration */}
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className="text-sm font-medium"
                      style={{ color: cfg.color }}
                    >
                      {cfg.label}
                    </span>
                    <span
                      className="text-xs px-2 py-0.5 rounded font-mono"
                      style={{
                        background: `${cfg.color}14`,
                        color:       cfg.color,
                      }}
                    >
                      {duration}
                    </span>
                  </div>

                  {/* Input summary */}
                  {event.inputSummary && (
                    <div className="space-y-0.5">
                      <p className="label" style={{ fontSize: "0.6rem" }}>Input</p>
                      <p className="text-xs text-text-muted leading-relaxed">
                        {event.inputSummary}
                      </p>
                    </div>
                  )}

                  {/* Output summary */}
                  {event.outputSummary && (
                    <div className="space-y-0.5">
                      <p className="label" style={{ fontSize: "0.6rem" }}>Output</p>
                      <p className="text-xs text-text-secondary leading-relaxed">
                        {event.outputSummary}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
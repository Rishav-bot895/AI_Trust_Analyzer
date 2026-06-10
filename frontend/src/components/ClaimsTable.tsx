"use client";

import { useState } from "react";
import type { Claim, ClaimStatus } from "../types/api";

interface ClaimsTableProps {
  claims: Claim[];
}

const STATUS_CONFIG: Record<ClaimStatus, { label: string; color: string; bg: string }> = {
  SUPPORTED:           { label: "Supported",            color: "var(--color-verified)",   bg: "rgba(34,197,94,0.08)"  },
  PARTIALLY_SUPPORTED: { label: "Partial",              color: "var(--color-uncertain)",  bg: "rgba(245,158,11,0.08)" },
  CONTRADICTED:        { label: "Contradicted",         color: "var(--color-refuted)",    bg: "rgba(239,68,68,0.08)"  },
  UNSUPPORTED:         { label: "Unsupported",          color: "var(--color-refuted)",    bg: "rgba(239,68,68,0.08)"  },
  UNVERIFIABLE:        { label: "Unverifiable",         color: "var(--color-unverified)", bg: "rgba(107,114,128,0.08)"},
};

const ALL_STATUSES: ClaimStatus[] = [
  "SUPPORTED",
  "PARTIALLY_SUPPORTED",
  "CONTRADICTED",
  "UNSUPPORTED",
  "UNVERIFIABLE",
];

function StatusBadge({ status }: { status: ClaimStatus }) {
  const cfg = STATUS_CONFIG[status];
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap"
      style={{ color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}33` }}
    >
      {cfg.label}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    pct >= 75 ? "var(--color-risk-low)"
    : pct >= 45 ? "var(--color-risk-medium)"
    : "var(--color-risk-high)";

  return (
    <div className="flex items-center gap-2 min-w-[80px]">
      <div className="flex-1 h-1 rounded-full bg-surface-high overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs text-text-muted w-8 text-right">{pct}%</span>
    </div>
  );
}

export function ClaimsTable({ claims }: ClaimsTableProps) {
  const [filter, setFilter] = useState<ClaimStatus | "ALL">("ALL");
  const [expanded, setExpanded] = useState<string | null>(null);

  const filtered = filter === "ALL" ? claims : claims.filter((c) => c.status === filter);

  const counts = ALL_STATUSES.reduce<Record<string, number>>((acc, s) => {
    acc[s] = claims.filter((c) => c.status === s).length;
    return acc;
  }, {});

  if (claims.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Claims</p>
        <p className="text-sm text-text-muted">No claims extracted.</p>
      </div>
    );
  }

  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <p className="label">Claims</p>
          <p className="text-xs text-text-muted mt-0.5">{claims.length} claim{claims.length !== 1 ? "s" : ""} extracted</p>
        </div>

        {/* Filter pills */}
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setFilter("ALL")}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              filter === "ALL"
                ? "bg-accent text-surface font-medium"
                : "border border-border text-text-secondary hover:border-accent hover:text-accent"
            }`}
          >
            All ({claims.length})
          </button>
          {ALL_STATUSES.filter((s) => counts[s] > 0).map((s) => {
            const cfg = STATUS_CONFIG[s];
            return (
              <button
                key={s}
                type="button"
                onClick={() => setFilter(s)}
                className="px-2.5 py-1 rounded text-xs transition-colors"
                style={
                  filter === s
                    ? { background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.color}` }
                    : { border: "1px solid var(--color-border)", color: "var(--color-text-secondary)" }
                }
              >
                {cfg.label} ({counts[s]})
              </button>
            );
          })}
        </div>
      </div>

      {/* Table */}
      <div className="space-y-2">
        {filtered.map((claim) => {
          const isOpen = expanded === claim.id;
          return (
            <div
              key={claim.id}
              className="rounded-md border border-border overflow-hidden transition-colors hover:border-accent/40"
            >
              {/* Row */}
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : claim.id)}
                className="w-full flex items-start gap-3 px-4 py-3 text-left bg-surface-high hover:bg-surface transition-colors"
              >
                {/* Index */}
                <span className="text-xs text-text-muted mt-0.5 w-5 flex-shrink-0">
                  {claim.claimIndex + 1}.
                </span>

                {/* Claim text */}
                <span className="flex-1 text-sm text-text-primary leading-relaxed">
                  {claim.text}
                </span>

                {/* Right side: badge + confidence + chevron */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  <StatusBadge status={claim.status} />
                  <ConfidenceBar value={claim.confidence} />
                  <span
                    className="text-text-muted text-xs transition-transform duration-200"
                    style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}
                  >
                    ▾
                  </span>
                </div>
              </button>

              {/* Expanded detail */}
              {isOpen && claim.sourceSpan && (
                <div className="px-4 py-3 border-t border-border bg-surface">
                  <p className="label mb-1">Source span</p>
                  <p className="text-xs text-text-secondary leading-relaxed italic">
                    "{claim.sourceSpan}"
                  </p>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
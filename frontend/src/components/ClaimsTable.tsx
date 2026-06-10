"use client";

import { useMemo, useState } from "react";
import type { Claim, ClaimStatus, Evidence } from "../types/api";
import { Skeleton, SkeletonRow } from "./Skeleton";

interface ClaimsTableProps {
  claims: Claim[];
  evidence?: Evidence[];
  isLoading?: boolean;
}

const STATUS_CONFIG: Record<ClaimStatus, { label: string; color: string; bg: string }> = {
  SUPPORTED:           { label: "Supported",            color: "var(--color-verified)",   bg: "rgba(34,197,94,0.08)"  },
  PARTIALLY_SUPPORTED: { label: "Partial",              color: "var(--color-uncertain)",  bg: "rgba(245,158,11,0.08)" },
  CONTRADICTED:        { label: "Contradicted",         color: "var(--color-refuted)",    bg: "rgba(239,68,68,0.08)"  },
  UNSUPPORTED:         { label: "Unsupported",          color: "var(--color-unverified)", bg: "rgba(107,114,128,0.08)" },
  UNVERIFIABLE:        { label: "Unverifiable",         color: "var(--color-unverified)", bg: "rgba(107,114,128,0.08)"},
};

type ClaimsFilter = "ALL" | "SUPPORTED" | "CONTRADICTED" | "UNSUPPORTED";
type ConfidenceSort = "desc" | "asc";

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
    pct >= 80 ? "var(--color-risk-low)"
    : pct >= 50 ? "var(--color-risk-medium)"
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

function ClaimsTableSkeleton() {
  return (
    <div className="card p-6 space-y-4" aria-label="claims-table-skeleton">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="space-y-2">
          <Skeleton width={58} height={12} />
          <Skeleton width={112} height={12} />
        </div>
        <div className="flex flex-wrap gap-1.5">
          <Skeleton width={54} height={26} />
          <Skeleton width={92} height={26} />
          <Skeleton width={104} height={26} />
          <Skeleton width={98} height={26} />
        </div>
      </div>

      <div className="overflow-hidden rounded-md border border-border">
        <div className="grid grid-cols-[56px_1fr_180px_180px] items-center gap-3 border-b border-border bg-surface-high px-4 py-2">
          <Skeleton width={14} height={12} />
          <Skeleton width={78} height={12} />
          <Skeleton width={52} height={12} />
          <Skeleton width={84} height={12} />
        </div>
        {[0, 1, 2, 3].map((index) => (
          <SkeletonRow key={index} />
        ))}
      </div>
    </div>
  );
}

export function ClaimsTable({ claims, evidence = [], isLoading = false }: ClaimsTableProps) {
  const [filter, setFilter] = useState<ClaimsFilter>("ALL");
  const [expanded, setExpanded] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<ConfidenceSort>("desc");

  const filteredAndSorted = useMemo(() => {
    const filtered = claims.filter((claim) => {
      if (filter === "ALL") return true;
      if (filter === "SUPPORTED") return claim.status === "SUPPORTED";
      if (filter === "CONTRADICTED") return claim.status === "CONTRADICTED";
      return claim.status === "UNSUPPORTED";
    });

    return [...filtered].sort((a, b) => {
      if (sortDirection === "desc") {
        return b.confidence - a.confidence;
      }
      return a.confidence - b.confidence;
    });
  }, [claims, filter, sortDirection]);

  const evidenceByClaimId = useMemo(() => {
    const map = new Map<string, Evidence[]>();
    for (const item of evidence) {
      const current = map.get(item.claimId) ?? [];
      current.push(item);
      map.set(item.claimId, current);
    }

    for (const [claimId, entries] of map.entries()) {
      entries.sort((a, b) => b.relevanceScore - a.relevanceScore);
      map.set(claimId, entries);
    }

    return map;
  }, [evidence]);

  const counts = useMemo(() => {
    return {
      ALL: claims.length,
      SUPPORTED: claims.filter((c) => c.status === "SUPPORTED").length,
      CONTRADICTED: claims.filter((c) => c.status === "CONTRADICTED").length,
      UNSUPPORTED: claims.filter((c) => c.status === "UNSUPPORTED").length,
    };
  }, [claims]);

  if (isLoading) {
    return <ClaimsTableSkeleton />;
  }

  if (claims.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Claims</p>
        <p className="text-sm text-text-muted">No claims extracted</p>
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
          {([
            ["ALL", "All"],
            ["SUPPORTED", "Supported"],
            ["CONTRADICTED", "Contradicted"],
            ["UNSUPPORTED", "Unsupported"],
          ] as Array<[ClaimsFilter, string]>).map(([value, label]) => {
            const active = filter === value;
            return (
              <button
                key={value}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(value)}
                className={`px-2.5 py-1 rounded text-xs transition-colors ${
                  active
                    ? "bg-accent text-surface font-medium"
                    : "border border-border text-text-secondary hover:border-accent hover:text-accent"
                }`}
              >
                {label} ({counts[value]})
              </button>
            );
          })}
        </div>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-md border border-border">
        <div className="grid grid-cols-[56px_1fr_180px_180px] items-center gap-3 border-b border-border bg-surface-high px-4 py-2 text-xs uppercase tracking-wide text-text-secondary">
          <span>#</span>
          <span>Claim Text</span>
          <span>Status</span>
          <button
            type="button"
            onClick={() => setSortDirection((current) => (current === "desc" ? "asc" : "desc"))}
            className="text-left uppercase tracking-wide hover:text-text-primary"
          >
            Confidence {sortDirection === "desc" ? "↓" : "↑"}
          </button>
        </div>

        {filteredAndSorted.map((claim, index) => {
          const isOpen = expanded === claim.id;
          const claimEvidence = evidenceByClaimId.get(claim.id) ?? [];

          return (
            <div key={claim.id} className="border-b border-border last:border-b-0">
              <button
                type="button"
                onClick={() => setExpanded(isOpen ? null : claim.id)}
                className="grid w-full grid-cols-[56px_1fr_180px_180px] items-start gap-3 px-4 py-3 text-left hover:bg-surface-high/60 transition-colors"
              >
                <span className="text-xs text-text-muted mt-0.5">
                  {index + 1}
                </span>

                <span className="text-sm text-text-primary leading-relaxed">
                  {claim.text}
                </span>

                <div className="flex items-center gap-2">
                  <StatusBadge status={claim.status} />
                </div>

                <div className="flex items-center gap-2">
                  <ConfidenceBar value={claim.confidence} />
                  <span className="text-xs text-text-muted transition-transform" style={{ transform: isOpen ? "rotate(180deg)" : "rotate(0deg)" }}>
                    ▾
                  </span>
                </div>
              </button>

              {isOpen && (
                <div className="border-t border-border bg-surface px-4 py-3">
                  <p className="label mb-2">Evidence snippets</p>
                  {claimEvidence.length === 0 ? (
                    <p className="text-xs text-text-muted">No evidence snippets for this claim.</p>
                  ) : (
                    <ul className="space-y-2">
                      {claimEvidence.slice(0, 3).map((item) => (
                        <li key={item.id} className="rounded border border-border bg-surface-high px-3 py-2 text-xs text-text-secondary leading-relaxed">
                          {item.snippet}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          );
        })}

        {filteredAndSorted.length === 0 && (
          <div className="px-4 py-4 text-sm text-text-muted">No claims extracted</div>
        )}
      </div>
    </div>
  );
}

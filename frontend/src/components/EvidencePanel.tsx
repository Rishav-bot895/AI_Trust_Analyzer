"use client";

import { useMemo, useState } from "react";
import type { Evidence, EvidencePolarity } from "../types/api";
import { Skeleton, SkeletonCard } from "./Skeleton";

interface EvidencePanelProps {
  evidence: Evidence[];
  claims: { id: string; text: string; claimIndex: number }[];
  isLoading?: boolean;
}

const POLARITY_CONFIG: Record<NonNullable<EvidencePolarity>, { label: string; color: string; symbol: string }> = {
  FOR:     { label: "Supports",   color: "var(--color-verified)", symbol: "↑" },
  AGAINST: { label: "Contradicts", color: "var(--color-refuted)",  symbol: "↓" },
  UNKNOWN: { label: "Unclear", color: "var(--color-unverified)", symbol: "?" },
};

const SOURCE_LABELS: Record<string, string> = {
  WEB_SEARCH: "WEB",
  PGVECTOR:   "VECTOR",
};

function RelevanceChip({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value > 0.7
      ? "var(--color-verified)"
      : value > 0.4
        ? "var(--color-uncertain)"
        : "var(--color-unverified)";

  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
      style={{
        color,
        background: `${color}14`,
        border: `1px solid ${color}44`,
      }}
    >
      Relevance {pct}%
    </span>
  );
}

function EvidencePanelSkeleton() {
  return (
    <div className="card p-6 space-y-4" aria-label="evidence-panel-skeleton">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div className="space-y-2">
          <Skeleton width={72} height={12} />
          <Skeleton width={136} height={12} />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Skeleton width={82} height={26} />
        <Skeleton width={72} height={26} />
        <Skeleton width={72} height={26} />
      </div>

      <div className="space-y-4">
        {[0, 1].map((section) => (
          <section key={section} className="overflow-hidden rounded-md border border-border">
            <header className="border-b border-border bg-surface-high px-4 py-3">
              <Skeleton width={68} height={12} />
              <Skeleton width="82%" height={12} className="mt-3" />
            </header>
            <div className="space-y-3 p-4">
              <SkeletonCard />
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

export function EvidencePanel({ evidence, claims, isLoading = false }: EvidencePanelProps) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | "ALL">("ALL");
  const [expandedSnippets, setExpandedSnippets] = useState<Record<string, boolean>>({});

  const filteredClaims = useMemo(() => {
    if (selectedClaimId === "ALL") {
      return claims;
    }
    return claims.filter((claim) => claim.id === selectedClaimId);
  }, [claims, selectedClaimId]);

  const evidenceByClaimId = useMemo(() => {
    const grouped: Record<string, Evidence[]> = {};
    for (const item of evidence) {
      const existing = grouped[item.claimId] ?? [];
      grouped[item.claimId] = [...existing, item];
    }

    for (const claimId of Object.keys(grouped)) {
      grouped[claimId].sort((a, b) => b.relevanceScore - a.relevanceScore);
    }

    return grouped;
  }, [evidence]);

  const displayedClaimsWithEvidence = filteredClaims.filter((claim) => {
    const claimEvidence = evidenceByClaimId[claim.id] ?? [];
    return claimEvidence.length > 0;
  });

  const claimsWithEvidence = claims.filter((claim) => {
    const claimEvidence = evidenceByClaimId[claim.id] ?? [];
    return claimEvidence.length > 0;
  });

  if (isLoading) {
    return <EvidencePanelSkeleton />;
  }

  if (evidence.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Evidence</p>
        <p className="text-sm text-text-muted">No evidence retrieved</p>
      </div>
    );
  }

  return (
    <div className="card p-6 space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <p className="label">Evidence</p>
          <p className="text-xs text-text-muted mt-0.5">
            {evidence.length} source{evidence.length !== 1 ? "s" : ""} retrieved
          </p>
        </div>
      </div>

      {/* Claim filter tabs */}
      {claimsWithEvidence.length > 1 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => setSelectedClaimId("ALL")}
            className={`px-2.5 py-1 rounded text-xs transition-colors ${
              selectedClaimId === "ALL"
                ? "bg-accent text-surface font-medium"
                : "border border-border text-text-secondary hover:border-accent hover:text-accent"
            }`}
          >
            All Claims
          </button>
          {claimsWithEvidence.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setSelectedClaimId(c.id)}
              className={`px-2.5 py-1 rounded text-xs transition-colors ${
                selectedClaimId === c.id
                  ? "bg-accent text-surface font-medium"
                  : "border border-border text-text-secondary hover:border-accent hover:text-accent"
              }`}
            >
              Claim {c.claimIndex + 1}
            </button>
          ))}
        </div>
      )}

      {/* Grouped evidence cards by claim */}
      <div className="space-y-4">
        {filteredClaims.map((claim) => {
          const claimEvidence = evidenceByClaimId[claim.id] ?? [];

          return (
            <section key={claim.id} className="rounded-md border border-border overflow-hidden">
              <header className="bg-surface-high px-4 py-3 border-b border-border">
                <p className="label">Claim {claim.claimIndex + 1}</p>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">{claim.text}</p>
              </header>

              <div className="p-4 space-y-3">
                {claimEvidence.length === 0 ? (
                  <p className="text-sm text-text-muted">No evidence retrieved</p>
                ) : (
                  claimEvidence.map((item) => {
                    const polarity = item.polarity ? POLARITY_CONFIG[item.polarity] : null;
                    const isExpanded = expandedSnippets[item.id] ?? false;
                    const snippetText =
                      !isExpanded && item.snippet.length > 200
                        ? `${item.snippet.slice(0, 200)}...`
                        : item.snippet;
                    const displaySnippet = item.snippet.length > 200 ? `"${snippetText}"` : snippetText;

                    return (
                      <article
                        key={item.id}
                        className="rounded-md border border-border bg-surface-high p-4 space-y-3 hover:border-accent/40 transition-colors"
                      >
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-xs border border-border text-text-muted">
                              {SOURCE_LABELS[item.sourceType] ?? item.sourceType}
                            </span>

                            {polarity && (
                              <span
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium"
                                style={{
                                  color: polarity.color,
                                  background: `${polarity.color}14`,
                                  border: `1px solid ${polarity.color}44`,
                                }}
                              >
                                <span>{polarity.symbol}</span>
                                {polarity.label}
                              </span>
                            )}
                          </div>

                          <RelevanceChip value={item.relevanceScore} />
                        </div>

                        <p className="text-sm text-text-secondary leading-relaxed border-l-2 border-border pl-3 italic">
                          {displaySnippet}
                        </p>

                        {item.snippet.length > 200 && (
                          <button
                            type="button"
                            onClick={() =>
                              setExpandedSnippets((current) => ({
                                ...current,
                                [item.id]: !isExpanded,
                              }))
                            }
                            className="text-xs text-accent hover:underline"
                          >
                            {isExpanded ? "Show less" : "Show more"}
                          </button>
                        )}

                        {item.sourceUrl && (
                          <div className="flex items-center gap-2">
                            <span className="w-3 h-3 flex-shrink-0 opacity-40">🔗</span>
                            <a
                              href={item.sourceUrl}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-accent hover:underline truncate max-w-xs"
                              title={item.sourceUrl}
                            >
                              {item.sourceTitle ?? item.sourceUrl}
                            </a>
                          </div>
                        )}
                      </article>
                    );
                  })
                )}
              </div>
            </section>
          );
        })}

        {displayedClaimsWithEvidence.length === 0 && (
          <p className="text-sm text-text-muted">No evidence retrieved</p>
        )}
      </div>
    </div>
  );
}

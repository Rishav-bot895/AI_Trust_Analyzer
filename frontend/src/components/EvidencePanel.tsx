"use client";

import { useState } from "react";
import type { Evidence, EvidencePolarity } from "../types/api";

interface EvidencePanelProps {
  evidence: Evidence[];
  claims: { id: string; text: string; claimIndex: number }[];
}

const POLARITY_CONFIG: Record<NonNullable<EvidencePolarity>, { label: string; color: string; symbol: string }> = {
  FOR:     { label: "Supports",   color: "var(--color-verified)", symbol: "↑" },
  AGAINST: { label: "Contradicts", color: "var(--color-refuted)",  symbol: "↓" },
};

const SOURCE_LABELS: Record<string, string> = {
  WEB_SEARCH: "Web",
  PGVECTOR:   "Vector DB",
};

function RelevanceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div className="flex items-center gap-2">
      <div className="w-16 h-1 rounded-full bg-surface overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${pct}%`,
            background: "var(--color-accent)",
            transition: "width 0.6s ease",
          }}
        />
      </div>
      <span className="text-xs text-text-muted">{pct}%</span>
    </div>
  );
}

export function EvidencePanel({ evidence, claims }: EvidencePanelProps) {
  const [selectedClaimId, setSelectedClaimId] = useState<string | "ALL">("ALL");

  const filtered =
    selectedClaimId === "ALL"
      ? evidence
      : evidence.filter((e) => e.claimId === selectedClaimId);

  // Only show claims that actually have evidence
  const claimsWithEvidence = claims.filter((c) =>
    evidence.some((e) => e.claimId === c.id),
  );

  if (evidence.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Evidence</p>
        <p className="text-sm text-text-muted">No evidence retrieved.</p>
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

      {/* Evidence cards */}
      <div className="space-y-3">
        {filtered.map((item) => {
          const polarity = item.polarity ? POLARITY_CONFIG[item.polarity] : null;
          const claimNum = claims.find((c) => c.id === item.claimId)?.claimIndex;

          return (
            <div
              key={item.id}
              className="rounded-md border border-border bg-surface-high p-4 space-y-3
                         hover:border-accent/40 transition-colors"
            >
              {/* Top row: source type, polarity, relevance */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  {/* Source type pill */}
                  <span className="px-2 py-0.5 rounded text-xs border border-border text-text-muted">
                    {SOURCE_LABELS[item.sourceType] ?? item.sourceType}
                  </span>

                  {/* Claim reference */}
                  {claimNum !== undefined && (
                    <span className="text-xs text-text-muted">
                      Claim {claimNum + 1}
                    </span>
                  )}

                  {/* Polarity badge */}
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

                <RelevanceBar value={item.relevanceScore} />
              </div>

              {/* Snippet */}
              <p className="text-sm text-text-secondary leading-relaxed border-l-2 border-border pl-3 italic">
                "{item.snippet}"
              </p>

              {/* Source link */}
              {item.sourceUrl && (
                <div className="flex items-center gap-2">
                  <span className="w-3 h-3 flex-shrink-0 opacity-40">🔗</span>
                  
                    href={item.sourceUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-accent hover:underline truncate max-w-xs"
                    title={item.sourceUrl}
                  <a>
                    {item.sourceTitle ?? item.sourceUrl}
                  </a>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
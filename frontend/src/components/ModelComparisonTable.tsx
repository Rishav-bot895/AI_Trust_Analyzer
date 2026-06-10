"use client";

import { useMemo, useState } from "react";
import type { AnalysisResponse, HallucinationRisk } from "../types/api";
import { modelLabel } from "../lib/models";

interface ModelComparisonTableProps {
  analyses: AnalysisResponse[];
  models: string[];
}

type SortDirection = "desc" | "asc";

const RISK_CONFIG: Record<HallucinationRisk, { label: string; color: string }> = {
  LOW: { label: "LOW", color: "var(--color-risk-low)" },
  MEDIUM: { label: "MEDIUM", color: "var(--color-risk-medium)" },
  HIGH: { label: "HIGH", color: "var(--color-risk-high)" },
  UNKNOWN: { label: "UNKNOWN", color: "var(--color-risk-unknown)" },
};

function scoreColor(score: number): string {
  if (score >= 80) return "var(--color-risk-low)";
  if (score >= 50) return "var(--color-risk-medium)";
  return "var(--color-risk-high)";
}

function ScoreCell({ score }: { score: number | null }) {
  if (score === null) {
    return <span className="text-text-muted">--</span>;
  }

  const color = scoreColor(score);

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm font-semibold" style={{ color }}>{score}</span>
      <div className="h-1 w-16 overflow-hidden rounded-full bg-surface">
        <div
          className="h-full rounded-full"
          style={{ width: `${score}%`, background: color, transition: "width 0.6s ease" }}
        />
      </div>
    </div>
  );
}

function RiskCell({ risk }: { risk: HallucinationRisk | null }) {
  if (!risk) return <span className="text-text-muted">--</span>;
  const cfg = RISK_CONFIG[risk];
  return (
    <span
      className="inline-flex rounded px-2 py-0.5 text-xs font-medium"
      style={{
        color: cfg.color,
        background: `${cfg.color}14`,
        border: `1px solid ${cfg.color}44`,
      }}
    >
      {cfg.label}
    </span>
  );
}

function WinnerBadge({ isBest }: { isBest: boolean }) {
  if (!isBest) return null;

  return (
    <span
      className="inline-flex rounded px-1.5 py-0.5 text-[11px] font-medium"
      style={{
        color: "var(--color-accent)",
        background: "var(--color-accent-glow)",
        border: "1px solid var(--color-accent-dim)",
      }}
    >
      Best
    </span>
  );
}

function formatDelta(current: number | null, baseline: number | null): string {
  if (current === null || baseline === null) return "--";
  const delta = current - baseline;
  if (delta === 0) return "0";
  return delta > 0 ? `+${delta}` : `${delta}`;
}

export function ModelComparisonTable({ analyses, models }: ModelComparisonTableProps) {
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const baselineScore = analyses[0]?.trustScore ?? null;

  const rows = useMemo(() => analyses.map((analysis, index) => ({
    modelName: modelLabel(analysis.modelName ?? models[index] ?? `Model ${index + 1}`),
    trustScore: analysis.trustScore,
    hallucinationRisk: analysis.hallucinationRisk,
    supportedClaims: analysis.claims.filter((c) => c.status === "SUPPORTED").length,
    contradictedClaims: analysis.claims.filter((c) => c.status === "CONTRADICTED").length,
    unsupportedClaims: analysis.claims.filter((c) => c.status === "UNSUPPORTED").length,
    verdict: analysis.verdict ?? "--",
    delta: index === 0 ? null : formatDelta(analysis.trustScore, baselineScore),
  })), [analyses, baselineScore, models]);

  const bestScore = rows.reduce<number | null>((currentBest, row) => {
    if (row.trustScore === null) return currentBest;
    if (currentBest === null || row.trustScore > currentBest) return row.trustScore;
    return currentBest;
  }, null);

  const sortedRows = useMemo(() => {
    return [...rows].sort((a, b) => {
      const aScore = a.trustScore ?? -1;
      const bScore = b.trustScore ?? -1;
      return sortDirection === "desc" ? bScore - aScore : aScore - bScore;
    });
  }, [rows, sortDirection]);

  if (analyses.length === 0) {
    return (
      <div className="card p-6">
        <p className="label mb-2">Model Comparison</p>
        <p className="text-sm text-text-muted">Run a comparison to see results</p>
      </div>
    );
  }

  return (
    <div className="card space-y-4 p-6">
      <div>
        <p className="label">Model Comparison</p>
        <p className="mt-0.5 text-xs text-text-muted">
          {analyses.length} model{analyses.length !== 1 ? "s" : ""} compared
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[860px] text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="pb-3 pr-4 text-left"><span className="label">Model Name</span></th>
              <th className="pb-3 pr-4 text-left">
                <button
                  type="button"
                  onClick={() => setSortDirection((current) => (current === "desc" ? "asc" : "desc"))}
                  className="label hover:text-text-primary"
                >
                  Trust Score {sortDirection === "desc" ? "Down" : "Up"}
                </button>
              </th>
              <th className="pb-3 pr-4 text-left"><span className="label">Risk Level</span></th>
              <th className="pb-3 pr-4 text-left"><span className="label">Supported Claims</span></th>
              <th className="pb-3 pr-4 text-left"><span className="label">Contradicted Claims</span></th>
              <th className="pb-3 pr-4 text-left"><span className="label">Unsupported Claims</span></th>
              <th className="pb-3 pr-4 text-left"><span className="label">Verdict</span></th>
            </tr>
          </thead>

          <tbody>
            {sortedRows.map((row, index) => (
              <tr
                key={`${row.modelName}-${index}`}
                className="border-b border-border-subtle transition-colors hover:bg-surface-high"
                style={
                  row.trustScore !== null && bestScore !== null && row.trustScore === bestScore
                    ? {
                        boxShadow: "inset 0 0 0 1px #d4af37",
                        background: "rgba(212,175,55,0.06)",
                      }
                    : undefined
                }
              >
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-text-primary">{row.modelName}</span>
                    <WinnerBadge isBest={row.trustScore !== null && bestScore !== null && row.trustScore === bestScore} />
                  </div>
                </td>
                <td className="py-3 pr-4">
                  <div className="flex items-center gap-2">
                    <ScoreCell score={row.trustScore} />
                    {row.delta !== null ? (
                      <span className="text-xs text-text-muted">({row.delta})</span>
                    ) : null}
                  </div>
                </td>
                <td className="py-3 pr-4"><RiskCell risk={row.hallucinationRisk} /></td>
                <td className="py-3 pr-4 text-verified">{row.supportedClaims}</td>
                <td className="py-3 pr-4 text-refuted">{row.contradictedClaims}</td>
                <td className="py-3 pr-4 text-text-secondary">{row.unsupportedClaims}</td>
                <td className="max-w-[320px] truncate py-3 pr-4 text-text-secondary" title={row.verdict}>
                  {row.verdict}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

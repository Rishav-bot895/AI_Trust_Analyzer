"use client";

import type { AnalysisResponse, HallucinationRisk } from "../types/api";

interface ModelComparisonTableProps {
  analyses: AnalysisResponse[];
  models: string[];
}

const RISK_CONFIG: Record<HallucinationRisk, { label: string; color: string }> = {
  LOW:     { label: "Low",     color: "var(--color-risk-low)"     },
  MEDIUM:  { label: "Medium",  color: "var(--color-risk-medium)"  },
  HIGH:    { label: "High",    color: "var(--color-risk-high)"    },
  UNKNOWN: { label: "Unknown", color: "var(--color-risk-unknown)" },
};

function ScoreCell({ score }: { score: number | null }) {
  if (score === null) return <span className="text-text-muted">—</span>;
  const color =
    score >= 75 ? "var(--color-risk-low)"
    : score >= 45 ? "var(--color-risk-medium)"
    : "var(--color-risk-high)";
  return (
    <div className="flex flex-col items-center gap-1">
      <span className="text-lg font-medium" style={{ color }}>{score}</span>
      <div className="w-12 h-1 rounded-full bg-surface overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{ width: `${score}%`, background: color, transition: "width 0.6s ease" }}
        />
      </div>
    </div>
  );
}

function RiskCell({ risk }: { risk: HallucinationRisk | null }) {
  if (!risk) return <span className="text-text-muted">—</span>;
  const cfg = RISK_CONFIG[risk];
  return (
    <span
      className="inline-flex px-2 py-0.5 rounded text-xs font-medium"
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

function WinnerBadge() {
  return (
    <span
      className="ml-2 inline-flex px-1.5 py-0.5 rounded text-xs font-medium"
      style={{
        color: "var(--color-accent)",
        background: "var(--color-accent-glow)",
        border: "1px solid var(--color-accent-dim)",
      }}
    >
      ★ Best
    </span>
  );
}

export function ModelComparisonTable({ analyses, models }: ModelComparisonTableProps) {
  if (analyses.length === 0) return null;

  // Find which model scored highest
  const bestIndex = analyses.reduce<number>((best, curr, i) => {
    const bestScore = analyses[best].trustScore ?? -1;
    const currScore = curr.trustScore ?? -1;
    return currScore > bestScore ? i : best;
  }, 0);

  const rows: {
    label: string;
    render: (a: AnalysisResponse) => React.ReactNode;
  }[] = [
    {
      label: "Trust Score",
      render: (a) => <ScoreCell score={a.trustScore} />,
    },
    {
      label: "Hallucination Risk",
      render: (a) => <RiskCell risk={a.hallucinationRisk} />,
    },
    {
      label: "Claims Found",
      render: (a) => (
        <span className="text-text-primary">{a.claims.length}</span>
      ),
    },
    {
      label: "Supported",
      render: (a) => (
        <span style={{ color: "var(--color-verified)" }}>
          {a.claims.filter((c) => c.status === "SUPPORTED").length}
        </span>
      ),
    },
    {
      label: "Contradicted",
      render: (a) => (
        <span style={{ color: "var(--color-refuted)" }}>
          {a.claims.filter((c) => c.status === "CONTRADICTED").length}
        </span>
      ),
    },
    {
      label: "Evidence Sources",
      render: (a) => (
        <span className="text-text-primary">{a.evidence.length}</span>
      ),
    },
    {
      label: "Status",
      render: (a) => (
        <span
          className={`text-xs ${
            a.status === "COMPLETED" ? "text-verified" :
            a.status === "FAILED"    ? "text-refuted"  :
            "text-text-muted"
          }`}
        >
          {a.status}
        </span>
      ),
    },
  ];

  return (
    <div className="card p-6 space-y-4">
      <div>
        <p className="label">Model Comparison</p>
        <p className="text-xs text-text-muted mt-0.5">
          {analyses.length} models compared
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {/* Empty corner cell */}
              <th className="pb-3 pr-4 text-left w-36">
                <span className="label">Metric</span>
              </th>
              {models.map((model, i) => (
                <th key={model} className="pb-3 px-4 text-center">
                  <div className="flex flex-col items-center gap-1">
                    <span className="text-text-primary font-medium text-xs">
                      {model}
                      {i === bestIndex && analyses[i].trustScore !== null && (
                        <WinnerBadge />
                      )}
                    </span>
                    <span
                      className={`text-xs ${
                        analyses[i].status === "FAILED"
                          ? "text-refuted"
                          : "text-text-muted"
                      }`}
                    >
                      {analyses[i].status === "FAILED" ? "Failed" : ""}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, ri) => (
              <tr
                key={row.label}
                className={`border-b border-border-subtle transition-colors hover:bg-surface-high ${
                  ri % 2 === 0 ? "bg-transparent" : "bg-surface-raised/40"
                }`}
              >
                <td className="py-3 pr-4">
                  <span className="text-xs text-text-secondary">{row.label}</span>
                </td>
                {analyses.map((analysis, i) => (
                  <td key={i} className="py-3 px-4 text-center">
                    {row.render(analysis)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Verdict comparison */}
      {analyses.some((a) => a.verdict) && (
        <div className="space-y-3 pt-2 border-t border-border">
          <p className="label">Verdicts</p>
          <div
            className="grid gap-3"
            style={{ gridTemplateColumns: `repeat(${analyses.length}, 1fr)` }}
          >
            {analyses.map((a, i) => (
              <div key={i} className="space-y-1">
                <p className="text-xs text-text-muted">{models[i]}</p>
                <p className="text-xs text-text-secondary leading-relaxed">
                  {a.verdict ?? "—"}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
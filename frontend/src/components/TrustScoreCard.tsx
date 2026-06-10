"use client";

import type { HallucinationRisk } from "../types/api";
import { Skeleton } from "./Skeleton";

interface TrustScoreCardProps {
  trustScore: number | null;
  hallucinationRisk: HallucinationRisk | null;
  verdict: string | null;
  critique?: string | null;
  isLoading?: boolean;
}

const RISK_CONFIG: Record<HallucinationRisk, { label: string; color: string; glow: string }> = {
  LOW: {
    label: "LOW RISK",
    color: "var(--color-risk-low)",
    glow: "rgba(34,197,94,0.15)",
  },
  MEDIUM: {
    label: "MEDIUM RISK",
    color: "var(--color-risk-medium)",
    glow: "rgba(245,158,11,0.15)",
  },
  HIGH: {
    label: "HIGH RISK",
    color: "var(--color-risk-high)",
    glow: "rgba(239,68,68,0.15)",
  },
  UNKNOWN: {
    label: "UNKNOWN RISK",
    color: "var(--color-risk-unknown)",
    glow: "rgba(107,114,128,0.15)",
  },
};

function getScoreColor(score: number): string {
  if (score >= 80) return "var(--color-risk-low)";
  if (score >= 50) return "var(--color-risk-medium)";
  return "var(--color-risk-high)";
}

function TrustScoreCardSkeleton() {
  return (
    <div className="card p-6 space-y-6" aria-label="trust-score-card-skeleton">
      <Skeleton width={128} height={14} />

      <div className="flex items-center gap-8">
        <div aria-label="trust-score-skeleton" className="relative flex-shrink-0" style={{ width: 128, height: 128 }}>
          <Skeleton width={128} height={128} className="rounded-full" />
        </div>

        <div className="flex-1 space-y-3">
          <Skeleton width={132} height={32} />
          <Skeleton width="100%" height={14} />
          <Skeleton width="78%" height={14} />
        </div>
      </div>

      <div className="accent-line space-y-2">
        <Skeleton width={64} height={12} />
        <Skeleton width="100%" height={14} />
        <Skeleton width="72%" height={14} />
      </div>
    </div>
  );
}

export function TrustScoreCard({ trustScore, hallucinationRisk, verdict, critique, isLoading = false }: TrustScoreCardProps) {
  if (isLoading || trustScore === null) {
    return <TrustScoreCardSkeleton />;
  }

  const risk   = hallucinationRisk ?? "UNKNOWN";
  const config = RISK_CONFIG[risk];
  const score  = Math.max(0, Math.min(100, trustScore));
  const ringColor = getScoreColor(score);
  const radius = 48;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - score / 100);

  const scoreSummary =
    score >= 80
      ? "This response appears well-grounded. Claims are largely supported by evidence."
      : score >= 50
        ? "Some claims may be uncertain or only partially supported. Review flagged items."
        : "Significant hallucination risk detected. Multiple claims lack evidence support.";

  return (
    <div className="card p-6 space-y-6">
      <p className="label">Trust Assessment</p>

      {/* Score gauge + risk badge */}
      <div className="flex items-center gap-8">
        <div className="relative flex-shrink-0" style={{ width: 128, height: 128 }}>
          <svg viewBox="0 0 128 128" className="h-full w-full">
              <circle
                cx="64"
                cy="64"
                r={radius}
                fill="none"
                stroke="var(--color-border)"
                strokeWidth="8"
              />
              <circle
                cx="64"
                cy="64"
                r={radius}
                fill="none"
                stroke={ringColor}
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={dashOffset}
                transform="rotate(-90 64 64)"
                className="trust-score-ring"
                style={{
                  ["--ring-from" as string]: `${circumference}`,
                  ["--ring-to" as string]: `${dashOffset}`,
                }}
              />
              <text
                x="64"
                y="60"
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="32"
                fontWeight="700"
                fill={ringColor}
                fontFamily="var(--font-mono)"
              >
                {Math.round(score)}
              </text>
              <text
                x="64"
                y="80"
                textAnchor="middle"
                fontSize="10"
                fill="var(--color-text-muted)"
                fontFamily="var(--font-mono)"
              >
                /100
              </text>
          </svg>
        </div>

        <div className="space-y-3 flex-1">
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium"
            style={{
              background: config.glow,
              border: `1px solid ${config.color}`,
              color: config.color,
            }}
          >
            {/* Pulsing dot */}
            <span
              className="w-2 h-2 rounded-full flex-shrink-0"
              style={{
                background: config.color,
                boxShadow: `0 0 6px ${config.color}`,
                animation: risk !== "UNKNOWN" ? "pulse 2s infinite" : "none",
              }}
            />
            {config.label}
          </div>

          <p className="text-xs text-text-secondary leading-relaxed">
            {scoreSummary}
          </p>
        </div>
      </div>

      {/* Verdict */}
      {verdict && (
        <div className="accent-line space-y-1">
          <p className="label">Verdict</p>
          <p className="text-sm text-text-primary leading-relaxed">{verdict}</p>
        </div>
      )}

      {/* Critique */}
      {critique && (
        <div className="space-y-1">
          <p className="label">Critique</p>
          <p className="text-sm text-text-secondary leading-relaxed">{critique}</p>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.4; }
        }
      `}</style>
    </div>
  );
}

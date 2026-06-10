"use client";

import { useEffect, useState } from "react";
import type { HallucinationRisk } from "../types/api";

interface TrustScoreCardProps {
  trustScore: number | null;
  hallucinationRisk: HallucinationRisk | null;
  verdict: string | null;
  critique: string | null;
}

const RISK_CONFIG: Record<HallucinationRisk, { label: string; color: string; glow: string }> = {
  LOW:     { label: "Low Risk",     color: "var(--color-risk-low)",     glow: "rgba(34,197,94,0.15)"  },
  MEDIUM:  { label: "Medium Risk",  color: "var(--color-risk-medium)",  glow: "rgba(245,158,11,0.15)" },
  HIGH:    { label: "High Risk",    color: "var(--color-risk-high)",    glow: "rgba(239,68,68,0.15)"  },
  UNKNOWN: { label: "Unknown Risk", color: "var(--color-risk-unknown)", glow: "rgba(107,114,128,0.15)"},
};

function getScoreColor(score: number): string {
  if (score >= 75) return "var(--color-risk-low)";
  if (score >= 45) return "var(--color-risk-medium)";
  return "var(--color-risk-high)";
}

// Converts a 0-100 score to SVG arc path coordinates
function describeArc(cx: number, cy: number, r: number, startDeg: number, endDeg: number) {
  const toRad = (d: number) => ((d - 90) * Math.PI) / 180;
  const x1 = cx + r * Math.cos(toRad(startDeg));
  const y1 = cy + r * Math.sin(toRad(startDeg));
  const x2 = cx + r * Math.cos(toRad(endDeg));
  const y2 = cy + r * Math.sin(toRad(endDeg));
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}`;
}

export function TrustScoreCard({ trustScore, hallucinationRisk, verdict, critique }: TrustScoreCardProps) {
  // Animate the score counting up from 0
  const [displayed, setDisplayed] = useState(0);

  useEffect(() => {
    if (trustScore === null) { setDisplayed(0); return; }
    let frame: number;
    const start = performance.now();
    const duration = 1200;
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplayed(Math.round(eased * trustScore));
      if (progress < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [trustScore]);

  const risk   = hallucinationRisk ?? "UNKNOWN";
  const config = RISK_CONFIG[risk];
  const score  = trustScore ?? 0;

  // Arc goes from -135° to +135° (270° sweep) like a gauge
  const SWEEP      = 270;
  const START_DEG  = -135;
  const fillDeg    = START_DEG + (score / 100) * SWEEP;
  const trackPath  = describeArc(60, 60, 46, START_DEG, START_DEG + SWEEP);
  const fillPath   = trustScore !== null ? describeArc(60, 60, 46, START_DEG, fillDeg) : null;

  return (
    <div className="card p-6 space-y-6">
      <p className="label">Trust Assessment</p>

      {/* Score gauge + risk badge */}
      <div className="flex items-center gap-8">

        {/* SVG Gauge */}
        <div className="relative flex-shrink-0" style={{ width: 120, height: 120 }}>
          <svg viewBox="0 0 120 120" className="w-full h-full">
            <defs>
              <filter id="glow">
                <feGaussianBlur stdDeviation="3" result="blur" />
                <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>

            {/* Track */}
            <path
              d={trackPath}
              fill="none"
              stroke="var(--color-border)"
              strokeWidth="8"
              strokeLinecap="round"
            />

            {/* Fill */}
            {fillPath && (
              <path
                d={fillPath}
                fill="none"
                stroke={getScoreColor(score)}
                strokeWidth="8"
                strokeLinecap="round"
                filter="url(#glow)"
                style={{ transition: "stroke 0.4s ease" }}
              />
            )}

            {/* Score number */}
            <text
              x="60" y="56"
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize="22"
              fontWeight="500"
              fontFamily="var(--font-mono)"
              fill={trustScore !== null ? getScoreColor(score) : "var(--color-text-muted)"}
            >
              {trustScore !== null ? displayed : "—"}
            </text>

            {/* "/100" label */}
            <text
              x="60" y="74"
              textAnchor="middle"
              fontSize="9"
              fontFamily="var(--font-mono)"
              fill="var(--color-text-muted)"
            >
              {trustScore !== null ? "/ 100" : "pending"}
            </text>
          </svg>
        </div>

        {/* Risk badge + description */}
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

          {trustScore !== null && (
            <p className="text-xs text-text-secondary leading-relaxed">
              {score >= 75
                ? "This response appears well-grounded. Claims are largely supported by evidence."
                : score >= 45
                ? "Some claims may be uncertain or only partially supported. Review flagged items."
                : "Significant hallucination risk detected. Multiple claims lack evidence support."}
            </p>
          )}
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
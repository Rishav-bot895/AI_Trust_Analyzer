"use client";

// ── Base shimmer block ────────────────────────────────────────
function Shimmer({ className = "", style }: { className?: string; style?: React.CSSProperties }) {

  return (
    <div
      className={`rounded ${className}`}
      style={{
        ...style,
        background: "linear-gradient(90deg, var(--color-surface-high) 25%, var(--color-border) 50%, var(--color-surface-high) 75%)",
        backgroundSize: "200% 100%",
        animation: "shimmer 1.6s infinite linear",
      }}
    />
  );
}

// ── TrustScoreCard skeleton ───────────────────────────────────
export function TrustScoreCardSkeleton() {
  return (
    <div className="card p-6 space-y-6">
      <Shimmer className="h-3 w-24" />

      <div className="flex items-center gap-8">
        {/* Gauge circle */}
        <div
          className="w-[120px] h-[120px] rounded-full flex-shrink-0"
          style={{
            background: "linear-gradient(90deg, var(--color-surface-high) 25%, var(--color-border) 50%, var(--color-surface-high) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.6s infinite linear",
          }}
        />
        <div className="space-y-3 flex-1">
          <Shimmer className="h-7 w-32" />
          <Shimmer className="h-3 w-full" />
          <Shimmer className="h-3 w-3/4" />
        </div>
      </div>

      <div className="space-y-2">
        <Shimmer className="h-3 w-16" />
        <Shimmer className="h-3 w-full" />
        <Shimmer className="h-3 w-5/6" />
      </div>
    </div>
  );
}

// ── ClaimsTable skeleton ──────────────────────────────────────
export function ClaimsTableSkeleton() {
  return (
    <div className="card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <Shimmer className="h-3 w-20" />
        <div className="flex gap-2">
          <Shimmer className="h-6 w-12 rounded-full" />
          <Shimmer className="h-6 w-20 rounded-full" />
          <Shimmer className="h-6 w-24 rounded-full" />
        </div>
      </div>

      <div className="space-y-2">
        {[90, 75, 85, 60, 80].map((w, i) => (
          <div key={i} className="rounded-md border border-border p-3 flex items-center gap-3">
            <Shimmer className="h-3 w-4 flex-shrink-0" />
            <Shimmer className={`h-3 flex-1`} style={{ width: `${w}%` } as React.CSSProperties} />
            <Shimmer className="h-5 w-20 rounded flex-shrink-0" />
            <Shimmer className="h-1 w-16 flex-shrink-0" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── EvidencePanel skeleton ────────────────────────────────────
export function EvidencePanelSkeleton() {
  return (
    <div className="card p-6 space-y-4">
      <Shimmer className="h-3 w-20" />

      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-md border border-border bg-surface-high p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex gap-2">
                <Shimmer className="h-5 w-14 rounded" />
                <Shimmer className="h-5 w-16 rounded" />
              </div>
              <Shimmer className="h-2 w-20 rounded-full" />
            </div>
            <Shimmer className="h-3 w-full" />
            <Shimmer className="h-3 w-4/5" />
            <Shimmer className="h-3 w-32" />
          </div>
        ))}
      </div>
    </div>
  );
}

// ── AgentTimeline skeleton ────────────────────────────────────
export function AgentTimelineSkeleton() {
  return (
    <div className="card p-6 space-y-4">
      <Shimmer className="h-3 w-28" />

      <div className="relative space-y-2">
        <div
          className="absolute left-[19px] top-6 bottom-6 w-px"
          style={{ background: "var(--color-border)" }}
        />
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="flex gap-4">
            <div
              className="w-10 h-10 rounded-full flex-shrink-0"
              style={{
                background: "linear-gradient(90deg, var(--color-surface-high) 25%, var(--color-border) 50%, var(--color-surface-high) 75%)",
                backgroundSize: "200% 100%",
                animation: "shimmer 1.6s infinite linear",
              }}
            />
            <div className="flex-1 rounded-md border border-border bg-surface-high p-3 space-y-2 mb-2">
              <div className="flex justify-between">
                <Shimmer className="h-3 w-28" />
                <Shimmer className="h-5 w-12 rounded" />
              </div>
              <Shimmer className="h-3 w-full" />
              <Shimmer className="h-3 w-3/4" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Stat row skeleton (Results tab) ──────────────────────────
export function StatRowSkeleton() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {[1, 2, 3, 4].map((i) => (
        <div key={i} className="card-high p-3 space-y-2">
          <Shimmer className="h-2 w-16" />
          <Shimmer className="h-7 w-10" />
        </div>
      ))}
    </div>
  );
}

// ── Full results skeleton (shown while polling) ───────────────
export function ResultsSkeleton() {
  return (
    <div className="w-full space-y-4">
      <TrustScoreCardSkeleton />
      <div className="card overflow-hidden">
        {/* Tab bar shimmer */}
        <div className="flex gap-1 px-2 pt-2 border-b border-border">
          {[80, 70, 80, 72, 76].map((w, i) => (
            <Shimmer key={i} className="h-8 rounded-t mb-0" style={{ width: w } as React.CSSProperties} />
          ))}
        </div>
        <div className="p-4 space-y-4">
          <StatRowSkeleton />
        </div>
      </div>
    </div>
  );
}

// ── Global shimmer keyframe ───────────────────────────────────
export function ShimmerStyles() {
  return (
    <style>{`
      @keyframes shimmer {
        0%   { background-position: 200% 0; }
        100% { background-position: -200% 0; }
      }
    `}</style>
  );
}
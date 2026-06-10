"use client";

import type { CSSProperties } from "react";

interface SkeletonProps {
  width?: number | string;
  height?: number | string;
  className?: string;
}

function dimension(value: number | string | undefined): number | string | undefined {
  return typeof value === "number" ? `${value}px` : value;
}

export function Skeleton({ width, height, className = "" }: SkeletonProps) {
  const style: CSSProperties = {
    width: dimension(width),
    height: dimension(height),
  };

  return (
    <div
      aria-hidden="true"
      data-testid="skeleton"
      className={`animate-pulse rounded bg-surface-high ${className}`.trim()}
      style={style}
    />
  );
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <article
      aria-label="evidence-card-skeleton"
      className={`rounded-md border border-border bg-surface-high p-4 ${className}`.trim()}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="flex gap-2">
          <Skeleton width={56} height={22} />
          <Skeleton width={78} height={22} />
        </div>
        <Skeleton width={96} height={22} />
      </div>
      <div className="mt-4 space-y-2">
        <Skeleton width="100%" height={14} />
        <Skeleton width="86%" height={14} />
        <Skeleton width="64%" height={14} />
      </div>
      <Skeleton width={180} height={14} className="mt-4" />
    </article>
  );
}

export function SkeletonRow({ className = "" }: { className?: string }) {
  return (
    <div
      aria-label="claim-row-skeleton"
      className={`grid grid-cols-[56px_1fr_180px_180px] items-center gap-3 border-b border-border px-4 py-3 last:border-b-0 ${className}`.trim()}
    >
      <Skeleton width={18} height={14} />
      <Skeleton width="100%" height={16} />
      <Skeleton width={94} height={22} />
      <div className="flex items-center gap-2">
        <Skeleton width={96} height={6} className="rounded-full" />
        <Skeleton width={34} height={14} />
      </div>
    </div>
  );
}

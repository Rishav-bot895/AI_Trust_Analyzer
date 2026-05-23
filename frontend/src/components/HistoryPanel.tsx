"use client";

import type { AnalysisListItem } from "../types/api";

interface HistoryPanelProps {
  history: AnalysisListItem[];
  isLoading: boolean;
  error: string | null;
  onReload: () => void;
}

export function HistoryPanel({ history, isLoading, error, onReload }: HistoryPanelProps) {
  return (
    <section className="w-full rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-700 dark:bg-zinc-900">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Authenticated History</h2>
        <button
          type="button"
          onClick={onReload}
          className="rounded-lg border border-zinc-300 px-3 py-1 text-sm font-medium text-zinc-700 hover:bg-zinc-100 dark:border-zinc-600 dark:text-zinc-200 dark:hover:bg-zinc-800"
        >
          Refresh
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-zinc-500">Loading history...</p>
      ) : null}

      {error ? (
        <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
      ) : null}

      {!isLoading && !error && history.length === 0 ? (
        <p className="text-sm text-zinc-500">No authenticated history yet.</p>
      ) : null}

      {!isLoading && !error && history.length > 0 ? (
        <ul className="space-y-2">
          {history.map((item) => (
            <li
              key={item.id}
              className="rounded-xl border border-zinc-200 px-3 py-2 text-sm dark:border-zinc-700"
            >
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-medium text-zinc-800 dark:text-zinc-100">{item.status}</span>
                <span className="text-zinc-500">{item.trustScore ?? "N/A"}</span>
                <span className="text-zinc-500">{item.hallucinationRisk ?? "UNKNOWN"}</span>
              </div>
              <p className="mt-1 break-all text-xs text-zinc-500">{item.id}</p>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

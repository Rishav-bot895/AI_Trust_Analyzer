"use client";

import { useCallback, useEffect, useState } from "react";

import { getAnalysisHistory } from "../lib/api-client";
import type { AnalysisListItem } from "../types/api";

interface UseHistoryState {
  history: AnalysisListItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useHistory(enabled: boolean, authToken: string | null): UseHistoryState {
  const [history, setHistory] = useState<AnalysisListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    if (!enabled) {
      setHistory([]);
      setError(null);
      setIsLoading(false);
      return;
    }

    try {
      const items = await getAnalysisHistory(authToken, { limit: 10, offset: 0 });
      setHistory(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history.");
      setHistory([]);
    } finally {
      setIsLoading(false);
    }
  }, [authToken, enabled]);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  return { history, isLoading, error, reload };
}

"use client";

import { useCallback, useEffect, useState } from "react";

import { getAuthenticatedHistory } from "../lib/api-client";
import type { AnalysisListItem } from "../types/api";

interface UseHistoryState {
  history: AnalysisListItem[];
  isLoading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

export function useHistory(authToken: string | null): UseHistoryState {
  const [history, setHistory] = useState<AnalysisListItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    if (!authToken) {
      setHistory([]);
      setError(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const items = await getAuthenticatedHistory(authToken, { limit: 10, offset: 0 });
      setHistory(items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load history.");
      setHistory([]);
    } finally {
      setIsLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    queueMicrotask(() => {
      void reload();
    });
  }, [reload]);

  return { history, isLoading, error, reload };
}

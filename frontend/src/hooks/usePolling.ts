"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { getAnalysis } from "../lib/api-client";
import type { AnalysisResponse, AnalysisStatus } from "../types/api";

const TERMINAL_STATUSES: AnalysisStatus[] = ["COMPLETED", "FAILED"];

export interface UsePollingState {
  analysis: AnalysisResponse | null;
  status: AnalysisStatus | null;
  error: string | null;
  isPolling: boolean;
  startPolling: () => void;
  stopPolling: () => void;
  clear: () => void;
}

export function usePolling(analysisId: string | null, intervalMs: number): UsePollingState {
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [status, setStatus] = useState<AnalysisStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const timerRef = useRef<number | null>(null);

  const stopPolling = useCallback(() => {
    setIsPolling(false);
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const clear = useCallback(() => {
    stopPolling();
    setAnalysis(null);
    setStatus(null);
    setError(null);
  }, [stopPolling]);

  const pollOnce = useCallback(async (): Promise<boolean> => {
    if (!analysisId) {
      stopPolling();
      return true;
    }

    try {
      const next = await getAnalysis(analysisId);
      setAnalysis(next);
      setStatus(next.status);
      setError(null);

      if (TERMINAL_STATUSES.includes(next.status)) {
        stopPolling();
        return true;
      }

      return false;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Polling failed.");
      stopPolling();
      return true;
    }
  }, [analysisId, stopPolling]);

  const startPolling = useCallback(() => {
    setError(null);
    setIsPolling(true);
  }, []);

  useEffect(() => {
    if (!analysisId || !isPolling) {
      return;
    }

    let cancelled = false;

    const tick = async () => {
      if (cancelled) {
        return;
      }

      const done = await pollOnce();
      if (!cancelled && !done) {
        timerRef.current = window.setTimeout(tick, intervalMs);
      }
    };

    timerRef.current = window.setTimeout(tick, intervalMs);

    return () => {
      cancelled = true;
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [analysisId, intervalMs, isPolling, pollOnce]);

  useEffect(() => {
    if (!analysisId) {
      queueMicrotask(() => {
        stopPolling();
        setAnalysis(null);
        setStatus(null);
        setError(null);
      });
    }
  }, [analysisId, stopPolling]);

  return {
    analysis,
    status,
    error,
    isPolling,
    startPolling,
    stopPolling,
    clear,
  };
}

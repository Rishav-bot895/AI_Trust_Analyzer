"use client";

import { useCallback, useEffect, useState } from "react";
import { submitAnalysis } from "../lib/api-client";
import { getStoredUserMode } from "../lib/auth";
import {
  getOrCreateGuestSessionId,
  initializeGuestSession,
  registerGuestSessionLifecycle,
} from "../lib/guest-session";
import { usePolling } from "./usePolling";
import type { AnalysisRequest, AnalysisResponse, UserMode } from "../types/api";

// ── useAnalysis ───────────────────────────────────────────────
// Submits an analysis request and polls until terminal state.

type Phase = "idle" | "submitting" | "polling" | "done" | "error";

interface UseAnalysisState {
  phase: Phase;
  analysisId: string | null;
  result: AnalysisResponse | null;
  error: string | null;
  submit: (request: AnalysisRequest) => Promise<void>;
  reset: () => void;
}

export function useAnalysis(): UseAnalysisState {
  const [phase, setPhase] = useState<Phase>("idle");
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<UserMode | null>(() => getStoredUserMode());
  const polling = usePolling(analysisId, 2500);

  useEffect(() => {
    if (activeMode !== "GUEST") {
      return;
    }

    return registerGuestSessionLifecycle();
  }, [activeMode]);

  useEffect(() => {
    if (polling.analysis) {
      queueMicrotask(() => {
        setResult(polling.analysis);
        if (polling.status === "FAILED") {
          setPhase("error");
          setError(polling.analysis?.error ?? "Analysis failed.");
        } else if (polling.status === "COMPLETED") {
          setPhase("done");
          setError(null);
        }
      });
    }
  }, [polling.analysis, polling.status]);

  useEffect(() => {
    if (!polling.error) {
      return;
    }

    if (phase === "polling" || phase === "submitting") {
      queueMicrotask(() => {
        setPhase("error");
        setError(polling.error);
      });
    }
  }, [phase, polling.error]);

  const submit = useCallback(async (request: AnalysisRequest) => {
    setPhase("submitting");
    setError(null);
    setResult(null);
    setAnalysisId(null);
    polling.clear();
    setActiveMode(request.userMode);

    try {
      let payload = request;
      if (request.userMode === "GUEST" && !request.guestSessionId) {
        const guestSessionId =
          (await initializeGuestSession()) ?? getOrCreateGuestSessionId();
        payload = {
          ...request,
          guestSessionId: guestSessionId ?? undefined,
        };
      }

      const { id } = await submitAnalysis(payload);
      setAnalysisId(id);
      setPhase("polling");
      polling.startPolling();
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : "Submission failed.");
    }
  }, [polling]);

  const reset = useCallback(() => {
    polling.clear();
    setPhase("idle");
    setAnalysisId(null);
    setResult(null);
    setError(null);
  }, [polling]);

  return { phase, analysisId, result, error, submit, reset };
}

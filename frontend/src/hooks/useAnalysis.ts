"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { submitAnalysis, getAnalysis } from "../lib/api-client";
import type { AnalysisRequest, AnalysisResponse, AnalysisStatus } from "../types/api";

// ── usePolling ────────────────────────────────────────────────
// Repeatedly calls `fn` every `intervalMs` while `active` is true.
// Stops automatically when the component unmounts.

interface UsePollingOptions {
  intervalMs?: number;
  active: boolean;
}

export function usePolling(fn: () => Promise<void>, { intervalMs = 2500, active }: UsePollingOptions) {
  const fnRef = useRef(fn);
  fnRef.current = fn; // always call the latest version without restarting the timer

  useEffect(() => {
    if (!active) return;

    let cancelled = false;

    const tick = async () => {
      if (cancelled) return;
      await fnRef.current();
      if (!cancelled) {
        timeoutId = window.setTimeout(tick, intervalMs);
      }
    };

    let timeoutId = window.setTimeout(tick, intervalMs);

    return () => {
      cancelled = true;
      clearTimeout(timeoutId);
    };
  }, [active, intervalMs]);
}

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

const TERMINAL: AnalysisStatus[] = ["COMPLETED", "FAILED"];

// The backend returns snake_case — normalise to our camelCase types
function normaliseAnalysis(raw: Record<string, unknown>): AnalysisResponse {
  return {
    id:               String(raw.id ?? ""),
    status:           (raw.status ?? "PENDING") as AnalysisStatus,
    trustScore:       (raw.trust_score ?? raw.trustScore ?? null) as number | null,
    hallucinationRisk:(raw.hallucination_risk ?? raw.hallucinationRisk ?? null) as AnalysisResponse["hallucinationRisk"],
    claims:           (raw.claims ?? []) as AnalysisResponse["claims"],
    evidence:         (raw.evidence ?? []) as AnalysisResponse["evidence"],
    critique:         (raw.critique ?? null) as string | null,
    verdict:          (raw.verdict ?? null) as string | null,
    createdAt:        String(raw.created_at ?? raw.createdAt ?? ""),
    completedAt:      (raw.completed_at ?? raw.completedAt ?? null) as string | null,
    error:            (raw.error ?? null) as string | null,
    timeline:         (raw.timeline ?? []) as AnalysisResponse["timeline"],
  };
}

export function useAnalysis(): UseAnalysisState {
  const [phase, setPhase]         = useState<Phase>("idle");
  const [analysisId, setAnalysisId] = useState<string | null>(null);
  const [result, setResult]       = useState<AnalysisResponse | null>(null);
  const [error, setError]         = useState<string | null>(null);

  // Poll while we have an ID and haven't reached a terminal state
  const shouldPoll = phase === "polling" && analysisId !== null;

  const poll = useCallback(async () => {
    if (!analysisId) return;
    try {
      const raw = await getAnalysis(analysisId) as unknown as Record<string, unknown>;
      const data = normaliseAnalysis(raw);
      setResult(data);
      if (TERMINAL.includes(data.status)) {
        setPhase(data.status === "FAILED" ? "error" : "done");
        if (data.status === "FAILED") {
          setError(data.error ?? "Analysis failed.");
        }
      }
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : "Polling failed.");
    }
  }, [analysisId]);

  usePolling(poll, { active: shouldPoll, intervalMs: 2500 });

  const submit = useCallback(async (request: AnalysisRequest) => {
    setPhase("submitting");
    setError(null);
    setResult(null);
    setAnalysisId(null);
    try {
      const { id } = await submitAnalysis(request);
      setAnalysisId(id);
      setPhase("polling");
    } catch (err) {
      setPhase("error");
      setError(err instanceof Error ? err.message : "Submission failed.");
    }
  }, []);

  const reset = useCallback(() => {
    setPhase("idle");
    setAnalysisId(null);
    setResult(null);
    setError(null);
  }, []);

  return { phase, analysisId, result, error, submit, reset };
}
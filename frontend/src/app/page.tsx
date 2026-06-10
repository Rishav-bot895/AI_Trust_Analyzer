"use client";

import { useEffect, useState } from "react";
import { AnalysisInputForm } from "../components/AnalysisInputForm";
import { ResultsView } from "../components/ResultsView";
import { useAnalysis } from "../hooks/useAnalysis";
import { compareModels } from "../lib/api-client";
import { initializeGuestSession, registerGuestSessionLifecycle } from "../lib/guest-session";
import type { AnalysisRequest, ComparisonResponse } from "../types/api";
import { ResultsSkeleton, ShimmerStyles } from "../components/SkeletonLoader";

const COMPARISON_MODELS = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet"];

type AppState = "idle" | "analyzing" | "done" | "error";

export default function Home() {
  const { phase, result, error, submit, reset } = useAnalysis();
  const [comparison, setComparison]             = useState<ComparisonResponse | null>(null);
  const [appState, setAppState]                 = useState<AppState>("idle");

  // Guest session lifecycle
  useEffect(() => {
    void initializeGuestSession();
    return registerGuestSessionLifecycle();
  }, []);

  // Mirror analysis phase → appState
  useEffect(() => {
    if (phase === "idle")                          setAppState("idle");
    else if (phase === "submitting" || phase === "polling") setAppState("analyzing");
    else if (phase === "done")                     setAppState("done");
    else if (phase === "error")                    setAppState("error");
  }, [phase]);

  async function handleSubmit(request: AnalysisRequest) {
    setComparison(null);
    await submit(request);

    // Fire off a comparison in the background once the main analysis completes
    try {
      const comp = await compareModels({
        prompt:   request.prompt,
        response: request.response,
        models:   COMPARISON_MODELS,
      });
      setComparison(comp);
    } catch {
      // Comparison is non-critical — silently ignore failures
    }
  }

  const isLoading = appState === "analyzing";

  return (
    <div className="flex flex-col min-h-screen">

      {/* ── Header ─────────────────────────────────────────── */}
      <header className="border-b border-border bg-surface-raised/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-7 h-7 rounded flex items-center justify-center text-sm"
              style={{ background: "var(--color-accent-glow)", border: "1px solid var(--color-accent-dim)", color: "var(--color-accent)" }}
            >
              ⬡
            </div>
            <span
              className="text-lg"
              style={{ fontFamily: "var(--font-serif)", color: "var(--color-text-primary)" }}
            >
              AI Trust Analyzer
            </span>
          </div>

          {appState !== "idle" && (
            <button
              type="button"
              onClick={() => { reset(); setComparison(null); }}
              className="text-xs text-text-secondary border border-border px-3 py-1.5 rounded
                         hover:border-accent hover:text-accent transition-colors"
            >
              ← New Analysis
            </button>
          )}
        </div>
      </header>

      {/* ── Main ───────────────────────────────────────────── */}
      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8 space-y-6">

        {/* Idle: hero + form */}
        {appState === "idle" && (
          <div className="space-y-8">
            {/* Hero */}
            <div className="text-center space-y-3 pt-6">
              <p className="label tracking-widest">Hallucination Detection</p>
              <h1
                className="text-4xl sm:text-5xl text-text-primary leading-tight"
                style={{ fontFamily: "var(--font-serif)" }}
              >
                Can you trust<br />
                <span style={{ color: "var(--color-accent)" }}>this AI response?</span>
              </h1>
              <p className="text-text-secondary text-sm max-w-md mx-auto leading-relaxed">
                Paste any AI-generated response and we'll extract every claim,
                find supporting or contradicting evidence, and give you a trust score.
              </p>
            </div>

            <AnalysisInputForm onSubmit={handleSubmit} isLoading={isLoading} />
          </div>
        )}

        {/* Analyzing: form stays visible with loading state + progress indicator */}
        {appState === "analyzing" && (
            <div className="space-y-6">
              <AnalysisInputForm onSubmit={handleSubmit} isLoading={true} />
              <ResultsSkeleton />
              <ShimmerStyles />
            </div>
          )}

             
        {/* Error state */}
        {appState === "error" && (
          <div className="space-y-4">
            <div
              className="card p-6 space-y-3"
              style={{ borderColor: "rgba(239,68,68,0.3)" }}
            >
              <p className="label" style={{ color: "var(--color-refuted)" }}>Analysis Failed</p>
              <p className="text-sm text-text-secondary">{error ?? "An unexpected error occurred."}</p>
              <button
                type="button"
                onClick={() => { reset(); setComparison(null); }}
                className="text-xs border border-border px-3 py-1.5 rounded
                           hover:border-accent hover:text-accent transition-colors text-text-secondary"
              >
                ← Try Again
              </button>
            </div>
          </div>
        )}

        {/* Done: results */}
        {appState === "done" && result && (
          <ResultsView
            result={result}
            comparison={comparison ?? undefined}
            comparisonModels={COMPARISON_MODELS}
          />
        )}
      </main>

      {/* ── Footer ─────────────────────────────────────────── */}
      <footer className="border-t border-border py-4 px-4">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <p className="text-xs text-text-muted">AI Trust Analyzer</p>
          <p className="text-xs text-text-muted">
            Results are probabilistic — always verify critical information independently.
          </p>
        </div>
      </footer>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: 0.35; }
        }
      `}</style>
    </div>
  );
}

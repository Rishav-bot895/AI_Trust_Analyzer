"use client";

import { useEffect, useState } from "react";
import { AnalysisInputForm } from "../components/AnalysisInputForm";
import { AuthGate } from "../components/AuthGate";
import { BackendWakeUpScreen } from "../components/BackendWakeUpScreen";
import { ResultsView } from "../components/ResultsView";
import { ResultsSkeleton, ShimmerStyles } from "../components/SkeletonLoader";
import { useAnalysis } from "../hooks/useAnalysis";
import { useBackendHealth } from "../hooks/useBackendHealth";
import {
  clearStoredAuthToken,
  clearStoredUserMode,
  getStoredAuthToken,
  getStoredUserMode,
  setStoredAuthToken,
  setStoredUserMode,
} from "../lib/auth";
import { clearGuestSession, initializeGuestSession } from "../lib/guest-session";
import type { AnalysisRequest, UserMode } from "../types/api";

const WAKE_SCREEN_DELAY_MS = 2000;

type AppState = "idle" | "analyzing" | "done" | "error";

function getAppState(phase: ReturnType<typeof useAnalysis>["phase"]): AppState {
  if (phase === "submitting" || phase === "polling") return "analyzing";
  if (phase === "done") return "done";
  if (phase === "error") return "error";
  return "idle";
}

export default function Home() {
  const { phase, result, error, submit, reset } = useAnalysis();
  const [selectedMode, setSelectedMode] = useState<UserMode | null>(() => getStoredUserMode());
  const [authToken, setAuthToken] = useState<string | null>(() => getStoredAuthToken());
  const [showWakeScreen, setShowWakeScreen] = useState(false);
  const [backendGateDone, setBackendGateDone] = useState(false);
  const [guestSessionReady, setGuestSessionReady] = useState(() => {
    const storedMode = getStoredUserMode();
    const storedToken = getStoredAuthToken();
    return storedMode !== "GUEST" && !(storedMode === "AUTHENTICATED" && storedToken?.startsWith("local:"));
  });

  const modeReady = selectedMode === "GUEST" || (selectedMode === "AUTHENTICATED" && Boolean(authToken));
  const { isHealthy } = useBackendHealth(modeReady);
  const appState = getAppState(phase);
  const backendReady = backendGateDone || (isHealthy && !showWakeScreen);
  const requiresGuestTransport = selectedMode === "AUTHENTICATED" && authToken?.startsWith("local:");
  const appReady = modeReady && backendReady && (!requiresGuestTransport || guestSessionReady) && guestSessionReady;
  const isLoading = appState === "analyzing";

  useEffect(() => {
    if (!modeReady || isHealthy || showWakeScreen) return;

    const timerId = window.setTimeout(() => {
      setShowWakeScreen(true);
    }, WAKE_SCREEN_DELAY_MS);

    return () => window.clearTimeout(timerId);
  }, [isHealthy, modeReady, showWakeScreen]);

  useEffect(() => {
    if (selectedMode !== "GUEST" || !backendReady) {
      return;
    }

    let cancelled = false;

    const prepareGuestSession = async () => {
      await initializeGuestSession();
      if (!cancelled) {
        setGuestSessionReady(true);
      }
    };

    void prepareGuestSession();

    return () => {
      cancelled = true;
    };
  }, [backendReady, selectedMode]);

  useEffect(() => {
    if (selectedMode !== "AUTHENTICATED" || !authToken?.startsWith("local:") || guestSessionReady) {
      return;
    }

    let cancelled = false;

    const prepareLocalTransport = async () => {
      await initializeGuestSession();
      if (!cancelled) {
        setGuestSessionReady(true);
      }
    };

    void prepareLocalTransport();

    return () => {
      cancelled = true;
    };
  }, [authToken, guestSessionReady, selectedMode]);

  async function handleAuthenticatedContinue(token: string) {
    clearStoredUserMode();
    clearStoredAuthToken();
    clearGuestSession();
    setStoredUserMode("AUTHENTICATED");
    setStoredAuthToken(token);
    setSelectedMode("AUTHENTICATED");
    setAuthToken(token);
    setShowWakeScreen(false);
    setBackendGateDone(false);
    setGuestSessionReady(!token.startsWith("local:"));
    reset();
  }

  async function handleGuestContinue() {
    clearStoredUserMode();
    clearStoredAuthToken();
    clearGuestSession();
    setStoredUserMode("GUEST");
    setSelectedMode("GUEST");
    setAuthToken(null);
    setShowWakeScreen(false);
    setBackendGateDone(false);
    setGuestSessionReady(false);
    reset();
  }

  async function handleSubmit(request: AnalysisRequest) {
    await submit(request);
  }

  if (!selectedMode || (selectedMode === "AUTHENTICATED" && !authToken)) {
    return <AuthGate isLoading={false} onAuthenticated={handleAuthenticatedContinue} onGuest={handleGuestContinue} />;
  }

  if (!appReady) {
    if (showWakeScreen) {
      return <BackendWakeUpScreen isHealthy={isHealthy} onComplete={() => setBackendGateDone(true)} />;
    }

    return <main className="min-h-screen bg-surface" aria-label="Checking backend readiness" />;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-50 border-b border-border bg-surface-raised/80 backdrop-blur-sm">
        <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
          <div className="flex items-center gap-3">
            <div
              className="flex h-7 w-7 items-center justify-center rounded text-[11px] font-semibold"
              style={{ background: "var(--color-accent-glow)", border: "1px solid var(--color-accent-dim)", color: "var(--color-accent)" }}
            >
              AI
            </div>
            <span className="text-lg" style={{ fontFamily: "var(--font-serif)", color: "var(--color-text-primary)" }}>
              AI Trust Analyzer
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs text-text-muted">
            <span className="rounded-full border border-border px-3 py-1 uppercase tracking-[0.18em]">
              {selectedMode === "AUTHENTICATED" ? "Authenticated" : "Guest"}
            </span>

            <button
              type="button"
              onClick={() => {
                clearStoredUserMode();
                clearStoredAuthToken();
                clearGuestSession();
                reset();
                setShowWakeScreen(false);
                setBackendGateDone(false);
                setGuestSessionReady(false);
                setSelectedMode(null);
                setAuthToken(null);
              }}
              className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
            >
              Change mode
            </button>

            {appState !== "idle" ? (
              <button
                type="button"
                onClick={() => {
                  reset();
                }}
                className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
              >
                New Analysis
              </button>
            ) : null}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 space-y-6 px-4 py-8">
        {appState === "idle" && (
          <div className="space-y-8">
            <div className="space-y-3 pt-6 text-center">
              <p className="label tracking-widest">Hallucination Detection</p>
              <h1 className="text-4xl leading-tight text-text-primary sm:text-5xl" style={{ fontFamily: "var(--font-serif)" }}>
                Can you trust<br />
                <span style={{ color: "var(--color-accent)" }}>this AI response?</span>
              </h1>
              <p className="mx-auto max-w-md text-sm leading-relaxed text-text-secondary">
                Paste any AI-generated response and we&apos;ll extract every claim, find supporting or contradicting evidence, and give you a trust score.
              </p>
            </div>

            <AnalysisInputForm onSubmit={handleSubmit} isLoading={isLoading} userMode={selectedMode} />
          </div>
        )}

        {appState === "analyzing" && (
          <div className="space-y-6">
            <AnalysisInputForm onSubmit={handleSubmit} isLoading={true} userMode={selectedMode} />
            <ResultsSkeleton />
            <ShimmerStyles />
          </div>
        )}

        {appState === "error" && (
          <div className="space-y-4">
            <div className="card space-y-3 p-6" style={{ borderColor: "rgba(239,68,68,0.3)" }}>
              <p className="label" style={{ color: "var(--color-refuted)" }}>
                Analysis Failed
              </p>
              <p className="text-sm text-text-secondary">{error ?? "An unexpected error occurred."}</p>
              <button
                type="button"
                onClick={() => {
                  reset();
                }}
                className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {appState === "done" && result ? (
          <section className="results-slide-in" aria-label="Analysis results">
            <ResultsView
              result={result}
              showHistoryTab={Boolean(selectedMode)}
              authToken={authToken}
            />
          </section>
        ) : null}
      </main>

      <footer className="border-t border-border px-4 py-4">
        <div className="mx-auto flex max-w-4xl items-center justify-between gap-4">
          <p className="text-xs text-text-muted">AI Trust Analyzer</p>
          <div className="flex items-center gap-4 text-xs text-text-muted">
            <p>Results are probabilistic. Always verify critical information independently.</p>
            <a
              href="https://github.com/Rishav-bot895/AI_Trust_Analyzer"
              target="_blank"
              rel="noopener noreferrer"
              className="text-text-secondary transition-colors hover:text-accent"
            >
              GitHub
            </a>
          </div>
        </div>
      </footer>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.35; }
        }

        @keyframes results-slide-in {
          from {
            opacity: 0;
            transform: translateY(16px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        .results-slide-in {
          animation: results-slide-in 360ms ease-out both;
        }
      `}</style>
    </div>
  );
}

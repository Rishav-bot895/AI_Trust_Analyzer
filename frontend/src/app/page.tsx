"use client";

import { useEffect, useState } from "react";
import { AnalysisInputForm } from "../components/AnalysisInputForm";
import { AuthGate } from "../components/AuthGate";
import { BackendWakeUpScreen } from "../components/BackendWakeUpScreen";
import { ResultsView } from "../components/ResultsView";
import { ResultsSkeleton, ShimmerStyles } from "../components/SkeletonLoader";
import { useAnalysis } from "../hooks/useAnalysis";
import { useBackendHealth } from "../hooks/useBackendHealth";
import { useHistory } from "../hooks/useHistory";
import { compareModels, getAnalysis } from "../lib/api-client";
import {
  clearStoredAuthToken,
  clearStoredUserMode,
  getStoredAuthToken,
  getStoredUserMode,
  setStoredAuthToken,
  setStoredUserMode,
} from "../lib/auth";
import { clearGuestSession, initializeGuestSession } from "../lib/guest-session";
import type { AnalysisListItem, AnalysisRequest, AnalysisResponse, ComparisonResponse, UserMode } from "../types/api";

const COMPARISON_MODELS = ["gpt-4o", "claude-sonnet", "gemini-2.5-pro"];
const WAKE_SCREEN_DELAY_MS = 2000;

type AppState = "idle" | "analyzing" | "done" | "error";

function getAppState(phase: ReturnType<typeof useAnalysis>["phase"]): AppState {
  if (phase === "submitting" || phase === "polling") return "analyzing";
  if (phase === "done") return "done";
  if (phase === "error") return "error";
  return "idle";
}

function formatHistoryDate(value: string | null): string {
  if (!value) return "In progress";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function PreAnalysisHistoryPanel({
  history,
  isLoading,
  error,
  onReload,
  onOpen,
  openingId,
}: {
  history: AnalysisListItem[];
  isLoading: boolean;
  error: string | null;
  onReload: () => Promise<void>;
  onOpen: (analysisId: string) => Promise<void>;
  openingId: string | null;
}) {
  return (
    <section className="card p-5" aria-label="Previous analyses">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="label">History</p>
          <p className="mt-1 text-sm text-text-secondary">Open previous authenticated analyses without starting a new run.</p>
        </div>
        <button
          type="button"
          onClick={() => void onReload()}
          className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
        >
          Refresh
        </button>
      </div>

      {isLoading ? (
        <p className="mt-4 text-sm text-text-muted">Loading history...</p>
      ) : null}

      {error ? (
        <p className="mt-4 text-sm text-refuted">{error}</p>
      ) : null}

      {!isLoading && !error && history.length === 0 ? (
        <p className="mt-4 text-sm text-text-muted">No previous analyses found for this account.</p>
      ) : null}

      {!isLoading && !error && history.length > 0 ? (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-border text-left">
                <th className="pb-2 pr-4"><span className="label">Created</span></th>
                <th className="pb-2 pr-4"><span className="label">Status</span></th>
                <th className="pb-2 pr-4"><span className="label">Score</span></th>
                <th className="pb-2 pr-4"><span className="label">Risk</span></th>
                <th className="pb-2 pr-4"><span className="label">Action</span></th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr key={item.id} className="border-b border-border-subtle last:border-b-0">
                  <td className="py-2 pr-4 text-text-secondary">{formatHistoryDate(item.createdAt)}</td>
                  <td className="py-2 pr-4 text-text-secondary">{item.status}</td>
                  <td className="py-2 pr-4 text-text-primary">{item.trustScore ?? "--"}</td>
                  <td className="py-2 pr-4 text-text-secondary">{item.hallucinationRisk ?? "--"}</td>
                  <td className="py-2 pr-4">
                    <button
                      type="button"
                      onClick={() => void onOpen(item.id)}
                      disabled={openingId === item.id}
                      className="rounded border border-border px-3 py-1 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent disabled:cursor-not-allowed disabled:opacity-60"
                    >
                      {openingId === item.id ? "Opening..." : "Open"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  );
}

export default function Home() {
  const { phase, result, error, submit, reset } = useAnalysis();
  const [isHydrated, setIsHydrated] = useState(false);
  const [selectedMode, setSelectedMode] = useState<UserMode | null>(null);
  const [authToken, setAuthToken] = useState<string | null>(null);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [comparisonError, setComparisonError] = useState<string | null>(null);
  const [isComparisonLoading, setIsComparisonLoading] = useState(false);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [historyResult, setHistoryResult] = useState<AnalysisResponse | null>(null);
  const [historyOpenError, setHistoryOpenError] = useState<string | null>(null);
  const [openingHistoryId, setOpeningHistoryId] = useState<string | null>(null);
  const [showWakeScreen, setShowWakeScreen] = useState(false);
  const [backendGateDone, setBackendGateDone] = useState(false);
  const [guestSessionReady, setGuestSessionReady] = useState(false);

  useEffect(() => {
    queueMicrotask(() => {
      const storedMode = getStoredUserMode();
      const storedToken = getStoredAuthToken();
      setSelectedMode(storedMode);
      setAuthToken(storedToken);
      setGuestSessionReady(storedMode !== "GUEST" && !(storedMode === "AUTHENTICATED" && storedToken?.startsWith("local:")));
      setIsHydrated(true);
    });
  }, []);

  const modeReady = selectedMode === "GUEST" || (selectedMode === "AUTHENTICATED" && Boolean(authToken));
  const { isHealthy } = useBackendHealth(modeReady);
  const appState = getAppState(phase);
  const effectiveAppState = historyResult ? "done" : appState;
  const displayedResult = historyResult ?? result;
  const backendReady = backendGateDone || (isHealthy && !showWakeScreen);
  const requiresGuestTransport = selectedMode === "AUTHENTICATED" && authToken?.startsWith("local:");
  const appReady = modeReady && backendReady && (!requiresGuestTransport || guestSessionReady) && guestSessionReady;
  const isLoading = appState === "analyzing";
  const canViewHistory = selectedMode === "AUTHENTICATED";
  const {
    history: preAnalysisHistory,
    isLoading: isPreAnalysisHistoryLoading,
    error: preAnalysisHistoryError,
    reload: reloadPreAnalysisHistory,
  } = useHistory(appReady && historyPanelOpen && canViewHistory, authToken);

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
    setComparison(null);
    setComparisonError(null);
    setShowWakeScreen(false);
    setBackendGateDone(false);
    setGuestSessionReady(!token.startsWith("local:"));
    reset();
    setHistoryResult(null);
    setHistoryPanelOpen(false);
    setHistoryOpenError(null);
  }

  async function handleGuestContinue() {
    clearStoredUserMode();
    clearStoredAuthToken();
    clearGuestSession();
    setStoredUserMode("GUEST");
    setSelectedMode("GUEST");
    setAuthToken(null);
    setComparison(null);
    setComparisonError(null);
    setShowWakeScreen(false);
    setBackendGateDone(false);
    setGuestSessionReady(false);
    reset();
    setHistoryResult(null);
    setHistoryPanelOpen(false);
    setHistoryOpenError(null);
  }

  async function handleSubmit(request: AnalysisRequest) {
    setComparison(null);
    setComparisonError(null);
    setHistoryResult(null);
    setHistoryOpenError(null);
    await submit(request);
  }

  async function handleRunComparison() {
    if (!result) {
      return;
    }

    setIsComparisonLoading(true);
    setComparisonError(null);

    try {
      const comp = await compareModels({
        prompt: result.prompt ?? "",
        response: result.response ?? "",
        models: COMPARISON_MODELS,
      });
      setComparison(comp);
    } catch (err) {
      setComparisonError(err instanceof Error ? err.message : "Comparison failed.");
    } finally {
      setIsComparisonLoading(false);
    }
  }

  async function handleOpenHistoryAnalysis(analysisId: string) {
    setOpeningHistoryId(analysisId);
    setHistoryOpenError(null);
    setComparison(null);
    setComparisonError(null);

    try {
      const previous = await getAnalysis(analysisId);
      setHistoryResult(previous);
      setHistoryPanelOpen(false);
      reset();
    } catch (err) {
      setHistoryOpenError(err instanceof Error ? err.message : "Failed to open analysis.");
    } finally {
      setOpeningHistoryId(null);
    }
  }

  if (!isHydrated) {
    return <main className="min-h-screen bg-surface" aria-label="Loading application" />;
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
                setComparison(null);
                setComparisonError(null);
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

            {effectiveAppState !== "idle" ? (
              <button
                type="button"
                onClick={() => {
                  reset();
                  setHistoryResult(null);
                  setComparison(null);
                  setComparisonError(null);
                  setHistoryOpenError(null);
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
        {effectiveAppState === "idle" && (
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

            {canViewHistory ? (
              <div className="flex justify-center">
                <button
                  type="button"
                  onClick={() => {
                    setHistoryPanelOpen((current) => !current);
                    setHistoryOpenError(null);
                  }}
                  className="rounded border border-border px-4 py-2 text-sm text-text-secondary transition-colors hover:border-accent hover:text-accent"
                >
                  {historyPanelOpen ? "Hide history" : "See history"}
                </button>
              </div>
            ) : null}

            {historyPanelOpen && canViewHistory ? (
              <>
                <PreAnalysisHistoryPanel
                  history={preAnalysisHistory}
                  isLoading={isPreAnalysisHistoryLoading}
                  error={preAnalysisHistoryError}
                  onReload={reloadPreAnalysisHistory}
                  onOpen={handleOpenHistoryAnalysis}
                  openingId={openingHistoryId}
                />
                {historyOpenError ? (
                  <p className="text-center text-sm text-refuted">{historyOpenError}</p>
                ) : null}
              </>
            ) : null}

            <AnalysisInputForm onSubmit={handleSubmit} isLoading={isLoading} userMode={selectedMode} />
          </div>
        )}

        {effectiveAppState === "analyzing" && (
          <div className="space-y-6">
            <AnalysisInputForm onSubmit={handleSubmit} isLoading={true} userMode={selectedMode} />
            <ResultsSkeleton />
            <ShimmerStyles />
          </div>
        )}

        {effectiveAppState === "error" && (
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
                  setHistoryResult(null);
                  setComparison(null);
                  setComparisonError(null);
                  setHistoryOpenError(null);
                }}
                className="rounded border border-border px-3 py-1.5 text-xs text-text-secondary transition-colors hover:border-accent hover:text-accent"
              >
                Try Again
              </button>
            </div>
          </div>
        )}

        {effectiveAppState === "done" && displayedResult ? (
          <section className="results-slide-in" aria-label="Analysis results">
            <ResultsView
              result={displayedResult}
              comparison={comparison ?? undefined}
              comparisonModels={COMPARISON_MODELS}
              onRunComparison={handleRunComparison}
              isComparisonLoading={isComparisonLoading}
              comparisonError={comparisonError}
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

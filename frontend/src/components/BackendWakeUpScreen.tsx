"use client";

import { useEffect, useMemo, useRef, useState } from "react";

const BOOT_LOGS = [
  "[OK] Locating idle server...",
  "[OK] Bringing compute workers online...",
  "[OK] Checking service routes...",
  "[OK] Rehydrating application cache...",
  "[OK] Negotiating database connection...",
  "[OK] Loading verification agents...",
  "[OK] Initializing evidence pipeline...",
  "[OK] Connecting to the cloud...",
  "[OK] Running health checks...",
  "[OK] Preparing launch sequence...",
  "[OK] Almost there...",
];

const STATUS_MESSAGES = [
  "Finding the server...",
  "Restoring the runtime...",
  "Waking up the database...",
  "Priming verification agents...",
  "Checking system pulse...",
  "Loading reasoning modules...",
  "Making sure everything still works...",
  "Almost ready for launch...",
];

interface BackendWakeUpScreenProps {
  isHealthy: boolean;
  onComplete: () => void;
}

function getProgressLabel(progress: number): string {
  if (progress < 25) return "Boot sequence started";
  if (progress < 50) return "Systems coming online";
  if (progress < 75) return "Database awakening";
  if (progress < 95) return "Final system checks";
  return "Ready for launch";
}

function getNextProgress(progress: number): number {
  if (progress < 25) return Math.min(progress + 2, 25);
  if (progress < 75) return Math.min(progress + 1, 75);
  if (progress < 95) return Math.min(progress + 0.25, 95);
  return 95;
}

export function BackendWakeUpScreen({ isHealthy, onComplete }: BackendWakeUpScreenProps) {
  const [progress, setProgress] = useState(0);
  const [visibleLogs, setVisibleLogs] = useState(1);
  const [statusIndex, setStatusIndex] = useState(0);
  const [isSuccessful, setIsSuccessful] = useState(false);
  const [isExiting, setIsExiting] = useState(false);
  const logContainerRef = useRef<HTMLDivElement | null>(null);

  const progressLabel = useMemo(() => getProgressLabel(progress), [progress]);

  useEffect(() => {
    if (isHealthy) return;

    const progressId = window.setInterval(() => {
      setProgress((current) => getNextProgress(current));
    }, 700);

    return () => window.clearInterval(progressId);
  }, [isHealthy]);

  useEffect(() => {
    if (isHealthy) return;

    const logId = window.setInterval(() => {
      setVisibleLogs((count) => Math.min(count + 1, BOOT_LOGS.length));
    }, 2500);

    return () => window.clearInterval(logId);
  }, [isHealthy]);

  useEffect(() => {
    if (isHealthy) return;

    const statusId = window.setInterval(() => {
      setStatusIndex((index) => (index + 1) % STATUS_MESSAGES.length);
    }, 3000);

    return () => window.clearInterval(statusId);
  }, [isHealthy]);

  useEffect(() => {
    const container = logContainerRef.current;
    if (!container) return;

    container.scrollTop = container.scrollHeight;
  }, [visibleLogs]);

  useEffect(() => {
    if (!isHealthy) return;

    const successId = window.setTimeout(() => {
      setProgress(100);
      setIsSuccessful(true);
    }, 0);

    const exitId = window.setTimeout(() => {
      setIsExiting(true);
    }, 1000);

    const completeId = window.setTimeout(onComplete, 1400);

    return () => {
      window.clearTimeout(successId);
      window.clearTimeout(exitId);
      window.clearTimeout(completeId);
    };
  }, [isHealthy, onComplete]);

  return (
    <main className={`wake-screen min-h-screen w-full text-text-primary ${isExiting ? "wake-exit" : ""}`}>
      <div className="wake-grid" aria-hidden="true" />

      <section className="relative z-10 mx-auto flex min-h-screen w-full max-w-5xl flex-col justify-center px-4 py-10">
        <div className="space-y-8">
          <div className="space-y-4">
            <p className="label tracking-widest">Startup sequence</p>
            <h1
              className={`wake-title text-4xl leading-tight sm:text-6xl ${isSuccessful ? "wake-success-title" : ""}`}
              style={{ fontFamily: "var(--font-serif)" }}
            >
              {isSuccessful ? "Backend Online" : "Waking up the backend..."}
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-text-secondary">
              {isSuccessful
                ? "All systems operational."
                : "The analysis API is coming back online after an idle period. We will launch the app as soon as the health check passes."}
            </p>
          </div>

          <div className="grid gap-5 lg:grid-cols-[1fr_360px]">
            <div className="space-y-4">
              <div className="wake-progress-frame">
                <div
                  className={`wake-progress-bar ${isSuccessful ? "wake-progress-success" : ""}`}
                  style={{ width: `${progress}%` }}
                />
              </div>

              <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <p className="text-sm text-text-primary">{progressLabel}</p>
                  <p className="wake-status text-xs text-text-secondary" key={statusIndex}>
                    {isSuccessful ? "Ready for launch." : STATUS_MESSAGES[statusIndex]}
                  </p>
                </div>
                <p className="text-2xl text-accent">{Math.round(progress)}%</p>
              </div>
            </div>

            <div className="wake-core" aria-hidden="true">
              <div className={`wake-ring ${isSuccessful ? "wake-ring-success" : ""}`} />
              <div className="wake-ring wake-ring-secondary" />
              <div className="wake-core-center">
                <span>{isSuccessful ? "OK" : "AI"}</span>
              </div>
            </div>
          </div>

          <div className="wake-terminal">
            <div className="wake-terminal-header">
              <span>health-check.log</span>
              <span>{isSuccessful ? "complete" : "polling"}</span>
            </div>
            <div ref={logContainerRef} className="wake-terminal-body" aria-live="polite">
              {BOOT_LOGS.slice(0, visibleLogs).map((log) => (
                <p key={log} className="wake-log-line">
                  {log}
                </p>
              ))}
              {isSuccessful && <p className="wake-log-line wake-log-success">[OK] Backend health confirmed.</p>}
            </div>
          </div>
        </div>
      </section>

      <style jsx>{`
        .wake-screen {
          position: relative;
          overflow: hidden;
          background:
            radial-gradient(circle at 24% 20%, rgba(240, 165, 0, 0.16), transparent 28rem),
            radial-gradient(circle at 80% 75%, rgba(34, 197, 94, 0.1), transparent 24rem),
            #050816;
          opacity: 1;
          transition: opacity 400ms ease, transform 400ms ease;
        }

        .wake-exit {
          opacity: 0;
          transform: translateY(-8px);
        }

        .wake-grid {
          position: absolute;
          inset: 0;
          background-image:
            linear-gradient(rgba(232, 237, 245, 0.04) 1px, transparent 1px),
            linear-gradient(90deg, rgba(232, 237, 245, 0.04) 1px, transparent 1px);
          background-size: 48px 48px;
          mask-image: linear-gradient(to bottom, black, transparent 88%);
        }

        .wake-title {
          color: var(--color-text-primary);
          text-shadow: 0 0 30px rgba(240, 165, 0, 0.28);
          animation: wake-pulse 2.4s ease-in-out infinite;
        }

        .wake-success-title {
          color: var(--color-verified);
          text-shadow: 0 0 30px rgba(34, 197, 94, 0.3);
          animation: none;
        }

        .wake-progress-frame {
          height: 14px;
          overflow: hidden;
          border: 1px solid rgba(240, 165, 0, 0.32);
          border-radius: var(--radius-md);
          background: rgba(10, 14, 26, 0.78);
          box-shadow: inset 0 0 18px rgba(0, 0, 0, 0.35);
        }

        .wake-progress-bar {
          height: 100%;
          min-width: 0.35rem;
          border-radius: inherit;
          background: linear-gradient(90deg, #f59e0b, #f0a500, #facc15);
          box-shadow: 0 0 22px rgba(240, 165, 0, 0.34);
          transition: width 650ms ease;
        }

        .wake-progress-success {
          background: linear-gradient(90deg, #16a34a, #22c55e);
          box-shadow: 0 0 22px rgba(34, 197, 94, 0.35);
        }

        .wake-status {
          animation: wake-fade 450ms ease;
        }

        .wake-core {
          position: relative;
          display: grid;
          min-height: 210px;
          place-items: center;
        }

        .wake-ring {
          position: absolute;
          width: 180px;
          height: 180px;
          border-radius: 999px;
          border: 1px solid rgba(240, 165, 0, 0.38);
          border-top-color: var(--color-accent);
          animation: wake-spin 1.8s linear infinite;
        }

        .wake-ring-secondary {
          width: 132px;
          height: 132px;
          border-color: rgba(232, 237, 245, 0.14);
          border-bottom-color: rgba(232, 237, 245, 0.46);
          animation-direction: reverse;
          animation-duration: 2.6s;
        }

        .wake-ring-success {
          border-color: rgba(34, 197, 94, 0.42);
          border-top-color: var(--color-verified);
        }

        .wake-core-center {
          display: grid;
          width: 82px;
          height: 82px;
          place-items: center;
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          background: rgba(15, 21, 36, 0.92);
          color: var(--color-accent);
          font-size: 1.6rem;
          box-shadow: 0 0 32px rgba(240, 165, 0, 0.18);
        }

        .wake-terminal {
          overflow: hidden;
          border: 1px solid var(--color-border);
          border-radius: var(--radius-md);
          background: rgba(10, 14, 26, 0.84);
          box-shadow: 0 20px 80px rgba(0, 0, 0, 0.26);
        }

        .wake-terminal-header {
          display: flex;
          justify-content: space-between;
          gap: 1rem;
          border-bottom: 1px solid var(--color-border);
          padding: 0.75rem 1rem;
          color: var(--color-text-muted);
          font-size: 0.7rem;
          text-transform: uppercase;
        }

        .wake-terminal-body {
          max-height: 220px;
          overflow-y: auto;
          padding: 1rem;
        }

        .wake-log-line {
          color: var(--color-text-secondary);
          font-size: 0.78rem;
          line-height: 1.85;
          animation: wake-log-in 350ms ease both;
        }

        .wake-log-success {
          color: var(--color-verified);
        }

        @keyframes wake-spin {
          to {
            transform: rotate(360deg);
          }
        }

        @keyframes wake-pulse {
          0%, 100% {
            opacity: 1;
          }
          50% {
            opacity: 0.72;
          }
        }

        @keyframes wake-fade {
          from {
            opacity: 0;
            transform: translateY(4px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes wake-log-in {
          from {
            opacity: 0;
            transform: translateY(8px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </main>
  );
}

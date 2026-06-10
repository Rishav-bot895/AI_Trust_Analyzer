"use client";

import { useMemo, useState } from "react";
import { authenticateLocalAccount } from "../lib/auth";
import { GuestLoginCard } from "./GuestLoginCard";

interface AuthGateProps {
  onAuthenticated: (authToken: string) => Promise<void> | void;
  onGuest: () => Promise<void> | void;
  isLoading?: boolean;
}

type AuthChoice = "LOGIN" | "SIGN_UP";

export function AuthGate({ onAuthenticated, onGuest, isLoading = false }: AuthGateProps) {
  const [choice, setChoice] = useState<AuthChoice>("LOGIN");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const busy = isLoading || isSubmitting;

  const helperText = useMemo(() => {
    if (choice === "LOGIN") {
      return "If the account exists, we'll log you in.";
    }

    return "If the account exists, we'll log you in. Otherwise we'll create it.";
  }, [choice]);

  async function handleSubmit() {
    const trimmedUsername = username.trim();
    const trimmedPassword = password.trim();

    if (!trimmedUsername || !trimmedPassword) {
      setStatusMessage("Enter a username and password to continue.");
      return;
    }

    setIsSubmitting(true);
    setStatusMessage(null);

    try {
      const session = authenticateLocalAccount(trimmedUsername, trimmedPassword, choice);
      setStatusMessage(session.created ? `Account created for ${session.username}.` : `Welcome back, ${session.username}.`);
      await onAuthenticated(session.sessionToken);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Unable to continue.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="relative min-h-[100dvh] overflow-hidden bg-[#050816] text-text-primary">
      <div
        className="absolute inset-0 opacity-80"
        aria-hidden="true"
        style={{
          background:
            "radial-gradient(circle at 18% 20%, rgba(240, 165, 0, 0.18), transparent 0, transparent 28%), radial-gradient(circle at 82% 18%, rgba(34, 197, 94, 0.16), transparent 0, transparent 24%), radial-gradient(circle at 50% 90%, rgba(59, 130, 246, 0.14), transparent 0, transparent 30%), linear-gradient(180deg, rgba(5, 8, 22, 0.98), rgba(10, 14, 26, 1))",
        }}
      />
      <div
        className="absolute inset-0 opacity-35"
        aria-hidden="true"
        style={{
          backgroundImage:
            "linear-gradient(rgba(232, 237, 245, 0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(232, 237, 245, 0.05) 1px, transparent 1px)",
          backgroundSize: "52px 52px",
        }}
      />

      <section className="relative mx-auto grid min-h-[100dvh] w-full max-w-7xl gap-6 px-4 py-4 sm:px-6 sm:py-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-8 lg:py-8">
        <div className="space-y-6 lg:space-y-8">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.24em] text-emerald-300 backdrop-blur-sm">
            <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_18px_rgba(110,231,183,0.7)]" />
            Access gateway
          </div>

          <div className="space-y-4">
            <p className="label tracking-[0.35em] text-emerald-300">AI Trust Analyzer</p>
            <h1
              className="max-w-2xl text-4xl leading-[1.02] text-text-primary sm:text-5xl lg:text-6xl"
              style={{ fontFamily: "var(--font-serif)" }}
            >
              Choose how you want to continue.
            </h1>
            <p className="max-w-2xl text-sm leading-7 text-text-secondary sm:text-base">
              Log in, create an account, or continue as a guest. The screen fills the viewport cleanly on desktop and mobile.
            </p>
          </div>

          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-cyan-300">Login</p>
              <p className="mt-2 text-sm text-text-secondary">Use an existing username and password.</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-amber-300">Sign up</p>
              <p className="mt-2 text-sm text-text-secondary">Create a new account in one step.</p>
            </div>
            <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-4 backdrop-blur-sm">
              <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Guest</p>
              <p className="mt-2 text-sm text-text-secondary">Jump straight into the analyzer.</p>
            </div>
          </div>
        </div>

        <div className="relative">
          <div className="absolute -inset-4 rounded-[2rem] bg-gradient-to-br from-amber-500/10 via-transparent to-emerald-400/10 blur-2xl" aria-hidden="true" />

          <section className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-white/[0.05] p-4 shadow-[0_24px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl sm:p-6">
            <div className="mb-5 flex items-center justify-between gap-3">
              <div>
                <p className="label">Account</p>
                <h2 className="text-2xl text-text-primary" style={{ fontFamily: "var(--font-serif)" }}>
                  Log in or sign up
                </h2>
              </div>
              <div className="rounded-full border border-border bg-surface-raised px-3 py-1 text-[11px] uppercase tracking-[0.18em] text-text-secondary">
                Local session
              </div>
            </div>

            <div className="grid grid-cols-2 rounded-2xl border border-border bg-surface-high p-1 text-sm">
              <button
                type="button"
                onClick={() => {
                  setChoice("LOGIN");
                  setStatusMessage(null);
                }}
                className={`rounded-xl px-4 py-2.5 transition-colors ${choice === "LOGIN" ? "bg-accent text-surface" : "text-text-secondary hover:text-text-primary"}`}
              >
                Log in
              </button>
              <button
                type="button"
                onClick={() => {
                  setChoice("SIGN_UP");
                  setStatusMessage(null);
                }}
                className={`rounded-xl px-4 py-2.5 transition-colors ${choice === "SIGN_UP" ? "bg-accent text-surface" : "text-text-secondary hover:text-text-primary"}`}
              >
                Sign up
              </button>
            </div>

            <div className="mt-5 space-y-4">
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.22em] text-text-muted">Username</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Enter a username"
                  autoComplete="username"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-text-primary outline-none transition focus:border-accent"
                />
              </label>

              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-[0.22em] text-text-muted">Password</span>
                <div className="relative">
                  <input
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    autoComplete={choice === "LOGIN" ? "current-password" : "new-password"}
                    className="w-full rounded-2xl border border-white/10 bg-slate-950/60 px-4 py-3 pr-12 text-sm text-text-primary outline-none transition focus:border-accent"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    className="absolute right-3 top-1/2 inline-flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-full text-text-muted transition-colors hover:bg-white/10 hover:text-text-primary"
                  >
                    {showPassword ? (
                      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M3 3l18 18" />
                        <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8" />
                        <path d="M9.9 5.1A9.9 9.9 0 0 1 12 5c5 0 8.4 4.1 9.5 6.5a11.8 11.8 0 0 1-2.2 3.1" />
                        <path d="M6.6 6.6A13.1 13.1 0 0 0 2.5 11.5C3.6 13.9 7 18 12 18c1.3 0 2.5-.3 3.6-.8" />
                      </svg>
                    ) : (
                      <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M2.5 12s3.5-6.5 9.5-6.5 9.5 6.5 9.5 6.5-3.5 6.5-9.5 6.5S2.5 12 2.5 12Z" />
                        <circle cx="12" cy="12" r="2.5" />
                      </svg>
                    )}
                  </button>
                </div>
              </label>

              <p className="text-xs leading-6 text-text-muted">{helperText}</p>

              <button
                type="button"
                onClick={() => void handleSubmit()}
                disabled={busy}
                className="inline-flex w-full items-center justify-center rounded-2xl bg-cyan-400 px-4 py-3 text-sm font-semibold text-slate-950 transition-transform duration-200 hover:-translate-y-0.5 hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-70"
              >
                {busy ? "Working..." : choice === "LOGIN" ? "Log in" : "Create account"}
              </button>

              {statusMessage ? (
                <p className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-text-secondary">
                  {statusMessage}
                </p>
              ) : null}
            </div>

            <div className="mt-5">
              <GuestLoginCard onContinue={onGuest} isLoading={busy} />
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

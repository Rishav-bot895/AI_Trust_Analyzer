"use client";

interface GuestLoginCardProps {
  onContinue: () => Promise<void> | void;
  isLoading?: boolean;
}

export function GuestLoginCard({ onContinue, isLoading = false }: GuestLoginCardProps) {
  return (
    <section className="flex h-full flex-col rounded-3xl border border-emerald-400/20 bg-emerald-400/5 p-5 shadow-[0_18px_60px_rgba(0,0,0,0.22)] backdrop-blur-sm sm:p-6">
      <div className="space-y-2">
        <p className="label text-[0.72rem] tracking-[0.24em] text-emerald-300">Guest access</p>
        <h3 className="text-xl text-text-primary" style={{ fontFamily: "var(--font-serif)" }}>
          Continue as guest
        </h3>
        <p className="text-sm leading-6 text-text-secondary">No account needed. Launch a private guest session.</p>
      </div>

      <button
        type="button"
        onClick={() => void onContinue()}
        disabled={isLoading}
        className="mt-5 inline-flex w-full items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400 px-4 py-3 text-sm font-semibold text-slate-950 transition-transform duration-200 hover:-translate-y-0.5 hover:bg-emerald-300 disabled:cursor-not-allowed disabled:opacity-70"
      >
        {isLoading ? "Preparing guest session..." : "Continue as guest"}
      </button>
    </section>
  );
}
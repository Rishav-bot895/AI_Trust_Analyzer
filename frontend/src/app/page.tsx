"use client";

import { useEffect } from "react";
import Image from "next/image";
import { useState } from "react";

import { HistoryPanel } from "../components/HistoryPanel";
import { useHistory } from "../hooks/useHistory";
import { initializeGuestSession, registerGuestSessionLifecycle } from "../lib/guest-session";

export default function Home() {
  const [userMode, setUserMode] = useState<"AUTHENTICATED" | "GUEST">("GUEST");
  const [accessToken, setAccessToken] = useState("");
  const { history, isLoading, error, reload } = useHistory(
    userMode === "AUTHENTICATED" ? accessToken : null,
  );

  useEffect(() => {
    void initializeGuestSession();
    return registerGuestSessionLifecycle();
  }, []);

  return (
    <div className="flex flex-col flex-1 items-center justify-center bg-zinc-50 font-sans dark:bg-black">
      <main className="flex flex-1 w-full max-w-3xl flex-col items-center justify-between py-32 px-16 bg-white dark:bg-black sm:items-start">
        <Image
          className="dark:invert"
          src="/next.svg"
          alt="Next.js logo"
          width={100}
          height={20}
          priority
        />
        <div className="flex flex-col items-center gap-6 text-center sm:items-start sm:text-left">
          <h1 className="max-w-xs text-3xl font-semibold leading-10 tracking-tight text-black dark:text-zinc-50">
            To get started, edit the page.tsx file.
          </h1>
          <p className="max-w-md text-lg leading-8 text-zinc-600 dark:text-zinc-400">
            Looking for a starting point or more instructions? Head over to{" "}
            <a
              href="https://vercel.com/templates?framework=next.js&utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Templates
            </a>{" "}
            or the{" "}
            <a
              href="https://nextjs.org/learn?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
              className="font-medium text-zinc-950 dark:text-zinc-50"
            >
              Learning
            </a>{" "}
            center.
          </p>
        </div>
        <div className="flex flex-col gap-4 text-base font-medium sm:flex-row">
          <a
            className="flex h-12 w-full items-center justify-center gap-2 rounded-full bg-foreground px-5 text-background transition-colors hover:bg-[#383838] dark:hover:bg-[#ccc] md:w-[158px]"
            href="https://vercel.com/new?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Image
              className="dark:invert"
              src="/vercel.svg"
              alt="Vercel logomark"
              width={16}
              height={16}
            />
            Deploy Now
          </a>
          <a
            className="flex h-12 w-full items-center justify-center rounded-full border border-solid border-black/[.08] px-5 transition-colors hover:border-transparent hover:bg-black/[.04] dark:border-white/[.145] dark:hover:bg-[#1a1a1a] md:w-[158px]"
            href="https://nextjs.org/docs?utm_source=create-next-app&utm_medium=appdir-template-tw&utm_campaign=create-next-app"
            target="_blank"
            rel="noopener noreferrer"
          >
            Documentation
          </a>
        </div>

        <section className="mt-10 w-full rounded-2xl border border-zinc-200 p-4 dark:border-zinc-700">
          <h2 className="mb-3 text-lg font-semibold">Mode</h2>
          <div className="mb-4 flex gap-2">
            <button
              type="button"
              onClick={() => setUserMode("AUTHENTICATED")}
              className={`rounded-lg px-3 py-1 text-sm ${
                userMode === "AUTHENTICATED"
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "border border-zinc-300"
              }`}
            >
              Authenticated
            </button>
            <button
              type="button"
              onClick={() => setUserMode("GUEST")}
              className={`rounded-lg px-3 py-1 text-sm ${
                userMode === "GUEST"
                  ? "bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900"
                  : "border border-zinc-300"
              }`}
            >
              Guest
            </button>
          </div>

          {userMode === "AUTHENTICATED" ? (
            <div className="space-y-3">
              <label className="block text-sm font-medium">User ID</label>
              <input
                value={accessToken}
                onChange={(event) => setAccessToken(event.target.value)}
                className="w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm"
                placeholder="Paste Bearer token (without the Bearer prefix)"
              />
              <HistoryPanel history={history} isLoading={isLoading} error={error} onReload={() => void reload()} />
            </div>
          ) : (
            <p className="text-sm text-zinc-500">
              Guest mode does not expose history beyond the active session.
            </p>
          )}
        </section>
      </main>
    </div>
  );
}

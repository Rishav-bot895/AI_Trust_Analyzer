import { getStoredUserMode } from "./auth";

const GUEST_SESSION_STORAGE_KEY = "ai_trust_guest_session_id";
const GUEST_SESSION_TOKEN_STORAGE_KEY = "ai_trust_guest_session_token";
const DEFAULT_API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

export function getOrCreateGuestSessionId(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const existing = window.sessionStorage.getItem(GUEST_SESSION_STORAGE_KEY);
  if (existing) {
    return existing;
  }

  return null;
}

function getGuestSessionToken(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }
  return window.sessionStorage.getItem(GUEST_SESSION_TOKEN_STORAGE_KEY);
}

export function getGuestSessionHeaders(): Record<string, string> | null {
  const userMode = getStoredUserMode();
  const authToken = typeof window !== "undefined" ? window.sessionStorage.getItem("ai_trust_auth_token") : null;

  if (userMode === "AUTHENTICATED" && (!authToken || !authToken.startsWith("local:"))) {
    return null;
  }

  const guestSessionId = getOrCreateGuestSessionId();
  const guestSessionToken = getGuestSessionToken();

  if (!guestSessionId || !guestSessionToken) {
    return null;
  }

  return {
    "X-Guest-Session-Id": guestSessionId,
    "X-Guest-Session-Token": guestSessionToken,
  };
}

export async function initializeGuestSession(
  apiBaseUrl: string = DEFAULT_API_BASE_URL,
): Promise<string | null> {
  if (!canUseSessionStorage()) {
    return null;
  }

  const existingId = window.sessionStorage.getItem(GUEST_SESSION_STORAGE_KEY);
  const existingToken = window.sessionStorage.getItem(GUEST_SESSION_TOKEN_STORAGE_KEY);
  if (existingId && existingToken) {
    return existingId;
  }

  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl}/api/v1/guest/session/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      cache: "no-store",
    });
  } catch {
    return null;
  }

  if (!response.ok) {
    return null;
  }

  const payload = (await response.json()) as {
    guest_session_id: string;
    guest_session_token: string;
  };
  window.sessionStorage.setItem(GUEST_SESSION_STORAGE_KEY, payload.guest_session_id);
  window.sessionStorage.setItem(GUEST_SESSION_TOKEN_STORAGE_KEY, payload.guest_session_token);
  return payload.guest_session_id;
}

export function endGuestSession(apiBaseUrl: string = DEFAULT_API_BASE_URL): void {
  if (typeof navigator === "undefined") {
    return;
  }

  const guestSessionId = getOrCreateGuestSessionId();
  const guestSessionToken = getGuestSessionToken();
  if (!guestSessionId || !guestSessionToken) {
    return;
  }

  const payload = JSON.stringify({ guest_session_id: guestSessionId });
  const endpoint = `${apiBaseUrl}/api/v1/guest/session/end`;

  void fetch(endpoint, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Guest-Session-Token": guestSessionToken,
    },
    body: payload,
    keepalive: true,
  });
}

export function clearGuestSession(): void {
  if (typeof window === "undefined" || typeof window.sessionStorage === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(GUEST_SESSION_STORAGE_KEY);
  window.sessionStorage.removeItem(GUEST_SESSION_TOKEN_STORAGE_KEY);
}

export function registerGuestSessionLifecycle(apiBaseUrl?: string): () => void {
  if (typeof window === "undefined") {
    return () => undefined;
  }

  const listener = () => endGuestSession(apiBaseUrl);
  window.addEventListener("pagehide", listener);
  window.addEventListener("beforeunload", listener);

  return () => {
    window.removeEventListener("pagehide", listener);
    window.removeEventListener("beforeunload", listener);
  };
}

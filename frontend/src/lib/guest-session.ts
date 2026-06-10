import { getStoredAuthToken, getStoredUserMode, getStoredUsername } from "./auth";
import { getApiBaseUrl } from "./api-base";

const GUEST_SESSION_STORAGE_KEY = "ai_trust_guest_session_id";
const GUEST_SESSION_TOKEN_STORAGE_KEY = "ai_trust_guest_session_token";
const DEFAULT_API_BASE_URL = getApiBaseUrl();

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined" && typeof window.localStorage !== "undefined";
}

function localAuthStorageSuffix(): string | null {
  const userMode = getStoredUserMode();
  const authToken = getStoredAuthToken();
  if (userMode !== "AUTHENTICATED" || !authToken?.startsWith("local:")) {
    return null;
  }

  const username = getStoredUsername() ?? authToken.split(":")[1] ?? "local-user";
  return username.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "_") || "local-user";
}

function storageKeys(): { id: string; token: string; persistent: boolean } {
  const suffix = localAuthStorageSuffix();
  if (!suffix) {
    return {
      id: GUEST_SESSION_STORAGE_KEY,
      token: GUEST_SESSION_TOKEN_STORAGE_KEY,
      persistent: false,
    };
  }

  return {
    id: `${GUEST_SESSION_STORAGE_KEY}:auth:${suffix}`,
    token: `${GUEST_SESSION_TOKEN_STORAGE_KEY}:auth:${suffix}`,
    persistent: true,
  };
}

function readStorage(key: string, persistent: boolean): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  return persistent ? window.localStorage.getItem(key) : window.sessionStorage.getItem(key);
}

function writeStorage(key: string, value: string, persistent: boolean): void {
  if (!canUseSessionStorage()) {
    return;
  }

  if (persistent) {
    window.localStorage.setItem(key, value);
    return;
  }

  window.sessionStorage.setItem(key, value);
}

export function getOrCreateGuestSessionId(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const keys = storageKeys();
  const existing = readStorage(keys.id, keys.persistent);
  if (existing) {
    return existing;
  }

  return null;
}

function getGuestSessionToken(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }
  const keys = storageKeys();
  return readStorage(keys.token, keys.persistent);
}

export function getGuestSessionHeaders(): Record<string, string> | null {
  const userMode = getStoredUserMode();
  const authToken = getStoredAuthToken();

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

  const keys = storageKeys();
  const existingId = readStorage(keys.id, keys.persistent);
  const existingToken = readStorage(keys.token, keys.persistent);
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
  writeStorage(keys.id, payload.guest_session_id, keys.persistent);
  writeStorage(keys.token, payload.guest_session_token, keys.persistent);
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

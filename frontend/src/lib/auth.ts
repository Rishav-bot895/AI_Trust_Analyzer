import type { UserMode } from "../types/api";

const USER_MODE_STORAGE_KEY = "ai_trust_user_mode";
const AUTH_TOKEN_STORAGE_KEY = "ai_trust_auth_token";
const LOCAL_ACCOUNTS_STORAGE_KEY = "ai_trust_local_accounts";

type AuthGateMode = "LOGIN" | "SIGN_UP";

interface LocalAccountRecord {
  username: string;
  password: string;
  createdAt: string;
}

interface LocalAuthSession {
  userMode: UserMode;
  username: string;
  sessionToken: string;
}

function canUseSessionStorage(): boolean {
  return typeof window !== "undefined" && typeof window.sessionStorage !== "undefined";
}

export function getStoredUserMode(): UserMode | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const storedMode = window.sessionStorage.getItem(USER_MODE_STORAGE_KEY);
  if (storedMode === "AUTHENTICATED" || storedMode === "GUEST") {
    return storedMode;
  }

  return null;
}

export function setStoredUserMode(mode: UserMode): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(USER_MODE_STORAGE_KEY, mode);
}

export function clearStoredUserMode(): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(USER_MODE_STORAGE_KEY);
}

export function getStoredAuthToken(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const token = window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  return token && token.trim() ? token : null;
}

export function setStoredAuthToken(token: string): void {
  if (!canUseSessionStorage()) {
    return;
  }

  const trimmed = token.trim();
  if (!trimmed) {
    window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    return;
  }

  window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, trimmed);
}

export function clearStoredAuthToken(): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
}

function getStoredAccounts(): LocalAccountRecord[] {
  if (!canUseSessionStorage()) {
    return [];
  }

  const raw = window.localStorage.getItem(LOCAL_ACCOUNTS_STORAGE_KEY);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.filter((entry): entry is LocalAccountRecord => {
      if (!entry || typeof entry !== "object") {
        return false;
      }

      const record = entry as Record<string, unknown>;
      return (
        typeof record.username === "string" &&
        typeof record.password === "string" &&
        typeof record.createdAt === "string"
      );
    });
  } catch {
    return [];
  }
}

function setStoredAccounts(accounts: LocalAccountRecord[]): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.localStorage.setItem(LOCAL_ACCOUNTS_STORAGE_KEY, JSON.stringify(accounts));
}

function createSessionToken(username: string): string {
  const randomSuffix = typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;

  return `local:${username}:${randomSuffix}`;
}

export function clearLocalAuthAccounts(): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.localStorage.removeItem(LOCAL_ACCOUNTS_STORAGE_KEY);
}

export function authenticateLocalAccount(
  username: string,
  password: string,
  mode: AuthGateMode,
): { username: string; sessionToken: string; created: boolean } {
  const normalizedUsername = username.trim().toLowerCase();
  if (!normalizedUsername || !password.trim()) {
    throw new Error("Username and password are required.");
  }

  const accounts = getStoredAccounts();
  const existingAccount = accounts.find((account) => account.username.toLowerCase() === normalizedUsername);

  if (existingAccount) {
    if (existingAccount.password !== password) {
      throw new Error(mode === "LOGIN" ? "Incorrect username or password." : "Account already exists. Use Log in.");
    }

    const sessionToken = createSessionToken(existingAccount.username);
    const session: LocalAuthSession = {
      userMode: "AUTHENTICATED",
      username: existingAccount.username,
      sessionToken,
    };
    setStoredAuthSession(session);
    return { username: existingAccount.username, sessionToken, created: false };
  }

  if (mode === "LOGIN") {
    throw new Error("No account found. Use Create account to continue.");
  }

  const newAccount: LocalAccountRecord = {
    username: username.trim(),
    password,
    createdAt: new Date().toISOString(),
  };
  setStoredAccounts([...accounts, newAccount]);

  const sessionToken = createSessionToken(newAccount.username);
  const session: LocalAuthSession = {
    userMode: "AUTHENTICATED",
    username: newAccount.username,
    sessionToken,
  };
  setStoredAuthSession(session);
  return { username: newAccount.username, sessionToken, created: true };
}

export function setStoredAuthSession(session: LocalAuthSession): void {
  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.setItem(
    USER_MODE_STORAGE_KEY,
    session.userMode,
  );
  window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, session.sessionToken);
  window.sessionStorage.setItem(`${USER_MODE_STORAGE_KEY}:username`, session.username);
}

export function getStoredUsername(): string | null {
  if (!canUseSessionStorage()) {
    return null;
  }

  const username = window.sessionStorage.getItem(`${USER_MODE_STORAGE_KEY}:username`);
  return username && username.trim() ? username : null;
}

export function clearStoredAuthSession(): void {
  clearStoredUserMode();
  clearStoredAuthToken();

  if (!canUseSessionStorage()) {
    return;
  }

  window.sessionStorage.removeItem(`${USER_MODE_STORAGE_KEY}:username`);
}
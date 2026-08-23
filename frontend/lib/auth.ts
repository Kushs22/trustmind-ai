const TOKEN_KEY = "trustmind_access_token";
const ANON_KEY = "trustmind_is_anonymous";
/** Cleared analyse UI must not resume after logout / account switch. */
export const ANALYSE_SESSIONS_KEY = "trustmind_analyse_sessions_v1";
export const ANALYSE_FORCE_FRESH_KEY = "trustmind_force_fresh_analyse";
export const AUTH_EPOCH_KEY = "trustmind_auth_epoch";

/** Fired on same-tab token changes so Header / Dashboard can refresh. */
export const AUTH_CHANGED_EVENT = "trustmind-auth-changed";

function notifyAuthChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

function bumpAuthEpoch(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(AUTH_EPOCH_KEY, String(Date.now()));
  } catch {
    // ignore
  }
}

/** Drop local analyse threads and force the next /analyse visit to start blank. */
export function clearAnalyseWorkspaceStorage(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(ANALYSE_SESSIONS_KEY);
    sessionStorage.setItem(ANALYSE_FORCE_FRESH_KEY, "1");
  } catch {
    // ignore
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  bumpAuthEpoch();
  notifyAuthChanged();
}

export function setAnonymousFlag(isAnonymous: boolean): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(ANON_KEY, isAnonymous ? "1" : "0");
}

export function isAnonymousSession(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(ANON_KEY) === "1";
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(ANON_KEY);
  clearAnalyseWorkspaceStorage();
  bumpAuthEpoch();
  notifyAuthChanged();
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

/** Signed-in email/password account (not anonymous guest session). */
export function isRegisteredUser(): boolean {
  return isAuthenticated() && !isAnonymousSession();
}

export function logout(): void {
  clearToken();
}

export function getAuthEpoch(): string {
  if (typeof window === "undefined") return "";
  try {
    return localStorage.getItem(AUTH_EPOCH_KEY) || "";
  } catch {
    return "";
  }
}

export function authIdentityLabel(): string {
  if (!isAuthenticated()) return "guest";
  if (isAnonymousSession()) return "anonymous";
  return "registered";
}

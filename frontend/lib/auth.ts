const TOKEN_KEY = "trustmind_access_token";
const ANON_KEY = "trustmind_is_anonymous";

/** Fired on same-tab token changes so Header / Dashboard can refresh. */
export const AUTH_CHANGED_EVENT = "trustmind-auth-changed";

function notifyAuthChanged(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
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

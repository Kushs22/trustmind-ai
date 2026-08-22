const TOKEN_KEY = "trustmind_access_token";

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

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  notifyAuthChanged();
}

export function isAuthenticated(): boolean {
  return Boolean(getToken());
}

export function logout(): void {
  clearToken();
}

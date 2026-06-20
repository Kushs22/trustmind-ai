import { clearToken, getToken, setToken } from "@/lib/auth";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "http://127.0.0.1:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type TokenResponse = {
  access_token: string;
  token_type: string;
  user_id: string;
  is_anonymous: boolean;
};

export type AnalyseResponse = {
  id: string | null;
  concern_level: string;
  ai_confidence: string;
  uncertainty_level: string;
  grounding_status: string;
  abstention_status: string;
  explanation: string;
  safe_next_steps: string[];
  safety_note: string;
  saved_to_history: boolean;
};

export type CheckIn = {
  id: string;
  date: string;
  concern: string;
  confidence: string;
  abstained: boolean;
  preview: string | null;
  is_private: boolean;
  created_at: string;
};

export type DashboardStats = {
  saved_analyses: number;
  avg_ai_confidence: number | null;
  abstention_count: number;
  privacy_mode: string;
};

function parseErrorDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          return String((item as { msg: string }).msg);
        }
        return "Validation error";
      })
      .join(". ");
  }
  return "Request failed";
}

async function request<T>(
  path: string,
  options: RequestInit & { requireAuth?: boolean } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (options.requireAuth) {
    throw new ApiError(401, "Authentication required");
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      message = parseErrorDetail(body.detail ?? message);
    } catch {
      message = response.statusText || message;
    }
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function storeAuth(response: TokenResponse): TokenResponse {
  setToken(response.access_token);
  return response;
}

export async function register(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return storeAuth(
    await request<TokenResponse>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  );
}

export async function login(
  email: string,
  password: string,
): Promise<TokenResponse> {
  return storeAuth(
    await request<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
  );
}

export async function createAnonymousSession(): Promise<TokenResponse> {
  return storeAuth(
    await request<TokenResponse>("/api/v1/auth/anonymous", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  );
}

export async function analyseText(payload: {
  text: string;
  save_to_history: boolean;
  analyse_privately: boolean;
}): Promise<AnalyseResponse> {
  return request<AnalyseResponse>("/api/v1/analyse", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getCheckIns(): Promise<CheckIn[]> {
  return request<CheckIn[]>("/api/v1/check-ins", { requireAuth: true });
}

export async function getDashboardStats(): Promise<DashboardStats> {
  return request<DashboardStats>("/api/v1/check-ins/stats", {
    requireAuth: true,
  });
}

export async function deleteCheckInHistory(): Promise<void> {
  await request<{ deleted: number; message: string }>("/api/v1/check-ins", {
    method: "DELETE",
    requireAuth: true,
  });
}

export async function deleteAccount(): Promise<void> {
  await request<{ message: string }>("/api/v1/privacy/me", {
    method: "DELETE",
    requireAuth: true,
  });
  clearToken();
}

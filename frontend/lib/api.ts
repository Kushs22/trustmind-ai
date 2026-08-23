import { clearToken, getToken, setAnonymousFlag, setToken } from "@/lib/auth";

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

export type SupportResource = {
  name: string;
  description: string;
  contact: string;
  url: string;
};

export type ConfidenceBreakdown = {
  retrieval_similarity: number | null;
  source_agreement: number | null;
  llm_confidence: number;
  classification_consistency: number | null;
  retrieval_coverage: number | null;
  input_clarity?: number | null;
};

export type TrustSignals = {
  model_confidence: number;
  evidence_strength: number | null;
  retrieval_quality: number | null;
};

export type GroundingInfo = {
  status: string;
  label: string;
};

export type EvidenceItem = {
  source_id: string;
  organisation: string;
  title: string;
  topic?: string;
  url?: string;
  retrieval_score?: number;
  reason_retrieved?: string;
  display_label?: string;
  snippet?: string;
};

export type AnalyseDebug = {
  latency_ms: number;
  n_retrieved_chunks: number;
  openai_model: string;
  embedding_model: string;
  confidence_threshold: number;
  grounding_retrieval_quality_min: number;
  grounding_evidence_strength_min: number;
  pipeline_used: string;
  consistency_runs: number;
};

export type InputSummary = {
  typed_text_used: boolean;
  speech_transcript_used: boolean;
  image_count: number;
  pdf_count: number;
};

export type ProcessedAttachment = {
  type: "image" | "pdf" | "audio";
  filename: string;
  status: string;
  included_in_analysis: boolean;
  warnings: string[];
};

export type AnalyseResponse = {
  id: string | null;
  status: string;
  prediction: string | null;
  prediction_display?: string | null;
  confidence: number;
  reasoning: string;
  sources: string[];
  message?: string;
  recommendation?: string;
  pipeline_used: string;
  support_resources?: SupportResource[];
  disclaimer?: string;
  privacy_notice?: string;
  human_oversight?: string;
  concern_level: string;
  ai_confidence: string;
  uncertainty_level: string;
  grounding_status: string;
  abstention_status: string;
  explanation: string;
  safe_next_steps: string[];
  safety_note: string;
  early_signs?: string[];
  potential_indicators?: string[];
  saved_to_history: boolean;
  continuity_used?: boolean;
  confidence_breakdown?: ConfidenceBreakdown | null;
  uncertainty?: string;
  trust_signals?: TrustSignals | null;
  grounding?: GroundingInfo | null;
  evidence_used?: EvidenceItem[];
  sources_detail?: EvidenceItem[];
  safety_triggered?: boolean;
  support_urgency?: number | null;
  support_urgency_band?: "low" | "moderate" | "elevated" | "urgent" | null;
  support_urgency_rationale?: string | null;
  support_urgency_uncertain?: boolean;
  debug?: AnalyseDebug | null;
  input_summary?: InputSummary | null;
  processed_attachments?: ProcessedAttachment[];
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
  support_urgency?: number | null;
  support_urgency_band?: "low" | "moderate" | "elevated" | "urgent" | null;
  support_urgency_uncertain?: boolean;
};

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  created_at?: string | null;
  safety_triggered?: boolean;
  input_type?: "text" | "audio" | null;
  transcript?: string | null;
  tone_summary?: string | null;
  affect_cues?: string[];
};

export type ChatFollowUpResponse = {
  check_in_id: string | null;
  reply: string;
  safety_triggered: boolean;
  support_resources: SupportResource[];
  messages: ChatMessage[];
  persisted: boolean;
  tone_disclaimer?: string | null;
};

export type CheckInDetail = {
  id: string;
  date: string;
  concern: string;
  confidence: string;
  uncertainty_level: string;
  grounding_status: string;
  abstention_status: string;
  abstained: boolean;
  explanation: string;
  safe_next_steps: string[];
  safety_note: string;
  preview: string | null;
  is_private: boolean;
  created_at: string;
  support_urgency?: number | null;
  support_urgency_band?: "low" | "moderate" | "elevated" | "urgent" | null;
  support_urgency_rationale?: string | null;
  support_urgency_uncertain?: boolean;
  messages?: ChatMessage[];
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

function messageFromFailedResponse(status: number, detail: unknown, fallback: string): string {
  let message = parseErrorDetail(detail ?? fallback);
  if (!message || message === "Request failed") {
    message = fallback || "Request failed";
  }
  if (status === 429) {
    return message === "Request failed"
      ? "Too many requests. Please wait a moment and try again."
      : message;
  }
  return message;
}

async function request<T>(
  path: string,
  options: RequestInit & { requireAuth?: boolean; timeoutMs?: number } = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else if (options.requireAuth) {
    throw new ApiError(401, "Authentication required");
  }

  const timeoutMs = options.timeoutMs ?? 90_000;
  const { timeoutMs: _ignored, requireAuth: _auth, ...fetchOptions } = options;

  async function once(): Promise<Response> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(`${API_URL}${path}`, {
        ...fetchOptions,
        headers,
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timer);
    }
  }

  let response: Response;
  try {
    response = await once();
  } catch (err) {
    // Cold-start / brief network blip: wake the API then retry once.
    try {
      await fetch(`${API_URL}/health`, { method: "GET" });
    } catch {
      /* ignore */
    }
    try {
      response = await once();
    } catch {
      const aborted =
        err instanceof DOMException && err.name === "AbortError";
      throw new ApiError(
        0,
        aborted
          ? "The service timed out while starting. Free hosting can take up to a minute to wake — wait a moment and try again."
          : "Unable to reach the service right now. It may be waking up from a cold start — wait a few seconds and try again.",
      );
    }
  }

  if (!response.ok) {
    let detail: unknown = "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = body.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(
      response.status,
      messageFromFailedResponse(response.status, detail, "Request failed"),
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function storeAuth(response: TokenResponse): TokenResponse {
  setToken(response.access_token);
  setAnonymousFlag(Boolean(response.is_anonymous));
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

export type PipelineMode = "llm" | "rag" | "auto";

export async function analyseText(payload: {
  text?: string;
  typed_text?: string;
  speech_transcript?: string;
  image_context?: Array<{
    filename: string;
    extracted_text: string;
    summary?: string;
    included: boolean;
    warnings?: string[];
  }>;
  pdf_context?: Array<{
    filename: string;
    extracted_text: string;
    summary?: string;
    included: boolean;
    warnings?: string[];
  }>;
  save_to_history: boolean;
  analyse_privately: boolean;
  use_past_checkins?: boolean;
  pipeline_mode?: PipelineMode;
  include_debug?: boolean;
}): Promise<AnalyseResponse> {
  return request<AnalyseResponse>("/api/v1/analyse", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** Multipart helper — does not set JSON Content-Type (browser sets boundary). */
export async function requestMultipart<T>(
  path: string,
  formData: FormData,
): Promise<T> {
  const headers = new Headers();
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
  });

  if (!response.ok) {
    let detail: unknown = "Request failed";
    try {
      const body = (await response.json()) as { detail?: unknown };
      detail = body.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new ApiError(
      response.status,
      messageFromFailedResponse(response.status, detail, "Request failed"),
    );
  }

  return response.json() as Promise<T>;
}

export type TranscriptionResult = {
  status: string;
  transcript: string;
  language: string;
  duration_seconds: number | null;
  warnings: string[];
};

export type ImageProcessResult = {
  filename: string;
  summary: string;
  extracted_text: string;
  contains_text: boolean;
  safety_flags: string[];
  warnings: string[];
  useful_context: boolean;
};

export type PdfProcessResult = {
  filename: string;
  page_count: number;
  extracted_text: string;
  document_summary: string;
  safety_flags: string[];
  warnings: string[];
  is_scanned: boolean;
};

export async function transcribeAudio(file: Blob, filename = "recording.webm") {
  const form = new FormData();
  form.append("file", file, filename);
  return requestMultipart<TranscriptionResult>("/api/v1/transcribe", form);
}

export async function processImageFile(file: File) {
  const form = new FormData();
  form.append("file", file, file.name);
  return requestMultipart<ImageProcessResult>("/api/v1/process-image", form);
}

export async function processPdfFile(file: File) {
  const form = new FormData();
  form.append("file", file, file.name);
  return requestMultipart<PdfProcessResult>("/api/v1/process-pdf", form);
}

export async function getCheckIns(): Promise<CheckIn[]> {
  return request<CheckIn[]>("/api/v1/check-ins", { requireAuth: true });
}

export async function getCheckIn(id: string): Promise<CheckInDetail> {
  return request<CheckInDetail>(`/api/v1/check-ins/${encodeURIComponent(id)}`, {
    requireAuth: true,
  });
}

export async function sendChatFollowUp(payload: {
  message: string;
  check_in_id?: string | null;
  history?: ChatMessage[];
}): Promise<ChatFollowUpResponse> {
  return request<ChatFollowUpResponse>("/api/v1/chat/follow-up", {
    method: "POST",
    body: JSON.stringify({
      message: payload.message,
      check_in_id: payload.check_in_id || null,
      history: payload.history || [],
    }),
  });
}

export async function sendChatFollowUpAudio(payload: {
  file: Blob;
  filename?: string;
  check_in_id?: string | null;
  history?: ChatMessage[];
}): Promise<ChatFollowUpResponse> {
  const form = new FormData();
  const name =
    payload.filename ||
    (payload.file.type.includes("mp4") ? "recording.mp4" : "recording.webm");
  form.append("file", payload.file, name);
  if (payload.check_in_id) {
    form.append("check_in_id", payload.check_in_id);
  }
  if (!payload.check_in_id && payload.history?.length) {
    form.append("history", JSON.stringify(payload.history));
  }
  return requestMultipart<ChatFollowUpResponse>(
    "/api/v1/chat/follow-up-audio",
    form,
  );
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

export type DataExport = {
  exported_at: string;
  format_version: number;
  profile: {
    id: string;
    email: string | null;
    is_anonymous: boolean;
    created_at: string | null;
  };
  check_ins: Array<Record<string, unknown>>;
};

export async function exportMyData(): Promise<DataExport> {
  return request<DataExport>("/api/v1/privacy/export", {
    method: "GET",
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

"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Toggle } from "@/components/Toggle";
import { SupportUrgencyMeter } from "@/components/SupportUrgencyMeter";
import { ChatThread } from "@/components/ChatThread";
import { CheckInComposer } from "@/components/analysis/CheckInComposer";
import {
  analyseText,
  ApiError,
  createAnonymousSession,
  getCheckIn,
  getCheckIns,
  sendChatFollowUp,
  sendChatFollowUpAudio,
  type AnalyseResponse,
  type CheckIn,
  type ChatMessage,
  type EvidenceItem,
  type PipelineMode,
  type SupportResource,
} from "@/lib/api";
import {
  ANALYSE_FORCE_FRESH_KEY,
  ANALYSE_SESSIONS_KEY,
  AUTH_CHANGED_EVENT,
  authIdentityLabel,
  clearAnalyseWorkspaceStorage,
  getAuthEpoch,
  getToken,
  isAnonymousSession,
  isAuthenticated,
  isRegisteredUser,
} from "@/lib/auth";
import { predictionDisplayName } from "@/lib/displayLabels";
import { useFileUpload } from "@/hooks/useFileUpload";

const PROCESSING_DURATION_MS = 350;
const SHORT_INPUT_TIP_WORDS = 12;
const INPUT_GUIDANCE =
  "The more you share, the better we can support you. A few sentences about how long this has lasted and how it affects sleep, study, or daily life often helps — one-word check-ins still work.";
const SHORT_INPUT_TIP =
  "Optional tip: adding a little more detail usually improves how well we can reflect what you're going through — short check-ins are still welcome.";
const SHORT_INPUT_EXAMPLE =
  "I've been feeling stressed for about two weeks. It's hard to sleep and I'm falling behind on coursework. Things feel heavier than usual.";

/** Client fallback when urgency is high but API omitted support_resources. */
const FALLBACK_SUPPORT_RESOURCES: SupportResource[] = [
  {
    name: "NHS Mental Health",
    description:
      "NHS guidance on where to get urgent help for mental health.",
    contact: "NHS 111 (option 2) for urgent mental health support in England",
    url: "https://www.nhs.uk/nhs-services/mental-health-services/where-to-get-urgent-help-for-mental-health/",
  },
  {
    name: "Samaritans",
    description: "24/7 listening support if you are struggling to cope.",
    contact: "Call 116 123 (UK & ROI)",
    url: "https://www.samaritans.org/",
  },
  {
    name: "Talk to someone (NHS)",
    description: "Find NHS talking therapies and local mental health services.",
    contact: "Self-referral available in many areas of England",
    url: "https://www.nhs.uk/mental-health/talking-therapies/",
  },
  {
    name: "Student Minds",
    description: "Student mental health charity with advice and peer support.",
    contact: "See website for support options",
    url: "https://www.studentminds.org.uk/",
  },
  {
    name: "UWE Student Wellbeing",
    description:
      "University of the West of England wellbeing service for students.",
    contact: "See UWE wellbeing contact page",
    url: "https://www.uwe.ac.uk/life/health-and-wellbeing/get-wellbeing-support/wellbeing-service",
  },
];

function countWords(value: string): number {
  const trimmed = value.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
}

function Spinner({ className }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className ?? ""}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
      />
    </svg>
  );
}

function buildAssistantOpening(analysis: AnalyseResponse): string {
  const softInvite =
    'Thanks for checking in. I don\'t quite have enough to go on yet — try adding a bit more about how you feel (even a few sentences) so we can support you better. One-word feelings like "stressed" or "sad" still work if they\'re real words. This isn\'t a diagnosis.';
  const reflection = (
    analysis.reasoning || analysis.explanation || analysis.message || ""
  ).trim();
  if (!reflection || /^assessment completed\.?$/i.test(reflection)) {
    return softInvite;
  }
  return reflection;
}

type AttachmentContext = {
  filename: string;
  extracted_text: string;
  summary: string;
  included: boolean;
  warnings: string[];
};

type LastCheckInPayload = {
  typed_text: string;
  userOpening: string;
  image_context: AttachmentContext[];
  pdf_context: AttachmentContext[];
};

/** In-memory analyse thread so New chat / mode switch do not wipe siblings. */
type AnalyseSession = {
  id: string;
  checkInId: string | null;
  label: string;
  chatMode: boolean;
  messages: ChatMessage[];
  result: AnalyseResponse | null;
  lastCheckIn: LastCheckInPayload | null;
  pipelineMode: Exclude<PipelineMode, "auto">;
  chatSupportResources: SupportResource[];
  toneDisclaimer: string | null;
  chatDraft: string;
};

function newSessionId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

const SESSION_STORAGE_KEY = ANALYSE_SESSIONS_KEY;

type PersistedSessionsV1 = {
  version: 1;
  /** guest | anonymous | registered — discard on mismatch after logout/login. */
  authIdentity?: string;
  authEpoch?: string;
  activeSessionId: string;
  active: AnalyseSession;
  archive: AnalyseSession[];
};

function readCheckInQuery(): string | null {
  try {
    return new URLSearchParams(window.location.search).get("check_in");
  } catch {
    return null;
  }
}

function consumeForceFreshFlag(): boolean {
  try {
    if (sessionStorage.getItem(ANALYSE_FORCE_FRESH_KEY) === "1") {
      sessionStorage.removeItem(ANALYSE_FORCE_FRESH_KEY);
      return true;
    }
  } catch {
    // ignore
  }
  return false;
}

function readPersistedSessions(): PersistedSessionsV1 | null {
  try {
    const raw = sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedSessionsV1;
    if (
      !parsed ||
      parsed.version !== 1 ||
      !parsed.active ||
      !Array.isArray(parsed.archive)
    ) {
      return null;
    }
    const identity = authIdentityLabel();
    const epoch = getAuthEpoch();
    if (
      (parsed.authIdentity && parsed.authIdentity !== identity) ||
      (parsed.authEpoch && epoch && parsed.authEpoch !== epoch)
    ) {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writePersistedSessions(
  active: AnalyseSession,
  archive: AnalyseSession[],
) {
  try {
    // Logout asked for a blank analyse — do not resurrect the prior thread.
    if (sessionStorage.getItem(ANALYSE_FORCE_FRESH_KEY) === "1") {
      return;
    }
    const payload: PersistedSessionsV1 = {
      version: 1,
      authIdentity: authIdentityLabel(),
      authEpoch: getAuthEpoch(),
      activeSessionId: active.id,
      active,
      archive: archive.slice(0, 12),
    };
    sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // quota / private mode — ignore
  }
}

function clearPersistedSessions() {
  clearAnalyseWorkspaceStorage();
  try {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // ignore
  }
}

/** Clear or set ?check_in= without a full navigation (avoids remount races). */
function setCheckInQuery(checkInId: string | null) {
  try {
    const url = new URL(window.location.href);
    if (checkInId) {
      url.searchParams.set("check_in", checkInId);
    } else {
      url.searchParams.delete("check_in");
    }
    const next = `${url.pathname}${url.search}${url.hash}`;
    window.history.replaceState(window.history.state, "", next);
  } catch {
    // ignore
  }
}

function labelFromMessages(
  messages: ChatMessage[],
  fallback = "New chat",
): string {
  const firstUser = messages.find((m) => m.role === "user");
  const text = (firstUser?.content || "").trim().replace(/\s+/g, " ");
  if (!text) return fallback;
  return text.length > 48 ? `${text.slice(0, 48)}…` : text;
}

function emptySession(
  id: string,
  pipelineMode: Exclude<PipelineMode, "auto"> = "llm",
): AnalyseSession {
  return {
    id,
    checkInId: null,
    label: "New chat",
    chatMode: false,
    messages: [],
    result: null,
    lastCheckIn: null,
    pipelineMode,
    chatSupportResources: [],
    toneDisclaimer: null,
    chatDraft: "",
  };
}

function evidenceItemsOf(result: AnalyseResponse): EvidenceItem[] {
  if (result.evidence_used?.length) return result.evidence_used;
  if (result.sources_detail?.length) return result.sources_detail;
  return [];
}

function isStandaloneLlmPipeline(result: AnalyseResponse): boolean {
  // Real retrieved evidence always means show grounded sources.
  if (evidenceItemsOf(result).length > 0) return false;
  if ((result.retrieval_mode || "").trim() && result.retrieval_mode !== "none") {
    return false;
  }
  const pipeline = (result.pipeline_used || "").toUpperCase();
  if (pipeline.includes("RAG")) return false;
  if (result.grounding?.status === "not_applicable") return true;
  // LLM-only or keyword fallback with no passages.
  return true;
}

function evidenceFromResult(result: AnalyseResponse): EvidenceItem[] {
  return evidenceItemsOf(result);
}

/**
 * Mode toggle / Re-analyse must NOT wipe the thread.
 * Keep follow-ups; only refresh the opening user + first assistant reflection.
 */
function messagesAfterReanalyse(
  previous: ChatMessage[],
  userOpening: string,
  assistantOpening: string,
): ChatMessage[] {
  let rest = previous;
  if (rest.length > 0 && rest[0]?.role === "user") {
    rest = rest.slice(1);
  }
  if (rest.length > 0 && rest[0]?.role === "assistant") {
    rest = rest.slice(1);
  }
  return [
    { role: "user", content: userOpening },
    { role: "assistant", content: assistantOpening },
    ...rest,
  ];
}

/** Rebuild re-analyse payload from the opening user turn when lastCheckIn was lost. */
function payloadFromOpeningText(text: string): LastCheckInPayload | null {
  const trimmed = text.trim();
  if (!trimmed) return null;
  return {
    typed_text: trimmed,
    userOpening: trimmed,
    image_context: [],
    pdf_context: [],
  };
}

function payloadFromMessages(
  messages: ChatMessage[],
): LastCheckInPayload | null {
  const firstUser = messages.find((m) => m.role === "user");
  const opening = (firstUser?.transcript || firstUser?.content || "").trim();
  return payloadFromOpeningText(opening);
}

export function AnalyseForm() {
  const [text, setText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [saveToHistory, setSaveToHistory] = useState(false);
  const [analysePrivately, setAnalysePrivately] = useState(true);
  const [usePastCheckins, setUsePastCheckins] = useState(false);
  const [hasSavedHistory, setHasSavedHistory] = useState(false);
  const [pipelineMode, setPipelineMode] =
    useState<Exclude<PipelineMode, "auto">>("llm");
  const [result, setResult] = useState<AnalyseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatDraft, setChatDraft] = useState("");
  const [chatSending, setChatSending] = useState(false);
  const [chatError, setChatError] = useState<string | null>(null);
  const [activeCheckInId, setActiveCheckInId] = useState<string | null>(null);
  const [chatSupportResources, setChatSupportResources] = useState<
    SupportResource[]
  >([]);
  const [loadingThread, setLoadingThread] = useState(false);
  const [toneDisclaimer, setToneDisclaimer] = useState<string | null>(null);
  const [showMoreEvidence, setShowMoreEvidence] = useState(false);
  const [lastCheckIn, setLastCheckIn] = useState<LastCheckInPayload | null>(
    null,
  );
  const [activeSessionId, setActiveSessionId] = useState(() => newSessionId());
  const [sessionArchive, setSessionArchive] = useState<AnalyseSession[]>([]);
  const [recentCheckIns, setRecentCheckIns] = useState<CheckIn[]>([]);
  const timersRef = useRef<number[]>([]);
  const activeCheckInIdRef = useRef<string | null>(null);
  const suppressUrlLoadRef = useRef(false);
  /** Synchronous session truth — state alone races with in-flight reanalyse. */
  const lastCheckInRef = useRef<LastCheckInPayload | null>(null);
  const messagesRef = useRef<ChatMessage[]>([]);
  const activeSessionIdRef = useRef(activeSessionId);
  const sessionArchiveRef = useRef<AnalyseSession[]>([]);
  const analyseGenerationRef = useRef(0);
  /** Prevents overlapping analyse runs and stuck "Reflecting…" spinners. */
  const analyseLockRef = useRef(false);
  /** Tracks guest / anon / registered so logout does not keep the prior chat. */
  const authIdentityRef = useRef<string | null>(null);
  const files = useFileUpload();

  activeCheckInIdRef.current = activeCheckInId;
  activeSessionIdRef.current = activeSessionId;
  messagesRef.current = messages;

  function currentAuthIdentity(): string {
    if (!isAuthenticated()) return "guest";
    if (isAnonymousSession()) return "anonymous";
    return "registered";
  }

  /** Wipe local chats on real account switches — not when a guest quietly gets an anon token. */
  function shouldResetOnAuthChange(prev: string, next: string): boolean {
    if (prev === next) return false;
    // analyse may mint an anonymous token mid-run; keep the in-progress thread.
    if (prev === "guest" && next === "anonymous") return false;
    return true;
  }

  function resetAnalyseWorkspace() {
    analyseGenerationRef.current += 1;
    analyseLockRef.current = false;
    setIsProcessing(false);
    lastCheckInRef.current = null;
    suppressUrlLoadRef.current = true;
    setCheckInQuery(null);
    setArchiveState([]);
    const next = emptySession(newSessionId(), "llm");
    activeSessionIdRef.current = next.id;
    applySession(next);
    // Keep the force-fresh flag set by logout; do not write the old thread back.
    try {
      sessionStorage.removeItem(SESSION_STORAGE_KEY);
      sessionStorage.setItem(ANALYSE_FORCE_FRESH_KEY, "1");
    } catch {
      // ignore
    }
    window.setTimeout(() => {
      suppressUrlLoadRef.current = false;
    }, 0);
  }

  function captureActiveSession(): AnalyseSession {
    return {
      id: activeSessionIdRef.current,
      checkInId: activeCheckInId,
      label: labelFromMessages(
        messages,
        lastCheckInRef.current?.typed_text?.trim()
          ? lastCheckInRef.current.typed_text.trim().slice(0, 48)
          : "New chat",
      ),
      chatMode,
      messages,
      result,
      lastCheckIn: lastCheckInRef.current,
      pipelineMode,
      chatSupportResources,
      toneDisclaimer,
      chatDraft,
    };
  }

  function sessionHasContent(session: AnalyseSession): boolean {
    return (
      session.chatMode ||
      session.messages.length > 0 ||
      Boolean(session.lastCheckIn) ||
      Boolean(session.result)
    );
  }

  /** Upsert session into the archive list (may include active for storage). */
  function upsertSessionInArchive(
    archive: AnalyseSession[],
    session: AnalyseSession,
  ): AnalyseSession[] {
    const without = archive.filter((s) => s.id !== session.id);
    if (!sessionHasContent(session)) return without.slice(0, 12);
    return [session, ...without].slice(0, 12);
  }

  /** UI archive is siblings only — never duplicate the active thread in the switcher. */
  function siblingsOnly(
    archive: AnalyseSession[],
    activeId: string,
  ): AnalyseSession[] {
    return archive.filter((s) => s.id !== activeId).slice(0, 12);
  }

  function setArchiveState(archive: AnalyseSession[]) {
    sessionArchiveRef.current = archive;
    setSessionArchive(archive);
  }

  function persistSessionsNow(
    active: AnalyseSession,
    archive: AnalyseSession[],
  ) {
    const siblings = siblingsOnly(archive, active.id);
    sessionArchiveRef.current = siblings;
    // Persist active + siblings; also keep an upserted copy of active in storage
    // so remount can recover the thread even if active snapshot is missing.
    writePersistedSessions(
      active,
      upsertSessionInArchive(siblings, active),
    );
  }

  /** After analyse/reanalyse: upsert active into storage and keep UI siblings-only. */
  function commitActiveSession(active: AnalyseSession) {
    const combined = upsertSessionInArchive(
      sessionArchiveRef.current,
      active,
    );
    const siblings = siblingsOnly(combined, active.id);
    setArchiveState(siblings);
    writePersistedSessions(active, combined);
  }

  function applySession(session: AnalyseSession) {
    activeSessionIdRef.current = session.id;
    // Prefer stored payload; otherwise rebuild from the opening user message so
    // LLM ↔ LLM+RAG still re-runs the same text after composer clear / remount.
    const restoredPayload =
      session.lastCheckIn || payloadFromMessages(session.messages);
    lastCheckInRef.current = restoredPayload;
    setActiveSessionId(session.id);
    setActiveCheckInId(session.checkInId);
    setChatMode(session.chatMode);
    messagesRef.current = session.messages;
    setMessages(session.messages);
    setResult(session.result);
    setLastCheckIn(restoredPayload);
    setPipelineMode(session.pipelineMode);
    const resources =
      session.chatSupportResources?.length
        ? session.chatSupportResources
        : session.result?.support_resources || [];
    setChatSupportResources(resources);
    setToneDisclaimer(session.toneDisclaimer);
    setChatDraft(session.chatDraft);
    setError(null);
    setChatError(null);
    setSaveNotice(null);
    setShowMoreEvidence(false);
    setText("");
    files.clearAll();
  }

  function resolveReanalysePayload(): LastCheckInPayload | null {
    if (lastCheckInRef.current?.typed_text?.trim()) {
      return lastCheckInRef.current;
    }
    if (lastCheckInRef.current?.userOpening?.trim()) {
      const opening = lastCheckInRef.current.userOpening.trim();
      return {
        ...lastCheckInRef.current,
        typed_text: lastCheckInRef.current.typed_text?.trim() || opening,
        userOpening: opening,
      };
    }
    return payloadFromMessages(messagesRef.current);
  }

  function archiveCurrentIfNeeded() {
    const current = captureActiveSession();
    if (!sessionHasContent(current)) return;
    // Keep the leaving session in the archive (do not sibling-filter by its id yet).
    setArchiveState(upsertSessionInArchive(sessionArchiveRef.current, current));
  }

  useEffect(() => {
    function syncAuthDefaults() {
      const nextIdentity = currentAuthIdentity();
      const prevIdentity = authIdentityRef.current;
      authIdentityRef.current = nextIdentity;
      // Logout / login: never continue the previous account's chat.
      if (
        prevIdentity !== null &&
        shouldResetOnAuthChange(prevIdentity, nextIdentity)
      ) {
        resetAnalyseWorkspace();
      }

      const authed = isAuthenticated();
      const registered = isRegisteredUser();
      setLoggedIn(authed);
      if (authed) {
        setSaveToHistory(true);
        setAnalysePrivately(false);
      } else {
        setSaveToHistory(false);
        setAnalysePrivately(true);
      }
      if (registered) {
        let preferContinue = false;
        try {
          preferContinue =
            new URLSearchParams(window.location.search).get("continue") === "1";
        } catch {
          preferContinue = false;
        }
        void getCheckIns()
          .then((rows) => {
            setRecentCheckIns(rows.slice(0, 20));
            const usable = rows.some((r) => !r.is_private && Boolean(r.preview));
            setHasSavedHistory(usable || rows.length > 0);
            setUsePastCheckins(usable || preferContinue);
          })
          .catch(() => {
            setRecentCheckIns([]);
            setHasSavedHistory(false);
            setUsePastCheckins(preferContinue);
          });
      } else {
        setRecentCheckIns([]);
        setHasSavedHistory(false);
        setUsePastCheckins(false);
      }
    }
    syncAuthDefaults();
    window.addEventListener(AUTH_CHANGED_EVENT, syncAuthDefaults);
    window.addEventListener("storage", syncAuthDefaults);
    return () => {
      window.removeEventListener(AUTH_CHANGED_EVENT, syncAuthDefaults);
      window.removeEventListener("storage", syncAuthDefaults);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadCheckInThread(checkInId: string, opts?: { sessionId?: string }) {
    if (!isAuthenticated()) {
      setError("Please log in to continue a saved check-in chat.");
      return;
    }
    setLoadingThread(true);
    setError(null);
    try {
      const detail = await getCheckIn(checkInId);
      const seeded: ChatMessage[] =
        detail.messages && detail.messages.length > 0
          ? detail.messages
          : [
              ...(detail.preview && !detail.is_private
                ? [{ role: "user" as const, content: detail.preview }]
                : []),
              ...(detail.explanation
                ? [
                    {
                      role: "assistant" as const,
                      content: detail.explanation,
                    },
                  ]
                : []),
            ];
      const sessionId = opts?.sessionId || checkInId;
      const openingPayload = payloadFromMessages(seeded);
      applySession({
        id: sessionId,
        checkInId: detail.is_private ? null : detail.id,
        label: labelFromMessages(
          seeded,
          detail.preview?.trim() || "Saved check-in",
        ),
        chatMode: true,
        messages: seeded,
        result: {
          id: detail.id,
          status: detail.abstained ? "abstained" : "accepted",
          prediction: null,
          confidence: 0,
          reasoning: detail.explanation,
          sources: [],
          pipeline_used: "LLM",
          concern_level: detail.concern,
          ai_confidence: detail.confidence,
          uncertainty_level: detail.uncertainty_level,
          grounding_status: detail.grounding_status,
          abstention_status: detail.abstention_status,
          explanation: detail.explanation,
          safe_next_steps: detail.safe_next_steps,
          safety_note: detail.safety_note,
          saved_to_history: true,
          support_urgency: detail.support_urgency,
          support_urgency_band: detail.support_urgency_band,
          support_urgency_rationale: detail.support_urgency_rationale,
          support_urgency_uncertain: detail.support_urgency_uncertain,
          support_resources: [],
        },
        // Rebuild from opening turn so LLM ↔ LLM+RAG can re-run the same text.
        lastCheckIn: openingPayload,
        pipelineMode: "llm",
        chatSupportResources: [],
        toneDisclaimer: null,
        chatDraft: "",
      });
      setCheckInQuery(detail.is_private ? null : detail.id);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to load that check-in conversation.",
      );
    } finally {
      setLoadingThread(false);
    }
  }

  useEffect(() => {
    let cancelled = false;
    async function bootstrapSessions() {
      if (suppressUrlLoadRef.current) return;

      // Logout / account switch: always open a blank check-in (no refresh needed).
      if (consumeForceFreshFlag()) {
        clearPersistedSessions();
        setCheckInQuery(null);
        setArchiveState([]);
        const next = emptySession(newSessionId(), "llm");
        activeSessionIdRef.current = next.id;
        applySession(next);
        // Leave force-fresh cleared; do not re-persist the prior account thread.
        try {
          sessionStorage.removeItem(ANALYSE_FORCE_FRESH_KEY);
          sessionStorage.removeItem(SESSION_STORAGE_KEY);
        } catch {
          // ignore
        }
        return;
      }

      const stored = readPersistedSessions();
      if (stored) {
        const activeId = stored.active?.id;
        const siblings = siblingsOnly(
          stored.archive,
          activeId || "",
        );
        setArchiveState(siblings);
      }

      const checkInId = readCheckInQuery();
      if (checkInId) {
        if (cancelled) return;
        // Guests cannot open account history threads after logout.
        if (!isAuthenticated()) {
          setCheckInQuery(null);
        } else {
          await loadCheckInThread(checkInId);
          return;
        }
      }

      if (stored?.active && sessionHasContent(stored.active)) {
        if (cancelled) return;
        applySession(stored.active);
      }
    }
    void bootstrapSessions();
    return () => {
      cancelled = true;
    };
    // Mount-only: New chat clears ?check_in= via replaceState without remounting.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onPopState() {
      if (suppressUrlLoadRef.current) return;
      const checkInId = readCheckInQuery();
      if (!checkInId) return;
      if (checkInId === activeCheckInIdRef.current) return;
      void loadCheckInThread(checkInId);
    }
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleNewChat() {
    // Invalidate any in-flight analyse/reanalyse before clearing session truth.
    analyseGenerationRef.current += 1;
    analyseLockRef.current = false;
    setIsProcessing(false);
    lastCheckInRef.current = null;

    archiveCurrentIfNeeded();
    suppressUrlLoadRef.current = true;
    setCheckInQuery(null);

    const next = emptySession(newSessionId(), pipelineMode);
    activeSessionIdRef.current = next.id;
    applySession(next);
    persistSessionsNow(next, sessionArchiveRef.current);

    window.setTimeout(() => {
      suppressUrlLoadRef.current = false;
    }, 0);
  }

  function handleSelectArchivedSession(sessionId: string) {
    if (sessionId === activeSessionIdRef.current) return;
    const target = sessionArchiveRef.current.find((s) => s.id === sessionId);
    if (!target) return;
    analyseGenerationRef.current += 1;
    const current = captureActiveSession();
    const without = sessionArchiveRef.current.filter(
      (s) => s.id !== target.id && s.id !== current.id,
    );
    const nextArchive = (
      sessionHasContent(current) ? [current, ...without] : without
    ).slice(0, 12);
    setArchiveState(siblingsOnly(nextArchive, target.id));
    suppressUrlLoadRef.current = true;
    applySession(target);
    setCheckInQuery(target.checkInId);
    persistSessionsNow(target, nextArchive);
    window.setTimeout(() => {
      suppressUrlLoadRef.current = false;
    }, 0);
  }

  function handleSelectRecentCheckIn(checkInId: string) {
    if (checkInId === activeCheckInId) return;
    const archived = sessionArchive.find((s) => s.checkInId === checkInId);
    if (archived) {
      handleSelectArchivedSession(archived.id);
      return;
    }
    archiveCurrentIfNeeded();
    suppressUrlLoadRef.current = true;
    void loadCheckInThread(checkInId).finally(() => {
      window.setTimeout(() => {
        suppressUrlLoadRef.current = false;
      }, 0);
    });
  }

  useEffect(() => {
    if (!isRegisteredUser() || !saveToHistory || analysePrivately) {
      setUsePastCheckins(false);
    } else if (hasSavedHistory) {
      setUsePastCheckins(true);
    }
  }, [loggedIn, saveToHistory, analysePrivately, hasSavedHistory]);

  const hasContent = Boolean(
    text.trim() ||
      files.images.some((i) => i.included && i.extractedText.trim()) ||
      files.pdfs.some((p) => p.included && p.extractedText.trim()),
  );

  const typedWordCount = countWords(text);
  const fileWordCount =
    files.images
      .filter((i) => i.included)
      .reduce((sum, i) => sum + countWords(i.extractedText), 0) +
    files.pdfs
      .filter((p) => p.included)
      .reduce((sum, p) => sum + countWords(p.extractedText), 0);
  const totalWordCount = typedWordCount + fileWordCount;
  const showShortInputTip =
    hasContent &&
    totalWordCount > 0 &&
    totalWordCount < SHORT_INPUT_TIP_WORDS;

  const filesBusy =
    files.images.some((i) => i.status === "uploading") ||
    files.pdfs.some((p) => p.status === "uploading");
  const canSubmit = hasContent && !isProcessing && !filesBusy;

  const developerMode = useMemo(() => {
    if (typeof window === "undefined") return false;
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get("dev") === "1") return true;
      return window.localStorage.getItem("trustmind_dev") === "1";
    } catch {
      return false;
    }
  }, []);

  function clearTimers() {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }

  async function runAnalyse(options: {
    mode: Exclude<PipelineMode, "auto">;
    payload: LastCheckInPayload;
    clearComposer: boolean;
  }) {
    if (analyseLockRef.current) return;
    analyseLockRef.current = true;

    const generation = analyseGenerationRef.current;
    const sessionIdAtStart = activeSessionIdRef.current;

    clearTimers();
    setIsProcessing(true);
    setError(null);
    setSaveNotice(null);
    setShowMoreEvidence(false);
    setPipelineMode(options.mode);
    // Persist payload immediately so mode toggle works even if the request fails.
    lastCheckInRef.current = options.payload;
    setLastCheckIn(options.payload);

    const minDelay = new Promise<void>((resolve) => {
      const finishTimer = window.setTimeout(resolve, PROCESSING_DURATION_MS);
      timersRef.current.push(finishTimer);
    });

    // Mode toggle / re-analyse: do not create a second saved check-in.
    const isReanalyse = !options.clearComposer;
    const wantSave = saveToHistory && !isReanalyse;

    try {
      if (wantSave && !getToken()) {
        await createAnonymousSession();
      }

      const [analysis] = await Promise.all([
        analyseText({
          typed_text: options.payload.typed_text,
          speech_transcript: "",
          image_context: options.payload.image_context,
          pdf_context: options.payload.pdf_context,
          save_to_history: wantSave,
          analyse_privately: analysePrivately,
          use_past_checkins:
            wantSave &&
            !analysePrivately &&
            usePastCheckins &&
            isRegisteredUser(),
          pipeline_mode: options.mode,
          include_debug: developerMode,
        }),
        minDelay,
      ]);

      // New chat / session switch invalidated this run — do not resurrect old thread.
      if (
        generation !== analyseGenerationRef.current ||
        sessionIdAtStart !== activeSessionIdRef.current
      ) {
        return;
      }

      lastCheckInRef.current = options.payload;
      setLastCheckIn(options.payload);
      setResult(analysis);

      const assistantOpening = buildAssistantOpening(analysis);
      // Re-analyse / mode toggle: refresh opening exchange only; keep follow-ups.
      const nextMessages: ChatMessage[] =
        isReanalyse && messagesRef.current.length > 0
          ? messagesAfterReanalyse(
              messagesRef.current,
              options.payload.userOpening,
              assistantOpening,
            )
          : [
              { role: "user", content: options.payload.userOpening },
              { role: "assistant" as const, content: assistantOpening },
            ];
      messagesRef.current = nextMessages;
      setMessages(nextMessages);

      const persistThread = Boolean(
        analysis.id &&
          wantSave &&
          analysis.saved_to_history &&
          !analysePrivately,
      );
      // Re-analyse keeps the existing thread id; first run may attach a new one.
      const nextCheckInId = isReanalyse
        ? activeCheckInIdRef.current
        : persistThread
          ? analysis.id!
          : null;
      setActiveCheckInId(nextCheckInId);
      setChatSupportResources(analysis.support_resources || []);
      setChatError(null);
      setChatDraft("");
      setToneDisclaimer(null);
      // Drop any deep-link so remount / history cannot resurrect a different thread.
      // Session state (incl. lastCheckIn for LLM↔RAG) stays the source of truth here.
      setCheckInQuery(null);
      if (options.clearComposer) {
        setText("");
        files.clearAll();
      }
      setChatMode(true);

      const activeSnapshot: AnalyseSession = {
        id: sessionIdAtStart,
        checkInId: nextCheckInId,
        label: labelFromMessages(
          nextMessages,
          options.payload.typed_text?.trim()
            ? options.payload.typed_text.trim().slice(0, 48)
            : "New chat",
        ),
        chatMode: true,
        messages: nextMessages,
        result: analysis,
        lastCheckIn: options.payload,
        pipelineMode: options.mode,
        chatSupportResources: analysis.support_resources || [],
        toneDisclaimer: null,
        chatDraft: "",
      };
      commitActiveSession(activeSnapshot);

      const pipeline = (analysis.pipeline_used || "").toLowerCase();
      if (pipeline.includes("keyword")) {
        setSaveNotice(
          analysis.message ||
            "AI providers were unavailable, so this used a basic keyword check-in. Replies may stay in English until Groq/Gemini/OpenAI is working again.",
        );
      } else if (wantSave && analysis.saved_to_history) {
        const continuityNote = analysis.continuity_used
          ? " We used your recent saved check-ins so this reflection can pick up where you left off."
          : "";
        setSaveNotice(
          `Saved to your history — you can review it on the Dashboard.${continuityNote}`,
        );
        setHasSavedHistory(true);
        if (isRegisteredUser()) {
          void getCheckIns()
            .then((rows) => setRecentCheckIns(rows.slice(0, 20)))
            .catch(() => {});
        }
      } else if (wantSave && !analysis.saved_to_history) {
        setError(
          "Analysis completed, but saving to history failed. Please try again or check you are still signed in.",
        );
      }
    } catch (err) {
      if (
        generation !== analyseGenerationRef.current ||
        sessionIdAtStart !== activeSessionIdRef.current
      ) {
        return;
      }
      clearTimers();
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to reach the analysis service right now. It may be waking up — wait a few seconds and try again.",
      );
    } finally {
      analyseLockRef.current = false;
      // Always clear the spinner — even if this run was invalidated mid-flight.
      setIsProcessing(false);
    }
  }

  async function handleAnalyse() {
    if (!hasContent || isProcessing || filesBusy) return;

    const image_context = files.images
      .filter((i) => i.status === "processed")
      .map((i) => ({
        filename: i.file.name,
        extracted_text: i.extractedText,
        summary: i.result?.summary || "",
        included: i.included && Boolean(i.extractedText.trim()),
        warnings: i.result?.warnings || [],
      }));
    const pdf_context = files.pdfs
      .filter((p) => p.status === "processed")
      .map((p) => ({
        filename: p.file.name,
        extracted_text: p.extractedText,
        summary: p.result?.document_summary || "",
        included: p.included && Boolean(p.extractedText.trim()),
        warnings: p.result?.warnings || [],
      }));

    await runAnalyse({
      mode: pipelineMode,
      payload: {
        typed_text: text.trim(),
        userOpening: text.trim() || "Shared a multimodal check-in",
        image_context,
        pdf_context,
      },
      clearComposer: true,
    });
  }

  async function handleReanalyse(mode: Exclude<PipelineMode, "auto">) {
    const payload = resolveReanalysePayload();
    if (!payload) {
      setError(
        "Nothing to re-analyse yet — send a check-in first, then switch LLM ↔ LLM+RAG.",
      );
      return;
    }
    lastCheckInRef.current = payload;
    setLastCheckIn(payload);
    await runAnalyse({
      mode,
      payload,
      clearComposer: false,
    });
  }

  function handlePipelineModeSelect(mode: Exclude<PipelineMode, "auto">) {
    if (pipelineMode === mode) return;
    // Immediate UI feedback; never loadCheckInThread from mode switch.
    setPipelineMode(mode);
    const payload = resolveReanalysePayload();
    if (!payload) {
      setError(
        "Nothing to re-analyse yet — send a check-in first, then switch LLM ↔ LLM+RAG.",
      );
      return;
    }
    lastCheckInRef.current = payload;
    setLastCheckIn(payload);
    void handleReanalyse(mode);
  }

  async function handleChatSend() {
    const outgoing = chatDraft.trim();
    if (!outgoing || chatSending) return;
    setChatSending(true);
    setChatError(null);
    setChatDraft("");
    const prior = messages;
    setMessages([
      ...prior,
      { role: "user", content: outgoing, input_type: "text" },
    ]);
    try {
      const response = await sendChatFollowUp({
        message: outgoing,
        check_in_id: activeCheckInId,
        history: activeCheckInId ? undefined : prior,
      });
      setMessages(response.messages);
      if (response.persisted && response.check_in_id) {
        setActiveCheckInId(response.check_in_id);
      }
      if (response.support_resources?.length) {
        setChatSupportResources(response.support_resources);
      }
    } catch (err) {
      setMessages(prior);
      setChatDraft(outgoing);
      setChatError(
        err instanceof ApiError
          ? err.message
          : "Unable to send your follow-up. Please try again.",
      );
    } finally {
      setChatSending(false);
    }
  }

  async function handleChatSendAudio(file: Blob, filename: string) {
    if (chatSending) return;
    setChatSending(true);
    setChatError(null);
    const prior = messages;
    setMessages([
      ...prior,
      {
        role: "user",
        content: "Audio message",
        input_type: "audio",
        transcript: "Transcribing…",
      },
    ]);
    try {
      const response = await sendChatFollowUpAudio({
        file,
        filename,
        check_in_id: activeCheckInId,
        history: activeCheckInId ? undefined : prior,
      });
      setMessages(response.messages);
      if (response.persisted && response.check_in_id) {
        setActiveCheckInId(response.check_in_id);
      }
      if (response.support_resources?.length) {
        setChatSupportResources(response.support_resources);
      }
      if (response.tone_disclaimer) {
        setToneDisclaimer(response.tone_disclaimer);
      }
    } catch (err) {
      setMessages(prior);
      setChatError(
        err instanceof ApiError
          ? err.message
          : "Unable to send your audio message. Please try again or type instead.",
      );
    } finally {
      setChatSending(false);
    }
  }

  const chatSubtitle = activeCheckInId
    ? null
    : loggedIn
      ? "Session thread — not saved to your history (private or unsaved check-in)"
      : "Session only — this chat isn’t saved while you’re signed out";

  useEffect(() => {
    return () => clearTimers();
  }, []);

  const privacyStatus = analysePrivately
    ? saveToHistory
      ? "Private mode · Metadata saved without raw text"
      : "Private mode · Raw text is not stored"
    : saveToHistory
      ? "Check-in will be saved to your history"
      : "Analysis processed securely · Not saved to history";

  const evidenceAll = result ? evidenceFromResult(result) : [];
  const evidenceVisible = showMoreEvidence
    ? evidenceAll
    : evidenceAll.slice(0, 3);
  const resultIsStandaloneLlm = result
    ? isStandaloneLlmPipeline(result)
    : pipelineMode === "llm";
  const ranAsRagIntent =
    pipelineMode === "rag" ||
    (result?.pipeline_used || "").toUpperCase().includes("RAG");
  const isQuotaFallback = (result?.pipeline_used || "")
    .toLowerCase()
    .includes("keyword");
  const canReanalyse =
    Boolean(resolveReanalysePayload()) && !isProcessing;

  const liveThreadLabel = chatMode
    ? labelFromMessages(messages, "Current chat")
    : text.trim()
      ? "Draft"
      : "New chat";

  const recentPickerOptions = recentCheckIns.filter((row) => {
    if (row.id === activeCheckInId) return false;
    if (sessionArchive.some((s) => s.checkInId === row.id)) return false;
    return true;
  });

  const showThreadSwitcher =
    sessionArchive.length > 0 ||
    recentPickerOptions.length > 0 ||
    chatMode ||
    Boolean(activeCheckInId);

  const displaySupportResources: SupportResource[] = (() => {
    if (chatSupportResources.length > 0) return chatSupportResources;
    if (result?.support_resources?.length) return result.support_resources;
    const band = result?.support_urgency_band;
    const concern = (result?.concern_level || "").toLowerCase();
    const serious =
      Boolean(result?.safety_triggered) ||
      band === "urgent" ||
      band === "elevated" ||
      concern === "high" ||
      concern === "moderate";
    return serious ? FALLBACK_SUPPORT_RESOURCES : [];
  })();

  const supportResourcesPanel =
    displaySupportResources.length > 0 ? (
      <div
        className="rounded-xl border-2 border-rose-300 bg-rose-50/90 px-4 py-4 dark:border-rose-800 dark:bg-rose-950/50"
        role="alert"
      >
        <p className="text-xs font-medium uppercase tracking-wide text-rose-800 dark:text-rose-300">
          Support / ethics resources
        </p>
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
          If you are in immediate danger, call 999 or go to A&amp;E. These
          services can help you talk to someone — NHS, Samaritans, Student
          Minds, UWE wellbeing.
        </p>
        <ul className="mt-3 space-y-3">
          {displaySupportResources.map((resource) => (
            <li
              key={resource.name}
              className="rounded-lg border border-rose-200/80 bg-white/70 px-3 py-2.5 dark:border-rose-900 dark:bg-slate-900/50"
            >
              <p className="font-medium text-slate-800 dark:text-slate-100">
                {resource.name}
              </p>
              {resource.description ? (
                <p className="mt-0.5 text-sm text-slate-600 dark:text-slate-400">
                  {resource.description}
                </p>
              ) : null}
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {resource.contact}
              </p>
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-block text-sm font-semibold text-teal-700 underline dark:text-teal-300"
              >
                Open {resource.name}
              </a>
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  // Strip provider suffix e.g. "LLM+RAG (groq)" → "LLM+RAG"
  const pipelineLabel = (
    result?.pipeline_used ||
    (resultIsStandaloneLlm ? "LLM" : "LLM+RAG")
  )
    .replace(/\s*\([^)]*\)\s*$/g, "")
    .replace(/^keyword_fallback$/i, "Basic check-in (AI busy)")
    .trim();

  const trustDetailsCard = result ? (
    <div className="rounded-xl border border-slate-200/80 bg-white/90 px-4 py-4 dark:border-slate-700/80 dark:bg-slate-900/90">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Trust details
          </p>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            Updates each time you re-analyse — useful for LLM vs LLM+RAG.
          </p>
        </div>
        {activeCheckInId ? (
          <Link
            href={`/dashboard/${activeCheckInId}`}
            className="text-sm text-teal-700 underline dark:text-teal-300"
          >
            View saved check-in
          </Link>
        ) : null}
      </div>

      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
        <div className="sm:col-span-2">
          <dt className="text-slate-500 dark:text-slate-400">
            What it sounds like
          </dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {result.prediction_display ||
              predictionDisplayName(result.prediction) ||
              result.concern_level ||
              "—"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">
            How sure we are
          </dt>
          <dd className="mt-0.5 font-medium tabular-nums text-slate-800 dark:text-slate-100">
            {result.ai_confidence ||
              (typeof result.confidence === "number"
                ? `${Math.round(result.confidence * 100)}%`
                : "—")}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Uncertainty</dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {result.uncertainty_level || result.uncertainty || "—"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Concern</dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {result.concern_level || "—"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Abstention</dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {result.abstention_status ||
              (result.status === "abstained"
                ? "Paused / abstained"
                : "Prediction accepted")}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">
            Grounding status
          </dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {evidenceAll.length > 0
              ? "Matched trusted guidance"
              : isQuotaFallback
                ? "Basic check-in (AI providers busy)"
                : resultIsStandaloneLlm && !ranAsRagIntent
                  ? "Not used in LLM-only mode"
                  : result.grounding_status &&
                      !/keyword|llm_only|formula|provider_/i.test(
                        result.grounding_status,
                      )
                    ? result.grounding_status
                    : "No matching sources this time"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-500 dark:text-slate-400">Pipeline used</dt>
          <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
            {pipelineLabel}
          </dd>
        </div>
      </dl>

      {(result.potential_indicators?.length
        ? result.potential_indicators
        : result.early_signs || []
      ).length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {(result.potential_indicators?.length
            ? result.potential_indicators
            : result.early_signs || []
          ).map((theme) => (
            <span
              key={theme}
              className="rounded-full border border-teal-200/80 bg-teal-50/70 px-2.5 py-0.5 text-[11px] font-medium text-teal-800 dark:border-teal-800 dark:bg-teal-950/40 dark:text-teal-200"
            >
              {theme}
            </span>
          ))}
        </div>
      ) : null}

      {typeof result.support_urgency === "number" &&
      result.support_urgency_band ? (
        <div className="mt-4">
          <SupportUrgencyMeter
            score={result.support_urgency}
            band={result.support_urgency_band}
            rationale={result.support_urgency_rationale}
            uncertain={Boolean(result.support_urgency_uncertain)}
          />
        </div>
      ) : null}
    </div>
  ) : null;

  const friendlyTrustSummary = (() => {
    if (!result) return "";
    if (evidenceAll.length > 0) {
      return `This reflection drew on ${evidenceAll.length} trusted guidance source${
        evidenceAll.length === 1 ? "" : "s"
      } (for example NHS or university wellbeing pages).`;
    }
    if (ranAsRagIntent && isQuotaFallback) {
      return "You chose LLM+RAG, but AI providers hit a temporary limit, so this used a basic check-in. Trusted guidance pages should still appear below when the knowledge base matches — or try Re-analyse in a few minutes.";
    }
    if (resultIsStandaloneLlm && !ranAsRagIntent) {
      return "This check-in used the model on its own — no trusted guidance pages were pulled in. Switch to LLM+RAG on the same text to compare.";
    }
    if (ranAsRagIntent) {
      return "LLM+RAG ran, but no matching guidance pages were found for this check-in. A little more detail about how you feel usually helps.";
    }
    return "We looked for matching guidance pages, but nothing close enough came back this time.";
  })();

  const showAsStandalonePanel =
    resultIsStandaloneLlm && !ranAsRagIntent && evidenceAll.length === 0;

  const groundingReliabilityPanel = result ? (
    <div
      className={`rounded-xl border px-4 py-4 ${
        showAsStandalonePanel
          ? "border-amber-200/80 bg-amber-50/50 dark:border-amber-900/70 dark:bg-amber-950/30"
          : "border-indigo-200/70 bg-indigo-50/40 dark:border-indigo-900/70 dark:bg-indigo-950/25"
      }`}
    >
      <p
        className={`text-xs font-medium uppercase tracking-wide ${
          showAsStandalonePanel
            ? "text-amber-800 dark:text-amber-300"
            : "text-indigo-700 dark:text-indigo-300"
        }`}
      >
        {showAsStandalonePanel
          ? "Standalone model"
          : isQuotaFallback
            ? "Grounding (limited)"
            : "Grounding & reliability"}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
        {friendlyTrustSummary}
      </p>
      {!showAsStandalonePanel ? (
        <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500 dark:text-slate-400">
              Guidance used
            </dt>
            <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
              {evidenceAll.length > 0
                ? `${evidenceAll.length} trusted source${
                    evidenceAll.length === 1 ? "" : "s"
                  }`
                : isQuotaFallback
                  ? "Waiting on AI providers — try re-analyse shortly"
                  : "None matched this check-in"}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500 dark:text-slate-400">
              Grounding status
            </dt>
            <dd className="mt-0.5 font-medium text-slate-800 dark:text-slate-100">
              {evidenceAll.length > 0
                ? "Matched trusted guidance"
                : isQuotaFallback
                  ? "Basic check-in (AI providers busy)"
                  : "No matching sources this time"}
            </dd>
          </div>
        </dl>
      ) : null}
    </div>
  ) : null;

  const pipelineCompareBar = (
    <div className="rounded-xl border border-slate-200/80 bg-white/90 px-4 py-3 dark:border-slate-700/80 dark:bg-slate-900/90">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Compare assessment mode
          </p>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {canReanalyse
              ? "Switch LLM ↔ LLM+RAG and re-run the same check-in text."
              : "Re-analyse needs a check-in from this page (not available for opened history threads)."}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div
            className="inline-flex rounded-lg border border-slate-200 p-0.5 dark:border-slate-600"
            role="radiogroup"
            aria-label="Assessment mode"
          >
            <button
              type="button"
              role="radio"
              aria-checked={pipelineMode === "llm"}
              disabled={isProcessing}
              onClick={() => handlePipelineModeSelect("llm")}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                pipelineMode === "llm"
                  ? "bg-teal-600 text-white dark:bg-teal-500"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              LLM
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={pipelineMode === "rag"}
              disabled={isProcessing}
              onClick={() => handlePipelineModeSelect("rag")}
              className={`rounded-md px-3 py-1.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                pipelineMode === "rag"
                  ? "bg-teal-600 text-white dark:bg-teal-500"
                  : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
              }`}
            >
              LLM+RAG
            </button>
          </div>
          <button
            type="button"
            disabled={!canReanalyse}
            onClick={() => void handleReanalyse(pipelineMode)}
            className="inline-flex items-center gap-1.5 rounded-lg border border-teal-300 bg-teal-50 px-3 py-1.5 text-sm font-semibold text-teal-800 transition-colors hover:bg-teal-100 disabled:cursor-not-allowed disabled:opacity-50 dark:border-teal-700 dark:bg-teal-950/50 dark:text-teal-200 dark:hover:bg-teal-950"
          >
            {isProcessing ? (
              <>
                <Spinner className="h-3.5 w-3.5" />
                Re-analysing…
              </>
            ) : (
              "Re-analyse"
            )}
          </button>
        </div>
      </div>
      {result ? (
        <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
          Last run:{" "}
          <span className="font-medium text-slate-700 dark:text-slate-200">
            {pipelineLabel}
          </span>
          {evidenceAll.length > 0 ? (
            <> · Grounding: matched trusted guidance</>
          ) : ranAsRagIntent && isQuotaFallback ? (
            <> · Grounding: AI providers busy — try again shortly</>
          ) : resultIsStandaloneLlm && !ranAsRagIntent ? (
            <> · Grounding: not used in this mode</>
          ) : (
            <> · Grounding: no matching sources this time</>
          )}
        </p>
      ) : null}
    </div>
  );

  const groundedSourcesPanel = result ? (
      <div className="rounded-xl border-2 border-teal-400/80 bg-teal-50/50 px-4 py-4 shadow-sm dark:border-teal-600/80 dark:bg-teal-950/30">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <p className="text-xs font-medium uppercase tracking-wide text-teal-800 dark:text-teal-300">
            Grounded sources / retrieved passages
          </p>
          {!resultIsStandaloneLlm && evidenceAll.length > 0 ? (
            <span className="rounded-full bg-teal-600 px-2.5 py-0.5 text-[11px] font-semibold text-white dark:bg-teal-500">
              {evidenceAll.length} source{evidenceAll.length === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>
        {showAsStandalonePanel ? (
          <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            This check-in used the model on its own, so no trusted guidance
            pages were pulled in. Switch to{" "}
            <span className="font-semibold">LLM+RAG</span> and re-analyse the
            same text to see supporting extracts from places like the NHS,
            Samaritans, or UWE wellbeing.
          </p>
        ) : evidenceVisible.length > 0 ? (
          <>
            <p className="mt-2 text-xs text-slate-600 dark:text-slate-400">
              Supporting extracts used for this reflection — from trusted
              wellbeing guidance, not invented by the model.
            </p>
            <ul className="mt-3 space-y-4">
              {evidenceVisible.map((item, idx) => (
                <li
                  key={`${item.source_id}-${idx}`}
                  className="rounded-lg border border-teal-200/80 bg-white/80 px-3 py-3 dark:border-teal-900 dark:bg-slate-900/60"
                >
                  <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">
                    {item.display_label ||
                      `${item.organisation} — ${item.title}`}
                  </p>
                  {item.snippet ? (
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                      {item.snippet}
                    </p>
                  ) : item.reason_retrieved ? (
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {item.reason_retrieved}
                    </p>
                  ) : null}
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
                    {item.url ? (
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-teal-700 underline dark:text-teal-300"
                      >
                        Open source
                      </a>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
            {evidenceAll.length > 3 ? (
              <button
                type="button"
                className="mt-3 text-sm font-medium text-teal-700 underline dark:text-teal-300"
                onClick={() => setShowMoreEvidence((open) => !open)}
              >
                {showMoreEvidence ? "Show fewer sources" : "Show more sources"}
              </button>
            ) : null}
          </>
        ) : result.sources && result.sources.length > 0 ? (
          <ul className="mt-3 space-y-2">
            {result.sources.map((source) => (
              <li
                key={source}
                className="text-sm leading-relaxed text-slate-700 dark:text-slate-300"
              >
                {source}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm leading-relaxed text-amber-900 dark:text-amber-100">
            {ranAsRagIntent && isQuotaFallback
              ? "You selected LLM+RAG, but AI providers are temporarily limited, so trusted pages could not be fully loaded. Wait a few minutes and press Re-analyse — or set LLM_PROVIDER=auto with OpenAI on the server as a backstop."
              : "We looked for trusted guidance pages that match what you shared, but nothing close enough came back this time. A little more detail about how you feel — and for how long — usually helps us find useful sources."}
          </p>
        )}
      </div>
    ) : null;

  const settingsPanel = (
    <details className="group rounded-xl border border-slate-200 bg-white/70 dark:border-slate-700 dark:bg-slate-900/70">
      <summary className="cursor-pointer list-none px-3 py-2.5 text-sm font-medium text-slate-700 outline-none marker:content-none dark:text-slate-200 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center justify-between gap-3">
          <span>Privacy options</span>
          <span className="text-xs font-normal text-slate-500 transition group-open:rotate-180 dark:text-slate-400">
            ▾
          </span>
        </span>
      </summary>
      <div className="space-y-4 border-t border-slate-200 px-3 py-3 dark:border-slate-700">
        <Toggle
          id="save-history"
          label={
            loggedIn
              ? "Save this check-in to my history (on by default while signed in)"
              : "Save this check-in to my history"
          }
          description={
            loggedIn
              ? "Stores a summary on your Dashboard. Turn off if you do not want this check-in saved. Original audio, images and PDFs are never saved."
              : "Store a summary in your dashboard for future reference. Original audio, images and PDFs are never saved."
          }
          checked={saveToHistory}
          onChange={setSaveToHistory}
          disabled={isProcessing}
        />
        <Toggle
          id="analyse-privately"
          label="Analyse privately"
          description="Process without storing raw text, transcripts, or file contents. When save is on, only metadata is kept. Continuity memory is off in private mode."
          checked={analysePrivately}
          onChange={setAnalysePrivately}
          disabled={isProcessing}
        />
        {isRegisteredUser() &&
          hasSavedHistory &&
          saveToHistory &&
          !analysePrivately && (
            <Toggle
              id="use-past-checkins"
              label="Use past check-ins"
              description="Includes up to your last few non-private saved check-ins as gentle continuity context — not a full chat thread."
              checked={usePastCheckins}
              onChange={setUsePastCheckins}
              disabled={isProcessing}
            />
          )}
        <p className="text-xs text-slate-500 dark:text-slate-400">{privacyStatus}</p>
      </div>
    </details>
  );

  return (
    <div className="space-y-4">
      {showThreadSwitcher && (
        <div className="flex flex-col gap-2 rounded-xl border border-slate-200/80 bg-white/90 px-3 py-2.5 dark:border-slate-700/80 dark:bg-slate-900/90 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 flex-1">
            <label
              htmlFor="analyse-thread-switcher"
              className="text-[11px] font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400"
            >
              Chats
            </label>
            <select
              id="analyse-thread-switcher"
              key={activeSessionId}
              className="mt-1 w-full truncate rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-sm text-slate-800 dark:border-slate-600 dark:bg-slate-950 dark:text-slate-100"
              value={`active:${activeSessionId}`}
              onChange={(event) => {
                const value = event.target.value;
                if (value === `active:${activeSessionId}`) return;
                if (value.startsWith("archive:")) {
                  const id = value.slice("archive:".length);
                  if (id === activeSessionId) return;
                  handleSelectArchivedSession(id);
                  return;
                }
                if (value.startsWith("checkin:")) {
                  handleSelectRecentCheckIn(value.slice("checkin:".length));
                }
              }}
            >
              <option value={`active:${activeSessionId}`}>
                {liveThreadLabel}
                {activeCheckInId ? " · saved" : ""}
              </option>
              {sessionArchive
                .filter((session) => session.id !== activeSessionId)
                .map((session) => (
                <option key={session.id} value={`archive:${session.id}`}>
                  {session.label}
                  {session.checkInId ? " · saved" : " · session"}
                </option>
              ))}
              {recentPickerOptions.length > 0 ? (
                <optgroup label="From dashboard">
                  {recentPickerOptions.map((row) => (
                    <option key={row.id} value={`checkin:${row.id}`}>
                      {(row.preview || "Saved check-in").slice(0, 48)}
                      {row.preview && row.preview.length > 48 ? "…" : ""}
                    </option>
                  ))}
                </optgroup>
              ) : null}
            </select>
          </div>
          <button
            type="button"
            onClick={handleNewChat}
            className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50/60 dark:border-slate-600 dark:text-slate-200 dark:hover:border-teal-700 dark:hover:bg-teal-950/40"
          >
            New chat
          </button>
        </div>
      )}

      {error && (
        <div
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100"
          role="alert"
        >
          <p className="font-semibold">{error}</p>
        </div>
      )}
      {saveNotice && !error && (
        <div
          className="rounded-xl border border-teal-200 bg-teal-50 px-4 py-3 text-sm text-teal-900 dark:border-teal-900 dark:bg-teal-950/40 dark:text-teal-100"
          role="status"
        >
          <p className="font-medium">{saveNotice}</p>
          <Link
            href="/dashboard"
            className="mt-2 inline-flex text-sm font-semibold text-teal-800 underline-offset-2 hover:underline dark:text-teal-200"
          >
            Open Dashboard
          </Link>
        </div>
      )}

      {loadingThread && (
        <div className="rounded-2xl border border-slate-200 bg-white p-10 text-center shadow-sm dark:border-slate-700 dark:bg-slate-900">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Loading conversation…
          </p>
        </div>
      )}

      {chatMode && !loadingThread && (
        <div className="space-y-4">
          <ChatThread
            messages={messages}
            draft={chatDraft}
            onDraftChange={setChatDraft}
            onSend={() => void handleChatSend()}
            onSendAudio={(file, filename) =>
              void handleChatSendAudio(file, filename)
            }
            isSending={chatSending || isProcessing}
            error={chatError}
            supportResources={
              // Prefer the dedicated panel under Grounded sources; avoid duplicate
              // crisis cards inside the thread when that panel is shown.
              supportResourcesPanel ? [] : chatSupportResources
            }
            persisted={Boolean(activeCheckInId)}
            subtitle={chatSubtitle}
            toneDisclaimer={toneDisclaimer}
            onNewChat={handleNewChat}
          />

          {pipelineCompareBar}
          {trustDetailsCard}
          {groundingReliabilityPanel}
          {groundedSourcesPanel}
          {supportResourcesPanel}

          {result && (
            <div className="space-y-3">
              {result.safe_next_steps && result.safe_next_steps.length > 0 && (
                <div className="rounded-xl border border-teal-200/70 bg-teal-50/40 px-4 py-4 dark:border-teal-900/70 dark:bg-teal-950/25">
                  <p className="text-xs font-medium uppercase tracking-wide text-teal-700 dark:text-teal-300">
                    Supportive next steps
                  </p>
                  <ul className="mt-3 space-y-2">
                    {result.safe_next_steps.map((step) => (
                      <li
                        key={step}
                        className="flex items-start gap-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300"
                      >
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
                        {step}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="space-y-2 rounded-xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-800/60">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                  A note on care
                </p>
                <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                  {result.disclaimer ||
                    "This tool provides wellbeing support information and should not be considered a medical diagnosis."}
                </p>
                {result.human_oversight ? (
                  <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {result.human_oversight}
                  </p>
                ) : null}
                {result.privacy_notice ? (
                  <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                    {result.privacy_notice}
                  </p>
                ) : null}
                <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  Curious about confidence, grounding, or how LLM vs LLM+RAG
                  works?{" "}
                  <Link
                    href="/#how-it-works"
                    className="text-teal-700 underline dark:text-teal-300"
                  >
                    See How it works
                  </Link>
                  .
                </p>
              </div>

              {result.safety_note ? (
                <div className="rounded-xl border border-amber-100 bg-amber-50/60 p-4 dark:border-amber-900 dark:bg-amber-950/40">
                  <p className="text-xs font-medium uppercase tracking-wide text-amber-700 dark:text-amber-300">
                    Safety disclaimer
                  </p>
                  <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {result.safety_note}
                  </p>
                </div>
              ) : null}

              <div className="pt-1">{settingsPanel}</div>
            </div>
          )}
        </div>
      )}

      {!chatMode && !loadingThread && (
        <>

        <div className="flex min-h-[70vh] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900">
          <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 dark:border-slate-700/80 sm:px-5">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
                Check-in conversation
              </p>
              <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                Share how you&apos;re feeling — then keep talking here
              </p>
            </div>
            {(sessionArchive.length > 0 || Boolean(activeCheckInId)) && (
              <button
                type="button"
                onClick={handleNewChat}
                className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50/60 dark:border-slate-600 dark:text-slate-200 dark:hover:border-teal-700 dark:hover:bg-teal-950/40"
              >
                New chat
              </button>
            )}
          </div>

          <div className="flex flex-1 flex-col justify-center px-4 py-10 sm:px-5">
            {isProcessing ? (
              <div
                className="flex flex-col items-center text-center"
                aria-live="polite"
                aria-busy="true"
              >
                <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-teal-100 text-teal-700 dark:bg-teal-950/50 dark:text-teal-300">
                  <Spinner className="h-6 w-6" />
                </span>
                <h2 className="mt-4 text-lg font-semibold text-slate-800 dark:text-slate-100">
                  Looking at what you&apos;ve shared
                </h2>
                <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
                  This usually takes a few seconds. If the API was idle, free
                  hosting may need up to about a minute to wake up first.
                </p>
              </div>
            ) : (
              <div className="mx-auto max-w-md text-center">
                <p className="text-sm text-slate-500 dark:text-slate-400">
                  No messages yet. Share what&apos;s on your mind below — type,
                  speak, or attach a file.
                </p>
                <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
                  Only share what you&apos;re comfortable with. This is not a
                  medical diagnosis.
                </p>
              </div>
            )}
          </div>

          <div className="border-t border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-700/80 dark:bg-slate-950/40 sm:px-5">
            <CheckInComposer
              embedded
              value={text}
              onChange={(next) => {
                setText(next);
                if (error) setError(null);
              }}
              disabled={isProcessing}
              canSubmit={canSubmit}
              isProcessing={isProcessing}
              onSubmit={() => void handleAnalyse()}
              images={files.images}
              pdfs={files.pdfs}
              fileError={files.error}
              onAddFiles={(f) => void files.addFiles(f)}
              onRemoveImage={files.removeImage}
              onRemovePdf={files.removePdf}
              onUpdateImageText={files.updateImageText}
              onUpdatePdfText={files.updatePdfText}
              onToggleImage={files.toggleImageIncluded}
              onTogglePdf={files.togglePdfIncluded}
              shortTip={showShortInputTip ? SHORT_INPUT_TIP : null}
              shortExample={showShortInputTip ? SHORT_INPUT_EXAMPLE : null}
            />
            <p className="mt-2 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
              {INPUT_GUIDANCE}
            </p>
          </div>
        </div>
        <div className="mt-4">{settingsPanel}</div>
      </>
      )}
    </div>
  );
}

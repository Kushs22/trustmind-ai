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
  type ChatMessage,
  type EvidenceItem,
  type PipelineMode,
  type SupportResource,
} from "@/lib/api";
import {
  AUTH_CHANGED_EVENT,
  getToken,
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

function isStandaloneLlmPipeline(result: AnalyseResponse): boolean {
  const pipeline = (result.pipeline_used || "").toUpperCase();
  if (result.grounding?.status === "not_applicable") return true;
  // Anything without RAG (LLM-only, keyword fallback, empty) has no retrieved sources.
  return !pipeline.includes("RAG");
}

function evidenceFromResult(result: AnalyseResponse): EvidenceItem[] {
  if (isStandaloneLlmPipeline(result)) return [];
  if (result.evidence_used?.length) return result.evidence_used;
  if (result.sources_detail?.length) return result.sources_detail;
  return [];
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
  const timersRef = useRef<number[]>([]);
  const files = useFileUpload();

  useEffect(() => {
    function syncAuthDefaults() {
      const authed = isAuthenticated();
      const registered = isRegisteredUser();
      setLoggedIn(authed);
      if (authed) {
        setSaveToHistory(true);
        setAnalysePrivately(false);
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
            const usable = rows.some((r) => !r.is_private && Boolean(r.preview));
            setHasSavedHistory(usable || rows.length > 0);
            setUsePastCheckins(usable || preferContinue);
          })
          .catch(() => {
            setHasSavedHistory(false);
            setUsePastCheckins(preferContinue);
          });
      } else {
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
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadThreadFromQuery() {
      let checkInId: string | null = null;
      try {
        checkInId = new URLSearchParams(window.location.search).get("check_in");
      } catch {
        checkInId = null;
      }
      if (!checkInId) return;
      if (!isAuthenticated()) {
        setError("Please log in to continue a saved check-in chat.");
        return;
      }
      setLoadingThread(true);
      setError(null);
      try {
        const detail = await getCheckIn(checkInId);
        if (cancelled) return;
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
        setMessages(seeded);
        setActiveCheckInId(detail.is_private ? null : detail.id);
        setChatMode(true);
        setResult({
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
        });
      } catch (err) {
        if (cancelled) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "Unable to load that check-in conversation.",
        );
      } finally {
        if (!cancelled) setLoadingThread(false);
      }
    }
    void loadThreadFromQuery();
    return () => {
      cancelled = true;
    };
  }, []);

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
    if (isProcessing) return;

    clearTimers();
    setIsProcessing(true);
    setError(null);
    setSaveNotice(null);
    setShowMoreEvidence(false);
    setPipelineMode(options.mode);

    const minDelay = new Promise<void>((resolve) => {
      const finishTimer = window.setTimeout(resolve, PROCESSING_DURATION_MS);
      timersRef.current.push(finishTimer);
    });

    const wantSave = saveToHistory;

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

      setLastCheckIn(options.payload);
      setResult(analysis);

      const assistantOpening = buildAssistantOpening(analysis);
      setMessages([
        { role: "user", content: options.payload.userOpening },
        ...(assistantOpening
          ? [{ role: "assistant" as const, content: assistantOpening }]
          : []),
      ]);

      const persistThread = Boolean(
        analysis.id &&
          wantSave &&
          analysis.saved_to_history &&
          !analysePrivately,
      );
      setActiveCheckInId(persistThread ? analysis.id! : null);
      setChatSupportResources(analysis.support_resources || []);
      setChatError(null);
      setChatDraft("");
      setToneDisclaimer(null);
      if (options.clearComposer) {
        setText("");
        files.clearAll();
      }
      setChatMode(true);

      const pipeline = (analysis.pipeline_used || "").toLowerCase();
      if (pipeline.includes("keyword")) {
        setSaveNotice(
          analysis.message ||
            "AI providers were unavailable, so this used a basic keyword check-in. Replies may stay in English until Groq/Gemini is working again.",
        );
      } else if (wantSave && analysis.saved_to_history) {
        const continuityNote = analysis.continuity_used
          ? " We used your recent saved check-ins so this reflection can pick up where you left off."
          : "";
        setSaveNotice(
          `Saved to your history — you can review it on the Dashboard.${continuityNote}`,
        );
        setHasSavedHistory(true);
      } else if (wantSave && !analysis.saved_to_history) {
        setError(
          "Analysis completed, but saving to history failed. Please try again or check you are still signed in.",
        );
      }
    } catch (err) {
      clearTimers();
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to reach the analysis service right now. It may be waking up — wait a few seconds and try again.",
      );
    } finally {
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
    if (!lastCheckIn || isProcessing) return;
    await runAnalyse({
      mode,
      payload: lastCheckIn,
      clearComposer: false,
    });
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
  const canReanalyse = Boolean(lastCheckIn) && !isProcessing;

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
        className="rounded-xl border border-rose-200 bg-rose-50/80 px-4 py-4 dark:border-rose-900 dark:bg-rose-950/40"
        role="alert"
      >
        <p className="text-xs font-medium uppercase tracking-wide text-rose-700 dark:text-rose-300">
          Support resources
        </p>
        <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
          If you are in immediate danger, call 999 or go to A&amp;E. These
          services can help you talk to someone.
        </p>
        <ul className="mt-3 space-y-3">
          {displaySupportResources.map((resource) => (
            <li
              key={resource.name}
              className="text-sm text-slate-700 dark:text-slate-300"
            >
              <p className="font-medium text-slate-800 dark:text-slate-100">
                {resource.name}
              </p>
              {resource.description ? (
                <p className="mt-0.5 text-slate-600 dark:text-slate-400">
                  {resource.description}
                </p>
              ) : null}
              <p className="text-slate-600 dark:text-slate-400">
                {resource.contact}
              </p>
              <a
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-1 inline-block text-teal-700 underline dark:text-teal-300"
              >
                Open resource
              </a>
            </li>
          ))}
        </ul>
      </div>
    ) : null;

  const pipelineLabel =
    result?.pipeline_used ||
    (resultIsStandaloneLlm ? "LLM" : "LLM+RAG");

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
            {result.grounding_status ||
              result.grounding?.label ||
              (resultIsStandaloneLlm ? "Not applicable (LLM-only)" : "—")}
          </dd>
        </div>
        <div className="sm:col-span-2">
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

  const pipelineCompareBar = (
    <div className="rounded-xl border border-slate-200/80 bg-white/90 px-4 py-3 dark:border-slate-700/80 dark:bg-slate-900/90">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
            Compare assessment mode
          </p>
          <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
            {lastCheckIn
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
              disabled={isProcessing || !lastCheckIn}
              onClick={() => {
                if (pipelineMode === "llm") return;
                void handleReanalyse("llm");
              }}
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
              disabled={isProcessing || !lastCheckIn}
              onClick={() => {
                if (pipelineMode === "rag") return;
                void handleReanalyse("rag");
              }}
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
          {result.grounding_status ? (
            <>
              {" "}
              · Grounding: {result.grounding_status}
            </>
          ) : null}
        </p>
      ) : null}
    </div>
  );

  const groundedSourcesPanel = result ? (
      <div className="rounded-xl border border-teal-200/70 bg-teal-50/30 px-4 py-4 dark:border-teal-900/70 dark:bg-teal-950/20">
        <p className="text-xs font-medium uppercase tracking-wide text-teal-700 dark:text-teal-300">
          Grounded sources
        </p>
        {resultIsStandaloneLlm ? (
          <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            Standalone model response — no retrieved guidance sources for this
            mode.
          </p>
        ) : evidenceVisible.length > 0 ? (
          <>
            <ul className="mt-3 space-y-3">
              {evidenceVisible.map((item) => (
                <li key={item.source_id}>
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                    {item.display_label ||
                      `${item.organisation} — ${item.title}`}
                  </p>
                  {item.snippet ? (
                    <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {item.snippet}
                    </p>
                  ) : item.reason_retrieved ? (
                    <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                      {item.reason_retrieved}
                    </p>
                  ) : null}
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-1 inline-block text-sm text-teal-700 underline dark:text-teal-300"
                    >
                      View source
                    </a>
                  ) : null}
                  {developerMode ? (
                    <p className="mt-1 text-xs text-slate-400">
                      ID: {item.source_id}
                      {typeof item.retrieval_score === "number"
                        ? ` · score ${item.retrieval_score.toFixed(3)}`
                        : ""}
                    </p>
                  ) : null}
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
          <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            LLM+RAG ran, but no guidance passages were retrieved for this
            check-in.
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
          {trustDetailsCard}
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
          />

          {pipelineCompareBar}
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

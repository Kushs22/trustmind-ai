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
import { AUTH_CHANGED_EVENT, getToken, isAuthenticated, isRegisteredUser } from "@/lib/auth";
import { indicatorDisplayName, predictionDisplayName } from "@/lib/displayLabels";
import { useFileUpload } from "@/hooks/useFileUpload";

const PROCESSING_DURATION_MS = 350;

/** Soft guidance only — never disables Analyse; one-word check-ins are allowed. */
const SHORT_INPUT_TIP_WORDS = 12;
const INPUT_GUIDANCE =
  "The more you share, the better we can support you. A few sentences about how long this has lasted and how it affects sleep, study, or daily life often helps — one-word check-ins still work.";
const SHORT_INPUT_TIP =
  "Optional tip: adding a little more detail usually improves how well we can reflect what you're going through — short check-ins are still welcome.";
const SHORT_INPUT_EXAMPLE =
  "I've been feeling stressed for about two weeks. It's hard to sleep and I'm falling behind on coursework. Things feel heavier than usual.";

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

export function AnalyseForm() {
  const [text, setText] = useState("");
  const [isProcessing, setIsProcessing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [saveToHistory, setSaveToHistory] = useState(false);
  const [analysePrivately, setAnalysePrivately] = useState(true);
  const [usePastCheckins, setUsePastCheckins] = useState(false);
  const [hasSavedHistory, setHasSavedHistory] = useState(false);
  const [pipelineMode, setPipelineMode] = useState<Exclude<PipelineMode, "auto">>(
    "llm",
  );
  const [result, setResult] = useState<AnalyseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [showMoreEvidence, setShowMoreEvidence] = useState(false);
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
  const timersRef = useRef<number[]>([]);
  const files = useFileUpload();

  // Authenticated users default Save ON / private off so Dashboard history works.
  // Continuity memory is registered (non-anonymous) accounts only.
  // ?continue=1 from Dashboard prefers continuity when history exists.
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

  // ?check_in=<id> opens the saved check-in as a ChatGPT-style thread.
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
        // Private check-ins stay session-only in chat (no server-side append).
        setActiveCheckInId(detail.is_private ? null : detail.id);
        setChatMode(true);
        setShowResult(false);
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

  // Continuity is only allowed for registered users with save on and private off.
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
  /** Optional tip only — never blocks submit. */
  const showShortInputTip =
    hasContent && totalWordCount > 0 && totalWordCount < SHORT_INPUT_TIP_WORDS;

  const filesBusy = files.images.some((i) => i.status === "uploading") ||
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

  async function handleAnalyse() {
    if (!hasContent || isProcessing || filesBusy) return;

    clearTimers();
    setIsProcessing(true);
    setShowResult(false);
    setError(null);
    setSaveNotice(null);
    setResult(null);
    setShowMoreEvidence(false);

    const minDelay = new Promise<void>((resolve) => {
      const finishTimer = window.setTimeout(resolve, PROCESSING_DURATION_MS);
      timersRef.current.push(finishTimer);
    });

    const wantSave = saveToHistory;

    try {
      if (wantSave && !getToken()) {
        await createAnonymousSession();
      }

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

      const [analysis] = await Promise.all([
        analyseText({
          typed_text: text.trim(),
          speech_transcript: "",
          image_context,
          pdf_context,
          save_to_history: wantSave,
          analyse_privately: analysePrivately,
          use_past_checkins:
            wantSave &&
            !analysePrivately &&
            usePastCheckins &&
            isRegisteredUser(),
          pipeline_mode: pipelineMode,
          include_debug: developerMode,
        }),
        minDelay,
      ]);

      setResult(analysis);
      setShowResult(true);

      const userOpening = text.trim() || "Shared a multimodal check-in";
      const assistantOpening =
        analysis.reasoning || analysis.explanation || analysis.message || "";
      setMessages([
        { role: "user", content: userOpening },
        ...(assistantOpening
          ? [{ role: "assistant" as const, content: assistantOpening }]
          : []),
      ]);
      // Persist follow-ups only for logged-in, saved, non-private check-ins.
      // Anonymous / private sessions can still chat; history stays in the browser
      // for this page only and is not written back to the server.
      const persistThread = Boolean(
        analysis.id &&
          wantSave &&
          analysis.saved_to_history &&
          !analysePrivately,
      );
      setActiveCheckInId(persistThread ? analysis.id! : null);
      setChatSupportResources(analysis.support_resources || []);
      setChatError(null);

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
          : "Unable to reach the service right now. It may be waking up from a cold start — wait a few seconds and try again.",
      );
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleChatSend() {
    const outgoing = chatDraft.trim();
    if (!outgoing || chatSending) return;
    setChatSending(true);
    setChatError(null);
    setChatDraft("");
    const prior = messages;
    setMessages([...prior, { role: "user", content: outgoing, input_type: "text" }]);
    try {
      // Ephemeral when no activeCheckInId (anonymous / private / not saved).
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

  return (
    <div className="space-y-8">
      {error && (
        <div
          className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-900 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100"
          role="alert"
        >
          <p className="font-semibold">{error}</p>
        </div>
      )}
      {saveNotice && !error && !chatMode && (
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
          {result &&
            typeof result.support_urgency === "number" &&
            result.support_urgency_band && (
              <SupportUrgencyMeter
                score={result.support_urgency}
                band={result.support_urgency_band}
                rationale={result.support_urgency_rationale}
                uncertain={Boolean(result.support_urgency_uncertain)}
              />
            )}
          {result && (
            <div className="rounded-xl border border-slate-200 bg-white/80 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-900/80 dark:text-slate-300">
              <span className="font-medium text-slate-800 dark:text-slate-100">
                Opening read:{" "}
              </span>
              {result.prediction_display ||
                predictionDisplayName(result.prediction) ||
                result.concern_level}
              {result.ai_confidence ? ` · ${result.ai_confidence} confidence` : ""}
              {activeCheckInId ? (
                <>
                  {" · "}
                  <Link
                    href={`/dashboard/${activeCheckInId}`}
                    className="text-teal-700 underline dark:text-teal-300"
                  >
                    View saved check-in
                  </Link>
                </>
              ) : null}
            </div>
          )}
          <ChatThread
            messages={messages}
            draft={chatDraft}
            onDraftChange={setChatDraft}
            onSend={() => void handleChatSend()}
            onSendAudio={(file, filename) => void handleChatSendAudio(file, filename)}
            isSending={chatSending}
            error={chatError}
            supportResources={chatSupportResources}
            persisted={Boolean(activeCheckInId)}
            subtitle={chatSubtitle}
            toneDisclaimer={toneDisclaimer}
          />
        </div>
      )}

      {!chatMode && !loadingThread && (
      <>
      <div className="rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-6 shadow-sm sm:p-8">
        <label
          htmlFor="wellbeing-input"
          className="block text-base font-medium text-slate-800 dark:text-slate-100"
        >
          How have you been feeling recently?
        </label>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          Type, speak, or attach images and PDFs — then hit Analyse.
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Only share information you are comfortable submitting. This tool is
          not a medical diagnosis.
        </p>

        <div className="mt-4">
          <CheckInComposer
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
            guidance={INPUT_GUIDANCE}
            shortTip={showShortInputTip ? SHORT_INPUT_TIP : null}
            shortExample={showShortInputTip ? SHORT_INPUT_EXAMPLE : null}
          />
        </div>

        <details className="mt-6 group rounded-xl border border-slate-200 bg-slate-50/40 dark:border-slate-700 dark:bg-slate-800/40">
          <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-slate-700 outline-none marker:content-none dark:text-slate-200 [&::-webkit-details-marker]:hidden">
            <span className="flex items-center justify-between gap-3">
              <span>Privacy &amp; assessment options</span>
              <span className="text-xs font-normal text-slate-500 transition group-open:rotate-180 dark:text-slate-400">▾</span>
            </span>
          </summary>
          <div className="space-y-4 border-t border-slate-200 px-4 py-4 dark:border-slate-700">
          <div className="rounded-xl border border-slate-200 bg-slate-50/50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/50">
            <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
              Assessment mode
            </p>
            <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
              Choose a simple model-only read, or one that also draws on trusted
              wellbeing guidance.{" "}
              <Link
                href="/#how-it-works"
                className="text-teal-700 underline dark:text-teal-300"
              >
                How it works
              </Link>
            </p>
            <div
              className="mt-3 grid grid-cols-2 gap-2"
              role="radiogroup"
              aria-label="Assessment mode"
            >
              <button
                type="button"
                role="radio"
                aria-checked={pipelineMode === "llm"}
                disabled={isProcessing}
                onClick={() => setPipelineMode("llm")}
                className={`rounded-lg border px-3 py-2.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  pipelineMode === "llm"
                    ? "border-teal-500 bg-teal-50 text-teal-900 dark:border-teal-400 dark:bg-teal-950/40 dark:text-teal-100"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                }`}
              >
                <span className="block text-sm font-semibold">LLM</span>
                <span className="mt-0.5 block text-xs opacity-80">
                  Model only
                </span>
              </button>
              <button
                type="button"
                role="radio"
                aria-checked={pipelineMode === "rag"}
                disabled={isProcessing}
                onClick={() => setPipelineMode("rag")}
                className={`rounded-lg border px-3 py-2.5 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-60 ${
                  pipelineMode === "rag"
                    ? "border-teal-500 bg-teal-50 text-teal-900 dark:border-teal-400 dark:bg-teal-950/40 dark:text-teal-100"
                    : "border-slate-200 bg-white text-slate-700 hover:border-slate-300 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
                }`}
              >
                <span className="block text-sm font-semibold">LLM+RAG</span>
                <span className="mt-0.5 block text-xs opacity-80">
                  With trusted guidance
                </span>
              </button>
            </div>
          </div>
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
          {isRegisteredUser() && hasSavedHistory && saveToHistory && !analysePrivately && (
            <div className="rounded-xl border border-teal-100 bg-teal-50/70 px-4 py-3 dark:border-teal-900 dark:bg-teal-950/30">
              <p className="text-sm text-teal-900 dark:text-teal-100">
                We&apos;ll remember your recent saved check-ins so you can pick
                up where you left off.
              </p>
              <div className="mt-3">
                <Toggle
                  id="use-past-checkins"
                  label="Use past check-ins"
                  description="Includes up to your last few non-private saved check-ins as gentle continuity context — not a full chat thread."
                  checked={usePastCheckins}
                  onChange={setUsePastCheckins}
                  disabled={isProcessing}
                />
              </div>
            </div>
          )}
          </div>
        </details>

        <div className="mt-6 border-t border-slate-100 pt-4 dark:border-slate-800">
          <p className="text-sm text-slate-500 dark:text-slate-400">{privacyStatus}</p>
        </div>
      </div>
      {isProcessing && (
        <div
          className="animate-fade-in-up rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-1 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50"
          aria-live="polite"
          aria-busy="true"
        >
          <div className="rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 p-8 dark:from-slate-900 dark:to-slate-800/50 sm:p-10">
            <div className="flex flex-col items-center text-center">
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-xl bg-teal-100 text-teal-700">
                <Spinner className="h-6 w-6" />
              </span>
              <h2 className="mt-4 text-lg font-semibold text-slate-800 dark:text-slate-100">
                Looking at what you&apos;ve shared
              </h2>
              <p className="mt-2 max-w-md text-sm text-slate-500 dark:text-slate-400">
                This usually takes a few seconds. If the API was idle, it may be
                waking up first — that can take up to about a minute on free
                hosting.
              </p>
            </div>
          </div>
        </div>
      )}

      {showResult && result && !isProcessing && (
        <div className="animate-fade-in-up rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-1 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50">
          <div className="rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 p-6 dark:from-slate-900 dark:to-slate-800/50 sm:p-8">
            {(() => {
              const confidencePct =
                typeof result.confidence === "number"
                  ? Math.round(
                      result.confidence <= 1
                        ? result.confidence * 100
                        : result.confidence,
                    )
                  : Number.parseInt(result.ai_confidence, 10) || 0;
              const isStandaloneLlm =
                (result.pipeline_used || "").toUpperCase() === "LLM" ||
                result.grounding?.status === "not_applicable";
              const evidenceAll: EvidenceItem[] = isStandaloneLlm
                ? []
                : result.evidence_used?.length
                  ? result.evidence_used
                  : result.sources_detail || [];
              const evidenceVisible = showMoreEvidence
                ? evidenceAll
                : evidenceAll.slice(0, 3);
              const indicators =
                result.potential_indicators?.length
                  ? result.potential_indicators
                  : (result.early_signs || []).map(indicatorDisplayName);
              const showSafety =
                result.safety_triggered ||
                (result.support_resources &&
                  result.support_resources.length > 0);

              return (
                <>
                  {showSafety && (
                    <div
                      className="mb-6 rounded-lg border border-rose-200 bg-rose-50/80 p-5 dark:border-rose-900 dark:bg-rose-950/40"
                      role="alert"
                    >
                      <p className="text-xs font-medium uppercase tracking-wide text-rose-700 dark:text-rose-300">
                        Priority support options
                      </p>
                      <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
                        If you are in immediate danger, call 999 or go to A&E.
                        Support services below are available whenever you need them.
                      </p>
                      {result.support_resources &&
                        result.support_resources.length > 0 && (
                          <ul className="mt-3 space-y-3">
                            {result.support_resources.map((resource) => (
                              <li
                                key={resource.name}
                                className="text-sm text-slate-700 dark:text-slate-300"
                              >
                                <p className="font-medium">{resource.name}</p>
                                <p className="mt-0.5 text-slate-600 dark:text-slate-400">
                                  {resource.description}
                                </p>
                                <p className="mt-0.5">{resource.contact}</p>
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
                        )}
                    </div>
                  )}

                  <div className="mb-6 flex items-center gap-3 border-b border-slate-200/60 pb-4 dark:border-slate-700/60">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-teal-100 text-teal-700">
                      <svg
                        className="h-4 w-4"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.5"
                        aria-hidden="true"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
                        />
                      </svg>
                    </span>
                    <div>
                      <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                        Your reflection
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {result.saved_to_history ? "Saved to history" : "Not saved"}{" "}
                        · {analysePrivately ? "Private mode" : "Standard mode"}
                        {developerMode
                          ? ` · Pipeline: ${result.pipeline_used || "LLM"}`
                          : null}
                      </p>
                    </div>
                  </div>

                  {result.status === "abstained" ? (
                    <div
                      className="rounded-lg border-2 border-amber-400 bg-amber-100 p-5 dark:border-amber-500 dark:bg-amber-950/50"
                      role="status"
                    >
                      <p className="text-xs font-semibold uppercase tracking-wide text-amber-900 dark:text-amber-100">
                        We&apos;re pausing a labelled read
                      </p>
                      <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-slate-50">
                        That&apos;s intentional care — not a broken result
                      </p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-800 dark:text-slate-200">
                        We held back a category label because we weren&apos;t
                        sure enough to classify this fairly. We&apos;d rather
                        not guess about how you&apos;re feeling.
                      </p>
                      {result.message ? (
                        <p className="mt-2 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                          {result.message}
                        </p>
                      ) : null}
                      {countWords(text) < SHORT_INPUT_TIP_WORDS ? (
                        <>
                          <p className="mt-3 text-sm text-slate-800 dark:text-slate-200">
                            If you can, add how long this has lasted and how it
                            affects sleep, study, or daily life, then analyse
                            again.
                          </p>
                          <p className="mt-2 rounded-lg border border-amber-300/80 bg-white/80 px-3 py-2 text-sm leading-relaxed text-slate-800 dark:border-amber-800 dark:bg-slate-900/60 dark:text-slate-200">
                            <span className="font-medium">Example: </span>
                            {SHORT_INPUT_EXAMPLE}
                          </p>
                        </>
                      ) : (
                        <p className="mt-3 text-sm text-slate-800 dark:text-slate-200">
                          What you shared was already taken into account.
                          Support options below remain available if you need
                          them.
                        </p>
                      )}
                      {result.recommendation ? (
                        <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                          {result.recommendation}
                        </p>
                      ) : null}
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div className="rounded-lg border border-white/80 bg-white p-5 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          What it sounds like
                        </p>
                        <p className="mt-2 text-lg font-semibold leading-snug text-slate-800 dark:text-slate-100">
                          {result.prediction_display ||
                            predictionDisplayName(result.prediction) ||
                            result.concern_level}
                        </p>
                        {showSafety ? (
                          <p className="mt-3 text-sm font-medium text-rose-700 dark:text-rose-300">
                            Priority: get support now
                          </p>
                        ) : (
                          <>
                            <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
                              How sure we are: {confidencePct}%
                              {result.uncertainty || result.uncertainty_level
                                ? ` · Uncertainty: ${result.uncertainty || result.uncertainty_level}`
                                : null}
                            </p>
                            {confidencePct < 75 &&
                            countWords(text) >= SHORT_INPUT_TIP_WORDS ? (
                              <p className="mt-3 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm leading-relaxed text-amber-950 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-100">
                                Limited confidence — this is a research category
                                based on what you wrote, not a diagnosis.
                              </p>
                            ) : null}
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {typeof result.support_urgency === "number" &&
                    result.support_urgency_band && (
                      <div className="mt-4">
                        <SupportUrgencyMeter
                          score={result.support_urgency}
                          band={result.support_urgency_band}
                          rationale={result.support_urgency_rationale}
                          uncertain={Boolean(result.support_urgency_uncertain)}
                        />
                      </div>
                    )}

                  <div className="mt-6 space-y-4">
                    {result.status !== "abstained" &&
                      indicators.length > 0 && (
                        <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                            Themes that came through
                          </p>
                          <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                            Themes only — not a clinical diagnosis
                          </p>
                          <div className="mt-3 flex flex-wrap gap-2">
                            {indicators.map((sign) => (
                              <span
                                key={sign}
                                className="rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-xs font-medium text-teal-800 dark:border-teal-800 dark:bg-teal-950/50 dark:text-teal-200"
                              >
                                {sign}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}

                    <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        A gentle reflection
                      </p>
                      <p className="mt-2 leading-relaxed text-slate-700 dark:text-slate-300">
                        {result.reasoning || result.explanation}
                      </p>
                    </div>

                    {result.status !== "abstained" &&
                      !isStandaloneLlm &&
                      evidenceVisible.length > 0 && (
                        <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                            Helpful guidance we looked at
                          </p>
                          <ul className="mt-3 space-y-4">
                            {evidenceVisible.map((item) => (
                              <li key={item.source_id}>
                                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                                  {item.display_label ||
                                    `${item.organisation} — ${item.title}`}
                                </p>
                                <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                                  {item.reason_retrieved}
                                </p>
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
                                {developerMode && (
                                  <p className="mt-1 text-xs text-slate-400">
                                    ID: {item.source_id}
                                    {typeof item.retrieval_score === "number"
                                      ? ` · score ${item.retrieval_score.toFixed(3)}`
                                      : ""}
                                  </p>
                                )}
                              </li>
                            ))}
                          </ul>
                          {evidenceAll.length > 3 && (
                            <button
                              type="button"
                              className="mt-3 text-sm font-medium text-teal-700 underline dark:text-teal-300"
                              onClick={() =>
                                setShowMoreEvidence((open) => !open)
                              }
                            >
                              {showMoreEvidence
                                ? "Show fewer sources"
                                : "Show more sources"}
                            </button>
                          )}
                        </div>
                      )}

                    {!showSafety &&
                      result.support_resources &&
                      result.support_resources.length > 0 && (
                        <div className="rounded-lg border border-rose-100 bg-rose-50/70 p-4 dark:border-rose-900 dark:bg-rose-950/30">
                          <p className="text-xs font-medium uppercase tracking-wide text-rose-700 dark:text-rose-300">
                            Support if you need it
                          </p>
                          <ul className="mt-3 space-y-3">
                            {result.support_resources.map((resource) => (
                              <li
                                key={resource.name}
                                className="text-sm text-slate-700 dark:text-slate-300"
                              >
                                <p className="font-medium">{resource.name}</p>
                                <p className="mt-0.5">{resource.contact}</p>
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
                      )}

                    <div className="rounded-lg border border-teal-100 bg-teal-50/60 p-4 dark:border-teal-900 dark:bg-teal-950/40">
                      <p className="text-xs font-medium uppercase tracking-wide text-teal-700">
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

                    <div className="space-y-2 rounded-lg border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-800/60">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        A note on care
                      </p>
                      <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                        {result.disclaimer ||
                          "This tool provides wellbeing support information and should not be considered a medical diagnosis."}
                      </p>
                      <p className="text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                        {result.human_oversight}
                      </p>
                      <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                        {result.privacy_notice}
                      </p>
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

                    <div className="rounded-lg border border-amber-100 bg-amber-50/60 p-4 dark:border-amber-900 dark:bg-amber-950/40">
                      <p className="text-xs font-medium uppercase tracking-wide text-amber-700">
                        Safety disclaimer
                      </p>
                      <p className="mt-2 leading-relaxed text-slate-700 dark:text-slate-300">
                        {result.safety_note}
                      </p>
                    </div>

                    {developerMode && result.debug && (
                      <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50/80 p-4 text-xs text-slate-600 dark:border-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
                        <p className="font-medium uppercase tracking-wide text-slate-500">
                          Developer debug
                        </p>
                        <ul className="mt-2 space-y-1 font-mono">
                          <li>pipeline: {result.debug.pipeline_used}</li>
                          <li>model: {result.debug.openai_model}</li>
                          <li>embedding: {result.debug.embedding_model}</li>
                          <li>latency_ms: {result.debug.latency_ms.toFixed(0)}</li>
                          <li>
                            n_chunks: {result.debug.n_retrieved_chunks}
                          </li>
                          <li>
                            confidence_threshold:{" "}
                            {result.debug.confidence_threshold}
                          </li>
                          <li>
                            grounding mins: rq=
                            {result.debug.grounding_retrieval_quality_min} ev=
                            {result.debug.grounding_evidence_strength_min}
                          </li>
                        </ul>
                        {result.confidence_breakdown && (
                          <pre className="mt-3 overflow-x-auto whitespace-pre-wrap">
                            {JSON.stringify(result.confidence_breakdown, null, 2)}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}

      {showResult && result && !isProcessing && messages.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center justify-between gap-3">
            <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
              Continue the conversation
            </h3>
            <Link
              href="/analyse"
              className="text-sm font-medium text-teal-700 hover:underline dark:text-teal-300"
            >
              New chat
            </Link>
          </div>
          <ChatThread
            messages={messages}
            draft={chatDraft}
            onDraftChange={setChatDraft}
            onSend={() => void handleChatSend()}
            onSendAudio={(file, filename) => void handleChatSendAudio(file, filename)}
            isSending={chatSending}
            error={chatError}
            supportResources={chatSupportResources}
            persisted={Boolean(activeCheckInId)}
            subtitle={chatSubtitle}
            toneDisclaimer={toneDisclaimer}
          />
        </div>
      )}
      </>
      )}
    </div>
  );
}

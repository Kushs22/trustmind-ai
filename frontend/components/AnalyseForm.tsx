"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Toggle } from "@/components/Toggle";
import { FileUpload } from "@/components/analysis/FileUpload";
import { InputReview } from "@/components/analysis/InputReview";
import { VoiceInput } from "@/components/analysis/VoiceInput";
import {
  analyseText,
  ApiError,
  createAnonymousSession,
  getCheckIns,
  type AnalyseResponse,
  type EvidenceItem,
  type PipelineMode,
} from "@/lib/api";
import { AUTH_CHANGED_EVENT, getToken, isAuthenticated, isRegisteredUser } from "@/lib/auth";
import { indicatorDisplayName, predictionDisplayName } from "@/lib/displayLabels";
import { useFileUpload } from "@/hooks/useFileUpload";

const PROCESSING_DURATION_MS = 2600;

/** Soft guidance only — never disables Review/Confirm; one-word check-ins are allowed. */
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
  const [speechTranscript, setSpeechTranscript] = useState("");
  const [speechDraft, setSpeechDraft] = useState("");
  const [showReview, setShowReview] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [loggedIn, setLoggedIn] = useState(false);
  const [saveToHistory, setSaveToHistory] = useState(false);
  const [analysePrivately, setAnalysePrivately] = useState(true);
  const [usePastCheckins, setUsePastCheckins] = useState(false);
  const [hasSavedHistory, setHasSavedHistory] = useState(false);
  const [pipelineMode, setPipelineMode] = useState<Exclude<PipelineMode, "auto">>(
    "rag",
  );
  const [result, setResult] = useState<AnalyseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saveNotice, setSaveNotice] = useState<string | null>(null);
  const [showMoreEvidence, setShowMoreEvidence] = useState(false);
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
      speechTranscript.trim() ||
      files.images.some((i) => i.included && i.extractedText.trim()) ||
      files.pdfs.some((p) => p.included && p.extractedText.trim()),
  );

  const typedWordCount = countWords(text);
  const speechWordCount = countWords(speechTranscript);
  const fileWordCount =
    files.images
      .filter((i) => i.included)
      .reduce((sum, i) => sum + countWords(i.extractedText), 0) +
    files.pdfs
      .filter((p) => p.included)
      .reduce((sum, p) => sum + countWords(p.extractedText), 0);
  const totalWordCount = typedWordCount + speechWordCount + fileWordCount;
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
    setShowReview(false);
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
          speech_transcript: speechTranscript.trim(),
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

      if (wantSave && analysis.saved_to_history) {
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
          : "Unable to reach the analysis service. Is the backend running?",
      );
    } finally {
      setIsProcessing(false);
    }
  }

  function handleReviewRequest() {
    if (!hasContent || isProcessing || filesBusy) return;
    setError(null);
    setShowReview(true);
  }

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

      <div className="rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-6 shadow-sm sm:p-8">
        <label
          htmlFor="wellbeing-input"
          className="block text-base font-medium text-slate-800 dark:text-slate-100"
        >
          How have you been feeling recently?
        </label>
        <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">
          You can type, speak, or attach supporting images and PDF documents.
        </p>
        <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
          Only share information you are comfortable submitting. This tool is
          not a medical diagnosis.
        </p>
        <textarea
          id="wellbeing-input"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            if (error) setError(null);
          }}
          rows={8}
          disabled={isProcessing || showReview}
          placeholder="Share what's on your mind — even one word works."
          className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 px-4 py-3 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-teal-300 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60"
        />
        <p className="mt-3 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {INPUT_GUIDANCE}
        </p>
        {showShortInputTip && (
          <div
            className="mt-3 rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 dark:border-slate-700 dark:bg-slate-800/60"
            role="status"
          >
            <p className="text-sm text-slate-700 dark:text-slate-200">
              {SHORT_INPUT_TIP}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              <span className="font-medium">Optional example:</span>{" "}
              {SHORT_INPUT_EXAMPLE}
            </p>
          </div>
        )}

        <div className="mt-4 space-y-4">
          <VoiceInput
            disabled={isProcessing || showReview}
            draftTranscript={speechDraft}
            onDraftChange={setSpeechDraft}
            onDiscard={() => {
              setSpeechDraft("");
              setSpeechTranscript("");
            }}
            onTranscriptConfirmed={(t) => {
              setSpeechTranscript(t);
              setSpeechDraft(t);
            }}
          />
          {speechTranscript && (
            <p className="text-xs text-teal-700 dark:text-teal-300" aria-live="polite">
              Speech transcript ready for analysis ({speechWordCount} words). You
              can still edit it above.
            </p>
          )}
          <FileUpload
            disabled={isProcessing || showReview}
            images={files.images}
            pdfs={files.pdfs}
            error={files.error}
            onAddFiles={(f) => void files.addFiles(f)}
            onRemoveImage={files.removeImage}
            onRemovePdf={files.removePdf}
            onUpdateImageText={files.updateImageText}
            onUpdatePdfText={files.updatePdfText}
            onToggleImage={files.toggleImageIncluded}
            onTogglePdf={files.togglePdfIncluded}
          />
        </div>

        {showReview && (
          <div className="mt-6">
            <InputReview
              typedText={text.trim()}
              speechTranscript={speechTranscript.trim()}
              imageSummaries={files.images
                .filter((i) => i.included && i.extractedText.trim())
                .map((i) => ({
                  filename: i.file.name,
                  text: i.extractedText.trim(),
                }))}
              pdfSummaries={files.pdfs
                .filter((p) => p.included && p.extractedText.trim())
                .map((p) => ({
                  filename: p.file.name,
                  text: p.extractedText.trim(),
                }))}
              analysePrivately={analysePrivately}
              disabled={!canSubmit}
              onBack={() => setShowReview(false)}
              onConfirm={() => void handleAnalyse()}
            />
          </div>
        )}

        <div className="mt-6 space-y-4">
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
        <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500 dark:text-slate-400">{privacyStatus}</p>
          {!showReview ? (
            <button
              type="button"
              onClick={handleReviewRequest}
              disabled={!canSubmit}
              title={
                !hasContent
                  ? "Enter some text, speech, or a file first"
                  : undefined
              }
              aria-disabled={!canSubmit}
              className="inline-flex h-12 min-w-[180px] items-center justify-center gap-2 rounded-xl bg-teal-600 px-8 text-base font-medium text-white shadow-md shadow-teal-600/20 transition-all hover:bg-teal-700 hover:shadow-lg hover:shadow-teal-600/25 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Review &amp; analyse
            </button>
          ) : (
            <p className="text-sm text-teal-700 dark:text-teal-300">
              Confirm your inputs above to continue.
            </p>
          )}
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
                This usually takes a few seconds. The first request after idle can
                take longer while the service wakes up.
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
    </div>
  );
}

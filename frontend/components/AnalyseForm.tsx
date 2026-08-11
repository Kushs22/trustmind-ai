"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Toggle } from "@/components/Toggle";
import { FileUpload } from "@/components/analysis/FileUpload";
import { InputReview } from "@/components/analysis/InputReview";
import { VoiceInput } from "@/components/analysis/VoiceInput";
import {
  analyseText,
  ApiError,
  createAnonymousSession,
  type AnalyseResponse,
  type EvidenceItem,
  type PipelineMode,
} from "@/lib/api";
import { getToken } from "@/lib/auth";
import { indicatorDisplayName, predictionDisplayName } from "@/lib/displayLabels";
import { useFileUpload } from "@/hooks/useFileUpload";

const PROCESSING_STEPS_RAG = [
  "Analysing emotional language",
  "Checking uncertainty level",
  "Retrieving evidence-informed support context",
  "Preparing safe response",
] as const;

const PROCESSING_STEPS_LLM = [
  "Analysing emotional language",
  "Checking uncertainty level",
  "Preparing model assessment",
  "Preparing safe response",
] as const;

const PROCESSING_DURATION_MS = 2600;

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

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fillRule="evenodd"
        d="M16.704 5.29a1 1 0 010 1.42l-7.25 7.25a1 1 0 01-1.42 0l-3.25-3.25a1 1 0 111.42-1.42l2.54 2.54 6.54-6.54a1 1 0 011.42 0z"
        clipRule="evenodd"
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
  const [activeStep, setActiveStep] = useState(0);
  const [showResult, setShowResult] = useState(false);
  const [saveToHistory, setSaveToHistory] = useState(false);
  const [analysePrivately, setAnalysePrivately] = useState(true);
  const [pipelineMode, setPipelineMode] = useState<Exclude<PipelineMode, "auto">>(
    "rag",
  );
  const [result, setResult] = useState<AnalyseResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showConfidenceDetails, setShowConfidenceDetails] = useState(false);
  const [showMoreEvidence, setShowMoreEvidence] = useState(false);
  const timersRef = useRef<number[]>([]);
  const files = useFileUpload();

  const hasContent = Boolean(
    text.trim() ||
      speechTranscript.trim() ||
      files.images.some((i) => i.included && i.extractedText.trim()) ||
      files.pdfs.some((p) => p.included && p.extractedText.trim()),
  );

  const filesBusy = files.images.some((i) => i.status === "uploading") ||
    files.pdfs.some((p) => p.status === "uploading");

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

  const processingSteps =
    pipelineMode === "rag" ? PROCESSING_STEPS_RAG : PROCESSING_STEPS_LLM;
  const stepIntervalMs = PROCESSING_DURATION_MS / processingSteps.length;

  function clearTimers() {
    timersRef.current.forEach((timer) => window.clearTimeout(timer));
    timersRef.current = [];
  }

  function startProgressAnimation() {
    processingSteps.forEach((_, index) => {
      const stepTimer = window.setTimeout(() => {
        setActiveStep(index + 1);
      }, stepIntervalMs * (index + 1));
      timersRef.current.push(stepTimer);
    });
  }

  async function handleAnalyse() {
    if (!hasContent || isProcessing || filesBusy) return;

    clearTimers();
    setIsProcessing(true);
    setActiveStep(0);
    setShowResult(false);
    setShowReview(false);
    setError(null);
    setResult(null);
    setShowConfidenceDetails(false);
    setShowMoreEvidence(false);
    startProgressAnimation();

    const minDelay = new Promise<void>((resolve) => {
      const finishTimer = window.setTimeout(resolve, PROCESSING_DURATION_MS);
      timersRef.current.push(finishTimer);
    });

    try {
      if (saveToHistory && !getToken()) {
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
          save_to_history: saveToHistory,
          analyse_privately: analysePrivately,
          pipeline_mode: pipelineMode,
          include_debug: developerMode,
        }),
        minDelay,
      ]);

      setResult(analysis);
      setShowResult(true);
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

  const progressPercent = isProcessing
    ? Math.min(100, Math.round((activeStep / processingSteps.length) * 100))
    : 0;

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
          className="rounded-xl border border-red-100 bg-red-50/80 px-4 py-3 text-sm text-red-800"
          role="alert"
        >
          {error}
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
          onChange={(event) => setText(event.target.value)}
          rows={8}
          disabled={isProcessing || showReview}
          placeholder="Share what's been on your mind. There are no right or wrong answers."
          className="mt-4 w-full resize-y rounded-xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 px-4 py-3 text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-teal-300 focus:bg-white dark:focus:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60"
        />

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
              Speech transcript ready for analysis ({speechTranscript.length}{" "}
              characters). You can still edit it above.
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
              disabled={isProcessing}
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
              Compare standalone LLM vs LLM with trusted-source retrieval (RAG).
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
                  Model only · no retrieval
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
                  Grounded in approved sources
                </span>
              </button>
            </div>
          </div>
          <Toggle
            id="save-history"
            label="Save this check-in to my history"
            description="Store a summary in your dashboard for future reference. Original audio, images and PDFs are never saved."
            checked={saveToHistory}
            onChange={setSaveToHistory}
            disabled={isProcessing}
          />
          <Toggle
            id="analyse-privately"
            label="Analyse privately"
            description="Process without storing raw text, transcripts, or file contents."
            checked={analysePrivately}
            onChange={setAnalysePrivately}
            disabled={isProcessing}
          />
        </div>
        <div className="mt-6 flex flex-col gap-3 border-t border-slate-100 pt-6 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-sm text-slate-500 dark:text-slate-400">{privacyStatus}</p>
          {!showReview ? (
            <button
              type="button"
              onClick={handleReviewRequest}
              disabled={!hasContent || isProcessing || filesBusy}
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
          <div className="rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-slate-900 dark:to-slate-800/50 dark:from-slate-900 dark:to-slate-800/50 p-6 sm:p-8">
            <div className="mb-6 flex items-start gap-3 border-b border-slate-200/60 dark:border-slate-700/60 pb-5">
              <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-teal-100 text-teal-700">
                <Spinner className="h-5 w-5" />
              </span>
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                  Analysing safely
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  TrustMind AI is reviewing your text with care. This usually
                  takes a few seconds.
                </p>
              </div>
            </div>

            <div className="mb-6">
              <div className="mb-2 flex items-center justify-between text-xs font-medium text-slate-500 dark:text-slate-400">
                <span>Processing</span>
                <span>{progressPercent}%</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-slate-200/80">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-teal-500 to-blue-500 transition-all duration-500 ease-out"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
            </div>

            <ul className="space-y-3">
              {processingSteps.map((step, index) => {
                const isComplete = activeStep > index;
                const isCurrent = activeStep === index;

                return (
                  <li
                    key={step}
                    className={`flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors ${
                      isComplete
                        ? "border-teal-100 bg-teal-50/70"
                        : isCurrent
                          ? "border-blue-100 bg-white shadow-sm"
                          : "border-slate-100 bg-white/60"
                    }`}
                  >
                    <span
                      className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full ${
                        isComplete
                          ? "bg-teal-600 text-white"
                          : isCurrent
                            ? "bg-blue-100 text-blue-600"
                            : "bg-slate-100 text-slate-400"
                      }`}
                    >
                      {isComplete ? (
                        <CheckIcon className="h-4 w-4" />
                      ) : isCurrent ? (
                        <Spinner className="h-3.5 w-3.5" />
                      ) : (
                        <span className="h-1.5 w-1.5 rounded-full bg-current" />
                      )}
                    </span>
                    <span
                      className={`text-sm ${
                        isComplete || isCurrent
                          ? "font-medium text-slate-800 dark:text-slate-100"
                          : "text-slate-500 dark:text-slate-400"
                      }`}
                    >
                      {step}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}

      {showResult && result && !isProcessing && (
        <div className="animate-fade-in-up rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-1 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50">
          <div className="rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-slate-900 dark:to-slate-800/50 p-6 sm:p-8">
            {(() => {
              const confidencePct =
                typeof result.confidence === "number"
                  ? Math.round(
                      result.confidence <= 1
                        ? result.confidence * 100
                        : result.confidence,
                    )
                  : Number.parseInt(result.ai_confidence, 10) || 0;
              const trust = result.trust_signals;
              const groundingLabel =
                result.grounding?.label || result.grounding_status;
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
              const formatBreakdownValue = (value: number | null | undefined) =>
                value === null || value === undefined
                  ? "Not applicable"
                  : `${value}%`;
              const confidenceDetailRows: ReadonlyArray<
                readonly [keyof NonNullable<AnalyseResponse["confidence_breakdown"]>, string]
              > = isStandaloneLlm
                ? [
                    ["llm_confidence", "LLM confidence"],
                    ["classification_consistency", "Classification consistency"],
                    ["input_clarity", "Input clarity"],
                    ["retrieval_similarity", "Retrieval similarity"],
                    ["source_agreement", "Source agreement"],
                    ["retrieval_coverage", "Retrieval coverage"],
                  ]
                : [
                    ["llm_confidence", "LLM confidence"],
                    ["retrieval_similarity", "Retrieval similarity"],
                    ["source_agreement", "Source agreement"],
                    ["classification_consistency", "Classification consistency"],
                    ["retrieval_coverage", "Retrieval coverage"],
                  ];
              const indicators =
                result.potential_indicators?.length
                  ? result.potential_indicators
                  : (result.early_signs || []).map(indicatorDisplayName);
              const showSafety =
                result.safety_triggered ||
                (result.support_resources &&
                  result.support_resources.length > 0);

              function TrustBar({
                label,
                value,
              }: {
                label: string;
                value: number | null | undefined;
              }) {
                const na = value === null || value === undefined;
                const pct = na ? 0 : Math.max(0, Math.min(100, value));
                return (
                  <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {label}
                      </p>
                      <p className="text-sm font-semibold tabular-nums text-slate-800 dark:text-slate-100">
                        {na ? "Not applicable" : `${pct}%`}
                      </p>
                    </div>
                    <div
                      className="mt-2 h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-700"
                      role="progressbar"
                      aria-valuemin={0}
                      aria-valuemax={100}
                      aria-valuenow={na ? 0 : pct}
                      aria-label={label}
                      aria-valuetext={na ? "Not applicable" : `${pct} percent`}
                    >
                      <div
                        className={`h-full rounded-full ${na ? "bg-slate-300 dark:bg-slate-600" : "bg-teal-500"}`}
                        style={{ width: na ? "100%" : `${pct}%`, opacity: na ? 0.35 : 1 }}
                      />
                    </div>
                  </div>
                );
              }

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
                        If you are in immediate danger, contact emergency services.
                        Support services below are available regardless of confidence
                        or retrieval quality — they are not a diagnosis.
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
                        Analysis result
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-slate-400">
                        {result.saved_to_history ? "Saved to history" : "Not saved"}{" "}
                        · {analysePrivately ? "Private mode" : "Standard mode"}
                        {` · Pipeline: ${result.pipeline_used || "LLM"}`}
                      </p>
                    </div>
                  </div>

                  {result.status === "abstained" ? (
                    <div
                      className="rounded-lg border border-amber-200 bg-amber-50/80 p-5 dark:border-amber-900 dark:bg-amber-950/40"
                      role="status"
                    >
                      <p className="text-xs font-medium uppercase tracking-wide text-amber-800 dark:text-amber-200">
                        Assessment abstained
                      </p>
                      <p className="mt-2 text-base font-semibold text-slate-800 dark:text-slate-100">
                        {result.message ||
                          "The system did not have enough reliable evidence to provide a confident assessment."}
                      </p>
                      <p className="mt-3 text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                        {result.recommendation}
                      </p>
                      <p className="mt-3 text-xs text-slate-500 dark:text-slate-400">
                        Calibrated confidence: {confidencePct}% · Uncertainty:{" "}
                        {result.uncertainty || result.uncertainty_level}
                      </p>
                    </div>
                  ) : (
                    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                      <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Research category
                        </p>
                        <p className="mt-1 text-base font-semibold leading-snug text-amber-600">
                          {result.prediction_display ||
                            predictionDisplayName(result.prediction) ||
                            result.concern_level}
                        </p>
                      </div>
                      <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Model confidence
                        </p>
                        <p className="mt-1 text-base font-semibold leading-snug text-teal-600">
                          {confidencePct}%
                        </p>
                      </div>
                      <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Uncertainty
                        </p>
                        <p className="mt-1 text-base font-semibold leading-snug text-blue-600">
                          {result.uncertainty || result.uncertainty_level}
                        </p>
                      </div>
                      <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm sm:col-span-2 dark:border-slate-700/80 dark:bg-slate-800 lg:col-span-3">
                        <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                          Grounding status
                        </p>
                        <p className="mt-1 text-base font-semibold leading-snug text-teal-600">
                          {groundingLabel}
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="mt-4 grid gap-3 sm:grid-cols-3">
                    <TrustBar
                      label="Model confidence"
                      value={trust?.model_confidence ?? confidencePct}
                    />
                    <TrustBar
                      label="Evidence strength"
                      value={trust?.evidence_strength ?? null}
                    />
                    <TrustBar
                      label="Retrieval quality"
                      value={trust?.retrieval_quality ?? null}
                    />
                  </div>

                  {result.confidence_breakdown &&
                    Object.keys(result.confidence_breakdown).length > 0 && (
                      <div className="mt-4">
                        <button
                          type="button"
                          className="flex w-full items-center justify-between rounded-lg border border-slate-200 bg-white px-4 py-3 text-left text-sm font-medium text-slate-800 shadow-sm transition hover:border-teal-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-teal-500 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
                          aria-expanded={showConfidenceDetails}
                          aria-controls="confidence-details-panel"
                          id="confidence-details-trigger"
                          onClick={() =>
                            setShowConfidenceDetails((open) => !open)
                          }
                        >
                          <span>Show confidence details</span>
                          <span aria-hidden="true" className="text-slate-400">
                            {showConfidenceDetails ? "−" : "+"}
                          </span>
                        </button>
                        {showConfidenceDetails && (
                          <div
                            id="confidence-details-panel"
                            role="region"
                            aria-labelledby="confidence-details-trigger"
                            className="mt-2 rounded-lg border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-800/60"
                          >
                            <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                              Confidence details
                            </p>
                            <ul className="mt-3 space-y-2">
                              {confidenceDetailRows.map(([key, label]) => (
                                <li
                                  key={key}
                                  className="flex items-center justify-between text-sm text-slate-700 dark:text-slate-300"
                                >
                                  <span>{label}</span>
                                  <span className="font-medium tabular-nums">
                                    {formatBreakdownValue(
                                      result.confidence_breakdown?.[key],
                                    )}
                                  </span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}

                  <div className="mt-6 space-y-4">
                    {result.status !== "abstained" &&
                      indicators.length > 0 && (
                        <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                            Potential wellbeing indicators
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
                        Explanation / reasoning
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
                            Evidence used
                          </p>
                          <ul className="mt-3 space-y-4">
                            {evidenceVisible.map((item) => (
                              <li key={item.source_id}>
                                <p className="text-sm font-medium text-slate-800 dark:text-slate-100">
                                  {item.display_label ||
                                    `${item.organisation} — ${item.title}`}
                                </p>
                                <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                                  <span className="font-medium text-slate-700 dark:text-slate-300">
                                    Why it was relevant:{" "}
                                  </span>
                                  {item.reason_retrieved}
                                </p>
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

                    {result.status !== "abstained" &&
                      !isStandaloneLlm &&
                      (result.sources_detail?.length ||
                        result.sources?.length) && (
                        <div className="rounded-lg border border-white/80 bg-white p-4 shadow-sm dark:border-slate-700/80 dark:bg-slate-800">
                          <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                            Retrieved sources
                          </p>
                          <ul className="mt-3 space-y-3">
                            {(result.sources_detail?.length
                              ? result.sources_detail
                              : evidenceAll
                            ).map((item) => (
                              <li
                                key={`src-${item.source_id}`}
                                className="text-sm text-slate-700 dark:text-slate-300"
                              >
                                <p className="font-medium">
                                  {item.display_label ||
                                    `${item.organisation} — ${item.title}`}
                                </p>
                                {item.topic ? (
                                  <p className="text-xs text-slate-500">
                                    Topic: {item.topic}
                                  </p>
                                ) : null}
                                {item.url ? (
                                  <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-1 inline-block text-teal-700 underline dark:text-teal-300"
                                  >
                                    View source
                                  </a>
                                ) : null}
                                {developerMode && (
                                  <p className="mt-1 text-xs text-slate-400">
                                    {item.source_id}
                                    {typeof item.retrieval_score === "number"
                                      ? ` · ${item.retrieval_score.toFixed(3)}`
                                      : ""}
                                  </p>
                                )}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                    {!showSafety &&
                      result.support_resources &&
                      result.support_resources.length > 0 && (
                        <div className="rounded-lg border border-rose-100 bg-rose-50/70 p-4 dark:border-rose-900 dark:bg-rose-950/30">
                          <p className="text-xs font-medium uppercase tracking-wide text-rose-700 dark:text-rose-300">
                            Available support services
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
                        Ethics &amp; transparency
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

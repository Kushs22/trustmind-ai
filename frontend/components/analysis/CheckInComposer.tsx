"use client";

import { useEffect, useRef, type KeyboardEvent } from "react";
import { FileUpload } from "@/components/analysis/FileUpload";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";
import type { PendingImage, PendingPdf } from "@/hooks/useFileUpload";

type CheckInComposerProps = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  canSubmit: boolean;
  isProcessing: boolean;
  onSubmit: () => void;
  images: PendingImage[];
  pdfs: PendingPdf[];
  fileError: string | null;
  onAddFiles: (files: FileList | File[]) => void;
  onRemoveImage: (id: string) => void;
  onRemovePdf: (id: string) => void;
  onUpdateImageText: (id: string, text: string) => void;
  onUpdatePdfText: (id: string, text: string) => void;
  onToggleImage: (id: string, included: boolean) => void;
  onTogglePdf: (id: string, included: boolean) => void;
  guidance?: string;
  shortTip?: string | null;
  shortExample?: string | null;
  /** Sit inside a ChatThread-style shell without a second card border. */
  embedded?: boolean;
};

/**
 * ChatGPT-style check-in composer: one textarea, mic + attach in the toolbar,
 * single Analyse button. Speech is appended into the main text field.
 */
export function CheckInComposer({
  value,
  onChange,
  disabled,
  canSubmit,
  isProcessing,
  onSubmit,
  images,
  pdfs,
  fileError,
  onAddFiles,
  onRemoveImage,
  onRemovePdf,
  onUpdateImageText,
  onUpdatePdfText,
  onToggleImage,
  onTogglePdf,
  guidance,
  shortTip,
  shortExample,
  embedded = false,
}: CheckInComposerProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const valueRef = useRef(value);
  valueRef.current = value;

  const speech = useSpeechRecognition();
  const recorder = useVoiceRecorder();
  const useBrowser = speech.supported;

  const listening = useBrowser
    ? speech.listening
    : recorder.status === "listening";
  const processingAudio = !useBrowser && recorder.status === "processing";

  useEffect(() => {
    if (useBrowser) return;
    if (recorder.status === "completed" && recorder.transcript.trim()) {
      const spoken = recorder.transcript.trim();
      const current = valueRef.current;
      onChange(current.trim() ? `${current.trim()} ${spoken}` : spoken);
      recorder.cancel();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [useBrowser, recorder.status, recorder.transcript]);

  async function handleMicClick() {
    if (listening) {
      if (useBrowser) {
        const spoken = `${speech.finalTranscript} ${speech.interim}`.trim();
        speech.stop();
        if (spoken) {
          const current = valueRef.current;
          onChange(current.trim() ? `${current.trim()} ${spoken}` : spoken);
        }
        speech.cancel();
      } else {
        await recorder.stopAndTranscribe();
      }
      return;
    }
    if (useBrowser) speech.start();
    else await recorder.start();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (canSubmit && !disabled && !isProcessing) onSubmit();
    }
  }

  const micError = useBrowser ? speech.error : recorder.error;
  const liveInterim =
    useBrowser && listening
      ? `${speech.finalTranscript} ${speech.interim}`.trim()
      : "";
  const locked = Boolean(disabled || isProcessing || processingAudio);

  const attachmentChips =
    images.length > 0 || pdfs.length > 0 ? (
      <div
        className={
          embedded
            ? "mb-2"
            : "border-b border-slate-100 px-3 pt-3 dark:border-slate-800"
        }
      >
        <FileUpload
          disabled={locked}
          images={images}
          pdfs={pdfs}
          error={null}
          onAddFiles={onAddFiles}
          onRemoveImage={onRemoveImage}
          onRemovePdf={onRemovePdf}
          onUpdateImageText={onUpdateImageText}
          onUpdatePdfText={onUpdatePdfText}
          onToggleImage={onToggleImage}
          onTogglePdf={onTogglePdf}
          hidePickers
        />
      </div>
    ) : null;

  const statusRow =
    listening || processingAudio || liveInterim ? (
      <div
        className={`flex flex-wrap items-center gap-2 text-xs text-slate-500 dark:text-slate-400 ${
          embedded ? "mb-2" : "px-4 pb-2"
        }`}
      >
        <span
          className={`inline-flex h-2 w-2 rounded-full ${
            listening ? "animate-pulse bg-rose-500" : "bg-teal-500"
          }`}
          aria-hidden
        />
        <span aria-live="polite">
          {processingAudio
            ? "Transcribing…"
            : useBrowser
              ? "Listening… click mic to stop"
              : `Recording ${recorder.elapsedLabel}`}
        </span>
        {liveInterim ? (
          <span className="truncate italic text-slate-400">“{liveInterim}”</span>
        ) : null}
        {listening && (
          <button
            type="button"
            onClick={() => {
              if (useBrowser) speech.cancel();
              else recorder.cancel();
            }}
            className="rounded-md border border-rose-200 px-2 py-0.5 text-rose-700 dark:border-rose-800 dark:text-rose-300"
          >
            Cancel
          </button>
        )}
      </div>
    ) : null;

  const fileInput = (
    <input
      ref={fileInputRef}
      type="file"
      accept="image/jpeg,image/png,image/webp,application/pdf,.pdf"
      multiple
      className="hidden"
      onChange={(event) => {
        if (event.target.files?.length) onAddFiles(event.target.files);
        event.target.value = "";
      }}
    />
  );

  const tipBlock = shortTip ? (
    <div
      className={`rounded-xl border border-slate-200 px-3 py-2 dark:border-slate-700 ${
        embedded
          ? "bg-white/80 dark:bg-slate-900/60"
          : "bg-slate-50 dark:bg-slate-800/60"
      }`}
      role="status"
    >
      <p
        className={`text-slate-700 dark:text-slate-200 ${
          embedded ? "text-xs" : "text-sm"
        }`}
      >
        {shortTip}
      </p>
      {shortExample && (
        <p className="mt-1 text-[11px] leading-relaxed text-slate-500 dark:text-slate-400">
          <span className="font-medium">Optional example:</span> {shortExample}
        </p>
      )}
    </div>
  ) : null;

  if (embedded) {
    return (
      <div
        className="space-y-2"
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (locked) return;
          if (e.dataTransfer.files?.length) onAddFiles(e.dataTransfer.files);
        }}
      >
        {attachmentChips}
        {statusRow}
        <div className="flex items-end gap-2">
          {fileInput}
          <button
            type="button"
            disabled={locked}
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
            aria-label="Attach image or PDF"
            title="Attach image or PDF"
          >
            <AttachIcon />
          </button>
          <button
            type="button"
            disabled={locked}
            onClick={() => void handleMicClick()}
            className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
              listening
                ? "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
                : "border-slate-200 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
            }`}
            aria-label={listening ? "Stop recording" : "Speak"}
            title={listening ? "Stop recording" : "Speak"}
          >
            <MicIcon />
          </button>
          <textarea
            id="wellbeing-input"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={locked}
            placeholder="Share what's on your mind…"
            className="max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-teal-900/40"
          />
          <button
            type="button"
            onClick={onSubmit}
            disabled={!canSubmit || locked}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 px-4 text-sm font-medium text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isProcessing ? "…" : "Analyse"}
          </button>
        </div>
        <p className="text-[11px] text-slate-500 dark:text-slate-400">
          Enter to analyse · Shift+Enter for a new line · Mic for speech ·
          Paperclip for images/PDFs (context only — not a file vault)
        </p>
        {micError && (
          <p className="text-sm text-rose-700 dark:text-rose-300" role="alert">
            {micError}
          </p>
        )}
        {fileError && (
          <p className="text-sm text-rose-700 dark:text-rose-300" role="alert">
            {fileError}
          </p>
        )}
        {tipBlock}
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div
        className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900"
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          if (locked) return;
          if (e.dataTransfer.files?.length) onAddFiles(e.dataTransfer.files);
        }}
      >
        {attachmentChips}

        <textarea
          id="wellbeing-input"
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          rows={5}
          disabled={locked}
          placeholder="Share what's on your mind — type, speak, or attach a file."
          className="max-h-64 min-h-[8rem] w-full resize-y border-0 bg-transparent px-4 pt-4 text-base text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-0 disabled:opacity-60 dark:text-slate-100"
        />

        {statusRow}

        <div className="flex flex-wrap items-center gap-2 border-t border-slate-100 px-3 py-2.5 dark:border-slate-800">
          {fileInput}
          <button
            type="button"
            disabled={locked}
            onClick={() => fileInputRef.current?.click()}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-600 transition hover:border-teal-300 hover:text-teal-700 disabled:opacity-50 dark:border-slate-600 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
            aria-label="Attach image or PDF"
            title="Attach image or PDF"
          >
            <AttachIcon />
          </button>
          <button
            type="button"
            disabled={locked}
            onClick={() => void handleMicClick()}
            className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border transition disabled:opacity-50 ${
              listening
                ? "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
                : "border-slate-200 text-slate-600 hover:border-teal-300 hover:text-teal-700 dark:border-slate-600 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
            }`}
            aria-label={listening ? "Stop recording" : "Speak"}
            title={listening ? "Stop recording" : "Speak"}
          >
            <MicIcon />
          </button>
          <div className="ml-auto">
            <button
              type="button"
              onClick={onSubmit}
              disabled={!canSubmit || locked}
              className="inline-flex h-10 items-center justify-center gap-2 rounded-xl bg-teal-600 px-5 text-sm font-medium text-white transition hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isProcessing ? "Analysing…" : "Analyse"}
            </button>
          </div>
        </div>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Enter to analyse · Shift+Enter for a new line · Mic for speech · Paperclip
        for images/PDFs (context only — files are not kept as a vault)
      </p>

      {micError && (
        <p className="text-sm text-rose-700 dark:text-rose-300" role="alert">
          {micError}
        </p>
      )}
      {fileError && (
        <p className="text-sm text-rose-700 dark:text-rose-300" role="alert">
          {fileError}
        </p>
      )}

      {guidance && (
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
          {guidance}
        </p>
      )}
      {tipBlock}
    </div>
  );
}

function MicIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z"
      />
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M19 10v2a7 7 0 01-14 0v-2M12 19v4M8 23h8"
      />
    </svg>
  );
}

function AttachIcon() {
  return (
    <svg
      className="h-4 w-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21.44 11.05l-8.49 8.49a5.5 5.5 0 01-7.78-7.78l8.49-8.49a3.5 3.5 0 014.95 4.95l-8.5 8.49a1.5 1.5 0 01-2.12-2.12l7.79-7.78"
      />
    </svg>
  );
}

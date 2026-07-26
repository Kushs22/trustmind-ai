"use client";

import { useEffect } from "react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";

type VoiceInputProps = {
  disabled?: boolean;
  onTranscriptConfirmed: (transcript: string) => void;
  draftTranscript: string;
  onDraftChange: (value: string) => void;
  onDiscard: () => void;
};

export function VoiceInput({
  disabled,
  onTranscriptConfirmed,
  draftTranscript,
  onDraftChange,
  onDiscard,
}: VoiceInputProps) {
  const browserSpeech = useSpeechRecognition();
  const recorder = useVoiceRecorder();
  const useBrowser = browserSpeech.supported;

  useEffect(() => {
    if (
      !useBrowser &&
      recorder.status === "completed" &&
      recorder.transcript &&
      recorder.transcript !== draftTranscript
    ) {
      onDraftChange(recorder.transcript);
    }
  }, [
    useBrowser,
    recorder.status,
    recorder.transcript,
    draftTranscript,
    onDraftChange,
  ]);

  const listening = useBrowser
    ? browserSpeech.listening
    : recorder.status === "listening";
  const paused = !useBrowser && recorder.status === "paused";
  const processing = !useBrowser && recorder.status === "processing";

  const statusLabel = processing
    ? "Processing"
    : paused
      ? "Paused"
      : listening
        ? "Listening"
        : draftTranscript
          ? "Completed"
          : "Ready";

  async function handleStart() {
    if (useBrowser) {
      browserSpeech.start();
    } else {
      await recorder.start();
    }
  }

  function handleStop() {
    if (useBrowser) {
      browserSpeech.stop();
      const text =
        `${browserSpeech.finalTranscript} ${browserSpeech.interim}`.trim();
      if (text) onDraftChange(text);
    } else {
      void recorder.stopAndTranscribe();
    }
  }

  const liveBrowser =
    `${browserSpeech.finalTranscript} ${browserSpeech.interim}`.trim();
  const displayDraft =
    draftTranscript || (useBrowser ? liveBrowser : recorder.transcript);

  const error = useBrowser ? browserSpeech.error : recorder.error;

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/60 p-4 dark:border-slate-700 dark:bg-slate-800/50">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          disabled={disabled || listening || processing}
          onClick={() => void handleStart()}
          className="inline-flex items-center gap-2 rounded-lg border border-teal-300 bg-white px-3 py-2 text-sm font-medium text-teal-800 shadow-sm transition hover:bg-teal-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-teal-700 dark:bg-slate-900 dark:text-teal-200"
          aria-label="Start microphone recording"
        >
          <MicIcon />
          Speak
        </button>
        {listening && !useBrowser && (
          <button
            type="button"
            onClick={recorder.pause}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
            aria-label="Pause recording"
          >
            Pause
          </button>
        )}
        {paused && (
          <button
            type="button"
            onClick={recorder.resume}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
            aria-label="Resume recording"
          >
            Resume
          </button>
        )}
        {(listening || paused) && (
          <button
            type="button"
            onClick={handleStop}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm dark:border-slate-600"
            aria-label="Stop recording"
          >
            Stop
          </button>
        )}
        {(listening || paused || displayDraft) && (
          <button
            type="button"
            onClick={() => {
              if (useBrowser) browserSpeech.cancel();
              else recorder.cancel();
              onDiscard();
            }}
            className="rounded-lg border border-rose-200 px-3 py-2 text-sm text-rose-700 dark:border-rose-800 dark:text-rose-300"
            aria-label="Cancel recording"
          >
            Cancel
          </button>
        )}
        <span className="text-xs text-slate-500" aria-live="polite">
          Status: {statusLabel}
          {!useBrowser && recorder.status !== "idle"
            ? ` · ${recorder.elapsedLabel}`
            : ""}
        </span>
      </div>
      <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
        {useBrowser
          ? "Using browser speech recognition. Mic access is requested only when you click Speak."
          : "Browser speech recognition unavailable — audio will be transcribed securely on the server. Audio is not retained in privacy mode."}
      </p>
      {error && (
        <p className="mt-2 text-sm text-rose-700 dark:text-rose-300" role="alert">
          {error}
        </p>
      )}
      {recorder.warnings.length > 0 && (
        <ul className="mt-2 list-disc pl-5 text-xs text-amber-700 dark:text-amber-300">
          {recorder.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}
      {displayDraft && (
        <div className="mt-3 space-y-2">
          <label
            htmlFor="speech-transcript"
            className="text-xs font-medium uppercase tracking-wide text-slate-500"
          >
            Speech transcript (editable)
          </label>
          <textarea
            id="speech-transcript"
            value={displayDraft}
            onChange={(e) => onDraftChange(e.target.value)}
            rows={3}
            disabled={disabled || listening || processing}
            className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-900"
          />
          <button
            type="button"
            disabled={disabled || !displayDraft.trim()}
            onClick={() => onTranscriptConfirmed(displayDraft.trim())}
            className="rounded-lg bg-teal-600 px-3 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-50"
          >
            Use transcript
          </button>
        </div>
      )}
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
      aria-hidden="true"
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

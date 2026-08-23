"use client";

import { useEffect } from "react";
import { useSpeechRecognition } from "@/hooks/useSpeechRecognition";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";

export type VoiceController = ReturnType<typeof useVoiceController>;

/** Shared speech state for the analyse composer (mic + transcript panel). */
export function useVoiceController(
  transcript: string,
  onTranscriptChange: (value: string) => void,
  onClear: () => void,
) {
  const browserSpeech = useSpeechRecognition();
  const recorder = useVoiceRecorder();
  const useBrowser = browserSpeech.supported;

  useEffect(() => {
    if (
      !useBrowser &&
      recorder.status === "completed" &&
      recorder.transcript.trim()
    ) {
      onTranscriptChange(recorder.transcript.trim());
    }
  }, [useBrowser, recorder.status, recorder.transcript, onTranscriptChange]);

  const listening = useBrowser
    ? browserSpeech.listening
    : recorder.status === "listening";
  const paused = !useBrowser && recorder.status === "paused";
  const processing = !useBrowser && recorder.status === "processing";
  const active = listening || paused || processing;

  const liveBrowser =
    `${browserSpeech.finalTranscript} ${browserSpeech.interim}`.trim();
  const livePreview =
    transcript || (useBrowser ? liveBrowser : recorder.transcript);

  const error = useBrowser ? browserSpeech.error : recorder.error;

  async function handleMicClick() {
    if (listening || paused) {
      if (useBrowser) {
        // Prefer refs so stop doesn't race with the last onresult paint.
        const text = browserSpeech.getSpokenText();
        browserSpeech.stop();
        if (text) onTranscriptChange(text);
        browserSpeech.clearTranscript();
      } else {
        await recorder.stopAndTranscribe();
      }
      return;
    }
    if (useBrowser) {
      browserSpeech.start();
    } else {
      await recorder.start();
    }
  }

  function handleCancel() {
    if (useBrowser) browserSpeech.cancel();
    else recorder.cancel();
    onClear();
  }

  return {
    useBrowser,
    listening,
    paused,
    processing,
    active,
    livePreview,
    error,
    warnings: recorder.warnings,
    elapsedLabel: recorder.elapsedLabel,
    handleMicClick,
    handleCancel,
    pause: recorder.pause,
    resume: recorder.resume,
    onTranscriptChange,
  };
}

type MicButtonProps = {
  voice: VoiceController;
  disabled?: boolean;
};

export function VoiceMicButton({ voice, disabled }: MicButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled || voice.processing}
      onClick={() => void voice.handleMicClick()}
      className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
        voice.active
          ? "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
          : "border-slate-200 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
      }`}
      aria-label={
        voice.listening || voice.paused
          ? "Stop recording"
          : voice.processing
            ? "Transcribing audio"
            : "Speak"
      }
      title={
        voice.listening || voice.paused
          ? "Stop"
          : voice.processing
            ? "Transcribing…"
            : "Speak"
      }
    >
      <MicIcon />
    </button>
  );
}

type TranscriptPanelProps = {
  voice: VoiceController;
  disabled?: boolean;
  hasTranscript: boolean;
};

export function VoiceTranscriptPanel({
  voice,
  disabled,
  hasTranscript,
}: TranscriptPanelProps) {
  if (!voice.livePreview.trim() && !voice.active && !hasTranscript) {
    return null;
  }

  return (
    <div className="space-y-1.5">
      {voice.active && (
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
          <span
            className="inline-flex h-2 w-2 animate-pulse rounded-full bg-rose-500"
            aria-hidden
          />
          <span aria-live="polite">
            {voice.processing
              ? "Transcribing…"
              : voice.paused
                ? "Paused"
                : "Listening"}
            {!voice.useBrowser && voice.active ? ` · ${voice.elapsedLabel}` : ""}
          </span>
          {!voice.useBrowser && voice.listening && (
            <button
              type="button"
              onClick={voice.pause}
              className="rounded-md border border-slate-200 px-2 py-0.5 dark:border-slate-600"
            >
              Pause
            </button>
          )}
          {voice.paused && (
            <button
              type="button"
              onClick={voice.resume}
              className="rounded-md border border-slate-200 px-2 py-0.5 dark:border-slate-600"
            >
              Resume
            </button>
          )}
          <button
            type="button"
            onClick={voice.handleCancel}
            className="rounded-md border border-rose-200 px-2 py-0.5 text-rose-700 dark:border-rose-800 dark:text-rose-300"
          >
            Cancel
          </button>
        </div>
      )}

      {voice.error && (
        <p className="text-xs text-rose-700 dark:text-rose-300" role="alert">
          {voice.error}
        </p>
      )}
      {voice.warnings.length > 0 && (
        <ul className="list-disc pl-4 text-xs text-amber-700 dark:text-amber-300">
          {voice.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </ul>
      )}

      {(voice.livePreview.trim() || voice.active) && (
        <div className="rounded-xl border border-teal-200/80 bg-teal-50/40 px-3 py-2 dark:border-teal-900 dark:bg-teal-950/30">
          <div className="flex items-center justify-between gap-2">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-teal-800 dark:text-teal-200">
              Speech
            </p>
            {hasTranscript && !voice.active && (
              <button
                type="button"
                onClick={voice.handleCancel}
                disabled={disabled}
                className="text-[11px] font-medium text-slate-500 hover:text-rose-600 dark:text-slate-400 dark:hover:text-rose-300"
              >
                Clear
              </button>
            )}
          </div>
          <textarea
            value={voice.livePreview}
            onChange={(e) => voice.onTranscriptChange(e.target.value)}
            rows={2}
            disabled={disabled || voice.listening || voice.processing}
            placeholder={voice.active ? "Listening…" : "Speech transcript"}
            aria-label="Speech transcript"
            className="mt-1.5 w-full resize-y rounded-lg border border-transparent bg-white/80 px-2 py-1.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-teal-300 focus:outline-none focus:ring-1 focus:ring-teal-200 disabled:opacity-70 dark:bg-slate-900/80 dark:text-slate-100 dark:focus:ring-teal-900/40"
          />
        </div>
      )}
    </div>
  );
}

/** Back-compat wrapper: mic + transcript stacked (unused by AnalyseForm). */
export function VoiceInput({
  disabled,
  transcript,
  onTranscriptChange,
  onClear,
}: {
  disabled?: boolean;
  transcript: string;
  onTranscriptChange: (value: string) => void;
  onClear: () => void;
}) {
  const voice = useVoiceController(transcript, onTranscriptChange, onClear);
  return (
    <div className="flex flex-wrap items-start gap-2">
      <VoiceMicButton voice={voice} disabled={disabled} />
      <div className="min-w-0 flex-1">
        <VoiceTranscriptPanel
          voice={voice}
          disabled={disabled}
          hasTranscript={Boolean(transcript.trim())}
        />
      </div>
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

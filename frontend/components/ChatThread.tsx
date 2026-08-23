"use client";

import Link from "next/link";
import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatMessage, SupportResource } from "@/lib/api";
import { useVoiceRecorder } from "@/hooks/useVoiceRecorder";

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

function MicIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "h-4 w-4"}
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

function AttachIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className ?? "h-4 w-4"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21.44 11.05l-8.49 8.49a5.5 5.5 0 01-7.78-7.78l8.49-8.49a3.5 3.5 0 014.95 4.95l-8.5 8.49a1.5 1.5 0 01-2.12-2.12l7.79-7.78"
      />
    </svg>
  );
}

type ChatThreadProps = {
  messages: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  onSendAudio?: (file: Blob, filename: string) => void;
  isSending: boolean;
  error?: string | null;
  supportResources?: SupportResource[];
  subtitle?: string | null;
  persisted?: boolean;
  disabled?: boolean;
  disabledReason?: string | null;
  toneDisclaimer?: string | null;
};

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  const isAudio = msg.input_type === "audio";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed sm:max-w-[75%] ${
          isUser
            ? "rounded-br-md bg-teal-600 text-white"
            : "rounded-bl-md border border-slate-200 bg-slate-50 text-slate-800 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-100"
        }`}
      >
        {!isUser && (
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-teal-700 dark:text-teal-300">
            TrustMind
          </p>
        )}
        {isUser && isAudio ? (
          <div className="space-y-1.5">
            <p className="inline-flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide text-teal-100">
              <MicIcon className="h-3 w-3" />
              Audio message
            </p>
            {msg.transcript ? (
              <p className="whitespace-pre-wrap opacity-95">&ldquo;{msg.transcript}&rdquo;</p>
            ) : (
              <p className="whitespace-pre-wrap opacity-95">{msg.content}</p>
            )}
            {msg.tone_summary && (
              <p
                className={`text-xs ${isUser ? "text-teal-100/90" : "text-slate-500"}`}
              >
                How this sounded: {msg.tone_summary}
              </p>
            )}
            {msg.affect_cues && msg.affect_cues.length > 0 && (
              <p className={`text-[11px] ${isUser ? "text-teal-100/80" : "text-slate-500"}`}>
                Tone cues: {msg.affect_cues.join(", ")}
              </p>
            )}
          </div>
        ) : (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        )}
      </div>
    </div>
  );
}

export function ChatThread({
  messages,
  draft,
  onDraftChange,
  onSend,
  onSendAudio,
  isSending,
  error,
  supportResources,
  subtitle,
  persisted,
  disabled,
  disabledReason,
  toneDisclaimer,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const recorder = useVoiceRecorder();

  const audioBusy =
    recorder.status === "listening" ||
    recorder.status === "paused" ||
    recorder.status === "processing";
  const composerLocked = isSending || disabled || audioBusy;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending, audioBusy]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!composerLocked && draft.trim()) onSend();
    }
  }

  async function handleMicClick() {
    // Do not gate on composerLocked: that includes audioBusy and would block Stop.
    if (!onSendAudio || isSending || disabled) return;
    if (recorder.status === "listening" || recorder.status === "paused") {
      const blob = await recorder.stopAndGetBlob();
      if (!blob) return;
      const ext = blob.type.includes("mp4") ? "mp4" : "webm";
      onSendAudio(blob, `recording.${ext}`);
      return;
    }
    await recorder.start();
  }

  function handleFilePick(file: File | null) {
    if (!file || !onSendAudio || composerLocked) return;
    onSendAudio(file, file.name || "upload.webm");
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  return (
    <div className="flex min-h-[70vh] flex-col overflow-hidden rounded-2xl border border-slate-200/80 bg-white shadow-sm dark:border-slate-700/80 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3 border-b border-slate-200/80 px-4 py-3 dark:border-slate-700/80 sm:px-5">
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-slate-800 dark:text-slate-100">
            Check-in conversation
          </p>
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">
            {subtitle ||
              (persisted
                ? "Saved thread — follow-ups stay with this check-in"
                : "Session thread — continues here only; not saved to history")}
          </p>
        </div>
        <Link
          href="/analyse"
          className="inline-flex h-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 px-3 text-sm font-medium text-slate-700 transition-colors hover:border-teal-200 hover:bg-teal-50/60 dark:border-slate-600 dark:text-slate-200 dark:hover:border-teal-700 dark:hover:bg-teal-950/40"
        >
          New chat
        </Link>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5">
        {messages.length === 0 && (
          <p className="text-center text-sm text-slate-500 dark:text-slate-400">
            No messages yet. Share how you&apos;re feeling below.
          </p>
        )}
        {messages.map((msg, index) => (
          <MessageBubble
            key={`${msg.role}-${index}-${msg.created_at || ""}`}
            msg={msg}
          />
        ))}

        {isSending && (
          <div className="flex justify-start">
            <div className="inline-flex items-center gap-2 rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300">
              <Spinner className="h-4 w-4 text-teal-600" />
              Reflecting…
            </div>
          </div>
        )}

        {supportResources && supportResources.length > 0 && (
          <div
            className="rounded-xl border border-rose-200 bg-rose-50/80 p-4 dark:border-rose-900 dark:bg-rose-950/40"
            role="alert"
          >
            <p className="text-xs font-medium uppercase tracking-wide text-rose-700 dark:text-rose-300">
              Priority support options
            </p>
            <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">
              If you are in immediate danger, call 999 or go to A&amp;E.
            </p>
            <ul className="mt-3 space-y-2">
              {supportResources.map((resource) => (
                <li key={resource.name} className="text-sm text-slate-700 dark:text-slate-300">
                  <p className="font-medium">{resource.name}</p>
                  <p className="text-slate-600 dark:text-slate-400">{resource.contact}</p>
                  <a
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-teal-700 underline dark:text-teal-300"
                  >
                    Open resource
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div className="border-t border-slate-200/80 bg-slate-50/80 px-4 py-3 dark:border-slate-700/80 dark:bg-slate-950/40 sm:px-5">
        {error && (
          <p className="mb-2 text-sm text-red-700 dark:text-red-300" role="alert">
            {error}
          </p>
        )}
        {recorder.error && (
          <p className="mb-2 text-sm text-red-700 dark:text-red-300" role="alert">
            {recorder.error}
          </p>
        )}
        {disabled && disabledReason && (
          <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">{disabledReason}</p>
        )}
        {(recorder.status === "listening" || recorder.status === "paused") && (
          <div className="mb-2 flex flex-wrap items-center gap-2 text-xs text-teal-800 dark:text-teal-200">
            <span
              className="inline-flex h-2 w-2 animate-pulse rounded-full bg-rose-500"
              aria-hidden
            />
            Recording {recorder.elapsedLabel}
            {recorder.status === "paused" ? " (paused)" : ""}
            <button
              type="button"
              onClick={() =>
                recorder.status === "paused" ? recorder.resume() : recorder.pause()
              }
              className="rounded-md border border-teal-300/60 px-2 py-0.5 dark:border-teal-700"
            >
              {recorder.status === "paused" ? "Resume" : "Pause"}
            </button>
            <button
              type="button"
              onClick={() => recorder.cancel()}
              className="rounded-md border border-rose-200 px-2 py-0.5 text-rose-700 dark:border-rose-800 dark:text-rose-300"
            >
              Cancel
            </button>
          </div>
        )}
        <div className="flex items-end gap-2">
          {onSendAudio && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="audio/*,.webm,.mp3,.wav,.m4a,.ogg"
                className="hidden"
                onChange={(event) =>
                  handleFilePick(event.target.files?.[0] ?? null)
                }
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={composerLocked}
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
                aria-label="Upload audio file"
                title="Upload audio"
              >
                <AttachIcon />
              </button>
              <button
                type="button"
                onClick={() => void handleMicClick()}
                disabled={isSending || disabled}
                className={`inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${
                  recorder.status === "listening" || recorder.status === "paused"
                    ? "border-rose-300 bg-rose-50 text-rose-700 dark:border-rose-800 dark:bg-rose-950/50 dark:text-rose-300"
                    : "border-slate-200 bg-white text-slate-600 hover:border-teal-300 hover:text-teal-700 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
                }`}
                aria-label={
                  recorder.status === "listening" || recorder.status === "paused"
                    ? "Stop recording and send"
                    : "Record audio message"
                }
                title={
                  recorder.status === "listening" || recorder.status === "paused"
                    ? "Stop & send"
                    : "Record"
                }
              >
                <MicIcon />
              </button>
            </>
          )}
          <textarea
            ref={composerRef}
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={composerLocked}
            placeholder="Message TrustMind…"
            className="max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-teal-900/40"
          />
          <button
            type="button"
            onClick={onSend}
            disabled={composerLocked || !draft.trim()}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 px-4 text-sm font-medium text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
          Enter to send · Mic or upload for audio · Tone cues are soft impressions,
          not a mood diagnosis · Not therapy
        </p>
        {toneDisclaimer && (
          <p className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
            {toneDisclaimer}
          </p>
        )}
      </div>
    </div>
  );
}

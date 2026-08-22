"use client";

import Link from "next/link";
import { useEffect, useRef, type KeyboardEvent } from "react";
import type { ChatMessage, SupportResource } from "@/lib/api";

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

type ChatThreadProps = {
  messages: ChatMessage[];
  draft: string;
  onDraftChange: (value: string) => void;
  onSend: () => void;
  isSending: boolean;
  error?: string | null;
  supportResources?: SupportResource[];
  subtitle?: string | null;
  persisted?: boolean;
  disabled?: boolean;
  disabledReason?: string | null;
};

export function ChatThread({
  messages,
  draft,
  onDraftChange,
  onSend,
  isSending,
  error,
  supportResources,
  subtitle,
  persisted,
  disabled,
  disabledReason,
}: ChatThreadProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const composerRef = useRef<HTMLTextAreaElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isSending && !disabled && draft.trim()) onSend();
    }
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
                : "Session thread — turn on save to keep this conversation")}
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
        {messages.map((msg, index) => {
          const isUser = msg.role === "user";
          return (
            <div
              key={`${msg.role}-${index}-${msg.created_at || ""}`}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}
            >
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
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          );
        })}

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
        {disabled && disabledReason && (
          <p className="mb-2 text-sm text-slate-600 dark:text-slate-400">{disabledReason}</p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            ref={composerRef}
            value={draft}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            disabled={isSending || disabled}
            placeholder="Message TrustMind…"
            className="max-h-40 min-h-[2.75rem] flex-1 resize-y rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 placeholder:text-slate-400 focus:border-teal-300 focus:outline-none focus:ring-2 focus:ring-teal-100 disabled:cursor-not-allowed disabled:opacity-60 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100 dark:focus:ring-teal-900/40"
          />
          <button
            type="button"
            onClick={onSend}
            disabled={isSending || disabled || !draft.trim()}
            className="inline-flex h-11 shrink-0 items-center justify-center rounded-xl bg-teal-600 px-4 text-sm font-medium text-white transition-colors hover:bg-teal-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Send
          </button>
        </div>
        <p className="mt-2 text-[11px] text-slate-500 dark:text-slate-400">
          Enter to send · Shift+Enter for a new line · Not a diagnosis or therapy service
        </p>
      </div>
    </div>
  );
}

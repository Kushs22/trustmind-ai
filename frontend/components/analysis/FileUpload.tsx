"use client";

import { useRef, useState } from "react";
import type { PendingImage, PendingPdf } from "@/hooks/useFileUpload";
import { ImagePreview } from "@/components/analysis/ImagePreview";
import { PdfPreview } from "@/components/analysis/PdfPreview";

type FileUploadProps = {
  disabled?: boolean;
  images: PendingImage[];
  pdfs: PendingPdf[];
  error: string | null;
  onAddFiles: (files: FileList | File[]) => void;
  onRemoveImage: (id: string) => void;
  onRemovePdf: (id: string) => void;
  onUpdateImageText: (id: string, text: string) => void;
  onUpdatePdfText: (id: string, text: string) => void;
  onToggleImage: (id: string, included: boolean) => void;
  onTogglePdf: (id: string, included: boolean) => void;
  /** When true, only the attach button is rendered (previews handled by parent). */
  buttonOnly?: boolean;
  /** When true, hide file pickers and show editable attachment previews only. */
  hidePickers?: boolean;
};

/**
 * Compact attach control for the analyse composer.
 * Single pick button accepts images and PDFs; previews stay compact chips.
 */
export function FileUpload({
  disabled,
  images,
  pdfs,
  error,
  onAddFiles,
  onRemoveImage,
  onRemovePdf,
  onUpdateImageText,
  onUpdatePdfText,
  onToggleImage,
  onTogglePdf,
  buttonOnly = false,
  hidePickers = false,
}: FileUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const attachButton = (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => fileInputRef.current?.click()}
        className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
        aria-label="Attach image or PDF for analysis context"
        title="Attach image or PDF (processed for context only — not stored as a vault)"
      >
        <AttachIcon />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf,.pdf"
        multiple
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(e) => {
          if (e.target.files?.length) onAddFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </>
  );

  if (buttonOnly && !hidePickers) {
    return attachButton;
  }

  // hidePickers (or default): editable attachment previews only — attach lives in the composer toolbar.
  return (
    <div className="space-y-2">
      {(images.length > 0 || pdfs.length > 0) && (
        <ul className="flex flex-wrap gap-2" aria-label="Attached files">
          {images.map((img) => {
            const open = expandedId === img.id;
            return (
              <li key={img.id} className="min-w-0 max-w-full">
                <button
                  type="button"
                  onClick={() => setExpandedId(open ? null : img.id)}
                  className={`inline-flex max-w-full items-center gap-2 rounded-full border px-2.5 py-1 text-xs transition-colors ${
                    open
                      ? "border-teal-400 bg-teal-50 text-teal-900 dark:border-teal-600 dark:bg-teal-950/40 dark:text-teal-100"
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:border-teal-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                  }`}
                  aria-expanded={open}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={img.previewUrl}
                    alt=""
                    className="h-5 w-5 rounded object-cover"
                  />
                  <span className="truncate">{img.file.name}</span>
                  <span className="shrink-0 text-[10px] uppercase text-slate-400">
                    {img.status === "uploading" ? "…" : "IMG"}
                  </span>
                </button>
                {open && (
                  <div className="mt-2">
                    <ImagePreview
                      item={img}
                      disabled={disabled}
                      onRemove={() => {
                        onRemoveImage(img.id);
                        setExpandedId(null);
                      }}
                      onTextChange={(t) => onUpdateImageText(img.id, t)}
                      onToggleIncluded={(v) => onToggleImage(img.id, v)}
                    />
                  </div>
                )}
              </li>
            );
          })}
          {pdfs.map((pdf) => {
            const open = expandedId === pdf.id;
            return (
              <li key={pdf.id} className="min-w-0 max-w-full">
                <button
                  type="button"
                  onClick={() => setExpandedId(open ? null : pdf.id)}
                  className={`inline-flex max-w-full items-center gap-2 rounded-full border px-2.5 py-1 text-xs transition-colors ${
                    open
                      ? "border-teal-400 bg-teal-50 text-teal-900 dark:border-teal-600 dark:bg-teal-950/40 dark:text-teal-100"
                      : "border-slate-200 bg-slate-50 text-slate-700 hover:border-teal-300 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-200"
                  }`}
                  aria-expanded={open}
                >
                  <span className="inline-flex h-5 w-5 items-center justify-center rounded bg-slate-200 text-[9px] font-semibold text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                    PDF
                  </span>
                  <span className="truncate">{pdf.file.name}</span>
                  <span className="shrink-0 text-[10px] uppercase text-slate-400">
                    {pdf.status === "uploading" ? "…" : "PDF"}
                  </span>
                </button>
                {open && (
                  <div className="mt-2">
                    <PdfPreview
                      item={pdf}
                      disabled={disabled}
                      onRemove={() => {
                        onRemovePdf(pdf.id);
                        setExpandedId(null);
                      }}
                      onTextChange={(t) => onUpdatePdfText(pdf.id, t)}
                      onToggleIncluded={(v) => onTogglePdf(pdf.id, v)}
                    />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      {error && (
        <p className="text-xs text-rose-700 dark:text-rose-300" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}

/** Toolbar attach button + hidden file input (use with FileUpload chip list). */
export function AttachButton({
  disabled,
  onAddFiles,
}: {
  disabled?: boolean;
  onAddFiles: (files: FileList | File[]) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  return (
    <>
      <button
        type="button"
        disabled={disabled}
        onClick={() => fileInputRef.current?.click()}
        className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-600 transition-colors hover:border-teal-300 hover:text-teal-700 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-teal-700 dark:hover:text-teal-200"
        aria-label="Attach image or PDF for analysis context"
        title="Attach image or PDF (processed for context only — not stored as a vault)"
      >
        <AttachIcon />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,application/pdf,.pdf"
        multiple
        className="sr-only"
        aria-hidden="true"
        tabIndex={-1}
        onChange={(e) => {
          if (e.target.files?.length) onAddFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </>
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

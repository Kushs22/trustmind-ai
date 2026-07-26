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
};

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
}: FileUploadProps) {
  const imageInputRef = useRef<HTMLInputElement>(null);
  const pdfInputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={disabled}
          onClick={() => imageInputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          aria-label="Add image"
        >
          <ImageIcon />
          Add image
        </button>
        <button
          type="button"
          disabled={disabled}
          onClick={() => pdfInputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200"
          aria-label="Add PDF"
        >
          <DocIcon />
          Add PDF
        </button>
        <input
          ref={imageInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => {
            if (e.target.files?.length) onAddFiles(e.target.files);
            e.target.value = "";
          }}
        />
        <input
          ref={pdfInputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          className="sr-only"
          aria-hidden="true"
          tabIndex={-1}
          onChange={(e) => {
            if (e.target.files?.length) onAddFiles(e.target.files);
            e.target.value = "";
          }}
        />
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          if (e.dataTransfer.files?.length) onAddFiles(e.dataTransfer.files);
        }}
        className={`rounded-xl border border-dashed px-4 py-6 text-center text-sm ${
          dragOver
            ? "border-teal-400 bg-teal-50/50 dark:bg-teal-950/30"
            : "border-slate-300 bg-slate-50/40 dark:border-slate-600 dark:bg-slate-800/40"
        }`}
        role="region"
        aria-label="Drag and drop upload area"
      >
        <p className="text-slate-600 dark:text-slate-300">
          Drag and drop images or PDFs here
        </p>
        <p className="mt-1 text-xs text-slate-500">
          Images should not include unnecessary personal information. Uploaded
          files are contextual only — not trusted medical evidence.
        </p>
      </div>

      {error && (
        <p className="text-sm text-rose-700 dark:text-rose-300" role="alert">
          {error}
        </p>
      )}

      {images.length > 0 && (
        <ul className="space-y-3" aria-label="Selected images">
          {images.map((img) => (
            <li key={img.id}>
              <ImagePreview
                item={img}
                disabled={disabled}
                onRemove={() => onRemoveImage(img.id)}
                onTextChange={(t) => onUpdateImageText(img.id, t)}
                onToggleIncluded={(v) => onToggleImage(img.id, v)}
              />
            </li>
          ))}
        </ul>
      )}

      {pdfs.length > 0 && (
        <ul className="space-y-3" aria-label="Selected PDFs">
          {pdfs.map((pdf) => (
            <li key={pdf.id}>
              <PdfPreview
                item={pdf}
                disabled={disabled}
                onRemove={() => onRemovePdf(pdf.id)}
                onTextChange={(t) => onUpdatePdfText(pdf.id, t)}
                onToggleIncluded={(v) => onTogglePdf(pdf.id, v)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ImageIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 5a2 2 0 012-2h12a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V5z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 13l2.5 2.5L15 11l5 6H4l4-4z" />
    </svg>
  );
}

function DocIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7 3h7l5 5v13a1 1 0 01-1 1H7a1 1 0 01-1-1V4a1 1 0 011-1z" />
      <path strokeLinecap="round" strokeLinejoin="round" d="M14 3v5h5M9 13h6M9 17h6" />
    </svg>
  );
}

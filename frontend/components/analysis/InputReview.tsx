"use client";

type InputReviewProps = {
  typedText: string;
  speechTranscript: string;
  imageSummaries: Array<{ filename: string; text: string }>;
  pdfSummaries: Array<{ filename: string; text: string }>;
  analysePrivately: boolean;
  disabled?: boolean;
  onBack: () => void;
  onConfirm: () => void;
};

export function InputReview({
  typedText,
  speechTranscript,
  imageSummaries,
  pdfSummaries,
  analysePrivately,
  disabled,
  onBack,
  onConfirm,
}: InputReviewProps) {
  return (
    <div
      className="rounded-xl border border-teal-200 bg-teal-50/40 p-5 dark:border-teal-900 dark:bg-teal-950/30"
      role="region"
      aria-label="Review inputs before analysis"
    >
      <h3 className="text-base font-semibold text-slate-800 dark:text-slate-100">
        Review before analysis
      </h3>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
        Confirm what will be sent. Uploaded files are contextual input only —
        not trusted RAG evidence.
      </p>

      <div className="mt-4 space-y-3 text-sm">
        <ReviewBlock title="Typed text" body={typedText || "(none)"} />
        <ReviewBlock
          title="Speech transcript"
          body={speechTranscript || "(none)"}
        />
        {imageSummaries.map((img) => (
          <ReviewBlock
            key={img.filename}
            title={`Image: ${img.filename}`}
            body={img.text || "(no text)"}
          />
        ))}
        {pdfSummaries.map((pdf) => (
          <ReviewBlock
            key={pdf.filename}
            title={`PDF: ${pdf.filename}`}
            body={pdf.text || "(no text)"}
          />
        ))}
      </div>

      <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
        {analysePrivately
          ? "Privacy mode: temporary files and extracted content are not retained after processing."
          : "You have disabled private mode for history — only an approved summary may be stored, not original files."}
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={onBack}
          disabled={disabled}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium dark:border-slate-600"
        >
          Back to edit
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={disabled}
          className="rounded-lg bg-teal-600 px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
        >
          Confirm and analyse
        </button>
      </div>
    </div>
  );
}

function ReviewBlock({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-lg border border-white/80 bg-white/80 p-3 dark:border-slate-700 dark:bg-slate-900/80">
      <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
        {title}
      </p>
      <p className="mt-1 whitespace-pre-wrap text-slate-700 dark:text-slate-200">
        {body}
      </p>
    </div>
  );
}

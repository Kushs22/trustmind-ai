export function LeafIcon({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 20 20"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="M4 16C4 9.5 9 4 16 3.5c.2 7-3.8 12.5-12 12.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
      <path
        d="M8 12c2-2 4.5-3.2 8-3.5"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function BrandMark({ inverted = false }: { inverted?: boolean }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="inline-flex h-5 w-5 items-center justify-center"
        style={{ color: inverted ? "var(--color-text-inverse)" : "var(--color-brand)" }}
      >
        <LeafIcon />
      </span>
      <span
        className="text-[18px] font-bold leading-none"
        style={{ color: inverted ? "var(--color-text-inverse)" : "var(--color-brand)" }}
      >
        TrustMind AI
      </span>
    </span>
  );
}

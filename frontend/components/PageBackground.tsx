export function PageBackground() {
  return (
    <div
      className="pointer-events-none absolute inset-0"
      aria-hidden="true"
    >
      <div className="absolute -right-32 top-0 h-96 w-96 rounded-full bg-teal-800/10 blur-3xl dark:bg-teal-400/10" />
      <div className="absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-amber-200/30 blur-3xl dark:bg-amber-500/10" />
    </div>
  );
}

export function PageBackground() {
  return (
    <div
      className="pointer-events-none absolute inset-0 opacity-40"
      aria-hidden="true"
    >
      <div className="absolute -right-32 top-0 h-96 w-96 rounded-full bg-teal-200/50 blur-3xl" />
      <div className="absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-blue-200/50 blur-3xl" />
    </div>
  );
}

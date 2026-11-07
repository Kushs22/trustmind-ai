import Link from "next/link";

function ShieldIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"
      />
    </svg>
  );
}

function ChartIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"
      />
    </svg>
  );
}

function SparklesIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 00-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z"
      />
    </svg>
  );
}

function LockIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z"
      />
    </svg>
  );
}

function EyeOffIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.894 7.894L21 21m-3.228-3.228l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88"
      />
    </svg>
  );
}

function ServerIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M21.75 17.25v-.228a4.5 4.5 0 00-.12-1.03L12 4.5l-9.63 11.47a4.5 4.5 0 00-.12 1.03v.228m19.5 0a3 3 0 01-3 3H5.25a3 3 0 01-3-3m19.5 0a3 3 0 00-3-3H5.25a3 3 0 00-3 3m16.5 0h.008v.008h-.008v-.008zm-3 0h.008v.008h-.008v-.008z"
      />
    </svg>
  );
}

const heroPoints = [
  {
    label: "Careful, not clinical",
    detail: "A warm read of what you shared — never a diagnosis.",
  },
  {
    label: "Trusted UK guidance",
    detail: "NHS, Mind and Samaritans extracts, only when we actually retrieved them.",
  },
  {
    label: "Help near you",
    detail: "Live Bristol services from Nyata AI, next to national helplines.",
  },
  {
    label: "Private by default",
    detail: "No account required. You choose what, if anything, is saved.",
  },
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0"
        aria-hidden="true"
      >
        <div className="absolute -right-20 top-0 h-[28rem] w-[28rem] rounded-full bg-teal-700/15 blur-3xl dark:bg-teal-400/10" />
        <div className="absolute -left-24 bottom-10 h-80 w-80 rounded-full bg-amber-200/40 blur-3xl dark:bg-amber-500/10" />
      </div>

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 pb-20 pt-28 lg:grid-cols-[1.15fr_0.85fr] lg:gap-16 lg:px-8 lg:pb-28 lg:pt-32">
        <div>
          <p className="inline-flex items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--surface)] px-3 py-1 text-xs font-semibold tracking-wide text-teal-900 dark:text-teal-200">
            <ShieldIcon className="h-3.5 w-3.5" />
            TrustMind × Nyata AI
          </p>
          <h1 className="font-display mt-6 max-w-xl text-5xl leading-[1.1] text-stone-900 dark:text-stone-50 sm:text-6xl">
            When things feel heavy, talk it through here.
          </h1>
          <p className="mt-6 max-w-xl text-lg leading-relaxed text-stone-600 dark:text-stone-300">
            A private check-in for anyone who is anxious, low, overwhelmed, or
            just needs to put something into words. We reply in your language,
            ground answers in trusted UK guidance, and can point to live
            Bristol support.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href="/analyse"
              className="inline-flex h-12 items-center justify-center rounded-full bg-teal-800 px-7 text-base font-semibold text-white hover:bg-teal-900 dark:bg-teal-400 dark:text-teal-950 dark:hover:bg-teal-300"
            >
              Start a private check-in
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex h-12 items-center justify-center rounded-full border border-[var(--line)] bg-[var(--surface)] px-7 text-base font-medium text-stone-700 hover:bg-white dark:text-stone-200 dark:hover:bg-stone-800"
            >
              See how it works
            </a>
          </div>
          <p className="mt-4 text-sm text-stone-500 dark:text-stone-400">
            Anonymous · Not a diagnosis · Get help now is always one tap away
          </p>
        </div>

        <div className="rounded-[2rem] border border-[var(--line)] bg-[var(--surface)] p-5 shadow-[0_24px_80px_-40px_rgba(28,25,23,0.45)] sm:p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-teal-800 dark:text-teal-300">
            What you get
          </p>
          <ul className="mt-4 space-y-3">
            {heroPoints.map((point) => (
              <li
                key={point.label}
                className="rounded-2xl border border-[var(--line)] bg-[var(--background)] px-4 py-3.5"
              >
                <p className="text-sm font-semibold text-stone-900 dark:text-stone-50">
                  {point.label}
                </p>
                <p className="mt-1 text-sm leading-relaxed text-stone-600 dark:text-stone-300">
                  {point.detail}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

const features = [
  {
    icon: ChartIcon,
    title: "A clear, human reply",
    description:
      "You get a careful reflection of what you shared, plus next steps you can actually use — not a diagnosis and not a lecture.",
  },
  {
    icon: ShieldIcon,
    title: "Grounded in trusted pages",
    description:
      "When it helps, we pull short extracts from NHS, Mind, Samaritans and similar sources. You can see where a reply came from.",
  },
  {
    icon: SparklesIcon,
    title: "Local help, when you want it",
    description:
      "Nyata AI can add live Bristol groups, meals, and support services next to national helplines — without replacing them.",
  },
];

export function FeaturesSection() {
  return (
    <section
      id="features"
      className="scroll-mt-28 py-20 lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-teal-800 dark:text-teal-300">
            Why TrustMind
          </p>
          <h2 className="font-display mt-3 text-4xl text-stone-900 dark:text-stone-50 sm:text-5xl">
            Built for the people around us, not a campus form
          </h2>
          <p className="mt-4 text-lg text-stone-600 dark:text-stone-400">
            Support that is easy to reach when things feel heavy — at 1am, after
            work, or on a difficult commute.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-[1.75rem] border border-[var(--line)] bg-[var(--surface)] p-8 transition-all hover:border-teal-700/40"
            >
              <div className="mb-5 inline-flex rounded-2xl bg-teal-800 p-3 text-teal-50 dark:bg-teal-500 dark:text-teal-950">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="font-display text-2xl text-stone-900 dark:text-stone-50">
                {feature.title}
              </h3>
              <p className="mt-3 leading-relaxed text-stone-600 dark:text-stone-400">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const privacyPoints = [
  {
    icon: LockIcon,
    title: "Secure in transit",
    description: "Connections use HTTPS. Passwords are stored as hashes, not plain text.",
  },
  {
    icon: EyeOffIcon,
    title: "No training on your data",
    description: "We do not use your check-ins to train public models on our side.",
  },
  {
    icon: ServerIcon,
    title: "You control retention",
    description: "Export or delete saved history from the privacy page anytime.",
  },
];

export function PrivacySection() {
  return (
    <section
      id="privacy"
      className="bg-teal-950 py-20 text-teal-50 lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-100">
              Privacy & Safety
            </p>
            <h2 className="font-display mt-3 text-4xl sm:text-5xl">
              Your wellbeing data stays yours
            </h2>
            <p className="mt-4 text-lg leading-relaxed text-teal-50/90">
              TrustMind AI is architected with privacy as a foundation—not an
              afterthought. We believe trustworthy support requires transparent
              data practices and strict boundaries around how information is
              handled.
            </p>
            <Link
              href="/privacy"
              className="mt-8 inline-flex items-center gap-2 text-sm font-medium text-teal-100 underline-offset-4 hover:underline"
            >
              Read our full privacy policy
            </Link>
            <ul className="mt-8 space-y-4">
              {[
                "Minimal data collection by design",
                "Full transparency on AI processing",
                "You control retention and deletion",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span className="mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-white/20">
                    <svg
                      className="h-3 w-3"
                      fill="currentColor"
                      viewBox="0 0 12 12"
                      aria-hidden="true"
                    >
                      <path d="M10.28 2.28a.75.75 0 00-1.06-1.06L4.5 8.44 2.78 6.72a.75.75 0 00-1.06 1.06l2.25 2.25a.75.75 0 001.06 0l5.25-5.25z" />
                    </svg>
                  </span>
                  <span className="text-teal-50">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-4">
            {privacyPoints.map((point) => (
              <div
                key={point.title}
                className="flex gap-4 rounded-xl border border-white/20 bg-white/10 p-6 backdrop-blur-sm"
              >
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-white/20">
                  <point.icon className="h-6 w-6" />
                </div>
                <div>
                  <h3 className="font-semibold">{point.title}</h3>
                  <p className="mt-1 text-sm text-teal-50/80">
                    {point.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

const steps = [
  {
    step: "01",
    title: "Share how you're feeling",
    description:
      "Type, speak, or attach notes. The more you share, the better we can support you — one-word check-ins still work.",
  },
  {
    step: "02",
    title: "Receive a gentle reflection",
    description:
      "You see a warm, non-diagnostic read of what you shared, plus supportive next steps — not pipeline mechanics.",
  },
  {
    step: "03",
    title: "Explore support at your pace",
    description:
      "Review insights privately. Export or delete your data anytime. Crisis support routes stay available when needed.",
  },
];

export function HowItWorksSection() {
  return (
    <section
      id="how-it-works"
      className="scroll-mt-28 py-20 lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-teal-800 dark:text-teal-300">
            How it works
          </p>
          <h2 className="font-display mt-3 text-4xl text-stone-900 dark:text-stone-50 sm:text-5xl">
            Three steps, no account required
          </h2>
          <p className="mt-4 text-lg text-stone-600 dark:text-stone-400">
            A straightforward process—no accounts required to explore.
          </p>
        </div>

        <div className="mt-16 grid gap-8 lg:grid-cols-3">
          {steps.map((item, index) => (
            <div key={item.step} className="relative">
              {index < steps.length - 1 && (
                <div
                  className="absolute left-1/2 top-12 hidden h-0.5 w-full bg-gradient-to-r from-teal-200 to-blue-200 dark:from-teal-800 dark:to-blue-900 lg:block"
                  aria-hidden="true"
                />
              )}
              <div className="relative rounded-[1.75rem] border border-[var(--line)] bg-[var(--surface)] p-8">
                <span className="font-display text-4xl text-teal-800/40 dark:text-teal-300/40">
                  {item.step}
                </span>
                <h3 className="font-display mt-4 text-2xl text-stone-900 dark:text-stone-50">
                  {item.title}
                </h3>
                <p className="mt-3 leading-relaxed text-stone-600 dark:text-stone-400">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function CTASection() {
  return (
    <section className="py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="relative overflow-hidden rounded-[2rem] bg-teal-900 px-8 py-16 text-center sm:px-16">
          <div
            className="pointer-events-none absolute inset-0 opacity-20"
            aria-hidden="true"
          >
            <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white blur-3xl" />
            <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-teal-300 blur-3xl" />
          </div>
          <div className="relative">
            <h2 className="font-display text-4xl text-white sm:text-5xl">
              You do not have to carry this alone
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-lg text-teal-50">
              Check in anonymously in a few minutes. If you want, we can also
              point you to someone nearby in Bristol.
            </p>
            <Link
              href="/analyse"
              className="mt-8 inline-flex h-12 items-center justify-center rounded-full bg-[var(--background)] px-8 text-base font-semibold text-teal-950 hover:bg-white"
            >
              Start a private check-in
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

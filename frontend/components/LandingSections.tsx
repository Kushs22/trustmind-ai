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

export function HeroSection() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-white via-teal-50/30 to-blue-50/40 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        aria-hidden="true"
      >
        <div className="absolute -right-32 -top-32 h-96 w-96 rounded-full bg-teal-200/50 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-80 w-80 rounded-full bg-blue-200/50 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-6xl px-6 pb-20 pt-16 lg:px-8 lg:pb-28 lg:pt-24">
        <div className="mx-auto max-w-3xl text-center">
          <div className="animate-fade-in-up mb-6 inline-flex items-center gap-2 rounded-full border border-teal-200/80 bg-white/80 dark:bg-slate-900/80 px-4 py-1.5 text-sm font-medium text-teal-700 shadow-sm">
            <ShieldIcon className="h-4 w-4" />
            Trustworthy AI wellbeing support
          </div>

          <h1 className="animate-fade-in-up animate-delay-100 text-4xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-5xl lg:text-6xl">
            Clarity and confidence for your{" "}
            <span className="bg-gradient-to-r from-teal-600 to-blue-500 bg-clip-text text-transparent">
              mental wellbeing
            </span>
          </h1>

          <p className="animate-fade-in-up animate-delay-200 mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-slate-600 dark:text-slate-400">
            TrustMind AI gives students and everyday users thoughtful,
            evidence-informed wellbeing insights—without compromising your
            privacy. A calm platform built for clarity when you need support
            you can trust.
          </p>

          <div className="animate-fade-in-up animate-delay-300 mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
            <Link
              href="/analyse"
              className="inline-flex h-12 min-w-[200px] items-center justify-center rounded-xl bg-teal-600 px-8 text-base font-medium text-white shadow-md shadow-teal-600/20 transition-all hover:bg-teal-700 hover:shadow-lg hover:shadow-teal-600/25"
            >
              Start your analysis
            </Link>
            <a
              href="#how-it-works"
              className="inline-flex h-12 min-w-[200px] items-center justify-center rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 px-8 text-base font-medium text-slate-700 dark:text-slate-300 transition-colors hover:border-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800"
            >
              See how it works
            </a>
          </div>
        </div>

        <div className="mx-auto mt-16 max-w-5xl">
          <div className="rounded-2xl border border-slate-200/80 bg-white dark:border-slate-700/80 dark:bg-slate-900 p-1 shadow-xl shadow-slate-200/50 dark:shadow-slate-950/50">
            <div className="rounded-xl bg-gradient-to-br from-slate-50 to-blue-50/50 dark:from-slate-900 dark:to-slate-800/50 p-6 sm:p-8">
              <div className="mb-4 flex items-center gap-2 border-b border-slate-200/60 pb-4">
                <div className="flex gap-1.5">
                  <span className="h-3 w-3 rounded-full bg-slate-300" />
                  <span className="h-3 w-3 rounded-full bg-slate-300" />
                  <span className="h-3 w-3 rounded-full bg-slate-300" />
                </div>
                <span className="text-xs font-medium text-slate-400">
                  Trust assessment preview
                </span>
              </div>
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {[
                  {
                    label: "Emotional distress level",
                    value: "Moderate",
                    detail: "Based on your input",
                    detailClass: "text-amber-600",
                  },
                  {
                    label: "AI confidence",
                    value: "87%",
                    detail: "High certainty",
                    detailClass: "text-teal-600",
                  },
                  {
                    label: "Uncertainty level",
                    value: "Low",
                    detail: "Clear signal detected",
                    detailClass: "text-teal-600",
                  },
                  {
                    label: "Grounding evidence",
                    value: "3 sources",
                    detail: "Verified references",
                    detailClass: "text-blue-600",
                  },
                  {
                    label: "Abstention status",
                    value: "Not triggered",
                    detail: "Response provided",
                    detailClass: "text-teal-600",
                  },
                  {
                    label: "Privacy protection",
                    value: "Active",
                    detail: "End-to-end encrypted",
                    detailClass: "text-teal-600",
                  },
                ].map((metric) => (
                  <div
                    key={metric.label}
                    className="rounded-lg border border-white/80 bg-white p-4 shadow-sm"
                  >
                    <p className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
                      {metric.label}
                    </p>
                    <p className="mt-1 text-xl font-semibold text-slate-800 dark:text-slate-100">
                      {metric.value}
                    </p>
                    <p className={`mt-1 text-sm ${metric.detailClass}`}>
                      {metric.detail}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

const features = [
  {
    icon: ChartIcon,
    title: "Structured wellbeing insights",
    description:
      "Receive clear, organized assessments based on your inputs—not vague advice. Understand patterns with dashboards built for clarity.",
  },
  {
    icon: ShieldIcon,
    title: "Evidence-informed analysis",
    description:
      "Our models draw on established wellbeing frameworks to surface meaningful signals, helping you make informed decisions about next steps.",
  },
  {
    icon: SparklesIcon,
    title: "Calm, focused experience",
    description:
      "A distraction-free interface designed for reflection. No gamification, no pressure—just thoughtful support when you need it.",
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="bg-white py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
            Why TrustMind AI
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-4xl">
            Built for thoughtful self-understanding
          </h2>
          <p className="mt-4 text-lg text-slate-600 dark:text-slate-400">
            Text-based analysis tools that respect your time and your data.
          </p>
        </div>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="group rounded-2xl border border-slate-200 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-800/50 p-8 transition-all hover:border-teal-200 hover:bg-teal-50/30 hover:shadow-md"
            >
              <div className="mb-5 inline-flex rounded-xl bg-teal-100 p-3 text-teal-700 transition-colors group-hover:bg-teal-600 group-hover:text-white">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                {feature.title}
              </h3>
              <p className="mt-3 leading-relaxed text-slate-600 dark:text-slate-400">
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
    title: "End-to-end encryption",
    description: "Your data is encrypted in transit and at rest.",
  },
  {
    icon: EyeOffIcon,
    title: "No training on your data",
    description: "Personal inputs are never used to train public models.",
  },
  {
    icon: ServerIcon,
    title: "Regional data residency",
    description: "Choose where your information is stored and processed.",
  },
];

export function PrivacySection() {
  return (
    <section
      id="privacy"
      className="bg-gradient-to-br from-teal-700 via-teal-600 to-blue-600 py-20 text-white lg:py-28"
    >
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-100">
              Privacy & Safety
            </p>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
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
    title: "Share your context",
    description:
      "Describe how you're feeling through a guided, text-based assessment focused on emotional wellbeing.",
  },
  {
    step: "02",
    title: "Receive your analysis",
    description:
      "Our AI processes your inputs privately and generates clear, AI-generated wellbeing insights.",
  },
  {
    step: "03",
    title: "Explore supportive next steps",
    description:
      "Review supportive insights at your own pace. Export or delete your data anytime.",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="bg-slate-50 py-20 lg:py-28">
      <div className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
            How it works
          </p>
          <h2 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-4xl">
            Three steps to clearer insight
          </h2>
          <p className="mt-4 text-lg text-slate-600 dark:text-slate-400">
            A straightforward process—no accounts required to explore.
          </p>
        </div>

        <div className="mt-16 grid gap-8 lg:grid-cols-3">
          {steps.map((item, index) => (
            <div key={item.step} className="relative">
              {index < steps.length - 1 && (
                <div
                  className="absolute left-1/2 top-12 hidden h-0.5 w-full bg-gradient-to-r from-teal-200 to-blue-200 lg:block"
                  aria-hidden="true"
                />
              )}
              <div className="relative rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-8 shadow-sm">
                <span className="text-4xl font-bold text-teal-100">
                  {item.step}
                </span>
                <h3 className="mt-4 text-xl font-semibold text-slate-800 dark:text-slate-100">
                  {item.title}
                </h3>
                <p className="mt-3 leading-relaxed text-slate-600 dark:text-slate-400">
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
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-r from-teal-600 to-blue-500 px-8 py-16 text-center shadow-xl sm:px-16">
          <div
            className="pointer-events-none absolute inset-0 opacity-20"
            aria-hidden="true"
          >
            <div className="absolute -right-16 -top-16 h-64 w-64 rounded-full bg-white blur-3xl" />
            <div className="absolute -bottom-16 -left-16 h-64 w-64 rounded-full bg-teal-300 blur-3xl" />
          </div>
          <div className="relative">
            <h2 className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">
              Ready to understand your wellbeing?
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-lg text-teal-50">
              Start a private analysis in minutes. No commitment, no chat
              sessions—just clear insights you can trust.
            </p>
            <Link
              href="/analyse"
              className="mt-8 inline-flex h-12 items-center justify-center rounded-xl bg-white px-8 text-base font-semibold text-teal-700 shadow-lg transition-all hover:bg-teal-50 hover:shadow-xl"
            >
              Start Analysis
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}

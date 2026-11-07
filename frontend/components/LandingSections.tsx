import Link from "next/link";
import { Reveal } from "@/components/Reveal";

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
    <section className="relative min-h-[100vh] overflow-hidden bg-[var(--color-bg)]">
      <div className="relative mx-auto grid min-h-[100vh] max-w-6xl items-center gap-12 px-6 py-24 lg:grid-cols-[1.15fr_0.85fr] lg:gap-16 lg:px-8">
        <div className="hero-in">
          <p className="inline-flex items-center gap-2 rounded-[999px] border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-1 text-xs font-semibold tracking-wide text-[var(--color-accent)]">
            <ShieldIcon className="h-3.5 w-3.5" />
            TrustMind AI × Nyata AI
          </p>
          <h1 className="mt-6 max-w-xl font-bold">
            When things feel heavy, talk it through here.
          </h1>
          <p className="mt-6 max-w-[540px] text-[var(--color-text-muted)]" style={{ lineHeight: 1.75 }}>
            A private check-in for anyone who is anxious, low, overwhelmed, or
            just needs to put something into words. We reply in your language,
            ground answers in trusted UK guidance, and can point to live
            Bristol support.
          </p>
          <div className="mt-8 flex w-full flex-col gap-3 sm:w-auto sm:flex-row sm:items-center">
            <Link href="/analyse" className="btn-primary w-full sm:w-auto">
              Start a private check-in
            </Link>
            <a href="#how-it-works" className="btn-secondary w-full sm:w-auto">
              See how it works
            </a>
          </div>
          <p className="mt-4 text-sm text-[var(--color-text-muted)]">
            Anonymous · Not a diagnosis · Get help now is always one tap away
          </p>
        </div>

        <div className="hero-in surface-card p-6" style={{ animationDelay: "80ms" }}>
          <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[var(--color-accent)]">
            What you get
          </p>
          <ul className="mt-4 space-y-3">
            {heroPoints.map((point) => (
              <li
                key={point.label}
                className="rounded-[16px] border border-[var(--color-border)] bg-[var(--color-surface-alt)] px-4 py-3.5"
              >
                <p className="text-[15px] font-semibold text-[var(--color-text)]">
                  {point.label}
                </p>
                <p className="mt-1 text-[14px] leading-[1.6] text-[var(--color-text-muted)]">
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
      className="section scroll-mt-28 bg-[var(--color-surface)]"
    >
      <Reveal className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--color-accent)]">
            Why TrustMind AI
          </p>
          <h2 className="mt-3">
            Built for the people around us, not a campus form
          </h2>
          <p className="mt-4 text-[var(--color-text-muted)]">
            Support that is easy to reach when things feel heavy — at 1am, after
            work, or on a difficult commute.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature) => (
            <div
              key={feature.title}
              className="card-hover reveal-child surface-card p-6"
            >
              <div className="mb-5 inline-flex h-10 w-10 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                <feature.icon className="h-5 w-5" />
              </div>
              <h3 className="text-[15px] font-semibold">
                {feature.title}
              </h3>
              <p className="mt-2 text-[14px] leading-[1.6] text-[var(--color-text-muted)]">
                {feature.description}
              </p>
            </div>
          ))}
        </div>
      </Reveal>
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
    <section id="privacy" className="section bg-[var(--color-bg)]">
      <Reveal className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="grid items-start gap-12 lg:grid-cols-2 lg:gap-16">
          <div className="max-w-[720px]">
            <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--color-accent)]">
              Privacy & Safety
            </p>
            <h2 className="mt-3">Your wellbeing data stays yours</h2>
            <p className="mt-4 text-[var(--color-text-muted)]">
              TrustMind AI is architected with privacy as a foundation—not an
              afterthought. We believe trustworthy support requires transparent
              data practices and strict boundaries around how information is
              handled.
            </p>
            <Link href="/privacy" className="btn-primary mt-8">
              Read our full privacy policy
            </Link>
            <ul className="mt-8 space-y-4">
              {[
                "Minimal data collection by design",
                "Full transparency on AI processing",
                "You control retention and deletion",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <span
                    className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center text-[var(--color-accent)]"
                    aria-hidden="true"
                  >
                    ✓
                  </span>
                  <span className="text-[var(--color-text)]">{item}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-4">
            {privacyPoints.map((point) => (
              <div
                key={point.title}
                className="reveal-child flex gap-4 rounded-[16px] border border-[var(--color-border)] border-l-[3px] border-l-[var(--color-accent)] bg-[var(--color-surface)] p-6 shadow-[var(--shadow-card)]"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-[var(--color-accent-soft)] text-[var(--color-accent)]">
                  <point.icon className="h-5 w-5" />
                </div>
                <div>
                  <h3>{point.title}</h3>
                  <p className="mt-1 text-sm text-[var(--color-text-muted)]">
                    {point.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Reveal>
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
      className="section scroll-mt-28 bg-[var(--color-surface-alt)]"
    >
      <Reveal className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="mx-auto max-w-2xl text-center">
          <p className="text-sm font-semibold uppercase tracking-[0.16em] text-[var(--color-accent)]">
            How it works
          </p>
          <h2 className="mt-3">Three steps, no account required</h2>
          <p className="mt-4 text-[var(--color-text-muted)]">
            A straightforward process—no accounts required to explore.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-8 lg:grid-cols-3">
          {steps.map((item, index) => (
            <div key={item.step} className="relative">
              {index < steps.length - 1 && (
                <div
                  className="absolute left-1/2 top-7 hidden w-full border-t border-dashed border-[var(--color-border)] lg:block"
                  aria-hidden="true"
                />
              )}
              <div className="reveal-child relative">
                <span className="text-[48px] font-semibold leading-none text-[var(--color-accent)]/40">
                  {item.step}
                </span>
                <h3 className="mt-4">{item.title}</h3>
                <p className="mt-3 text-[var(--color-text-muted)]">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

export function CTASection() {
  return (
    <section className="section bg-[var(--color-bg)]">
      <Reveal className="mx-auto max-w-6xl px-6 lg:px-8">
        <div className="rounded-[16px] bg-[var(--color-surface)] px-8 py-16 text-center shadow-[var(--shadow-card)] sm:px-16">
          <h2>You do not have to carry this alone</h2>
          <p className="mx-auto mt-4 max-w-xl text-[var(--color-text-muted)]">
            Check in anonymously in a few minutes. If you want, we can also
            point you to someone nearby in Bristol.
          </p>
          <Link href="/analyse" className="btn-primary mt-8">
            Start a private check-in
          </Link>
        </div>
      </Reveal>
    </section>
  );
}

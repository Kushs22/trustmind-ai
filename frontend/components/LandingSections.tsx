import Link from "next/link";
import type { CSSProperties } from "react";
import { Reveal } from "@/components/Reveal";

function IconWrap({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      className="h-5 w-5"
      aria-hidden="true"
    >
      {children}
    </svg>
  );
}

function HeartIcon() {
  return (
    <IconWrap>
      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12.57l-7.5 7.43-7.5-7.43a5 5 0 117.5-6.56 5 5 0 117.5 6.56z" />
    </IconWrap>
  );
}

function ShieldIcon() {
  return (
    <IconWrap>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l8 4v6c0 5-3.4 8.4-8 9.5C7.4 21.4 4 18 4 13V7l8-4z" />
    </IconWrap>
  );
}

function MapPinIcon() {
  return (
    <IconWrap>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 21s7-5.4 7-11a7 7 0 10-14 0c0 5.6 7 11 7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </IconWrap>
  );
}

function LockIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-8 w-8" aria-hidden="true">
      <rect x="5" y="11" width="14" height="10" rx="2" />
      <path strokeLinecap="round" d="M8 11V8a4 4 0 018 0v3" />
    </svg>
  );
}

function EyeOffIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-8 w-8" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M3 3l18 18M10.6 10.6A3 3 0 0012 15a3 3 0 002.4-4.4M9.9 5.1A10.5 10.5 0 0121 12c-.5 1-1.2 2-2.1 2.8M6.1 6.1C4.6 7.3 3.4 8.9 2.5 12c1.6 5 6 8.5 9.5 8.5 1.3 0 2.6-.3 3.8-.9" />
    </svg>
  );
}

function ServerIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="h-8 w-8" aria-hidden="true">
      <rect x="3" y="4" width="18" height="6" rx="1.5" />
      <rect x="3" y="14" width="18" height="6" rx="1.5" />
      <circle cx="7" cy="7" r="0.8" fill="currentColor" />
      <circle cx="7" cy="17" r="0.8" fill="currentColor" />
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

function HeroArt() {
  return (
    <svg
      className="animate-float mx-auto mt-12 w-full max-w-[600px]"
      viewBox="0 0 600 220"
      fill="none"
      aria-hidden="true"
    >
      <circle cx="220" cy="110" r="90" fill="var(--color-brand-soft)" />
      <circle cx="360" cy="100" r="80" fill="var(--color-accent-soft)" />
      <circle cx="300" cy="130" r="70" fill="var(--color-brand-soft)" opacity="0.7" />
      <circle cx="160" cy="140" r="40" fill="var(--color-accent-soft)" opacity="0.8" />
    </svg>
  );
}

export function HeroSection() {
  return (
    <section
      className="relative flex min-h-[100vh] flex-col justify-center overflow-hidden"
      style={{
        background:
          "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(42,92,69,0.08), transparent), var(--color-bg)",
      }}
    >
      <div className="page-wrap flex flex-col items-center py-24 text-center">
        <p
          className="animate-fade-up inline-flex items-center rounded-[var(--radius-pill)] bg-[var(--color-brand-soft)] px-3 py-1 text-[13px] font-medium text-[var(--color-brand)]"
          style={{ animationDelay: "0ms" }}
        >
          TrustMind AI × Nyata AI
        </p>
        <h1 className="hero-title animate-fade-up mt-6 max-w-[820px] font-normal" style={{ animationDelay: "80ms" }}>
          When things feel heavy, <em>talk it through here.</em>
        </h1>
        <p
          className="animate-fade-up mt-6 max-w-[540px] text-[length:var(--text-lg)] text-[var(--color-text-secondary)]"
          style={{ animationDelay: "160ms", lineHeight: 1.75 }}
        >
          A private check-in for anyone who is anxious, low, overwhelmed, or
          just needs to put something into words. We reply in your language,
          ground answers in trusted UK guidance, and can point to live
          Bristol support.
        </p>
        <div className="animate-fade-up mt-8 flex w-full flex-col items-stretch justify-center gap-4 sm:w-auto sm:flex-row" style={{ animationDelay: "240ms" }}>
          <Link href="/analyse" className="btn-primary btn-lg w-full sm:w-auto">
            Start a private check-in
          </Link>
          <a href="#how-it-works" className="btn-secondary btn-lg w-full sm:w-auto">
            See how it works
          </a>
        </div>
        <p className="animate-fade-up mt-4 text-[length:var(--text-xs)] text-[var(--color-text-muted)]" style={{ animationDelay: "300ms" }}>
          Anonymous · Not a diagnosis · Get help now is always one tap away
        </p>

        <div className="animate-fade-up mt-10 flex w-full max-w-[720px] flex-col divide-y divide-[var(--color-border)] overflow-hidden rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] sm:flex-row sm:divide-x sm:divide-y-0" style={{ animationDelay: "360ms" }}>
          {[
            ["100% private", "No data sold"],
            ["Anonymous", "No account needed"],
            ["Bristol ♥", "Local support included"],
          ].map(([label, sub]) => (
            <div key={label} className="flex-1 px-5 py-4">
              <p className="text-[13px] font-semibold">{label}</p>
              <p className="text-[11px] text-[var(--color-text-muted)]">{sub}</p>
            </div>
          ))}
        </div>

        <HeroArt />

        <ul className="mt-4 grid w-full grid-cols-1 gap-3 text-left sm:grid-cols-2">
          {heroPoints.map((point, i) => (
            <li
              key={point.label}
              className="surface-card p-5"
              style={{ ["--i" as string]: i } as CSSProperties}
            >
              <p className="text-[15px] font-semibold">{point.label}</p>
              <p className="mt-1 text-[14px] leading-[1.65] text-[var(--color-text-secondary)]">
                {point.detail}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

export function TrustBar() {
  return (
    <div className="border-y border-[var(--color-border)] bg-[var(--color-bg-alt)] py-5">
      <p className="page-wrap text-center text-[13px] font-medium leading-relaxed text-[var(--color-text-muted)]">
        HTTPS encrypted · No ads · No data sold · Built by MSc AI researchers ·
        Local Bristol support via Nyata AI
      </p>
    </div>
  );
}

const features = [
  {
    icon: HeartIcon,
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
    icon: MapPinIcon,
    title: "Local help, when you want it",
    description:
      "Nyata AI can add live Bristol groups, meals, and support services next to national helplines — without replacing them.",
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="section scroll-mt-28 bg-[var(--color-surface)]">
      <Reveal className="page-wrap">
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-[13px] font-medium uppercase tracking-[0.06em] text-[var(--color-brand)]">
            Why TrustMind AI
          </p>
          <h2 className="mt-3">
            Built for the people around us, not a campus form
          </h2>
          <p className="mt-4 text-[var(--color-text-secondary)]">
            Support that is easy to reach when things feel heavy — at 1am, after
            work, or on a difficult commute.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => (
            <div
              key={feature.title}
              className="card-hover reveal-child rounded-[var(--radius-lg)] border border-[var(--color-border)] border-l-2 border-l-[var(--color-brand)] bg-[var(--color-surface)] p-8 shadow-[var(--shadow-sm)]"
              style={{ ["--i" as string]: i } as CSSProperties}
            >
              <div className="mb-5 inline-flex h-11 w-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-brand-soft)] text-[var(--color-brand-mid)]">
                <feature.icon />
              </div>
              <p className="text-[15px] font-semibold">{feature.title}</p>
              <p className="mt-2 text-[14px] leading-[1.65] text-[var(--color-text-secondary)]">
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
    <section id="privacy" className="section bg-[var(--color-dark-bg)] text-[var(--color-dark-text)]">
      <Reveal className="page-wrap">
        <div className="max-w-[720px]">
          <p className="text-[13px] font-medium uppercase tracking-[0.06em] text-[var(--color-brand-mid)]">
            Privacy & Safety
          </p>
          <h2 className="mt-3 text-[var(--color-text-inverse)]">
            Your wellbeing data stays yours
          </h2>
          <p className="mt-4 text-[var(--color-dark-muted)]">
            TrustMind AI is architected with privacy as a foundation—not an
            afterthought. We believe trustworthy support requires transparent
            data practices and strict boundaries around how information is
            handled.
          </p>
        </div>

        <div className="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {privacyPoints.map((point, i) => (
            <div
              key={point.title}
              className="reveal-child rounded-[var(--radius-md)] border border-[var(--color-dark-border)] bg-[var(--color-dark-surface)] p-5"
              style={{ ["--i" as string]: i } as CSSProperties}
            >
              <span className="text-[var(--color-brand-mid)]">
                <point.icon />
              </span>
              <p className="mt-3 text-[14px] font-semibold text-[var(--color-dark-text)]">
                {point.title}
              </p>
              <p className="mt-1 text-[13px] text-[var(--color-dark-muted)]">
                {point.description}
              </p>
            </div>
          ))}
        </div>

        <ul className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-3">
          {[
            "Minimal data collection by design",
            "Full transparency on AI processing",
            "You control retention and deletion",
          ].map((item, i) => (
            <li
              key={item}
              className="rounded-[var(--radius-md)] border-t border-[var(--color-brand-mid)] bg-[var(--color-dark-surface)] px-5 py-4 text-[14px]"
              style={{ ["--i" as string]: i } as CSSProperties}
            >
              {item}
            </li>
          ))}
        </ul>

        <Link
          href="/privacy"
          className="mt-10 inline-flex h-11 items-center justify-center rounded-[var(--radius-md)] bg-[var(--color-surface)] px-5 text-[15px] font-semibold text-[var(--color-brand)]"
        >
          Read our full privacy policy
        </Link>
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
      className="section scroll-mt-28 bg-[var(--color-bg-alt)]"
    >
      <Reveal className="page-wrap">
        <div className="mx-auto max-w-[600px] text-center">
          <p className="text-[13px] font-medium uppercase tracking-[0.06em] text-[var(--color-brand)]">
            How it works
          </p>
          <h2 className="mt-3">Three steps, no account required</h2>
          <p className="mt-4 text-[var(--color-text-secondary)]">
            A straightforward process—no accounts required to explore.
          </p>
        </div>

        <div className="mt-16 grid grid-cols-1 gap-10 lg:grid-cols-3">
          {steps.map((item, index) => (
            <div key={item.step} className="relative">
              {index < steps.length - 1 && (
                <div
                  className="absolute left-1/2 top-8 hidden w-full border-t border-dashed border-[var(--color-border)] lg:block"
                  aria-hidden="true"
                />
              )}
              <div
                className="reveal-child relative"
                style={{ ["--i" as string]: index } as CSSProperties}
              >
                <span
                  className="font-display pointer-events-none absolute -top-4 left-0 text-[72px] leading-none text-[var(--color-brand)]"
                  style={{ opacity: 0.12 }}
                >
                  {item.step}
                </span>
                <p className="relative pt-10 text-[18px] font-bold">{item.title}</p>
                <p className="relative mt-3 text-[15px] text-[var(--color-text-secondary)]">
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

export function SocialProofSection() {
  // TODO: Replace with real user quotes when available
  const quotes = [
    {
      text: "Finally a tool that doesn't feel like a form. It just listens.",
      by: "Anonymous user",
    },
    {
      text: "Showed me a local support group I didn't know existed.",
      by: "Bristol student",
    },
    {
      text: "Quick, private, no sign-up needed. Used it at 2am.",
      by: "Anonymous",
    },
  ];

  return (
    <section
      className="section"
      style={{
        background:
          "linear-gradient(180deg, var(--color-bg) 0%, var(--color-bg-alt) 100%)",
      }}
    >
      <Reveal className="page-wrap">
        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {quotes.map((quote, i) => (
            <figure
              key={quote.by + quote.text}
              className="reveal-child rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-7"
              style={{ ["--i" as string]: i } as CSSProperties}
            >
              <span className="font-display text-[48px] leading-none text-[var(--color-brand-soft)]">
                “
              </span>
              <blockquote className="font-display mt-2 text-[17px] italic leading-snug">
                {quote.text}
              </blockquote>
              <figcaption className="mt-4 text-[13px] font-medium text-[var(--color-text-muted)]">
                — {quote.by}
              </figcaption>
            </figure>
          ))}
        </div>
      </Reveal>
    </section>
  );
}

export function CTASection() {
  return (
    <section className="section bg-[var(--color-bg)]">
      <Reveal className="page-wrap">
        <div className="rounded-[var(--radius-xl)] bg-[var(--color-surface)] px-8 py-16 text-center shadow-[var(--shadow-md)] sm:px-16">
          <h2>You do not have to carry this alone</h2>
          <p className="mx-auto mt-4 max-w-xl text-[var(--color-text-secondary)]">
            Check in anonymously in a few minutes. If you want, we can also
            point you to someone nearby in Bristol.
          </p>
          <Link href="/analyse" className="btn-primary btn-lg mt-8">
            Start a private check-in
          </Link>
        </div>
      </Reveal>
    </section>
  );
}

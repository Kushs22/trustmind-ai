import type { Metadata } from "next";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Resources — TrustMind AI",
  description:
    "Crisis numbers, NHS and charity support, and live Bristol listings via Nyata AI.",
};

const resourceCategories = [
  {
    title: "Immediate Crisis Support",
    description: "If you need urgent help right now.",
    items: [
      {
        name: "Emergency services",
        detail: "Call 999 if you or someone else is in immediate danger.",
        href: "tel:999",
      },
      {
        name: "NHS 111",
        detail: "Urgent medical advice when it is not a life-threatening emergency.",
        href: "https://111.nhs.uk/",
      },
    ],
  },
  {
    title: "National charities",
    description: "Information and listening support for anyone in the UK.",
    items: [
      {
        name: "Mind",
        detail: "Advice and support if you are experiencing a mental health problem.",
        href: "https://www.mind.org.uk/",
      },
      {
        name: "CALM",
        detail: "Call 0800 58 58 58, 5pm–midnight, if you are struggling to cope.",
        href: "https://www.thecalmzone.net/",
      },
      {
        name: "Rethink Mental Illness",
        detail: "Practical information for people affected by mental illness.",
        href: "https://www.rethink.org/",
      },
    ],
  },
  {
    title: "Bristol, with Nyata AI",
    description: "Live local services appear on your check-in when Nyata finds a match.",
    items: [
      {
        name: "Nyata AI",
        detail: "Community meals, groups, and support listed by verified local organisations.",
        href: "https://nyataai.co.uk",
      },
      {
        name: "Bristol Mindline",
        detail: "0117 203 4419 · Wednesday–Sunday, 7pm–11pm.",
        href: "tel:01172034419",
      },
    ],
  },
  {
    title: "NHS Mental Health Support",
    description: "Free NHS services for mental health concerns.",
    items: [
      {
        name: "NHS Every Mind Matters",
        detail: "Practical tips and NHS-approved wellbeing guidance.",
        href: "https://www.nhs.uk/every-mind-matters/",
      },
      {
        name: "Find NHS talking therapies",
        detail: "Self-refer for NHS psychological therapies (IAPT).",
        href: "https://www.nhs.uk/nhs-services/mental-health-services/",
      },
    ],
  },
  {
    title: "Samaritans",
    description: "Confidential emotional support, 24 hours a day.",
    items: [
      {
        name: "Samaritans — Call 116 123",
        detail: "Free to call from any phone, available 24/7.",
        href: "https://www.samaritans.org/",
      },
      {
        name: "Samaritans email support",
        detail: "Write to jo@samaritans.org (response within 24 hours).",
        href: "https://www.samaritans.org/",
      },
    ],
  },
  {
    title: "Practical support",
    description: "Housing, money, and everyday strain can sit underneath low mood.",
    items: [
      {
        name: "Shelter housing advice",
        detail: "Free housing and homelessness support in the UK.",
        href: "https://www.shelter.org.uk/",
      },
      {
        name: "Citizens Advice",
        detail: "Help with benefits, debt, housing, and work problems.",
        href: "https://www.citizensadvice.org.uk/",
      },
    ],
  },
];

export default function ResourcesPage() {
  return (
    <div className="min-h-screen bg-[#fafbfc] dark:bg-slate-950">
      <Header />
      <main className="relative overflow-hidden">
        <PageBackground />
        <div className="relative mx-auto max-w-6xl px-6 py-12 lg:px-8 lg:py-16">
          <div className="mb-10 text-center">
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-600">
              Support directory
            </p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-800 dark:text-slate-100 sm:text-4xl">
              Wellbeing resources
            </h1>
            <p className="mx-auto mt-4 max-w-2xl text-base leading-relaxed text-slate-600 dark:text-slate-400">
              Trusted support options alongside TrustMind AI. If you are in
              crisis, please use immediate support services first.
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {resourceCategories.map((category) => (
              <section
                key={category.title}
                className="rounded-2xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900 p-6 shadow-sm"
              >
                <h2 className="text-lg font-semibold text-slate-800 dark:text-slate-100">
                  {category.title}
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  {category.description}
                </p>
                <ul className="mt-5 space-y-4">
                  {category.items.map((item) => (
                    <li
                      key={item.name}
                      className="rounded-xl border border-slate-100 bg-slate-50/50 p-4 dark:border-slate-700 dark:bg-slate-800/80"
                    >
                      <a
                        href={item.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-teal-700 hover:underline dark:text-teal-400"
                      >
                        {item.name}
                      </a>
                      <p className="mt-1 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
                        {item.detail}
                      </p>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}

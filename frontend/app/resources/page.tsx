import type { Metadata } from "next";
import { Footer, Header } from "@/components/Header";
import { PageBackground } from "@/components/PageBackground";

export const metadata: Metadata = {
  title: "Resources — TrustMind AI",
  description:
    "Support resources for crisis help, UWE wellbeing, NHS services, and more.",
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
    title: "UWE Wellbeing Support",
    description: "Support services for UWE Bristol students.",
    items: [
      {
        name: "UWE Wellbeing Service",
        detail: "Counselling, mental health advice, and student support.",
        href: "https://www.uwe.ac.uk/students/support",
      },
      {
        name: "UWE Out of Hours Support",
        detail: "Support options outside standard office hours.",
        href: "https://www.uwe.ac.uk/students/support",
      },
    ],
  },
  {
    title: "Wisdom App",
    description: "Digital wellbeing tools and guided support.",
    items: [
      {
        name: "Wisdom App",
        detail: "A wellbeing app with exercises, tracking, and guided content.",
        href: "https://www.wisdom.app/",
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
    title: "Academic Stress Support",
    description: "Help managing study pressure and academic wellbeing.",
    items: [
      {
        name: "UWE Study Support",
        detail: "Academic skills, exam preparation, and study wellbeing.",
        href: "https://www.uwe.ac.uk/students/support",
      },
      {
        name: "Student Minds",
        detail: "UK student mental health charity with guides and resources.",
        href: "https://www.studentminds.org.uk/",
      },
    ],
  },
  {
    title: "Financial and Housing Support",
    description: "Practical support that can affect wellbeing.",
    items: [
      {
        name: "UWE Money Advice",
        detail: "Financial guidance and hardship support for students.",
        href: "https://www.uwe.ac.uk/students/support",
      },
      {
        name: "Shelter housing advice",
        detail: "Free housing and homelessness support in the UK.",
        href: "https://www.shelter.org.uk/",
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

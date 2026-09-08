/** User-facing display labels — research/storage labels stay unchanged. */

import type { AnalyseResponse } from "@/lib/api";

const PREDICTION_DISPLAY: Record<string, string> = {
  depression: "It sounds like low mood may be weighing on you",
  anxiety: "It sounds like stress or worry has been weighing on you",
  suicidewatch: "I'm really sorry you're feeling this way — please get support now",
  bipolar: "It sounds like your mood or energy has felt up-and-down lately",
  offmychest: "It sounds like something's been sitting heavy on your mind",
};

function normaliseKey(label: string): string {
  return label.trim().toLowerCase().replace(/\s+/g, "").replace(/^self\./, "");
}

export function predictionDisplayName(
  prediction: string | null | undefined,
  userText?: string | null,
): string {
  if (isPositiveLowDistressCheckin(userText)) return POSITIVE_DISPLAY;
  if (!prediction) return "A gentle read of what you shared";
  const key = normaliseKey(prediction);
  return PREDICTION_DISPLAY[key] ?? prediction;
}

export function indicatorDisplayName(label: string): string {
  return predictionDisplayName(label);
}

const POSITIVE_PHRASES = [
  "happy",
  "happier",
  "glad",
  "grateful",
  "thankful",
  "relieved",
  "hopeful",
  "excited",
  "proud",
  "content",
  "enjoying",
  "feeling good",
  "feel good",
  "feeling great",
  "doing well",
  "good mood",
];

const DISTRESS_PHRASES = [
  "kill myself",
  "end my life",
  "want to die",
  "suicid",
  "self-harm",
  "self harm",
  "hurt myself",
  "hopeless",
  "worthless",
  "can't cope",
  "cant cope",
  "panic",
  "struggling",
];

export function isPositiveLowDistressCheckin(
  text: string | null | undefined,
): boolean {
  const raw = (text || "").trim();
  if (!raw || raw.split(/\s+/).length > 60) return false;
  const lower = raw.toLowerCase();
  if (DISTRESS_PHRASES.some((p) => lower.includes(p))) return false;
  return POSITIVE_PHRASES.some((p) => lower.includes(p));
}

const POSITIVE_DISPLAY =
  "It sounds like you're feeling in a good place right now";

/** Correct stale API outputs (90% urgent / heavy-mind) on short happy check-ins. */
export function sanitizeAnalyseForUserText(
  result: AnalyseResponse,
  userText: string,
): AnalyseResponse {
  if (!isPositiveLowDistressCheckin(userText) || result.safety_triggered) {
    return result;
  }
  return {
    ...result,
    prediction_display: POSITIVE_DISPLAY,
    concern_level: "Low",
    support_urgency: 22,
    support_urgency_band: "low",
    support_urgency_rationale:
      "Milder signals for now — keep an eye on how you feel and use support if that changes. Not a diagnosis or clinical risk score.",
    support_urgency_uncertain: false,
    safety_triggered: false,
    support_resources: [],
    evidence_used: [],
    sources_detail: [],
    sources: [],
    early_signs: [],
    potential_indicators: [],
  };
}

/** User-facing display labels — research/storage labels stay unchanged. */

const PREDICTION_DISPLAY: Record<string, string> = {
  depression: "It sounds like you may be experiencing low-mood themes",
  anxiety: "It sounds like you may be experiencing anxiety-related themes",
  suicidewatch: "It sounds like you may need urgent safety support",
  bipolar: "It sounds like you may be experiencing mood-swing themes",
  offmychest: "It sounds like you're sharing something that's been on your mind",
};

function normaliseKey(label: string): string {
  return label.trim().toLowerCase().replace(/\s+/g, "").replace(/^self\./, "");
}

export function predictionDisplayName(prediction: string | null | undefined): string {
  if (!prediction) return "A gentle read of what you shared";
  const key = normaliseKey(prediction);
  return PREDICTION_DISPLAY[key] ?? prediction;
}

export function indicatorDisplayName(label: string): string {
  return predictionDisplayName(label);
}

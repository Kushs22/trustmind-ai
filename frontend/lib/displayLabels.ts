/** User-facing display labels — research/storage labels stay unchanged. */

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

export function predictionDisplayName(prediction: string | null | undefined): string {
  if (!prediction) return "A gentle read of what you shared";
  const key = normaliseKey(prediction);
  return PREDICTION_DISPLAY[key] ?? prediction;
}

export function indicatorDisplayName(label: string): string {
  return predictionDisplayName(label);
}

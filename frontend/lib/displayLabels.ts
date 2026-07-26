/** User-facing display labels — research/storage labels stay unchanged. */

const PREDICTION_DISPLAY: Record<string, string> = {
  depression: "Depression-related indicators",
  anxiety: "Anxiety-related indicators",
  suicidewatch: "Urgent safety-related indicators",
  bipolar: "Bipolar-related indicators",
  offmychest: "General emotional expression",
};

function normaliseKey(label: string): string {
  return label.trim().toLowerCase().replace(/\s+/g, "").replace(/^self\./, "");
}

export function predictionDisplayName(prediction: string | null | undefined): string {
  if (!prediction) return "Assessment";
  const key = normaliseKey(prediction);
  return PREDICTION_DISPLAY[key] ?? prediction;
}

export function indicatorDisplayName(label: string): string {
  return predictionDisplayName(label);
}

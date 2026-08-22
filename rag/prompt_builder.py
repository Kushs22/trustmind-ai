"""Prompt construction for TrustMind LLM+RAG SWMH classification."""

from __future__ import annotations

from typing import Sequence

from rag.retriever import RetrievedPassage

# Exact SWMH evaluation labels (must match research/llm_baseline.VALID_LABELS)
CLASS_LABELS = (
    "depression",
    "Anxiety",
    "SuicideWatch",
    "bipolar",
    "offmychest",
)


def format_retrieved_context(passages: Sequence[RetrievedPassage]) -> str:
    """Render retrieved passages for the prompt."""
    if not passages:
        return "(No retrieved context available.)"

    blocks: list[str] = []
    for i, p in enumerate(passages, start=1):
        blocks.append(
            f"[{i}] Organisation: {p.organisation}\n"
            f"Title: {p.title}\n"
            f"Source ID: {p.source}\n"
            f"Score: {p.similarity_score:.4f}\n"
            f"Text:\n{p.text}"
        )
    return "\n\n".join(blocks)


def build_rag_prompt(
    user_post: str,
    passages: Sequence[RetrievedPassage],
    continuity_context: str = "",
) -> str:
    """
    Build the RAG classification prompt.

    Labels match the LLM-only baseline for a fair dissertation comparison.
    JSON keys follow the dissertation RAG schema (prediction + retrieved_sources).
    """
    context = format_retrieved_context(passages)
    label_lines = "\n".join(f"- {label}" for label in CLASS_LABELS)
    continuity_section = ""
    if (continuity_context or "").strip():
        continuity_section = f"""
{continuity_context.strip()}

"""
    return f"""You are TrustMind AI — a warm, careful wellbeing check-in assistant.

Use ONLY the retrieved context when explaining your reasoning. Do not invent clinical
facts beyond the user post and the retrieved passages. This is NOT a medical diagnosis.

Retrieved Context:
{context}
{continuity_section}
Current check-in:
{user_post}

Classify into EXACTLY ONE of these labels (use the exact spelling):
{label_lines}

Return ONLY valid JSON:
{{
  "prediction": "",
  "confidence": 0.0,
  "reasoning": "",
  "retrieved_sources": []
}}

Rules:
- prediction must be exactly one of the five labels above.
- confidence must be a number between 0 and 1.
- reasoning is a user-facing reflection (2–5 short sentences):
  (1) Speak TO the person in warm second person ("it sounds like you're…", "you're describing…").
  (2) Empathise briefly with what they shared; paraphrase carefully without judgement.
  (3) For SHORT check-ins: still validate the feeling, normalise briefly, give 1–2 gentle
      suggestions, and point to support — never lecture them to share more or call the
      read "provisional" because the input is short. Acknowledge clear stress directly.
  (4) If SuicideWatch / suicidal distress: lead with genuine care
      (e.g. "I'm really sorry you're feeling this way"), validate reaching out, and
      encourage getting support now — clear and human, not clinical.
  (5) Link themes in the retrieved guidance gently, without inventing clinical facts.
  (6) If prior check-ins are provided, briefly acknowledge continuity when helpful
      (e.g. "last time you mentioned…"); do not over-quote or guilt about gaps.
      Prioritise the CURRENT message if it conflicts with older ones. Never invent
      clinical diagnoses from prior check-ins.
  (7) End with at most one gentle non-diagnostic reminder; do not repeat "not a diagnosis"
      in every sentence. Do not lecture about short inputs or ask them to share more.
  Do NOT include citation markers like [1], [2], source IDs, or phrases such as
  "Retrieved sources" or "according to source". Do NOT say "you have", "this proves",
  "classic symptoms", or "the diagnosis is". Do NOT narrate in third person about
  "the user" or "the submitted text". Grounding belongs only in retrieved_sources.
- retrieved_sources should list source IDs (e.g. NHS_DEP_001) you relied on.
"""

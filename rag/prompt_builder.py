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


def build_rag_prompt(user_post: str, passages: Sequence[RetrievedPassage]) -> str:
    """
    Build the RAG classification prompt.

    Labels match the LLM-only baseline for a fair dissertation comparison.
    JSON keys follow the dissertation RAG schema (prediction + retrieved_sources).
    """
    context = format_retrieved_context(passages)
    label_lines = "\n".join(f"- {label}" for label in CLASS_LABELS)
    return f"""You are a mental wellbeing assessment assistant for academic research.

Use ONLY the retrieved context when explaining your reasoning. Do not invent clinical
facts beyond the user post and the retrieved passages. This is NOT a medical diagnosis.

Retrieved Context:
{context}

User Post:
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
- reasoning should briefly cite which retrieved sources informed your explanation.
- retrieved_sources should list source IDs (e.g. NHS_DEP_001) you relied on.
"""

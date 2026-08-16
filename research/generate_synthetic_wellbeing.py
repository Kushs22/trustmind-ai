#!/usr/bin/env python3
"""
Generate a fully synthetic wellbeing classification dataset with the same
schema and label set as SWMH (text, label with self.* prefix), without using
any Reddit or other scraped social-media posts.

Default size (balanced across 5 classes):
  train=1600, val=400, test=500  → total 2500
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path

LABELS = (
    "self.depression",
    "self.SuicideWatch",
    "self.Anxiety",
    "self.bipolar",
    "self.offmychest",
)

CONTEXTS = [
    "university deadlines",
    "group project work",
    "part-time work shifts",
    "flatmate tension",
    "family video calls",
    "commuting to campus",
    "quiet evenings alone",
    "weekend plans falling through",
    "library revision sessions",
    "internship applications",
    "student accommodation",
    "friendship changes",
    "money worries this month",
    "sleep schedule chaos",
    "sports club pressure",
]

TIMES = [
    "this week",
    "for the past few days",
    "since midterms started",
    "lately",
    "over the last fortnight",
    "this term",
    "especially at night",
    "after lectures",
]

OPENERS = [
    "I keep noticing that",
    "Honestly,",
    "I do not know how to explain this, but",
    "Lately I have been thinking",
    "It feels like",
    "I have been sitting with the thought that",
    "Today I realised",
    "I keep writing and deleting this, but",
]

CLOSERS = [
    "I am not looking for a diagnosis, just trying to put words to it.",
    "I wanted to write it down so it feels less stuck in my head.",
    "Sharing this anonymously because saying it out loud still feels hard.",
    "I know other people have harder weeks, but this is where I am.",
    "If anyone has been through something similar, I would appreciate hearing how you cope.",
    "I am trying to stay safe and reach out to support services if I need them.",
]

# Theme banks: fictional first-person posts for academic label prediction only.
# SuicideWatch templates stay non-graphic (no methods) and include help-seeking language.
TEMPLATES: dict[str, list[str]] = {
    "self.depression": [
        "{opener} everything around {context} feels heavy {time}. I wake up tired, "
        "lose interest in things I used to enjoy, and even simple tasks take forever. "
        "{closer}",
        "{opener} my motivation for {context} has drained away {time}. I cancel plans, "
        "stare at my notes without absorbing anything, and feel flat rather than sad. "
        "{closer}",
        "Around {context}, I have felt empty {time}. Food does not appeal, messages go "
        "unanswered, and I keep thinking nothing I do will matter. {closer}",
        "I used to care about {context}, but {time} I feel numb and slow. Getting out of "
        "bed is the hardest part of the day. {closer}",
        "{opener} I am going through the motions with {context}. People say I seem quiet; "
        "inside it is more like a grey fog that will not lift. {closer}",
        "Studying for {context} feels pointless {time}. I forget appointments, cry without "
        "a clear reason, and then feel guilty for being low. {closer}",
        "{opener} the spark is gone from {context}. I isolate myself, replay old mistakes, "
        "and struggle to believe next week will feel any better. {closer}",
        "I am not in crisis, but {time} with {context} I feel persistently down, worthless, "
        "and disconnected from friends. {closer}",
    ],
    "self.SuicideWatch": [
        "{opener} {time} thoughts about not wanting to continue keep returning when I face "
        "{context}. I feel overwhelmed and hopeless, though I am trying to stay safe and "
        "think about talking to someone. {closer}",
        "I feel exhausted by {context} and sometimes wish I could just disappear. I am not "
        "sharing a plan; I just need space to say how dark it feels {time}. {closer}",
        "{opener} hopelessness around {context} has been intense {time}. Part of me wants "
        "the pain to stop. I know support lines exist and I am considering using them. {closer}",
        "Tonight {context} hit hard. I keep thinking people would be better off without me. "
        "I want help more than I want to act on those thoughts. {closer}",
        "{opener} I feel trapped by {context} {time}. Ideation comes in waves, then fades. "
        "Writing this is my way of not keeping it secret. {closer}",
        "I am scared by how often I imagine an ending when {context} piles up. I am reaching "
        "toward support rather than making any plan. {closer}",
        "{opener} life with {context} feels unbearable {time}. I feel empty and tired of "
        "fighting. If you are reading this, I am asking for encouragement to keep going. {closer}",
        "Some days with {context} I wonder whether continuing is worth it. I am staying with "
        "a friend tonight and trying to get through the next hour. {closer}",
    ],
    "self.Anxiety": [
        "{opener} {context} triggers racing thoughts {time}. My chest tightens, I over-prepare "
        "for every worst case, and I struggle to switch off. {closer}",
        "Before {context}, I spiral into what-ifs {time}. Heart racing, sweaty hands, and a "
        "sense that something bad is about to happen even when nothing has. {closer}",
        "{opener} I cannot stop checking messages related to {context}. The worry loop runs "
        "all day and then steals my sleep. {closer}",
        "Around {context} I feel constantly on edge {time}. I avoid situations that might "
        "make me anxious, then feel frustrated for avoiding them. {closer}",
        "{opener} physical anxiety hits during {context}: shallow breathing, restless legs, "
        "and a need to escape the room. {closer}",
        "I rehearse conversations about {context} for hours {time}. If something small goes "
        "wrong, my mind treats it like a catastrophe. {closer}",
        "{opener} uncertainty around {context} makes me panic. I seek reassurance, then "
        "doubt the reassurance five minutes later. {closer}",
        "Social situations tied to {context} feel threatening {time}. I scan for judgment "
        "and leave early even when people are kind. {closer}",
    ],
    "self.bipolar": [
        "{opener} my energy around {context} swings wildly {time}. Some days I sleep little "
        "and feel unstoppable; other days I crash and can barely move. {closer}",
        "With {context}, I notice rapid shifts {time}: buzzing ideas and talking too fast, "
        "then a sudden drop into heaviness and self-doubt. {closer}",
        "{opener} mood episodes make {context} unpredictable. High periods feel exciting but "
        "risky; low periods wipe out everything I started. {closer}",
        "I have been cycling through intense highs and lows while dealing with {context}. "
        "Friends say I seem like a different person week to week. {closer}",
        "{opener} during elevated phases I take on too much around {context}, then spiral "
        "when the low arrives and deadlines remain. {closer}",
        "Sleep, appetite, and focus flip with my mood {time}. {context} becomes either a "
        "grand project or an impossible mountain. {closer}",
        "{opener} I am trying to track patterns: irritability, racing thoughts, then days of "
        "shutdown that make {context} feel unreachable. {closer}",
        "Stability is the goal, but {time} {context} collides with mood swings that change "
        "how I speak, spend, and plan. {closer}",
    ],
    "self.offmychest": [
        "{opener} I just need to get this off my chest about {context}. Nothing dramatic, "
        "just a messy week I have been holding in {time}. {closer}",
        "Nobody in my circle knows how annoyed I am about {context}. Writing it here helps "
        "me release the pressure without a big confrontation. {closer}",
        "{opener} I feel guilty admitting this, but {context} has been frustrating {time} "
        "and I am tired of pretending everything is fine. {closer}",
        "This is more of a vent than a crisis: {context} went sideways {time} and I keep "
        "replaying the awkward parts. {closer}",
        "{opener} I am overloaded by small irritations around {context}. Saying it out loud "
        "(well, in text) makes it feel lighter. {closer}",
        "I do not need advice as much as a place to unload about {context}. Today was one "
        "of those days where everything rubbed me the wrong way. {closer}",
        "{opener} pride stopped me telling friends how stressed {context} made me {time}. "
        "So I am posting anonymously instead. {closer}",
        "Just needed somewhere honest to say that {context} drained me {time}. Tomorrow I "
        "will try again; tonight I am venting. {closer}",
    ],
}

STYLES = [
    lambda t: t,
    lambda t: t.replace("I am", "I'm").replace("I have", "I've").replace("do not", "don't"),
    lambda t: t + " Anyway, that is all for now.",
    lambda t: "Quick update: " + t[0].lower() + t[1:] if t else t,
]


def _fill(template: str, rng: random.Random) -> str:
    text = template.format(
        opener=rng.choice(OPENERS),
        closer=rng.choice(CLOSERS),
        context=rng.choice(CONTEXTS),
        time=rng.choice(TIMES),
    )
    text = rng.choice(STYLES)(text)
    # Light uniqueness salt that still reads naturally
    if rng.random() < 0.35:
        text += f" (note to self: remember week {rng.randint(1, 12)})."
    return " ".join(text.split())


def _fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_rows(
    n_per_label: int,
    rng: random.Random,
    *,
    seen: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label in LABELS:
        templates = TEMPLATES[label]
        made = 0
        attempts = 0
        max_attempts = n_per_label * 80
        while made < n_per_label and attempts < max_attempts:
            attempts += 1
            text = _fill(rng.choice(templates), rng)
            fp = _fingerprint(text)
            if fp in seen:
                continue
            seen.add(fp)
            rows.append({"text": text, "label": label})
            made += 1
        if made < n_per_label:
            raise RuntimeError(f"Could not generate enough unique rows for {label}")
    rng.shuffle(rows)
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["text", "label"])
        writer.writeheader()
        writer.writerows(rows)


def label_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {label: 0 for label in LABELS}
    for row in rows:
        counts[row["label"]] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--train-per-class", type=int, default=320)
    parser.add_argument("--val-per-class", type=int, default=80)
    parser.add_argument("--test-per-class", type=int, default=100)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "datasets" / "synthetic_wellbeing",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    seen: set[str] = set()
    train = generate_rows(args.train_per_class, rng, seen=seen)
    val = generate_rows(args.val_per_class, rng, seen=seen)
    test = generate_rows(args.test_per_class, rng, seen=seen)

    out = args.out_dir
    write_csv(out / "train.csv", train)
    write_csv(out / "val.csv", val)
    write_csv(out / "test.csv", test)

    manifest = {
        "name": "TrustMind Synthetic Wellbeing (SWMH-schema)",
        "purpose": "Ethical replacement for Reddit-sourced SWMH evaluation data",
        "columns": ["text", "label"],
        "labels": list(LABELS),
        "seed": args.seed,
        "generation": "template+combinatorial; no scraped social posts",
        "splits": {
            "train": {"n": len(train), "per_class": args.train_per_class, "counts": label_counts(train)},
            "val": {"n": len(val), "per_class": args.val_per_class, "counts": label_counts(val)},
            "test": {"n": len(test), "per_class": args.test_per_class, "counts": label_counts(test)},
        },
        "total": len(train) + len(val) + len(test),
        "notes": [
            "Labels mirror SWMH class names for pipeline compatibility.",
            "Texts are fictional student/everyday wellbeing narratives.",
            "Not clinical data; not for diagnosis.",
            "SuicideWatch class uses non-graphic distress language only.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["splits"], indent=2))
    print(f"Wrote {manifest['total']} rows to {out}")


if __name__ == "__main__":
    main()

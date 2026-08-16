#!/usr/bin/env python3
"""
Generate a fully synthetic wellbeing classification dataset (SWMH-compatible schema).

Version 2 — deliberately harder / more real-world oriented than v1:
  - overlapping symptom language across classes
  - short messy informal style
  - ambiguous / borderline posts
  - fewer template “giveaway” phrases

No scraped Reddit or social-media posts. Seed-reproducible.
Default size: train=1600, val=400, test=500 → total 2500 (balanced).
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

# Shared everyday hooks (appear across classes → harder discrimination)
HOOKS = [
    "uni",
    "my course",
    "the flat",
    "my shifts",
    "home",
    "messages",
    "sleep",
    "money",
    "my mates",
    "family",
    "the library",
    "group chat",
    "deadlines",
    "commute",
    "this term",
]

FILLERS = [
    "idk",
    "tbh",
    "anyway",
    "not sure how to say this",
    "whatever",
    "i keep typing then deleting",
    "maybe its nothing",
    "feels stupid writing this",
]

STYLES = ("messy", "short", "medium", "ambiguous")


def _fp(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _maybe_messy(text: str, rng: random.Random) -> str:
    t = " ".join(text.split())
    if rng.random() < 0.55:
        t = t.replace("I am", "im").replace("I have", "ive").replace("don't", "dont")
        t = t.replace("I'm", "im").replace("I've", "ive").replace("It's", "its")
    if rng.random() < 0.35:
        t = t[0].lower() + t[1:] if t else t
    if rng.random() < 0.25:
        t = t.replace(".", "").replace(",", "")
    if rng.random() < 0.3:
        t += " " + rng.choice(["...", "lol", "idk", "yeah", ""]) 
    return " ".join(t.split()).strip()


def _gen_depression(rng: random.Random, style: str) -> str:
    h = rng.choice(HOOKS)
    f = rng.choice(FILLERS)
    bank = {
        "short": [
            f"cant get myself to care about {h} today. just blank.",
            f"everything with {h} feels muted. not sad exactly just empty.",
            f"woke up already tired of {h}. scrolling then nothing.",
        ],
        "messy": [
            f"{f} {h} is fine on paper but i cancel everything and sit there. "
            f"food is meh friends feel far. not dramatic just flat for days",
            f"people ask about {h} and i say im ok then do nothing all evening. "
            f"like moving through glue. small stuff takes forever",
        ],
        "medium": [
            f"Around {h} I have been low for a while. I still show up but interest is gone "
            f"and I replay mistakes until I shut down. Not looking for a label, just stuck.",
            f"Motivation for {h} disappeared. I sleep odd hours, leave messages unread, "
            f"and feel heavy without a clear reason.",
        ],
        "ambiguous": [
            # overlaps anxiety / offmychest
            f"stressed about {h} but also just... numb? worry comes then fades into nothing. "
            f"hard to tell if im overthinking or just done",
            f"{h} has me drained. chest feels tight some nights then i feel nothing next morning. "
            f"{f}",
        ],
    }
    return rng.choice(bank[style])


def _gen_suicidewatch(rng: random.Random, style: str) -> str:
    """Non-graphic; passive ideation / hopelessness; includes safety-oriented language often."""
    h = rng.choice(HOOKS)
    f = rng.choice(FILLERS)
    bank = {
        "short": [
            f"keep thinking {h} would be easier if i wasnt around. not planning anything. just tired of existing tonight.",
            f"wish i could disappear quietly. {h} piled up and i feel like a burden.",
        ],
        "messy": [
            f"{f} dark thoughts about not continuing keep looping when {h} hits. "
            f"im staying with someone tonight and trying to get through the next hour",
            f"part of me wants the noise to stop. no plan. just {h} and this hollow feeling. "
            f"might message a support line if it gets worse",
        ],
        "medium": [
            f"Hopelessness around {h} has been intense. I have thoughts about not wanting to continue, "
            f"then they pass. I am trying to stay safe and talk to someone.",
            f"I feel trapped by {h}. Ideation comes in waves. Writing this so it is not only in my head. "
            f"I want help more than I want to act on those thoughts.",
        ],
        "ambiguous": [
            # can look like severe depression
            f"everything with {h} feels pointless and heavy. sometimes i wonder what the point of next week is. "
            f"not saying im going to do anything. just exhausted of fighting",
            f"if i vanished would {h} even notice. that thought scares me a bit. trying not to spiral alone",
        ],
    }
    return rng.choice(bank[style])


def _gen_anxiety(rng: random.Random, style: str) -> str:
    h = rng.choice(HOOKS)
    f = rng.choice(FILLERS)
    bank = {
        "short": [
            f"heart racing before {h} again. worst case playlist on loop.",
            f"cant stop checking {h}. then checking again.",
        ],
        "messy": [
            f"{f} {h} makes my stomach drop. i rehearse conversations then avoid them. "
            f"sleep is broken cos my brain wont shut up",
            f"on edge all day about {h}. sweaty hands shallow breath then i feel silly after",
        ],
        "medium": [
            f"Uncertainty around {h} keeps me scanning for danger. I seek reassurance then doubt it "
            f"five minutes later. Physical tension will not switch off.",
            f"Before {h} I spiral into what-ifs. I leave early even when people are kind.",
        ],
        "ambiguous": [
            # overlaps depression / offmychest
            f"worried sick about {h} and also weirdly flat after the panic fades. "
            f"am i anxious or just burnt out",
            f"{h} stress sits in my chest. not crying just restless and snappy. {f}",
        ],
    }
    return rng.choice(bank[style])


def _gen_bipolar(rng: random.Random, style: str) -> str:
    h = rng.choice(HOOKS)
    f = rng.choice(FILLERS)
    bank = {
        "short": [
            f"two days buzzing about {h} barely sleeping then crash. different person vibes.",
            f"ideas for {h} come too fast then i cant move. swingy week.",
        ],
        "messy": [
            f"{f} started {h} projects at 2am felt unstoppable now i cant answer a text. "
            f"friends say i flip too quick",
            f"irritable then suddenly on a high about {h} then nothing. sleep appetite focus all over the place",
        ],
        "medium": [
            f"Energy around {h} will not stay steady. Elevated spells feel risky; the drop wipes out "
            f"what I started. Trying to track the pattern.",
            f"Talking too fast about {h} one week, shut down the next. Mood changes how I plan and spend.",
        ],
        "ambiguous": [
            # can look like anxiety or depression alone
            f"some days {h} im wired and sharp other days im useless. could be stress could be more. idk",
            f"sleep vanished then returned with a crash while dealing with {h}. mood followed it. {f}",
        ],
    }
    return rng.choice(bank[style])


def _gen_offmychest(rng: random.Random, style: str) -> str:
    h = rng.choice(HOOKS)
    f = rng.choice(FILLERS)
    bank = {
        "short": [
            f"just need to vent about {h}. annoying week nothing deep.",
            f"had to say this somewhere: {h} was messy and im annoyed.",
        ],
        "messy": [
            f"{f} not a crisis just sick of pretending {h} is fine. small stuff kept piling up "
            f"and i snapped at someone. whatever",
            f"unloading about {h}. pride stopped me telling mates. tomorrow ill try again tonight im moaning",
        ],
        "medium": [
            f"This is more of a vent than anything else: {h} went sideways and I keep replaying "
            f"the awkward parts. Advice optional.",
            f"I feel guilty admitting how frustrated {h} made me. Writing it here releases the pressure "
            f"without a big confrontation.",
        ],
        "ambiguous": [
            # deliberately confusable with mild anxiety/depression
            f"tired of {h} and a bit low about it but mostly just annoyed and overthinking conversations. "
            f"needed somewhere to dump it",
            f"{h} stressed me out and now i feel weirdly empty after venting to no one. probably fine. {f}",
        ],
    }
    return rng.choice(bank[style])


GENERATORS = {
    "self.depression": _gen_depression,
    "self.SuicideWatch": _gen_suicidewatch,
    "self.Anxiety": _gen_anxiety,
    "self.bipolar": _gen_bipolar,
    "self.offmychest": _gen_offmychest,
}

# Bias toward harder styles for more realistic error rates
STYLE_WEIGHTS = [("ambiguous", 0.35), ("messy", 0.30), ("short", 0.20), ("medium", 0.15)]


def _pick_style(rng: random.Random) -> str:
    styles, weights = zip(*STYLE_WEIGHTS)
    return rng.choices(list(styles), weights=list(weights), k=1)[0]


def generate_rows(
    n_per_label: int,
    rng: random.Random,
    *,
    seen: set[str],
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label in LABELS:
        gen = GENERATORS[label]
        made = 0
        attempts = 0
        while made < n_per_label and attempts < n_per_label * 120:
            attempts += 1
            style = _pick_style(rng)
            text = _maybe_messy(gen(rng, style), rng)
            if len(text.split()) < 8:
                continue
            fp = _fp(text)
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
        "version": "2.0",
        "purpose": "Harder ethical replacement for Reddit-sourced SWMH evaluation data",
        "design": {
            "goal": "More realistic classification difficulty via ambiguity and overlap",
            "style_mix": dict(STYLE_WEIGHTS),
            "traits": [
                "shared everyday vocabulary across classes",
                "messy informal orthography",
                "ambiguous borderline posts",
                "non-graphic SuicideWatch language with help-seeking cues",
            ],
        },
        "columns": ["text", "label"],
        "labels": list(LABELS),
        "seed": args.seed,
        "generation": "template+combinatorial v2 (hard); no scraped social posts",
        "splits": {
            "train": {"n": len(train), "per_class": args.train_per_class, "counts": label_counts(train)},
            "val": {"n": len(val), "per_class": args.val_per_class, "counts": label_counts(val)},
            "test": {"n": len(test), "per_class": args.test_per_class, "counts": label_counts(test)},
        },
        "total": len(train) + len(val) + len(test),
        "notes": [
            "Not clinical data; not for diagnosis.",
            "Absolute metrics may still differ from real social media; interpret cautiously.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"version": "2.0", "total": manifest["total"], "splits": manifest["splits"]}, indent=2))
    print(f"Wrote dataset to {out}")


if __name__ == "__main__":
    main()

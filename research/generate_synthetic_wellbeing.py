#!/usr/bin/env python3
"""
Generate a fully synthetic wellbeing classification dataset (SWMH-compatible schema).

Version 3 — real-world length + emotional breadth:
  - overlapping symptom language across classes
  - short / messy / medium / long / very_long first-person posts
  - loneliness, heartbreak, stress, mixed feelings, relief/hope, anger,
    guilt/shame, numbness, energy swings (non-diagnostic), stuckness,
    rejection/abandonment themes
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
    "the relationship",
    "my ex",
    "work",
    "the weekend",
    "my room",
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

# v3 styles include long / very_long for product-realistic check-ins
STYLES = ("messy", "short", "medium", "ambiguous", "long", "very_long")

# Theme fragments reused inside long builders (non-clinical phrasing)
LONELINESS = [
    "rooms feel louder when nobody texts back",
    "I scroll through chats and put my phone down again",
    "weekends stretch out and I pretend I planned to be alone",
    "I miss having someone who just checks in without being asked",
]
HEARTBREAK = [
    "I still flinch when their name shows up somewhere random",
    "I keep replaying the last conversation like I can edit it",
    "some days I miss the person, some days I miss who I was with them",
    "I catch myself writing messages I never send",
]
STUCK = [
    "I know what I should do next but my body will not start",
    "plans sit in notes apps untouched for weeks",
    "I feel parked between who I was and whoever comes next",
    "forward motion feels fake even when I force a routine",
]
MIXED = [
    "I can laugh at a meme and feel hollow five minutes later",
    "relief and dread take turns without asking",
    "I am grateful for small kindnesses and still tense underneath",
    "hope shows up briefly then I talk myself out of it",
]
RELIEF_HOPE = [
    "today was lighter than yesterday and that surprised me",
    "I finished something small and felt a real spark of pride",
    "talking to a friend helped more than I expected",
    "I am not fixed but I can see a thinner path forward",
]
ANGER = [
    "I snap over tiny things and then feel worse",
    "irritation sits under my skin like static",
    "I am angry that I have to carry this alone",
]
GUILT_SHAME = [
    "I keep thinking I made everything harder for people around me",
    "shame shows up when I cancel plans again",
    "I replay awkward moments until they feel larger than they were",
]
NUMBNESS = [
    "music that used to hit does nothing",
    "I go through the motions and feel buffered from myself",
    "emotions arrive late or not at all",
]
ENERGY_SWING = [
    "one stretch I barely sleep and ideas pile up too fast",
    "then a crash hits and answering a text feels huge",
    "friends notice I flip between wired and wiped",
    "appetite focus and spending change with the swings",
]


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


def _pick(rng: random.Random, bank: list[str], k: int = 1) -> list[str]:
    return rng.sample(bank, k=min(k, len(bank)))


def _expand_to_words(rng: random.Random, base: str, target_min: int, target_max: int) -> str:
    """Pad a narrative with themed sentences until within a word-count band."""
    parts = [base.strip()]
    pools = [
        LONELINESS,
        HEARTBREAK,
        STUCK,
        MIXED,
        RELIEF_HOPE,
        ANGER,
        GUILT_SHAME,
        NUMBNESS,
        ENERGY_SWING,
    ]
    connectors = [
        "Also,",
        "Meanwhile,",
        "On top of that,",
        "Lately,",
        "Some nights,",
        "In the mornings,",
        "When I try to explain it,",
        "Honestly,",
    ]
    attempts = 0
    while len(" ".join(parts).split()) < target_min and attempts < 80:
        attempts += 1
        pool = rng.choice(pools)
        bits = _pick(rng, pool, k=rng.randint(1, 2))
        parts.append(f"{rng.choice(connectors)} {' '.join(bits)}.")
    text = " ".join(parts)
    words = text.split()
    if len(words) > target_max:
        text = " ".join(words[:target_max])
    return text.strip()


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
            f"stressed about {h} but also just... numb? worry comes then fades into nothing. "
            f"hard to tell if im overthinking or just done",
            f"{h} has me drained. chest feels tight some nights then i feel nothing next morning. "
            f"{f}",
        ],
        "long": [
            f"For the last few weeks around {h} I have felt hollow more than tearful. "
            f"I get up, do the minimum, and then sit with that heavy quiet that makes "
            f"ordinary tasks feel pointless. Friends still invite me; I say maybe and then "
            f"do not go. Food tastes like cardboard some days. I am not trying to diagnose "
            f"myself — I just want language for this flatness and the way interest keeps "
            f"slipping away. Sleep is weird: either too much or broken. I keep hoping tomorrow "
            f"will feel different and it mostly does not.",
        ],
        "very_long": [
            f"I keep writing and deleting this because talking about low mood around {h} "
            f"still feels dramatic even when it has lasted months. Mornings are the worst: "
            f"I wake already tired, scroll without absorbing anything, and bargain with myself "
            f"to shower. Showers help for twenty minutes. Then the flatness returns. "
            f"I cancel plans, leave laundry in bags, and tell people I am busy when I am "
            f"actually staring at a wall. Concentration for coursework or shifts is thin; "
            f"I reread the same paragraph. There is guilt about being distant, then numbness "
            f"that makes the guilt feel far away. Some evenings I cry without a clear story; "
            f"other evenings I feel nothing and that scares me more. I am not looking for a "
            f"clinical label from an app — I want a careful read of how heavy this has been "
            f"and whether support options might help while I try to rebuild a bit of routine.",
        ],
    }
    text = rng.choice(bank[style])
    if style == "long":
        return _expand_to_words(rng, text, 150, 320)
    if style == "very_long":
        return _expand_to_words(rng, text, 350, 750)
    return text


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
            f"everything with {h} feels pointless and heavy. sometimes i wonder what the point of next week is. "
            f"not saying im going to do anything. just exhausted of fighting",
            f"if i vanished would {h} even notice. that thought scares me a bit. trying not to spiral alone",
        ],
        "long": [
            f"Tonight the hopelessness around {h} is loud. I am not making a plan and I do not want "
            f"to describe anything graphic — I just keep having thoughts about not wanting to continue, "
            f"then they ebb. I am staying somewhere safe and telling myself to get through the next hour. "
            f"Writing this is me choosing help over silence. If it worsens I will contact a support line.",
        ],
        "very_long": [
            f"I need to put this somewhere before it only lives in my head. For days around {h} I have "
            f"had waves of not wanting to be here. They are thoughts, not a plan, and that distinction "
            f"matters to me. Still, the heaviness makes ordinary life feel unreachable. I have told a "
            f"friend I am struggling and I am trying to stay with people tonight. I want support more "
            f"than I want those thoughts to win. Please treat this as distress that needs care pathways, "
            f"not as something to analyse clinically. I will reach out further if the wave gets worse.",
        ],
    }
    text = rng.choice(bank[style])
    if style == "long":
        return _expand_to_words(rng, text, 140, 300)
    if style == "very_long":
        return _expand_to_words(rng, text, 300, 650)
    return text


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
            f"worried sick about {h} and also weirdly flat after the panic fades. "
            f"am i anxious or just burnt out",
            f"{h} stress sits in my chest. not crying just restless and snappy. {f}",
        ],
        "long": [
            f"My body treats {h} like a threat even when nothing has gone wrong yet. Chest tight, "
            f"jaw locked, brain running disaster scripts. I check messages repeatedly, then feel "
            f"embarrassed about checking. Sleep is shallow because I rehearse conversations at 2am. "
            f"I cancel social things to avoid the spiral, which makes next week worse. This is not "
            f"a diagnosis request — I want a clear reflection that this is worry and bodily tension "
            f"piling up, and some gentle next steps.",
        ],
        "very_long": [
            f"Stress around {h} has stopped being a one-day spike. For weeks I wake with dread, "
            f"scan for mistakes, and catastrophise tiny delays. My heart races in lectures or on "
            f"the bus for no neat reason. I ask friends if everything is okay then distrust the answer. "
            f"Deadlines feel like cliffs. I leave early from gatherings because my hands shake. "
            f"Afterward I feel drained and a bit numb, which confuses me — is it anxiety, burnout, "
            f"or both? I am trying to track triggers: sleep debt, caffeine, unread emails. I do not "
            f"want clinical certainty from software; I want acknowledgement that this worry loop is "
            f"real and that support exists if it keeps growing.",
        ],
    }
    text = rng.choice(bank[style])
    if style == "long":
        return _expand_to_words(rng, text, 150, 320)
    if style == "very_long":
        return _expand_to_words(rng, text, 350, 750)
    return text


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
            f"some days {h} im wired and sharp other days im useless. could be stress could be more. idk",
            f"sleep vanished then returned with a crash while dealing with {h}. mood followed it. {f}",
        ],
        "long": [
            f"My energy around {h} swings hard. For a stretch I sleep little, talk fast, start too many "
            f"plans, and feel oddly invincible. Then the drop arrives and I can barely reply to a message. "
            f"Friends say I seem like different people across the week. I am not asking an app to diagnose "
            f"anything medical — I want a careful theme read about up-and-down mood and energy affecting "
            f"daily life, sleep, and spending.",
        ],
        "very_long": [
            f"I am trying to describe the pattern without claiming a clinical label. Around {h}, elevated "
            f"spells show up as racing ideas, irritability, and nights where sleep feels optional. I spend "
            f"more, promise more, and feel sharp in a way that later looks reckless. Then a crash hits: "
            f"heavy limbs, flat mood, cancelled plans, and shame about what I started. Tracking sleep and "
            f"appetite helps a bit. Stress can trigger either end. Mixed days confuse me most — restless "
            f"and low at once. Please reflect the swing pattern supportively and keep language "
            f"non-diagnostic; I already know software cannot replace a clinician.",
        ],
    }
    text = rng.choice(bank[style])
    if style == "long":
        return _expand_to_words(rng, text, 150, 320)
    if style == "very_long":
        return _expand_to_words(rng, text, 350, 750)
    return text


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
            f"tired of {h} and a bit low about it but mostly just annoyed and overthinking conversations. "
            f"needed somewhere to dump it",
            f"{h} stressed me out and now i feel weirdly empty after venting to no one. probably fine. {f}",
        ],
        "long": [
            f"Mostly I need to unload about {h}. It is not a crisis and I am not asking for a diagnosis — "
            f"just space to say I am frustrated, a bit lonely after a messy week, and weirdly relieved "
            f"after writing this down. There were arguments, awkward silences, and a stretch where I felt "
            f"happier than I have in months after a good conversation. Emotions are mixed: annoyance, "
            f"guilt, hope, then back to annoyance. Advice optional; listening preferred.",
        ],
        "very_long": [
            f"This is a long vent about {h} and the pile of ordinary human feelings that came with it. "
            f"Heartbreak from a friendship cooling off, loneliness on Sundays, stress about money, "
            f"then a surprising afternoon where I felt genuinely happy walking home. I also feel stuck "
            f"about next steps and a little ashamed that small things rattled me. Mixed feelings are "
            f"the point: anger one hour, soft hope the next. I do not want clinical language — I want "
            f"acknowledgement that dumping this out is allowed, plus gentle support options if I want "
            f"them later. Tomorrow I will try again; tonight I just needed somewhere to put the words.",
        ],
    }
    text = rng.choice(bank[style])
    if style == "long":
        return _expand_to_words(rng, text, 150, 320)
    if style == "very_long":
        return _expand_to_words(rng, text, 350, 750)
    return text


GENERATORS = {
    "self.depression": _gen_depression,
    "self.SuicideWatch": _gen_suicidewatch,
    "self.Anxiety": _gen_anxiety,
    "self.bipolar": _gen_bipolar,
    "self.offmychest": _gen_offmychest,
}

# Bias toward harder + longer styles for more realistic product coverage
STYLE_WEIGHTS = [
    ("ambiguous", 0.22),
    ("messy", 0.18),
    ("short", 0.12),
    ("medium", 0.18),
    ("long", 0.20),
    ("very_long", 0.10),
]


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
        while made < n_per_label and attempts < n_per_label * 200:
            attempts += 1
            style = _pick_style(rng)
            text = gen(rng, style)
            if style not in {"long", "very_long"}:
                text = _maybe_messy(text, rng)
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


def length_stats(rows: list[dict[str, str]]) -> dict[str, float | int]:
    words = [len(r["text"].split()) for r in rows]
    words_sorted = sorted(words)
    n = len(words_sorted)
    mid = words_sorted[n // 2] if n else 0
    return {
        "min": min(words) if words else 0,
        "median": mid,
        "mean": round(sum(words) / n, 1) if n else 0,
        "max": max(words) if words else 0,
        "pct_ge_150": round(100.0 * sum(1 for w in words if w >= 150) / n, 1) if n else 0,
    }


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
        "version": "3.0",
        "purpose": "Ethical SWMH-schema corpus with longer, broader emotional check-ins",
        "design": {
            "goal": "Cover short-to-long first-person posts including loneliness, heartbreak, "
            "stress, mixed feelings, relief/hope, anger, guilt/shame, numbness, and "
            "non-diagnostic energy swings",
            "style_mix": dict(STYLE_WEIGHTS),
            "traits": [
                "shared everyday vocabulary across classes",
                "messy informal orthography on short/medium styles",
                "ambiguous borderline posts",
                "long and very_long multi-paragraph check-ins (~150–800 words)",
                "non-graphic SuicideWatch language with help-seeking cues",
                "non-diagnostic bipolar/energy-swing wording",
            ],
        },
        "columns": ["text", "label"],
        "labels": list(LABELS),
        "seed": args.seed,
        "generation": "template+combinatorial v3 (long-form); no scraped social posts",
        "splits": {
            "train": {
                "n": len(train),
                "per_class": args.train_per_class,
                "counts": label_counts(train),
                "length": length_stats(train),
            },
            "val": {
                "n": len(val),
                "per_class": args.val_per_class,
                "counts": label_counts(val),
                "length": length_stats(val),
            },
            "test": {
                "n": len(test),
                "per_class": args.test_per_class,
                "counts": label_counts(test),
                "length": length_stats(test),
            },
        },
        "total": len(train) + len(val) + len(test),
        "notes": [
            "Not clinical data; not for diagnosis.",
            "Live TrustMind product uses LLM classification; this corpus supports eval/RAG research.",
            "Absolute metrics may still differ from real social media; interpret cautiously.",
        ],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "version": "3.0",
                "total": manifest["total"],
                "splits": {
                    k: {"n": v["n"], "length": v["length"]}
                    for k, v in manifest["splits"].items()
                },
            },
            indent=2,
        )
    )
    print(f"Wrote dataset to {out}")


if __name__ == "__main__":
    main()

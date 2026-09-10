# Synthetic Wellbeing Dataset (SWMH-compatible schema)

**Version 3.1** — four theme classes (bipolar bank folded into depression / Anxiety).  
Ethical replacement for Reddit-sourced SWMH. No scraped social media.

## Files

| File | Rows | Per class |
|------|------|-----------|
| `train.csv` | 1,600 | 400 |
| `val.csv` | 400 | 100 |
| `test.csv` | 500 | 125 |
| **Total** | **2,500** | balanced (4 classes) |

Also: `manifest.json`, `DATASET_CARD.md`, `processed/*_clean.csv`.

## Schema

| Column | Description |
|--------|-------------|
| `text` | Synthetic first-person wellbeing post |
| `label` | `self.depression`, `self.SuicideWatch`, `self.Anxiety`, `self.offmychest` |

v3.1 drops `self.bipolar`. Energy-down / crash fragments sit under `self.depression`; racing / worry / restlessness fragments sit under `self.Anxiety`. Ambiguous swing templates were split ~50/50 under seed 42. SuicideWatch and offmychest are unchanged.

## v3.1 design (length + emotion)

- Styles: messy / short / medium / ambiguous / **long** / **very_long** (~150–800 word targets)
- Themes: loneliness, heartbreak, stress, mixed feelings, relief/hope, anger, guilt/shame, numbness, energy-down and racing/restlessness language (non-diagnostic), stuckness, rejection
- Shared everyday vocabulary across classes; ambiguous borderline posts
- About **31–39%** of posts are ≥150 words depending on split (product-realistic long check-ins)
- Live TrustMind product still classifies primarily via **LLM**; this corpus supports eval / research

## Regenerate

```bash
python research/generate_synthetic_wellbeing.py --seed 42
```

## Ethics

- No human subjects; fictional text only  
- Labels are author-defined themes, not diagnoses  
- Not for clinical use

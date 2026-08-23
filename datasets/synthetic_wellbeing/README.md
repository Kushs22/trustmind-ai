# Synthetic Wellbeing Dataset (SWMH-compatible schema)

**Version 3.0** — real-world length + emotional breadth (long / very_long styles, broader themes).  
Ethical replacement for Reddit-sourced SWMH. No scraped social media.

## Files

| File | Rows | Per class |
|------|------|-----------|
| `train.csv` | 1,600 | 320 |
| `val.csv` | 400 | 80 |
| `test.csv` | 500 | 100 |
| **Total** | **2,500** | balanced |

Also: `manifest.json`, `DATASET_CARD.md`, `processed/*_clean.csv`.

## Schema

| Column | Description |
|--------|-------------|
| `text` | Synthetic first-person wellbeing post |
| `label` | `self.depression`, `self.SuicideWatch`, `self.Anxiety`, `self.bipolar`, `self.offmychest` |

## v3 design (length + emotion)

- Styles: messy / short / medium / ambiguous / **long** / **very_long** (~150–800 word targets)
- Themes: loneliness, heartbreak, stress, mixed feelings, relief/hope, anger, guilt/shame, numbness, non-diagnostic energy swings, stuckness, rejection
- Shared everyday vocabulary across classes; ambiguous borderline posts
- About **33%+** of posts are ≥150 words (product-realistic long check-ins)
- Live TrustMind product still classifies primarily via **LLM**; this corpus supports eval / research

## Regenerate

```bash
python research/generate_synthetic_wellbeing.py --seed 42
```

## Ethics

- No human subjects; fictional text only  
- Labels are author-defined themes, not diagnoses  
- Not for clinical use

# Synthetic Wellbeing Dataset (SWMH-compatible schema)

Ethical **replacement** for Reddit-sourced SWMH evaluation data. All posts are
**fictional**, generated locally with templates (no scraped social media).

## Files

| File | Rows | Per class |
|------|------|-----------|
| `train.csv` | 1,600 | 320 |
| `val.csv` | 400 | 80 |
| `test.csv` | 500 | 100 |
| **Total** | **2,500** | balanced |

Also: `manifest.json` (seed, counts, provenance) and **`DATASET_CARD.md`** (full dataset description for the report / supervisor).

## Schema (same as SWMH)

| Column | Description |
|--------|-------------|
| `text` | Synthetic first-person wellbeing post |
| `label` | One of `self.depression`, `self.SuicideWatch`, `self.Anxiety`, `self.bipolar`, `self.offmychest` |

## Regenerate

```bash
python research/generate_synthetic_wellbeing.py
# optional size overrides:
python research/generate_synthetic_wellbeing.py --train-per-class 320 --val-per-class 80 --test-per-class 100 --seed 42
```

## Ethics notes

- No human subjects; no Reddit / social scrape.
- Labels are **author-defined themes** for academic classification, not diagnoses.
- `SuicideWatch` texts are non-graphic and include help-seeking language.
- Product crisis support remains rule-based and separate from this dataset.

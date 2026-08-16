# Synthetic Wellbeing Dataset (SWMH-compatible schema)

**Version 2.0** — harder, more real-world-oriented synthetic posts (ambiguity + overlap).  
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

## v2 design (why scores should look more realistic)

- Shared everyday vocabulary across classes  
- Messy informal style (short / incomplete)  
- Ambiguous borderline posts (e.g. anxiety ↔ depression ↔ venting)  
- Fewer obvious “giveaway” template phrases than v1  

## Regenerate

```bash
python research/generate_synthetic_wellbeing.py --seed 42
```

## Ethics

- No human subjects; fictional text only  
- Labels are author-defined themes, not diagnoses  
- `SuicideWatch` texts are non-graphic and often include help-seeking language  

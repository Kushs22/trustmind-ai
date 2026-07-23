# SWMH Dataset

Place the following files in this directory (not committed to Git — see `.gitignore`):

- `train.csv`
- `val.csv`
- `test.csv`

**Source location (local):**
```
/Users/kushsharma/Desktop/AI Group /
```

**Expected columns:** `text`, `label`

**Classes:** `self.depression`, `self.SuicideWatch`, `self.Anxiety`, `self.offmychest`, `self.bipolar`

## Notebooks

| Notebook | Purpose |
|----------|---------|
| `research/01_SWMH_EDA.ipynb` | Exploratory data analysis |
| `research/02_SWMH_Preprocessing.ipynb` | Cleaning + write processed CSVs |

## Processed data

After running preprocessing:

```bash
cd research
python preprocessing.py
# or open 02_SWMH_Preprocessing.ipynb
```

Outputs (also gitignored):

- `processed/train_clean.csv`
- `processed/val_clean.csv`
- `processed/test_clean.csv`

Columns: `text`, `label`, `word_count`, `truncated`

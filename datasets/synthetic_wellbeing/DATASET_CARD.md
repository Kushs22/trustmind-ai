# TrustMind Synthetic Wellbeing Dataset — Full Description

**Version:** 1.0  
**Created for:** TrustMind AI (UWE MSc AI group project)  
**Purpose:** Ethical evaluation corpus with the same schema as SWMH, without using Reddit or any scraped social-media posts  
**Location:** `datasets/synthetic_wellbeing/`  
**Generator:** `research/generate_synthetic_wellbeing.py`  
**Seed:** 42 (fully reproducible)

---

## 1. Why this dataset exists

The original SWMH dataset (Ji et al., 2021) contains real Reddit posts from mental-health-related communities. Our supervisor advised **not** to use it for evaluation because those posts were collected **without individual research consent**.

This synthetic dataset is TrustMind’s replacement:

| Requirement | How this dataset meets it |
|-------------|---------------------------|
| No real people / no Reddit scrape | All texts are fictional, generated from templates |
| Keep TrustMind pipelines unchanged | Same CSV columns and same 5 label names as SWMH |
| Support LLM vs LLM+RAG ablation | Fixed train / val / test splits; test set large enough for n=100 sampling |
| Dissertation transparency | Documented method, seed, counts, limitations |

**Important:** SWMH may still be cited historically (“originally motivated by Ji et al.”). It is **not** used as evaluation data in the ethical workflow.

---

## 2. What the dataset is (and is not)

### It is

- A **labelled text classification** corpus for academic experiments
- First-person fictional posts in an everyday / student-life voice
- Organised into five **theme classes** that mirror SWMH label names
- Suitable for offline evaluation of LLM-only vs LLM+RAG pipelines

### It is not

- Clinical data or medical records
- A diagnostic instrument
- Real user messages from TrustMind
- A copy or paraphrase of SWMH Reddit posts
- Ground truth for real-world mental-health status

Labels mean: “this synthetic post was written to reflect theme X for classification experiments.”  
They do **not** mean: “this person has diagnosis X.”

---

## 3. Files included

| File | Description |
|------|-------------|
| `train.csv` | Training split (1,600 rows) |
| `val.csv` | Validation split (400 rows) |
| `test.csv` | Held-out test split (500 rows) — used for LLM vs RAG eval |
| `manifest.json` | Machine-readable provenance (seed, counts, notes) |
| `README.md` | Short folder overview |
| `DATASET_CARD.md` | This full description (use in report / supervisor pack) |

Each CSV has exactly two columns:

```text
text,label
```

Example row:

```csv
"I keep noticing that everything around university deadlines feels heavy this week. I wake up tired, lose interest in things I used to enjoy, and even simple tasks take forever. I am not looking for a diagnosis, just trying to put words to it.",self.depression
```

---

## 4. Size and splits

**Total samples: 2,500**

| Split | Rows | Share | Per class | Role |
|-------|------|-------|-----------|------|
| Train | 1,600 | 64% | 320 × 5 | Optional fine-tuning / prompt design / analysis |
| Val | 400 | 16% | 80 × 5 | Tuning thresholds / sanity checks |
| Test | 500 | 20% | 100 × 5 | Final LLM vs LLM+RAG evaluation |

Split ratios follow the familiar **64 / 16 / 20** style used by SWMH, but at a smaller, reviewable scale.

### Why 2,500 (not ~54,000 like SWMH)?

1. Ethics: fully synthetic and group-authored / group-reviewed is feasible at this size.  
2. Evaluation design: TrustMind’s main ablation already samples **n=100, seed=42** from the test set.  
3. Balance: every class has equal support (no majority-class bias from Reddit traffic).  
4. Practicality: regenerable, inspectable, and safe to commit to the repo.

---

## 5. Label set (SWMH-compatible)

Labels keep the `self.*` prefix so existing normalisers (`self.depression` → `depression`, etc.) work without code changes.

| CSV label | Canonical short label (after normalisation) | Theme meaning in this synthetic set |
|-----------|-----------------------------------------------|-------------------------------------|
| `self.depression` | `depression` | Persistent low mood, emptiness, loss of interest, fatigue |
| `self.SuicideWatch` | `SuicideWatch` | Hopelessness / passive ideation themes; **non-graphic**; help-seeking language included |
| `self.Anxiety` | `Anxiety` | Worry loops, physical tension, avoidance, catastrophising |
| `self.bipolar` | `bipolar` | Mood/energy swings (highs and lows) affecting daily functioning |
| `self.offmychest` | `offmychest` | General venting / unload; not primarily one of the above themes |

### Class balance

Every split is **perfectly balanced** (equal rows per class).  
That differs from real SWMH (where depression was largest). Balanced design makes macro-F1 easier to interpret for the RQ ablation.

---

## 6. How texts were generated

Method: **template + combinatorial generation** (local Python; seed 42).

1. For each class, several theme templates encode the intended linguistic pattern.  
2. Slots are filled from banks of:
   - openers (“Lately I have been thinking…”)
   - everyday contexts (deadlines, flatmates, commuting, money worries, etc.)
   - time phrases (“this week”, “since midterms started”, …)
   - closers (non-diagnostic framing / anonymous sharing language)
3. Light style variants (contractions, short prefixes/suffixes) increase diversity.  
4. Duplicate texts are rejected via hashing so each row is unique across the whole dataset.  
5. Rows are shuffled within each split.

**Provenance guarantee:** no Reddit API, no Hugging Face SWMH download, no copied social posts.

Regenerate identically:

```bash
python research/generate_synthetic_wellbeing.py --seed 42 \
  --train-per-class 320 --val-per-class 80 --test-per-class 100
```

---

## 7. Text length profile (approx.)

Across splits, posts are short-to-medium first-person paragraphs:

| Split | Min words | Median | Mean | Max words |
|-------|-----------|--------|------|-----------|
| Train | ~30 | ~44 | ~45 | ~66 |
| Val | ~32 | ~45 | ~45 | ~65 |
| Test | ~30 | ~45 | ~45 | ~68 |

This is shorter and more uniform than raw Reddit SWMH (which has very long / noisy posts). That is expected for synthetic template data and should be stated as a limitation.

---

## 8. How TrustMind uses this dataset

| Component | Uses this dataset? |
|-----------|--------------------|
| Live product UI / RAG knowledge base | **No** — KB remains curated NHS/Mind-style sources |
| Offline LLM-only baseline | **Yes** — sample from `test.csv` |
| Offline LLM+RAG arm | **Yes** — same sample / seed for fair comparison |
| Crisis detection rules | **Independent** — not trained on this CSV |

Default eval path:

```text
datasets/synthetic_wellbeing/test.csv
```

Override if needed:

```bash
export EVAL_TEST_CSV=/absolute/path/to/test.csv
```

Recommended fair ablation settings (unchanged protocol):

- Model: GPT-4.1  
- Temperature: 0.0  
- Sample size: 100  
- Seed: 42  
- Metrics: accuracy + macro precision / recall / F1  

---

## 9. Ethics and safety notes

1. **No human subjects** — fictional texts only.  
2. **Consent issue resolved** — nothing scraped from Reddit users.  
3. **Non-diagnostic** — outputs remain “indicator / theme classification” language in the product.  
4. **SuicideWatch class** — distress themes without graphic methods; templates encourage help-seeking wording.  
5. **Crisis support in the app** stays rule-based and separate from dataset labels.  
6. **Limitation for the dissertation:** results generalise to this synthetic distribution, not to real clinical populations or Reddit.

Suggested report wording:

> Evaluation used a group-prepared synthetic wellbeing corpus (2,500 posts; SWMH-compatible five-class schema) because Reddit-sourced SWMH lacks individual research consent. Architecture, retrieval, and metrics were held constant; only the evaluation texts were replaced.

---

## 10. Comparison with original SWMH (for clarity)

| Aspect | SWMH (legacy) | TrustMind synthetic |
|--------|---------------|---------------------|
| Source | Reddit communities | Local templates |
| Consent | Problematic for our ethics bar | Acceptable (no subjects) |
| Size | ~54k | 2,500 |
| Columns | `text`, `label` | `text`, `label` (same) |
| Labels | 5 `self.*` classes | Same 5 names |
| Balance | Imbalanced | Balanced |
| Use in TrustMind now | Do not use | Default eval corpus |

---

## 11. Quick start for the group

1. Open CSVs in Excel / Numbers / pandas from `datasets/synthetic_wellbeing/`.  
2. For dissertation tables, cite counts from Section 4 and `manifest.json`.  
3. Run experiments against `test.csv` (or the n=100 seed-42 sample).  
4. Do **not** mix SWMH Reddit rows back into evaluation.  
5. If the supervisor wants a larger set, regenerate with higher `--train-per-class` / `--test-per-class` and document the new counts.

---

## 12. Citation-style reference (internal)

```text
TrustMind AI Group (2026). Synthetic Wellbeing Dataset (SWMH-compatible schema),
version 1.0. Generated with research/generate_synthetic_wellbeing.py (seed=42).
Total N=2500 (train=1600, val=400, test=500), 5 balanced theme classes.
```

Historical motivation (not the data source):

```text
Ji, S., et al. (2021). Suicidal ideation and mental disorder detection with
reciprocal perspective with social media. Neural Computing and Applications.
Dataset hub (not used here): https://huggingface.co/datasets/AIMH/SWMH
```

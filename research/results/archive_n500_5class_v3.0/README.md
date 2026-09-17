# Archived 5-class n=500 dual-arm (Synthetic Wellbeing v3.0)

These artefacts used the **five-class** schema including `bipolar`
(100 rows per class on test.csv). They are **not valid** for Synthetic
Wellbeing v3.1 (4-class: depression, SuicideWatch, Anxiety, offmychest;
125 per class). Headline numbers here were Acc 0.860 vs 0.832.

Do not restore these as current results. Re-run
`research/run_rag_vs_llm_via_local_api.py --sample-size 500 --seed 42`
on the current `datasets/synthetic_wellbeing/test.csv`.

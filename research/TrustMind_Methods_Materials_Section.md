> **GenAI note (module policy).** This file is a *draft* Methods and Materials (§3) for the group to own, edit, and finalise before Blackboard submission. Generative AI must not author the submitted report; the group is responsible for verifying every claim, citation, and number against the codebase, dataset card, and primary sources, and for rewriting in its own voice where required.

# 3 Methods and Materials

## 3.1 Methodological Approach

Following the clear, phased presentation style used in recent LLM--MeHE surveys (for example Ghorbian and Ghobaei-Arani [9]), this section explains TrustMind as a structured methodological pipeline rather than as an informal product narrative. The primary objective is to measure---under matched controls---to what extent RAG improves trustworthiness, reliability, and explainability of LLM wellbeing assessments versus a standalone LLM, while shipping a non-diagnostic student check-in over allow-listed public guidance.

The work proceeds in five phases (Fig. 1): (1) problem and research-question design; (2) dual-pipeline system architecture; (3) allow-listed knowledge-base construction and indexing; (4) seed-reproducible synthetic evaluation data; (5) fair dual-arm evaluation with an explicit trust layer. Three artefacts result: a live product, a curated BM25(/FAISS) knowledge base, and n=500 reliability metrics.

**[[FIG:fig1_method_overview.png]]**

**Fig. 1.** TrustMind methodological approach: five phases from research-question design to dual-arm evaluation, producing the live product, curated KB, and reliability artefacts.

### 3.1.1 Defining Research Inquiries

Table 2 states the inquiries that organise the method (mirroring survey-style TQ tables [9], adapted to an empirical dual-arm product study).

**Table 2.** Research inquiries guiding the TrustMind method.

| ID | Inquiry | How this section addresses it |
|----|---------|-------------------------------|
| TQ1 | What system design compares LLM-only vs LLM+RAG fairly? | Dual pipeline, same labels/model family, controlled retrieval mode (Sections 3.2--3.3, 3.6) |
| TQ2 | How is ethically evaluable data formed without Reddit scrapes? | Synthetic Wellbeing v3.0 generator (Section 3.4, Fig. 2) |
| TQ3 | Why BM25, FAISS, and RRF---and when is each used? | Literature-linked justification + decision flow (Section 3.5, Fig. 3) |
| TQ4 | How are trustworthiness and explainability operationalised beyond accuracy? | Calibration, grounding, abstention, source cards, crisis rules (Sections 3.2, 3.5) |

## 3.2 Problem Formulation and System Architecture

TrustMind maps a confirmed user check-in---plain text, optionally derived from speech, image, or PDF after user confirmation---to one of five non-diagnostic theme indicators: depression, SuicideWatch, Anxiety, bipolar, and offmychest. Labels are theme proxies compatible with the SWMH schema [1]; they are not diagnoses.

**Architecture (Phase 2).** Frontend: Next.js (Vercel). Backend: FastAPI (Render) + PostgreSQL. The browser never holds provider keys. POST /api/v1/analyse accepts pipeline_mode in {llm, rag, auto}. Live generation uses multi-provider routing (Groq → Gemini → OpenAI); the offline reliability table fixes gpt-4.1. Multimodal files are converted to text, confirmed by the user, and never written into BM25 or FAISS. Mode A (llm_pipeline.py) uses a classification prompt only. Mode B (rag_pipeline_service.py) always retrieves BM25 passages and may optionally fuse FAISS via RRF [2] (Section 3.5). A trust layer then applies calibration, grounding, abstention, and independent crisis routing before the UI shows reflections and grounded sources (RAG only).

## 3.3 Knowledge Base Construction

**Phase 3** builds an allow-listed KB only (approved_sources.csv, 110+ rows): NHS-style guidance, charity and student resources, UWE wellbeing pages, crisis charity pages, and selected peer-reviewed PDFs---no open-web crawl. Sources are cleaned to Markdown and chunked into 500-word windows with 100-word overlap. Indexes: BM25 (primary) and optional FAISS. The production checkout has on the order of 90 cleaned documents and 836 chunks. This implements the Section 2 gap on public guidance rather than DSM/ICD-style corpora [3].

**Table 3.** Knowledge-base construction stages.

| Stage | Artefact / tool | Design choice |
|-------|-----------------|---------------|
| Allow-list | approved_sources.csv | Manual curation; no crawl |
| Acquire / clean | Collector and HTML/PDF cleaner | Rate-limited fetch or local PDF |
| Chunk / index | 500/100 word windows; BM25; optional FAISS | BM25 primary in production |

## 3.4 Synthetic Dataset Formation (Technology)

**Phase 4** answers TQ2. After supervisor advice against Reddit SWMH (no individual research consent), evaluation uses TrustMind Synthetic Wellbeing v3.0 (N=2500; splits 1600/400/500; seed 42). Fig. 2 shows how texts are formed with software---not scraped and not copied from SWMH posts.

**[[FIG:fig2_synthetic_data.png]]**

**Fig. 2.** Synthetic Wellbeing v3.0 formation: seed-reproducible Python generator combines label banks, shared student-life hooks, and a length/style mixer into balanced train/val/test CSVs.

**Step-by-step formation technology** (research/generate_synthetic_wellbeing.py):

1. Label banks --- five SWMH-compatible self.* theme fragment libraries (depression, SuicideWatch, Anxiety, bipolar, offmychest).
2. Shared hooks --- everyday student cues (university, sleep, money, mates, deadlines) appear across classes so models cannot rely on a single keyword.
3. Style mixer --- ambiguous (~22%), messy (~18%), short (~12%), medium (~18%), long (~20%), very_long (~10%) to cover sparse posts through ~150--800-word narratives.
4. Combinatorial assembly --- templates + random composition under seed 42; long builders add loneliness, heartbreak, stress, mixed feelings, hope, anger, guilt, numbness, non-diagnostic energy swings; SuicideWatch stays non-graphic with help-seeking language.
5. Export --- balanced CSVs; eval preprocessing scrubbs URLs/@handles (max 512 words). The live product is not trained on this set---it is for offline dual-arm inference only.

This fills the ethics gap highlighted in surveys and dual-arm MH RAG work that rely heavily on social-media corpora [1,3,9].

## 3.5 Retrieval Techniques: BM25, FAISS, and RRF

**Phase 3/5 retrieval design** answers TQ3. Section 2 showed RAG can improve provenance [4] yet add noise or hurt accuracy in some settings [3,6,7], while healthcare RAG reviews warn about poorly matched retrieval [8]. TrustMind therefore decomposes ``RAG'' into three technologies with an explicit when-to-use rule (Fig. 3).

**[[FIG:fig3_retrieval_decision.png]]**

**Fig. 3.** Retrieval decision flow: BM25 always runs on the RAG arm; FAISS and RRF run only when embeddings succeed; otherwise the system soft-falls back to BM25-only so grounded sources remain available.

### 3.5.1 Why These Techniques (Gaps vs Prior Approaches)

- BM25 (always on RAG). Fills the gap left by standalone LLMs (fluent but unauditable) and by dense-only stacks that fail without embedding APIs. Lexical overlap matches student phrasing to NHS/charity headings; stays inside the allow-list (unlike free-web search); avoids diagnostic DSM/ICD KBs [3].
- FAISS + embeddings (optional). Fills the sparse-only gap: paraphrases (drained/empty vs low mood) need semantic neighbours [8]. Uses text-embedding-3-small and FAISS IndexFlatIP when available.
- RRF (optional, with FAISS) [2]. Fills the fusion gap: BM25 and dense scores are incomparable; RRF (k=60) merges ranks without a trained re-ranker and reduces one-channel domination---a noise pattern noted when vanilla RAG hurts performance [3,6,7].

**Table 4.** Technique selection linked to literature gaps.

| Decision | Chosen | Gap in prior / alternative tech | How TrustMind fills it |
|----------|--------|----------------------------------|------------------------|
| Grounding | Allow-listed RAG | Free-web; DSM/ICD RAG [3] | Provenance [4] over public guidance |
| Sparse | BM25 always | Dense-only / LLM-only | Grounded sources without embeddings |
| Dense | FAISS optional | Sparse misses paraphrases [8] | Semantic recall when API healthy |
| Fusion | RRF when both lists exist | Naive score merge noise [2,8] | Rank fusion, top-k truncate |
| Data | Synthetic v3.0 | Reddit consent issues [1,3,9] | Seed-42 template synthesis |
| Trust | Calibrate / abstain / ground | Overconfident raw scores [5] | Explicit trust UX |

### 3.5.2 When FAISS and RRF Are Used (and How They Help)

BM25 runs on every LLM+RAG request (and on the n=500 reliability arm). FAISS+RRF are optional enrichments:

- BM25-only (default live path today): embeddings missing, rate-limited, or failed → still return allow-listed passages (retrieval_mode often bm25_only).
- Hybrid: FAISS index present + OpenAI embedding call succeeds → FAISS top-20 + BM25 top-20 → RRF → product top-k=5. FAISS helps paraphrase recall; RRF helps balanced fusion. Soft fallback never drops grounding solely because dense retrieval failed.

## 3.6 Experimental Protocol

**Phase 5** answers TQ1 for reliability. Fig. 4 and Table 5 state the fair dual-arm controls (rq_answer_summary.md).

**[[FIG:fig4_dual_arm.png]]**

**Fig. 4.** Fair dual-arm protocol: identical held-out posts and model; Arm A has no passages; Arm B adds BM25 top-3 curated passages; metrics are accuracy and macro-P/R/F1.

**Table 5.** Fair dual-arm experimental controls.

| Control | Value |
|---------|--------|
| Test set | Synthetic wellbeing test.csv, n=500, seed 42 |
| Model | gpt-4.1 via local TrustMind API proxy |
| LLM arm | Same five-class prompt; no passages |
| RAG arm | Same prompt + BM25 top-3 curated passages |
| Metrics | Accuracy; macro-P/R/F1 (invalid predictions = errors) |

Product retrieval (BM25 always; optional FAISS+RRF; top-k=5) is not identical to the reported reliability configuration (BM25 top-3); both are stated honestly in Results.

## 3.7 Delivery

Short supervisor-aligned iterations delivered the dual pipeline and trust UI, then synthetic data and offline ablation, then deployment hardening. Assessable artefacts match Fig. 1: live system, committed KB indexes, and reproducible eval scripts.

## References

1. Ji, S., Li, X., Huang, Z., Cambria, E.: Suicidal Ideation and Mental Disorder Detection with Attentive Relation Networks. Neural Computing and Applications (2021)
2. Cormack, G.V., Clarke, C.L.A., Buettcher, S.: Reciprocal Rank Fusion Outperforms Condorcet and Individual Rank Learning Methods. In: SIGIR 2009, pp. 758--759 (2009)
3. Ge, Z., Hu, N., Wang, Y., et al.: Survey and Experiments on Mental Disorder Detection via Social Media: From Large Language Models and RAG to Agents. arXiv:2504.02800 (2025)
4. Lewis, P., et al.: Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. In: NeurIPS (2020)
5. Guo, C., Pleiss, G., Sun, Y., Weinberger, K.Q.: On Calibration of Modern Neural Networks. In: ICML (2017)
6. Xu, S., Yan, Z., Dai, C., Wu, F.: MEGA-RAG... Frontiers in Public Health 13, 1635381 (2025)
7. Zhang, X., et al.: SpeechT-RAG... Findings of ACL 2025, pp. 10019--10030 (2025)
8. Neha, F., Bhati, D., Shukla, D.K.: Retrieval-Augmented Generation (RAG) in Healthcare: a Comprehensive Review. AI 6(9), 226 (2025)
9. Ghorbian, M., Ghobaei-Arani, M.: Large Language Models for Mental Health Diagnosis and Treatment: a Survey. Artificial Intelligence Review 59, 9 (2026). https://doi.org/10.1007/s10462-025-11418-0

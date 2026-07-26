"""Generate TrustMind supervisor briefing PDF."""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent / "TrustMind_Supervisor_Briefing_Notes.pdf"


def clean(s: str) -> str:
    return (
        s.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "-")
        .replace("\u00a0", " ")
    )


class PDF(FPDF):
    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(
            0,
            8,
            clean("TrustMind AI - Supervisor Briefing Notes | MSc AI, UWE Bristol"),
            align="L",
        )
        self.ln(4)
        self.set_draw_color(200, 200, 200)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(6)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def main() -> None:
    pdf = PDF(format="A4")
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    width = pdf.epw

    def h2(text: str) -> None:
        pdf.ln(3)
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(20, 100, 110)
        pdf.multi_cell(width, 7, clean(text))
        pdf.ln(1)

    def body(text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(width, 5.5, clean(text))
        pdf.ln(1.5)

    def bullet(text: str) -> None:
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(width, 5.5, clean(f"  - {text}"))

    def quote(text: str) -> None:
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(50, 70, 80)
        pdf.set_fill_color(240, 248, 248)
        pdf.multi_cell(width, 6, clean(text), fill=True)
        pdf.ln(2)

    # Title
    pdf.set_fill_color(15, 90, 95)
    y0 = pdf.get_y()
    pdf.rect(pdf.l_margin, y0, width, 28, style="F")
    pdf.set_xy(pdf.l_margin, y0 + 5)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(width, 10, "TrustMind AI", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(
        width,
        8,
        clean("Supervisor Briefing Notes | MSc Artificial Intelligence | UWE Bristol"),
        align="C",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.set_y(y0 + 32)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 90, 90)
    pdf.multi_cell(
        width,
        5,
        clean(
            "Speakable project notes for supervisor meetings - "
            "From project start to current status"
        ),
    )
    pdf.ln(3)

    h2("1. Opening - what the project is")
    body(
        "TrustMind AI is an MSc Artificial Intelligence dissertation project "
        "at UWE Bristol."
    )
    body(
        "I am building a text-based wellbeing check-in system that can assess "
        "early signs of distress from free text, with a strong focus on trust, "
        "reliability, and explainability - not diagnosis or therapy."
    )
    body(
        "The live demo is at https://trustmind-ai.vercel.app, with the API "
        "hosted on Render."
    )

    h2("2. Research question")
    body("My research question is:")
    quote(
        "To what extent does Retrieval-Augmented Generation (RAG) improve the "
        "trustworthiness, reliability, and explainability of LLM-generated "
        "wellbeing assessments compared with a standalone LLM?"
    )
    body(
        "In plain terms: if I take the same language model, does adding "
        "retrieval from trusted wellbeing sources make the outputs more "
        "reliable, more trustworthy, and easier to explain - versus the model "
        "answering from its own knowledge alone?"
    )

    h2("3. Why this problem matters")
    body(
        "Standalone LLMs can sound confident but hallucinate or invent advice. "
        "In mental wellbeing, that is especially risky."
    )
    body(
        "Commercial chatbots and analytics tools exist, but many are closed "
        "black boxes, or are not set up for a fair LLM versus LLM+RAG "
        "comparison with transparent methods."
    )
    body(
        "The gap I am filling is an academic, controlled comparison of RAG for "
        "wellbeing assessment, using curated trusted sources, with a working "
        "demo to show it in practice."
    )

    h2("4. Project journey - from the very start")
    body(
        "Stage 1 - Dataset and EDA. I started with the SWMH dataset: Reddit "
        "posts labelled for depression, anxiety, SuicideWatch, bipolar, and "
        "offmychest. I ran exploratory analysis and preprocessing so the "
        "evaluation data was clean and consistent."
    )
    body(
        "Stage 2 - LLM-only baseline. I built a standalone GPT-4.1 classifier "
        "with a fixed prompt and structured JSON output (label, confidence, "
        "reasoning), with no retrieval. I evaluated on 100 test posts, seed "
        "42, temperature 0. Result so far: about 65% accuracy, macro-F1 "
        "around 0.65. That is my baseline."
    )
    body(
        "Stage 3 - Knowledge base. Separately from SWMH, I built a curated "
        "knowledge base of trusted guidance - NHS, Student Minds, Samaritans, "
        "YoungMinds, UWE, and similar. Sources are manually approved URLs, "
        "not an open web crawl. Roughly 100+ approved URLs and about 85 "
        "cleaned documents."
    )
    body(
        "Stage 4 - RAG pipeline. I chunked those documents, embedded them, "
        "and built hybrid retrieval: BM25 plus FAISS, fused with reciprocal "
        "rank fusion, top-5 passages into GPT-4.1. The model returns "
        "prediction, confidence, natural-language reasoning, and source IDs."
    )
    body(
        "Stage 5 - Product demo. I shipped a full stack: Next.js frontend, "
        "FastAPI backend, with privacy controls, abstention if confidence is "
        "low, ethics disclaimers, and support links. Users can toggle LLM "
        "versus LLM+RAG on the same page for demos."
    )
    body(
        "Stage 6 - Still to finish for the thesis numbers. I still need to "
        "run the full RAG evaluation on the same 100 samples and produce the "
        "side-by-side comparison notebook. The demo works; the formal RAG "
        "metrics file is the remaining experimental step."
    )

    pdf.add_page()
    h2("5. What technology we are using - and why")

    body("A. Evaluation data - SWMH")
    bullet("What: labelled Reddit wellbeing-related posts.")
    bullet(
        "Why: public research benchmark with clear classes for measuring "
        "reliability (accuracy / F1)."
    )
    bullet(
        "Versus alternatives: clinical interviews or private counselling "
        "data are not available at scale for a student project; SWMH lets me "
        "measure classification performance reproducibly."
    )
    pdf.ln(1)

    body("B. Knowledge collection - requests + BeautifulSoup + manual allow-list")
    bullet(
        "What: download only pre-approved pages; extract main text; store "
        "Markdown plus an audit CSV."
    )
    bullet("Why: ethical control, reproducibility, trusted organisations only.")
    bullet(
        "Versus Scrapy / open crawling: noisier, ethically riskier, harder "
        "to defend."
    )
    bullet(
        "Versus browser automation everywhere: unnecessary for mostly static "
        "guidance pages."
    )
    bullet(
        "Versus commercial content APIs: less transparent provenance for a "
        "dissertation."
    )
    pdf.ln(1)

    body("C. Embeddings - OpenAI text-embedding-3-small")
    bullet(
        "Why: good quality, cheap, simple, same vendor as the generator."
    )
    bullet(
        "Versus local models (BGE, E5): viable but add setup or GPU "
        "complexity for limited thesis benefit."
    )
    pdf.ln(1)

    body("D. Retrieval - hybrid BM25 + FAISS + RRF")
    bullet(
        "Why: wellbeing text needs both keyword matching (for example crisis "
        'terms) and semantic matching (paraphrases such as "worried about '
        'exams"). Hybrid covers both.'
    )
    bullet("Versus BM25 only: misses paraphrases.")
    bullet("Versus vectors only: can miss exact important terms.")
    bullet(
        "Versus Pinecone / Weaviate / cloud RAG: less reproducible offline, "
        "extra cost, less control for an MSc."
    )
    bullet(
        "Versus GraphRAG / multi-agent RAG: overkill for a curated guidance "
        "knowledge base."
    )
    pdf.ln(1)

    body("E. Generator - GPT-4.1 (same in both arms)")
    bullet(
        "Why: strong instruction following and structured JSON; keeping the "
        "model fixed means any gain is from RAG, not from switching to a "
        "bigger model."
    )
    bullet(
        "Versus Claude, Gemini, or Llama: they could work, but switching "
        "models would confound the research question."
    )
    bullet(
        "Versus fine-tuning a classifier: that would be a different research "
        "question."
    )
    pdf.ln(1)

    body("F. Application - Next.js + FastAPI + Vercel + Render")
    bullet(
        "Why: clear separation - the frontend never calls OpenAI; the "
        "backend owns the pipeline, keys, abstention, and logging."
    )
    bullet(
        "Versus no-code chatbot builders: faster to ship but opaque for "
        "academic evaluation and harder to instrument for LLM versus RAG."
    )

    h2("6. How this compares to what is in the market")
    body(
        "Consumer wellbeing chatbots optimise for engagement and support "
        "chat, but are often closed and hard to measure for RAG lift."
    )
    body(
        "Enterprise analytics RAG platforms optimise for business data Q&A - "
        "a different domain from wellbeing classification."
    )
    body(
        "Pure fine-tuned classifiers can optimise label accuracy, but are "
        "weaker on explainability and trusted grounding."
    )
    body(
        "Generic ChatGPT with no corpus is convenient, but has no controlled "
        "retrieval and a weak audit trail."
    )
    body(
        "Our approach optimises for a fair LLM versus RAG comparison plus a "
        "transparent demo: curated sources, measurable metrics, and clear "
        "methods. We are not claiming to beat every commercial product. We "
        "are claiming a clear, defensible academic contribution: quantify "
        "what RAG adds for trustworthy wellbeing assessment."
    )

    h2('7. How we measure "better"')
    body("We do not judge from one website click. We use:")
    bullet(
        "Reliability - accuracy, macro-F1, confusion matrix on the same 100 "
        "SWMH posts."
    )
    bullet(
        "Trustworthiness - grounded in approved sources; abstain when unsure; "
        "safety framing."
    )
    bullet(
        "Explainability - natural reasoning for users, plus explicit "
        "retrieved source IDs for transparency."
    )
    body(
        "The website toggle shows the difference live; the notebooks give "
        "the dissertation evidence."
    )

    h2("8. Current status (honest)")
    bullet("LLM baseline: done (n=100, about 65% accuracy).")
    bullet("Knowledge base and hybrid RAG pipeline: built and live.")
    bullet("Demo site with LLM / LLM+RAG toggle: working.")
    bullet("Full RAG evaluation versus baseline metrics: next step.")
    bullet(
        "Evaluation is on 100 samples by design (cost and reproducibility), "
        "not the full test set of roughly 11,000 posts."
    )

    h2("9. Closing line")
    quote(
        "TrustMind AI is a controlled study of whether hybrid RAG over a "
        "curated trusted wellbeing corpus improves reliability, "
        "trustworthiness, and explainability versus the same GPT-4.1 model "
        "alone - with a live student-facing demo to show the system in "
        "practice, and SWMH metrics to answer the research question "
        "rigorously."
    )

    pdf.ln(4)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(110, 110, 110)
    pdf.multi_cell(
        width,
        4,
        clean(
            "Demo: https://trustmind-ai.vercel.app  |  "
            "API: https://trustmind-ai.onrender.com/health  |  "
            "Repo: github.com/Kushs22/trustmind-ai"
        ),
    )

    pdf.output(str(OUT))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate LNCS-style Methods and Materials PDF with survey-style figures.

Phased structure inspired by Ghorbian & Ghobaei-Arani (Artif. Intell. Rev. 2026).
Figures live in research/figures/methods/.
"""

from __future__ import annotations

import re
from pathlib import Path

from fpdf import FPDF
from PIL import Image as PILImage

HERE = Path(__file__).resolve().parent
MD = HERE / "TrustMind_Methods_Materials_Section.md"
OUT = HERE / "TrustMind_Methods_Materials_Section.pdf"
FIG_DIR = HERE / "figures" / "methods"
DESKTOP = Path.home() / "Desktop" / "TrustMind_Methods_Materials_Section.pdf"
REPO_COPY = HERE.parent / "TrustMind_Methods_Materials_Section.pdf"


def clean(s: str) -> str:
    repl = {
        "\u2014": "--",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u00a0": " ",
        "\u2192": "->",
        "---": "--",
        "·": "-",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return s


def strip_md(s: str) -> str:
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
    s = re.sub(r"\*([^*]+)\*", r"\1", s)
    return s.strip()


def parse_table(block: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for raw in block.splitlines():
        s = raw.strip()
        if not s.startswith("|"):
            continue
        if re.match(r"^\|[\s\-:|]+\|$", s):
            continue
        cells = [strip_md(c.strip()) for c in s.strip("|").split("|")]
        if cells:
            rows.append(cells)
    return rows


class PDF(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4", unit="mm")
        self.set_margins(44, 18, 44)
        self.set_auto_page_break(auto=True, margin=16)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Times", "I", 8)
        self.set_text_color(120, 120, 120)
        self.cell(0, 8, f"{self.page_no()}", align="C")
        self.set_text_color(0, 0, 0)

    def title_block(self) -> None:
        self.set_font("Times", "B", 14)
        self.multi_cell(
            self.epw,
            6.5,
            clean(
                "Methods and Materials: Phased Dual LLM/RAG Design, "
                "Synthetic Data Formation, and Hybrid Retrieval"
            ),
            align="C",
        )
        self.ln(2)
        self.set_font("Times", "I", 9)
        self.multi_cell(
            self.epw,
            4.5,
            clean(
                "TrustMind AI -- LNCS-style draft (UFCEM1-60-M | UWE Bristol)\n"
                "Presentation style adapted from survey-style phased methodology "
                "(Ghorbian and Ghobaei-Arani, 2026)"
            ),
            align="C",
        )
        self.ln(3)

    def h1(self, text: str) -> None:
        self.ln(2)
        self.set_font("Times", "B", 12)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 6, clean(text))
        self.ln(1)

    def h2(self, text: str) -> None:
        self.ln(1.5)
        self.set_font("Times", "B", 10)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 5, clean(text))
        self.ln(0.8)

    def h3_inline(self, text: str) -> None:
        self.ln(1)
        self.set_font("Times", "B", 10)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 4.6, clean(text))
        self.ln(0.5)

    def p(self, text: str) -> None:
        self.set_font("Times", "", 10)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 4.8, clean(strip_md(text)), align="J")
        self.ln(1.1)

    def caption(self, text: str) -> None:
        self.set_font("Times", "", 9)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 4.2, clean(strip_md(text)), align="C")
        self.ln(1.2)

    def note(self, text: str) -> None:
        self.set_font("Times", "I", 8)
        self.set_text_color(80, 80, 80)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 3.8, clean(strip_md(text)), align="J")
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def ref(self, text: str) -> None:
        self.set_font("Times", "", 9)
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 4.2, clean(text), align="J")
        self.ln(0.6)

    def embed_figure(self, image_path: Path, max_h_mm: float = 70) -> None:
        if not image_path.is_file():
            self.note(f"[Missing figure: {image_path.name}]")
            return
        self.ln(1)
        with PILImage.open(image_path) as im:
            w_px, h_px = im.size
        aspect = h_px / max(w_px, 1)
        w_mm = self.epw
        h_mm = min(max_h_mm, w_mm * aspect)
        if self.get_y() + h_mm + 16 > self.page_break_trigger:
            self.add_page()
        self.image(str(image_path), x=self.l_margin, w=w_mm, h=h_mm)
        self.ln(1.5)

    def table_blocks(self, rows: list[list[str]], skip_header: bool = True) -> None:
        start = 1 if skip_header and rows else 0
        headers = rows[0] if rows else []
        for row in rows[start:]:
            if self.get_y() > self.page_break_trigger - 28:
                self.add_page()
            self.set_font("Times", "B", 8.5)
            self.set_x(self.l_margin)
            self.multi_cell(self.epw, 3.8, clean(row[0] if row else ""))
            self.set_font("Times", "", 8.5)
            for i, cell in enumerate(row[1:], start=1):
                label = headers[i] if i < len(headers) else f"Col{i}"
                self.set_x(self.l_margin)
                self.multi_cell(self.epw, 3.6, clean(f"  {label}: {cell}"))
            self.ln(1.0)

    def simple_two_col_table(self, rows: list[list[str]]) -> None:
        col_w = [38, self.epw - 38]
        for i, row in enumerate(rows):
            if self.get_y() > self.page_break_trigger - 16:
                self.add_page()
            self.set_font("Times", "B" if i == 0 else "", 8.5)
            x0, y0 = self.l_margin, self.get_y()
            h1 = self._cell_height(col_w[0], 3.6, row[0] if row else "")
            h2 = self._cell_height(col_w[1], 3.6, row[1] if len(row) > 1 else "")
            h = max(h1, h2, 4.0)
            self.rect(x0, y0, col_w[0], h)
            self.rect(x0 + col_w[0], y0, col_w[1], h)
            self.set_xy(x0 + 1, y0 + 0.5)
            self.multi_cell(col_w[0] - 2, 3.5, clean(row[0] if row else ""))
            self.set_xy(x0 + col_w[0] + 1, y0 + 0.5)
            self.multi_cell(col_w[1] - 2, 3.5, clean(row[1] if len(row) > 1 else ""))
            self.set_y(y0 + h)

    def _cell_height(self, w: float, line_h: float, text: str) -> float:
        self.set_font("Times", "", 8.5)
        words = clean(text).split()
        if not words:
            return line_h
        lines, cur = 1, ""
        for tok in words:
            trial = (cur + " " + tok).strip()
            if self.get_string_width(trial) <= w - 2:
                cur = trial
            else:
                lines += 1
                cur = tok
        return max(line_h, lines * line_h + 1.0)


def _emit_paras(pdf: PDF, text: str) -> None:
    for para in [p.strip() for p in text.split("\n\n") if p.strip()]:
        if para.startswith("|") or para.startswith("**Table") or para.startswith("**Fig"):
            continue
        if "[[FIG:" in para:
            continue
        if para.startswith("§§§") and para.endswith("§§§"):
            pdf.h3_inline(para.strip("§"))
        elif para.startswith("- ") or para.startswith("1. "):
            # keep lists as paragraphs (simple)
            pdf.p(para)
        else:
            pdf.p(para)


def build() -> Path:
    md = MD.read_text(encoding="utf-8")
    note = md.split("\n", 1)[0].lstrip("> ").strip() if md.startswith(">") else ""
    body = md[md.index("# 3 Methods and Materials") : md.index("## References")]
    refs_block = md[md.index("## References") + len("## References") :].strip()

    pdf = PDF()
    pdf.add_page()
    pdf.title_block()
    if note:
        pdf.note(note)
    pdf.h1("3 Methods and Materials")

    parts = re.split(r"\n## ", body)[1:]  # skip empty opening under H1
    for part in parts:
        lines = part.strip().split("\n", 1)
        heading = lines[0].strip()
        content = lines[1] if len(lines) > 1 else ""
        pdf.h2(heading)

        content = re.sub(
            r"^### (.+)$",
            lambda m: f"\n\n§§§{m.group(1).strip()}§§§\n\n",
            content,
            flags=re.M,
        )

        # Tokenise into figure / table / prose blocks
        tokens = re.split(
            r"\n(?=\*\*\[\[FIG:|\[\[FIG:|\*\*Table |\*\*Fig\. )",
            content.strip(),
        )
        for tok in tokens:
            tok = tok.strip()
            if not tok:
                continue

            if "[[FIG:" in tok[:40]:
                m = re.search(r"\[\[FIG:([^\]]+)\]\]", tok)
                fname = m.group(1).strip() if m else ""
                pdf.embed_figure(FIG_DIR / fname)
                cap = re.search(r"\*\*(Fig\. \d+\..*?)\*\*", tok)
                if cap:
                    pdf.caption(cap.group(1))
                else:
                    # caption may be next token; handled separately
                    pass
                rest = re.sub(r"^(?:\*\*)?\[\[FIG:[^\]]+\]\](?:\*\*)?", "", tok).strip()
                rest = re.sub(r"^\*\*Fig\. \d+\..*?\*\*", "", rest).strip()
                if rest:
                    _emit_paras(pdf, rest)
                continue

            if tok.startswith("**Fig."):
                pdf.caption(tok.split("\n", 1)[0])
                rest = tok.split("\n", 1)[1] if "\n" in tok else ""
                if rest.strip():
                    _emit_paras(pdf, rest)
                continue

            if tok.startswith("**Table"):
                first, _, rest = tok.partition("\n")
                pdf.caption(first)
                table_lines, after, in_table = [], [], True
                for raw in rest.split("\n"):
                    s = raw.strip()
                    if in_table:
                        if s.startswith("|") or re.match(r"^\|?[\s\-:|]+\|?$", s):
                            table_lines.append(s)
                            continue
                        if not s:
                            continue
                        in_table = False
                        after.append(raw)
                    else:
                        after.append(raw)
                rows = parse_table("\n".join(table_lines))
                if rows and len(rows[0]) <= 2:
                    pdf.simple_two_col_table(rows)
                else:
                    pdf.table_blocks(rows, skip_header=True)
                pdf.ln(1)
                if after:
                    _emit_paras(pdf, "\n".join(after))
                continue

            _emit_paras(pdf, tok)

    pdf.add_page()
    pdf.h1("References")
    pdf.note(
        "Section-local numbering. Merge into the full-paper bibliography when "
        "pasting into the Springer LNCS Word template. Method presentation "
        "adapted from the phased approach in Ghorbian and Ghobaei-Arani [9]."
    )
    for line in refs_block.split("\n"):
        line = line.strip()
        if re.match(r"^\d+\.", line):
            pdf.ref(line)
    pdf.ln(3)
    pdf.note(
        "Figures also saved under research/figures/methods/ for Word/LNCS insertion. "
        "Group must rewrite in its own voice per module GenAI policy."
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(OUT))
    for dest in (DESKTOP, REPO_COPY):
        try:
            dest.write_bytes(OUT.read_bytes())
        except OSError:
            pass
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"Wrote {path}")
    print(f"Figures: {sorted(p.name for p in FIG_DIR.glob('*.png'))}")

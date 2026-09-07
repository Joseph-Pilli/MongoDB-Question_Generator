"""Convert project markdown docs to PDF using fpdf2."""

import re
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent


class DocPDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")


def _sanitize(text: str) -> str:
    replacements = {
        "\u2014": "-",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "-",
        "\u2192": "->",
        "\u2190": "<-",
        "\u2264": "<=",
        "\u2265": ">=",
        "\u0101": "a",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def render_markdown(pdf: DocPDF, md_text: str) -> None:
    pdf.set_auto_page_break(auto=True, margin=18)
    in_code = False
    code_lines: list[str] = []

    for raw_line in md_text.splitlines():
        line = raw_line.rstrip()
        line = _sanitize(line)

        if line.strip().startswith("```"):
            if in_code:
                pdf.set_font("Courier", "", 9)
                pdf.set_fill_color(245, 245, 245)
                block = "\n".join(code_lines)
                pdf.multi_cell(0, 5, block, fill=True)
                pdf.ln(2)
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            pdf.ln(3)
            continue

        if line.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(20, 60, 100)
            pdf.multi_cell(0, 9, line[2:].strip())
            pdf.ln(2)
            continue

        if line.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(30, 80, 120)
            pdf.multi_cell(0, 8, line[3:].strip())
            pdf.ln(1)
            continue

        if line.startswith("### "):
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 7, line[4:].strip())
            pdf.ln(1)
            continue

        if line.startswith("|") and "|" in line[1:]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(30, 30, 30)
            cells = [c.strip() for c in line.strip("|").split("|")]
            row = "  |  ".join(cells)
            if re.match(r"^[-| :]+$", row.replace("  |  ", "")):
                continue
            pdf.multi_cell(0, 5, row)
            continue

        if line.startswith("- [ ]") or line.startswith("- [x]"):
            mark = "[x]" if "[x]" in line[:6] else "[ ]"
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, f"{mark} {line[5:].strip()}")
            continue

        if line.startswith("- ") or line.startswith("* "):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, f"- {line[2:].strip()}")
            continue

        if re.match(r"^\d+\.\s", line):
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 6, line)
            continue

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(30, 30, 30)
        pdf.multi_cell(0, 6, line)

    pdf.set_text_color(0, 0, 0)


def convert(md_path: Path, pdf_path: Path) -> None:
    text = md_path.read_text(encoding="utf-8")
    pdf = DocPDF()
    pdf.set_margins(18, 18, 18)
    pdf.add_page()
    render_markdown(pdf, text)
    pdf.output(str(pdf_path))


def main() -> None:
    pairs = [
        (ROOT / "DOCUMENTATION.md", ROOT / "DOCUMENTATION.pdf"),
        (ROOT / "EVAL_SETS.md", ROOT / "EVAL_SETS.pdf"),
    ]
    for md, pdf in pairs:
        if not md.exists():
            print(f"Missing: {md}")
            sys.exit(1)
        convert(md, pdf)
        print(f"Created: {pdf}")


if __name__ == "__main__":
    main()

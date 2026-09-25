"""
AUTOMATION 4 — IEEE LaTeX RESEARCH PAPER

Converts the Markdown research paper into IEEE conference format LaTeX.
Generates BibTeX references.
Compiles to PDF (or provides files for Overleaf upload).

Usage:  Imported by pipeline.py (receives paper_md string)

LLMs used:
  - Claude Sonnet → LaTeX conversion + BibTeX generation
    (most reliable LaTeX output, fewer compilation errors than GPT)
"""

import subprocess
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from core.claude import claude

console = Console()


# ══════════════════════════════════════════════════════════
# LaTeX CONVERSION PROMPT
# ══════════════════════════════════════════════════════════

LATEX_PROMPT = r"""Convert this research paper from Markdown to IEEE conference format LaTeX.

REQUIREMENTS:
- \documentclass[conference]{IEEEtran}
- Use these packages ONLY:
  \usepackage{cite}
  \usepackage{amsmath,amssymb}
  \usepackage{graphicx}
  \usepackage{url}
  \usepackage{hyperref}
  \usepackage{booktabs}
  \usepackage[utf8]{inputenc}

- Convert all inline [N] citations to \cite{refN}
- Convert Markdown headers to \section{}, \subsection{}
- Convert Markdown tables to LaTeX tabular with booktabs
- Convert bullet lists to \begin{itemize}...\end{itemize}
- Convert numbered lists to \begin{enumerate}...\end{enumerate}
- Escape special LaTeX characters: & % $ # _ { } ~ ^
- Use \textbf{} for bold, \textit{} for italic

- Author block:
  \author{
    \IEEEauthorblockN{Rakshan Kotian}
    \IEEEauthorblockA{Independent Research\\
    Email: rakshankotian1017@gmail.com}
  }

- Include \begin{abstract}...\end{abstract}
- End with:
  \bibliographystyle{IEEEtran}
  \bibliography{refs}
  \end{document}

- NO \usepackage that requires special installation
- NO custom commands or environments
- The paper must compile with standard pdflatex + bibtex

Return ONLY the complete .tex file content. No explanation, no markdown fences."""


# ══════════════════════════════════════════════════════════
# BibTeX GENERATION PROMPT
# ══════════════════════════════════════════════════════════

BIBTEX_PROMPT = r"""Extract every \cite{refN} from this LaTeX paper and generate
a complete, valid BibTeX file.

RULES:
- Every \cite{refN} in the paper MUST have a corresponding @entry in the .bib
- Use the correct entry type:
  @article    — journal papers
  @misc       — websites, news articles, government docs, tweets
  @inproceedings — conference papers
  @techreport — think tank / policy reports
  @book       — books

For web sources (most of these will be):
@misc{refN,
  author = {Publisher Name OR Author Name},
  title = {{Article Title}},
  howpublished = {\url{https://exact-url-here}},
  year = {2026},
  note = {Accessed: 2026-09-25}
}

For government / institutional sources:
@misc{refN,
  author = {{Ministry of External Affairs, India}},
  title = {{Official Statement on...}},
  howpublished = {\url{https://mea.gov.in/...}},
  year = {2026},
  note = {Official Government Source. Accessed: 2026-09-25}
}

For think tank reports:
@techreport{refN,
  author = {Author Name},
  title = {{Report Title}},
  institution = {Brookings Institution},
  year = {2026},
  url = {https://brookings.edu/...}
}

CRITICAL:
- Double-brace titles: title = {{Like This}} to preserve capitalization
- Escape special characters in URLs
- Every refN used in the .tex MUST exist in the .bib — missing entries = compilation failure
- Do NOT include entries not cited in the paper

Return ONLY valid BibTeX content. No explanation, no markdown fences."""


# ══════════════════════════════════════════════════════════
# PDF COMPILATION
# ══════════════════════════════════════════════════════════

def compile_pdf(output_dir: Path) -> bool:
    """
    Compile LaTeX to PDF using pdflatex + bibtex.
    Requires texlive installed.
    Returns True if PDF was generated.
    """
    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "paper.tex"],
        ["bibtex", "paper"],
        ["pdflatex", "-interaction=nonstopmode", "paper.tex"],
        ["pdflatex", "-interaction=nonstopmode", "paper.tex"],
    ]

    for i, cmd in enumerate(commands):
        step_names = ["First pass", "BibTeX", "Second pass", "Final pass"]
        console.print(f"    {step_names[i]}...")
        try:
            result = subprocess.run(
                cmd,
                cwd=output_dir,
                capture_output=True,
                timeout=60,
                text=True,
            )
            # BibTeX warnings are ok, only fail on pdflatex errors
            if result.returncode != 0 and cmd[0] == "pdflatex":
                # Check if PDF was still generated (sometimes returncode=1 but PDF exists)
                if not (output_dir / "paper.pdf").exists():
                    console.print(f"    [yellow]⚠ {step_names[i]} had errors[/]")
                    # Show last few lines of log
                    log = output_dir / "paper.log"
                    if log.exists():
                        log_text = log.read_text(encoding="utf-8", errors="ignore")
                        # Find error lines
                        errors = [l for l in log_text.split("\n") if l.startswith("!")]
                        if errors:
                            for e in errors[:5]:
                                console.print(f"      [red]{e}[/]")
        except FileNotFoundError:
            return False
        except subprocess.TimeoutExpired:
            console.print(f"    [yellow]⚠ {step_names[i]} timed out[/]")

    return (output_dir / "paper.pdf").exists()


# ══════════════════════════════════════════════════════════
# CLEANUP
# ══════════════════════════════════════════════════════════

def cleanup_latex_artifacts(output_dir: Path):
    """Remove intermediate LaTeX files, keep .tex .bib .pdf"""
    extensions_to_remove = [
        ".aux", ".bbl", ".blg", ".log", ".out",
        ".fls", ".fdb_latexmk", ".synctex.gz",
    ]
    for ext in extensions_to_remove:
        for f in output_dir.glob(f"*{ext}"):
            f.unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def build_ieee_paper(paper_md: str, output_dir: Path) -> dict:
    console.print(f"\n[bold purple]━━━ IEEE LaTeX PAPER GENERATION ━━━[/]\n")

    output_dir.mkdir(parents=True, exist_ok=True)

    # ── 1. Generate LaTeX ──
    console.print("  📝 Converting to IEEE LaTeX format...")
    try:
        latex = claude(
            system=LATEX_PROMPT,
            user=paper_md,
        )
    except Exception as e:
        console.print(f"  [red]⚠ LaTeX generation failed: {e}[/]")
        return {"error": str(e)}

    # Clean output
    latex = latex.strip()
    if latex.startswith("```"):
        lines = latex.split("\n")
        latex = "\n".join(lines[1:-1]).strip()

    # Validate it looks like LaTeX
    if "\\documentclass" not in latex:
        console.print("  [red]⚠ Generated content doesn't look like LaTeX. Retrying...[/]")
        try:
            latex = claude(
                system=LATEX_PROMPT + "\n\nIMPORTANT: Return ONLY raw LaTeX starting with \\documentclass. No markdown fences.",
                user=paper_md,
            )
            latex = latex.strip()
            if latex.startswith("```"):
                latex = "\n".join(latex.split("\n")[1:-1]).strip()
        except Exception:
            pass

    # ── 2. Generate BibTeX ──
    console.print("  📚 Generating BibTeX references...")
    try:
        bibtex = claude(
            system=BIBTEX_PROMPT,
            user=latex,
        )
    except Exception as e:
        console.print(f"  [red]⚠ BibTeX generation failed: {e}[/]")
        bibtex = "% BibTeX generation failed\n"

    # Clean output
    bibtex = bibtex.strip()
    if bibtex.startswith("```"):
        bibtex = "\n".join(bibtex.split("\n")[1:-1]).strip()

    # ── 3. Write files ──
    tex_path = output_dir / "paper.tex"
    bib_path = output_dir / "refs.bib"
    tex_path.write_text(latex, encoding="utf-8")
    bib_path.write_text(bibtex, encoding="utf-8")
    console.print(f"  💾 {tex_path}")
    console.print(f"  💾 {bib_path}")

    # ── 4. Compile PDF ──
    console.print("\n  🔨 Compiling PDF...")
    pdf_success = False
    try:
        pdf_success = compile_pdf(output_dir)
    except Exception as e:
        console.print(f"  [yellow]⚠ Compilation error: {e}[/]")

    if pdf_success:
        console.print(f"  [bold green]✅ PDF compiled: {output_dir / 'paper.pdf'}[/]")
        cleanup_latex_artifacts(output_dir)
    else:
        # Check if pdflatex is even installed
        try:
            subprocess.run(["pdflatex", "--version"], capture_output=True, timeout=5)
            console.print("  [yellow]⚠ PDF compilation failed — check paper.log for errors[/]")
            console.print("  [dim]   The .tex and .bib files are still valid — upload to Overleaf[/]")
        except FileNotFoundError:
            console.print("  [yellow]⚠ pdflatex not installed[/]")
            console.print("  [dim]   Install: sudo apt install texlive-full (Linux)[/]")
            console.print("  [dim]            brew install --cask mactex (Mac)[/]")
            console.print("  [dim]   Or upload paper.tex + refs.bib to Overleaf[/]")

    # ── Count references ──
    ref_count = bibtex.count("@")
    cite_count = latex.count("\\cite{")

    console.print(f"\n  📊 Paper: {cite_count} citations, {ref_count} references")
    console.print()

    return {
        "tex": str(tex_path),
        "bib": str(bib_path),
        "pdf": str(output_dir / "paper.pdf") if pdf_success else None,
        "citations": cite_count,
        "references": ref_count,
        "pdf_compiled": pdf_success,
    }

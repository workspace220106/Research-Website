"""
GEORESEARCH PIPELINE — MASTER RUNNER

One command. Four automations. Free-tier LLMs. Full research pipeline.

Usage:
    python pipeline.py "India-China LAC standoff September 2026"
    python pipeline.py "BRICS summit 2026 outcomes"
    python pipeline.py "NATO expansion implications 2026"

What it does:
    1. Twitter Intelligence  → Tavily + OpenRouter (Nemotron 70B)
    2. Deep Web Research     → Gemini (grounded, 7 req) + Tavily (7 req) + OpenRouter
    3. Merge + Audit + Build → OpenRouter (Nemotron 70B) + NVIDIA NIM (Llama 3.3)
    4. IEEE LaTeX Paper      → OpenRouter (Nemotron 70B) + pdflatex

Output folder: output/{date}_{topic}/
    ├── twitter_intel.json    — Twitter claims + fact-check
    ├── deep_research.json    — Web research + sources
    ├── audit.md              — Cross-reference audit report
    ├── paper_draft.md        — Research paper (Markdown)
    ├── script.md             — YouTube script
    ├── paper.tex             — IEEE LaTeX paper
    ├── refs.bib              — BibTeX references
    └── paper.pdf             — Compiled PDF (if texlive installed)

Cost: Free (OpenRouter free + Tavily 1K/mo + NVIDIA NIM free + Groq free)
Time: ~3-5 minutes
"""

import sys
import os
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
import json
import shutil
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

load_dotenv()

from auto1_twitter import twitter_intel
from auto2_deepweb import deep_web_research
from auto3_merge_audit import merge_and_build
from auto4_latex import build_ieee_paper

console = Console()


def validate_env():
    """Check all API keys are present before running."""
    required = {
        "GOOGLE_API_KEY": "aistudio.google.com/apikey",
        "OPENROUTER_API_KEY": "openrouter.ai/keys",
        "TAVILY_API_KEY": "app.tavily.com",
    }
    optional_script = ("NVIDIA_API_KEY", "GROQ_API_KEY")
    has_script_key = any(os.getenv(k) for k in optional_script)

    missing = []
    for key, url in required.items():
        if not os.getenv(key):
            missing.append((key, url))

    if missing:
        console.print("\n[bold red]Missing API keys:[/]\n")
        for key, url in missing:
            console.print(f"  x {key}")
            console.print(f"    Get it from: [blue]{url}[/]\n")
        console.print("Add them to your .env file and retry.\n")
        sys.exit(1)

    if not has_script_key:
        console.print("[yellow]! No NVIDIA_API_KEY or GROQ_API_KEY -- YouTube script step will fail.[/]")
        console.print("  Get a free NVIDIA key from: [blue]build.nvidia.com[/]\n")


def run_pipeline(topic: str):
    """Run the full 4-automation pipeline."""

    start_time = datetime.now()

    # ── Header ──
    console.print()
    console.print(Panel(
        f"[bold white]{topic}[/]",
        title="[bold red]GeoResearch Pipeline",
        subtitle="[dim]4 automations - 4 LLMs - 1 query",
        border_style="red",
        padding=(1, 2),
    ))
    console.print()

    # ── Validate ──
    validate_env()

    # ── Create output directory ──
    slug = topic.lower()
    # Clean slug: keep only alphanumeric and hyphens
    slug = "".join(c if c.isalnum() or c == " " else "" for c in slug)
    slug = slug.strip().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out_dir = Path("output") / f"{date}_{slug}"
    out_dir.mkdir(parents=True, exist_ok=True)

    console.print(f"  Output: {out_dir}/\n")

    # ══════════════════════════════════════════
    # AUTOMATION 1 — Twitter Intelligence
    # ══════════════════════════════════════════
    try:
        twitter = twitter_intel(topic)
    except Exception as e:
        console.print(f"[red]! Twitter Intelligence failed: {e}[/]")
        console.print("[dim]  Continuing with empty Twitter data...[/]\n")
        twitter = {"topic": topic, "source": "twitter", "claims": [], "summary": {}, "speaker_breakdown": {}, "raw_citations": [], "needs_verification": []}

    (out_dir / "twitter_intel.json").write_text(
        json.dumps(twitter, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ══════════════════════════════════════════
    # AUTOMATION 2 — Deep Web Research
    # ══════════════════════════════════════════
    try:
        research = deep_web_research(topic)
    except Exception as e:
        console.print(f"[red]! Deep Web Research failed: {e}[/]")
        console.print("[dim]  Continuing with empty research data...[/]\n")
        research = {"topic": topic, "source": "deep_web", "claims": [], "synthesis": {}, "all_sources": [], "summary": {}, "raw_citations": []}

    (out_dir / "deep_research.json").write_text(
        json.dumps(research, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ══════════════════════════════════════════
    # AUTOMATION 3 — Merge + Audit + Build
    # ══════════════════════════════════════════
    try:
        outputs = merge_and_build(twitter, research)
    except Exception as e:
        console.print(f"[red]! Merge/Build failed: {e}[/]")
        outputs = {
            "audit": f"# Audit Failed\nError: {e}",
            "paper": f"# Paper Failed\nError: {e}",
            "script": f"# Script Failed\nError: {e}",
        }

    (out_dir / "audit.md").write_text(outputs["audit"], encoding="utf-8")
    (out_dir / "paper_draft.md").write_text(outputs["paper"], encoding="utf-8")
    (out_dir / "script.md").write_text(outputs["script"], encoding="utf-8")

    # ══════════════════════════════════════════
    # AUTOMATION 4 — IEEE LaTeX Paper
    # ══════════════════════════════════════════
    try:
        latex_result = build_ieee_paper(outputs["paper"], out_dir)
    except Exception as e:
        console.print(f"[red]! LaTeX generation failed: {e}[/]")
        latex_result = {"error": str(e), "pdf_compiled": False}

    # ══════════════════════════════════════════
    # COPY TO OBSIDIAN (optional)
    # ══════════════════════════════════════════
    vault = os.getenv("OBSIDIAN_VAULT")
    if vault:
        vault_dir = Path(vault) / "Research" / f"{date}_{slug}"
        vault_dir.mkdir(parents=True, exist_ok=True)

        # Copy key files to Obsidian
        for fname in ["audit.md", "paper_draft.md", "script.md"]:
            src = out_dir / fname
            if src.exists():
                shutil.copy2(src, vault_dir / fname)

        console.print(f"  Copied to Obsidian: {vault_dir}/\n")

    # ══════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════
    elapsed = (datetime.now() - start_time).total_seconds()
    minutes = int(elapsed // 60)
    seconds = int(elapsed % 60)

    # File listing
    files = []
    for f in sorted(out_dir.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            size = f.stat().st_size
            if size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            files.append(f"  {'[OK]' if size > 100 else '[!!]'}  {f.name:<30} {size_str:>10}")

    files_text = "\n".join(files)

    # Counts
    t_claims = len(twitter.get("claims", []))
    r_claims = len(research.get("claims", []))
    pdf_status = "Compiled" if latex_result.get("pdf_compiled") else "Upload .tex to Overleaf"

    console.print(Panel(
        f"""[bold green]Pipeline Complete![/]

{out_dir}/

{files_text}

------------------------------
  Twitter claims:     {t_claims}
  Research claims:    {r_claims}
  PDF status:         {pdf_status}
  Time elapsed:       {minutes}m {seconds}s
------------------------------""",
        title="[bold]Results",
        border_style="green",
        padding=(1, 2),
    ))


# ── Individual automation runners ──

def run_twitter_only(topic: str):
    """Run only Twitter Intelligence."""
    console.print(Panel(f"[bold]{topic}[/]", title="Twitter Intel Only", border_style="red"))
    validate_env()
    result = twitter_intel(topic)
    slug = topic.lower().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out = Path("output") / f"{date}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "twitter_intel.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"\n  Saved: {out}/twitter_intel.json\n")


def run_research_only(topic: str):
    """Run only Deep Web Research."""
    console.print(Panel(f"[bold]{topic}[/]", title="Deep Research Only", border_style="blue"))
    validate_env()
    result = deep_web_research(topic)
    slug = topic.lower().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out = Path("output") / f"{date}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "deep_research.json").write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    console.print(f"\n  Saved: {out}/deep_research.json\n")


# ── CLI ──

USAGE = """
[bold]GeoResearch Pipeline[/]

[bold]Full pipeline (all 4 automations):[/]
  python pipeline.py "India-China LAC standoff 2026"

[bold]Individual automations:[/]
  python pipeline.py --twitter "topic"     Twitter only
  python pipeline.py --research "topic"    Deep web only
  python pipeline.py "topic"               Full pipeline

[bold]Examples:[/]
  python pipeline.py "BRICS summit 2026 outcomes"
  python pipeline.py "NATO Article 5 implications"
  python pipeline.py --twitter "G20 summit reactions"
"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print(USAGE)
        sys.exit(1)

    args = sys.argv[1:]

    if args[0] == "--twitter":
        if len(args) < 2:
            console.print("[red]Usage: python pipeline.py --twitter \"topic\"[/]")
            sys.exit(1)
        run_twitter_only(" ".join(args[1:]))

    elif args[0] == "--research":
        if len(args) < 2:
            console.print("[red]Usage: python pipeline.py --research \"topic\"[/]")
            sys.exit(1)
        run_research_only(" ".join(args[1:]))

    elif args[0] in ("--help", "-h"):
        console.print(USAGE)

    else:
        run_pipeline(" ".join(args))

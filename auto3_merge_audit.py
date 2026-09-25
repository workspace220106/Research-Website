"""
AUTOMATION 3 — MERGE + DEEP AUDIT + BUILD PAPER + SCRIPT

Takes Twitter intel (auto1) + Deep web research (auto2).
Cross-references, deduplicates, runs deep audit.
Builds: research paper draft (Markdown) + YouTube script + audit report.

Usage:  Imported by pipeline.py (receives dicts from auto1 + auto2)

LLMs used:
  - Gemini 3.6 Flash → merge, cross-reference, audit, research paper
  - GPT-4.1 / Groq Llama 3.3 → YouTube script (better conversational tone)
"""

import json
from rich.console import Console
from rich.table import Table
from core.claude import claude
from core.gpt import gpt
from core.models import VERDICT_EMOJI

console = Console()


# ══════════════════════════════════════════════════════════
# AUDIT PROMPT
# ══════════════════════════════════════════════════════════

AUDIT_PROMPT = """You are a senior geopolitical fact-checking editor.

You have two datasets:
1. TWITTER INTELLIGENCE — claims from X/Twitter (officials, journalists, analysts, viral posts)
2. DEEP WEB RESEARCH — claims from government sites, UN, NATO, BRICS, G7, G20, EU, think tanks, news wires

PERFORM A DEEP CROSS-REFERENCE AUDIT:

1. CORROBORATED CLAIMS
   Claims that appear in BOTH Twitter AND official/news sources.
   These are the strongest evidence. List each with both sources.

2. TWITTER-ONLY CLAIMS
   Claims found ONLY on Twitter with NO official or news corroboration.
   These are the weakest. Flag each with risk level (high/medium/low).
   High risk = high engagement + no primary source.

3. OFFICIAL-ONLY INFORMATION
   Important facts from government/institutional sources that
   NO ONE on Twitter is discussing. These are often overlooked
   and can be the most valuable for original content.

4. CONTRADICTIONS
   Where Twitter claims CONFLICT with official sources or where
   official sources contradict each other. List each contradiction
   with both sides and their source tiers.

5. CLAIM RELIABILITY MATRIX
   Create a table:
   | # | Claim | Twitter Source | Official Source | Verdict | Confidence |

6. TIMELINE RECONSTRUCTION
   Build a dated timeline of events from ALL verified/reported claims.
   Each entry must cite its source.

7. INFORMATION GAPS
   What critical questions remain unanswered?
   What would you need to fully verify the remaining claims?

8. OVERALL ASSESSMENT
   - How reliable is the overall narrative?
   - What percentage of claims are independently corroborated?
   - What is the single most important unverified claim?
   - Recommendation for the creator: what is safe to state as fact,
     what needs hedging, what should be omitted?

Output in Markdown format."""


# ══════════════════════════════════════════════════════════
# RESEARCH PAPER PROMPT
# ══════════════════════════════════════════════════════════

PAPER_PROMPT = """You are an academic researcher writing a formal research paper
on a geopolitical topic. You have access to verified evidence from multiple
sources including government statements, international organizations,
wire services, think tanks, and social media intelligence.

Write a COMPLETE research paper in Markdown with inline citations [1], [2], etc.

STRUCTURE:
# {Title — descriptive, academic, specific}

## Abstract
200-250 words. State the research question, methodology, key findings, and implications.

## I. Introduction
- Why this topic matters now
- Research question
- Scope and limitations
- Paper structure overview

## II. Background and Historical Context
- Relevant history leading to current events
- Previous agreements, disputes, precedents
- Key actors and their historical positions

## III. Methodology
- Evidence-based analysis of primary and secondary sources
- Source classification (government statements, wire services, think tanks, social media)
- Verification approach used

## IV. Current Developments
- Chronological account of recent events
- Each statement backed by cited source
- Distinguish confirmed facts from reported claims

## V. Analysis of Key Actors and Positions
- Each major actor's stated position (with source)
- Underlying interests and motivations (analysis, clearly labeled)
- Areas of agreement and disagreement

## VI. Institutional Responses
- UN, NATO, EU, BRICS, G7, G20, SCO positions (where relevant)
- Official communiqués and resolutions
- Gaps between institutional statements and actions

## VII. Economic and Strategic Implications
- Trade, sanctions, economic impact
- Military/security dimensions
- Technology and supply chain effects

## VIII. Competing Interpretations
- Present at least 2 different analytical frameworks
- Western vs non-Western perspectives where relevant
- Identify where the evidence genuinely supports multiple readings

## IX. Limitations and Uncertainties
- What evidence is missing
- Which claims could not be independently verified
- What assumptions underpin the analysis
- This section is MANDATORY — never pretend certainty you don't have

## X. Conclusion
- Summary of key findings
- Implications for future developments
- Questions for further research

## References
List EVERY cited source with:
[N] Author/Publisher. "Title." Publication/Website, Date. URL.

CRITICAL RULES:
- EVERY factual statement must have a citation [N]
- NEVER present unverified claims as facts — use "reportedly", "according to"
- DISTINGUISH between primary sources and analysis throughout
- Academic tone, third person, no sensationalism
- If Twitter is the only source for a claim, explicitly note that"""


# ══════════════════════════════════════════════════════════
# YOUTUBE SCRIPT PROMPT
# ══════════════════════════════════════════════════════════

SCRIPT_PROMPT = """You are a YouTube scriptwriter for a serious geopolitics channel.
The channel is known for well-researched, citation-backed analysis — not clickbait.

Write an engaging, authoritative script from this research evidence.

STRUCTURE:

🎯 HOOK (10-15 seconds)
- One striking fact or question that makes the viewer stay
- NOT clickbait — genuinely surprising or important
- Example: "In the last 72 hours, three governments issued contradictory statements about..."

📖 CONTEXT (45-60 seconds)
- What happened before this? Brief historical setup
- Only what the viewer NEEDS to understand the current event
- [B-ROLL: relevant map or historical footage suggestion]

📰 WHAT HAPPENED (2-3 minutes)
- The core developments, chronologically
- Each claim attributed: "According to Reuters...", "The MEA stated..."
- [B-ROLL: suggestions for each segment]

🔍 EVIDENCE DEEP-DIVE (1-2 minutes)
- What do the PRIMARY sources actually say?
- Show the difference between what officials said and what media reported
- This is the section that makes the channel credible

🧠 ANALYSIS (2 minutes)
- What does this mean? Who benefits?
- Present competing interpretations
- Draw from think tank analysis where available

⚖️ COUNTERPOINT (45-60 seconds)
- The opposite view or what could go wrong with the main narrative
- "However, some analysts argue..." or "What this analysis misses is..."

❓ WHAT TO WATCH (30 seconds)
- What happens next?
- Specific things to monitor (upcoming meetings, deadlines, decisions)

📢 CALL TO ACTION (10 seconds)
- Question to drive comments
- Subscribe prompt tied to the topic

FORMAT RULES:
- Conversational but authoritative. NOT academic, NOT clickbait.
- Mark citations: [Source: Reuters], [Source: MEA India], etc.
- Mark visual cues: [B-ROLL: map of LAC region], [GRAPHIC: timeline]
- Mark emphasis: **key phrase the speaker should stress**
- Include a suggested TITLE (under 60 chars) and THUMBNAIL CONCEPT at the top
- Script should be 8-12 minutes when read aloud (~1500-2200 words)
- NEVER present disputed claims as facts — always attribute
- End with an open question, not a definitive conclusion"""


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def merge_and_build(twitter_data: dict, research_data: dict) -> dict:
    topic = twitter_data.get("topic", research_data.get("topic", "Unknown"))
    console.print(f"\n[bold green]━━━ MERGE + AUDIT + BUILD ━━━[/]\n")
    console.print(f"  Topic: [bold]{topic}[/]")

    # Compile combined evidence
    combined = json.dumps({
        "topic": topic,
        "twitter_claims": twitter_data.get("claims", []),
        "twitter_summary": twitter_data.get("summary", {}),
        "twitter_speaker_breakdown": twitter_data.get("speaker_breakdown", {}),
        "research_claims": research_data.get("claims", []),
        "research_summary": research_data.get("summary", {}),
        "synthesis": research_data.get("synthesis", {}),
        "all_sources": research_data.get("all_sources", []),
        "institutions_searched": research_data.get("institutions_searched", []),
    }, indent=2, ensure_ascii=False)

    twitter_count = len(twitter_data.get("claims", []))
    research_count = len(research_data.get("claims", []))
    console.print(f"  Twitter claims: {twitter_count}")
    console.print(f"  Research claims: {research_count}")
    console.print(f"  Total to cross-reference: {twitter_count + research_count}\n")

    # ── 1. Deep Cross-Reference Audit ──
    console.print("  🔬 Running deep cross-reference audit...")
    try:
        audit = claude(
            system=AUDIT_PROMPT,
            user=f"TOPIC: {topic}\n\nCOMBINED EVIDENCE:\n{combined}",
        )
    except Exception as e:
        console.print(f"  [red]⚠ Audit failed: {e}[/]")
        audit = f"# Audit Failed\n\nError: {e}\n\nRaw data available in JSON files."

    console.print("  ✅ Audit complete\n")

    # ── 2. Research Paper Draft ──
    console.print("  📄 Building research paper draft...")
    try:
        paper = claude(
            system=PAPER_PROMPT,
            user=f"TOPIC: {topic}\n\nVERIFIED EVIDENCE + AUDIT:\n{combined}\n\nAUDIT FINDINGS:\n{audit[:3000]}",
        )
    except Exception as e:
        console.print(f"  [red]⚠ Paper generation failed: {e}[/]")
        paper = f"# Paper Generation Failed\n\nError: {e}"

    console.print("  ✅ Paper draft complete\n")

    # ── 3. YouTube Script ──
    console.print("  🎬 Building YouTube script...")
    try:
        script = gpt(
            system=SCRIPT_PROMPT,
            user=f"TOPIC: {topic}\n\nRESEARCH EVIDENCE:\n{combined}\n\nAUDIT NOTES:\n{audit[:2000]}",
        )
    except Exception as e:
        console.print(f"  [red]⚠ Script generation failed: {e}[/]")
        # Fallback to Gemini
        console.print("  🔄 Falling back to Gemini for script...")
        try:
            script = claude(
                system=SCRIPT_PROMPT,
                user=f"TOPIC: {topic}\n\nRESEARCH EVIDENCE:\n{combined}",
            )
        except Exception as e2:
            script = f"# Script Generation Failed\n\nError: {e2}"

    console.print("  ✅ Script complete\n")

    # ── Summary ──
    table = Table(title="Build Summary")
    table.add_column("Output", style="bold")
    table.add_column("Status")
    table.add_column("Size", justify="right")
    table.add_row("Audit Report", "[green]✅[/]", f"{len(audit):,} chars")
    table.add_row("Research Paper", "[green]✅[/]", f"{len(paper):,} chars")
    table.add_row("YouTube Script", "[green]✅[/]", f"{len(script):,} chars")
    console.print(table)
    console.print()

    return {
        "topic": topic,
        "audit": audit,
        "paper": paper,
        "script": script,
    }

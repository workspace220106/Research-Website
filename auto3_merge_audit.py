"""
AUTOMATION 3 — MERGE + DEEP AUDIT + BUILD PAPER + SCRIPT

Takes Twitter intel (auto1) + Deep web research (auto2).
Cross-references, deduplicates, runs deep audit.
Builds: research paper draft (Markdown) + YouTube script + audit report.
Now with full scraped article text for maximum detail.

Usage:  Imported by pipeline.py (receives dicts from auto1 + auto2)

LLMs used:
  - OpenRouter -> merge, cross-reference, audit, research paper
  - NVIDIA NIM / Groq -> YouTube script
"""

import json
from rich.console import Console
from rich.table import Table
from core.claude import claude
from core.gpt import gpt
from core.models import VERDICT_EMOJI

console = Console()


# ══════════════════════════════════════════════════════════
# AUDIT PROMPT (EXPANDED)
# ══════════════════════════════════════════════════════════

AUDIT_PROMPT = """You are a senior geopolitical fact-checking editor conducting an
EXHAUSTIVE cross-reference audit.

You have two datasets with FULL SCRAPED ARTICLE TEXT:
1. TWITTER INTELLIGENCE -- claims from X/Twitter (officials, journalists, analysts,
   viral posts) + full text from cited articles scraped via Scrapling
2. DEEP WEB RESEARCH -- claims from government sites, UN, NATO, BRICS, G7, G20, EU,
   think tanks, news wires + full text from every source page scraped via Scrapling

PERFORM AN EXTREMELY DETAILED CROSS-REFERENCE AUDIT:

## 1. CORROBORATED CLAIMS (claims found in BOTH Twitter AND official sources)
For each corroborated claim:
- Exact claim text
- Twitter source (who, when, URL)
- Official source (institution, document, URL)
- Confidence level (1-10)
- Direct quotes from both sources

## 2. TWITTER-ONLY CLAIMS (found ONLY on Twitter)
For each:
- The claim
- Who said it and their credibility
- Risk level (HIGH/MEDIUM/LOW) with reasoning
- What official source SHOULD have this info but doesn't
- Recommendation: safe to report / needs hedging / should omit

## 3. OFFICIAL-ONLY INFORMATION (important facts NOT discussed on Twitter)
These are often the most valuable for original content.
For each:
- The information
- Which official source published it
- Why it matters
- Why Twitter might have missed it
- Recommendation for how to use it

## 4. CONTRADICTIONS (where sources conflict)
For each contradiction:
- Claim A (source, tier, exact quote)
- Claim B (source, tier, exact quote)
- Analysis of which is more likely correct and why
- What additional evidence would resolve it

## 5. DETAILED CLAIM RELIABILITY MATRIX
| # | Claim | Twitter Source | Official Source | Verdict | Confidence | Direct Quote |

## 6. COMPLETE TIMELINE RECONSTRUCTION
Build a DETAILED dated timeline (minimum 20 entries if data available):
| Date | Event | Source | Tier | Verified? |

## 7. SOURCE CREDIBILITY ANALYSIS
For each major source used:
- Source name and type
- Number of claims from this source
- Track record / reliability assessment
- Potential biases

## 8. INFORMATION GAPS
- Critical questions that remain unanswered
- What sources should be consulted next
- What evidence would be needed to verify remaining claims
- Geographic/temporal blind spots in the coverage

## 9. NARRATIVE ANALYSIS
- What is the dominant narrative on Twitter?
- How does it differ from official sources?
- Are there information operations or coordinated messaging?
- What perspective is underrepresented?

## 10. OVERALL ASSESSMENT
- Reliability score (1-10) for the overall narrative
- Percentage of claims independently corroborated
- The 3 most important verified facts
- The 3 most dangerous unverified claims
- Detailed recommendation for the creator:
  * What is SAFE to state as fact (with citations)
  * What needs HEDGING (and suggested language)
  * What should be OMITTED (and why)
  * What is EXCLUSIVE (official-only info not on Twitter)

Output in detailed Markdown format. Be EXHAUSTIVE. Every detail matters."""


# ══════════════════════════════════════════════════════════
# RESEARCH PAPER PROMPT (EXPANDED)
# ══════════════════════════════════════════════════════════

PAPER_PROMPT = """You are an academic researcher writing a COMPREHENSIVE, PUBLICATION-QUALITY
research paper on a geopolitical topic. You have access to FULL TEXT articles scraped
from government websites, international organizations, wire services, think tanks,
and social media intelligence.

Write an EXHAUSTIVE research paper in Markdown with inline citations [1], [2], etc.
USE EVERY PIECE OF EVIDENCE. Include specific numbers, dates, quotes, and statistics.

STRUCTURE:

# {Title -- descriptive, academic, specific}

## Abstract
300-400 words. State the research question, methodology, key findings, implications,
and contribution to existing literature.

## I. Introduction
- Why this topic matters now (with specific recent events)
- Research question (clearly stated)
- Scope and limitations
- Methodology overview
- Paper structure

## II. Background and Historical Context
- Relevant history leading to current events (500+ words)
- Previous agreements, disputes, precedents (with specific dates)
- Key actors and their historical positions
- Evolution of the issue over time
- Relevant international law and treaty frameworks

## III. Methodology
- Multi-source evidence analysis approach
- Source classification framework (PRIMARY/JOURNALISM/RESEARCH)
- Scrapled full-text analysis from official government and institutional websites
- Social media intelligence collection via Twitter/X
- Cross-reference verification methodology
- Limitations of the approach

## IV. Current Developments
- Chronological account of events (every date, every statement)
- Each claim attributed with inline citation
- Distinguish confirmed facts from reported claims
- Include direct quotes from officials where available
- Note information gaps explicitly

## V. Analysis of Key Actors and Positions
For EACH major actor (minimum 5):
- Full name, title, institution
- Exact stated position (with direct quotes)
- Specific actions taken (with dates)
- Underlying interests and motivations (analytical)
- Historical context for their position
- Credibility assessment

## VI. Institutional and Multilateral Responses
- UN position (GA, SC, Secretariat -- with resolution numbers)
- NATO communiques (exact language)
- EU/EEAS statements
- BRICS joint declarations
- G7/G20 positions
- SCO/ASEAN/AU responses
- ICJ/ICC rulings if relevant
- IMF/World Bank/WTO assessments
- Regional organization responses

## VII. Economic and Strategic Implications
- Trade impacts (specific figures, percentages)
- Sanctions and their effects (specific measures)
- GDP/growth projections
- Supply chain disruptions
- Energy security dimensions
- Currency and financial market impacts
- Investment and FDI effects

## VIII. Military and Security Dimensions
- Troop deployments and movements
- Defense spending changes
- Arms deals and transfers
- Military exercises and posturing
- Nuclear/WMD dimensions if relevant
- Cyber and hybrid warfare elements
- Intelligence assessments

## IX. Diplomatic Landscape
- Bilateral negotiations and their status
- Treaty obligations and compliance
- Diplomatic incidents (recalls, expulsions)
- Summit outcomes and communiques
- Track-2 diplomacy efforts
- Mediation attempts

## X. Competing Interpretations
- Western analytical framework
- Non-Western / Global South perspective
- Realist vs liberal institutionalist readings
- Historical analogies (with caveats)
- Where evidence genuinely supports multiple readings

## XI. Regional and Global Impact
- Impact on neighboring countries (specific effects)
- Impact on global institutions and norms
- Precedent-setting implications
- Alliance dynamics shifts
- Global South positioning

## XII. Public Opinion and Media Analysis
- How different national media covered the topic
- Social media narratives and their divergence from facts
- Polling data if available
- Protest movements or public reactions

## XIII. Limitations and Uncertainties
- What evidence is missing
- Which claims could not be independently verified
- Methodological limitations
- Information that may emerge later
- Assumptions underlying the analysis

## XIV. Scenario Analysis and Outlook
- Most likely scenario (with reasoning)
- Best-case scenario
- Worst-case scenario
- Key decision points to watch
- Indicators that would signal escalation or de-escalation

## XV. Conclusion
- Summary of key findings
- Contribution to understanding
- Policy implications
- Questions for further research

## References
List EVERY cited source with FULL bibliographic information:
[N] Author/Publisher. "Title." Publication/Website, Date. URL.
Minimum 20 references. Include ALL sources from the evidence package.

CRITICAL RULES:
- EVERY factual statement must have a citation [N]
- Include DIRECT QUOTES from officials wherever available
- Include SPECIFIC NUMBERS (dates, statistics, financial figures)
- NEVER present unverified claims as facts
- DISTINGUISH between primary sources and analysis
- Academic tone, third person, no sensationalism
- If Twitter is the only source, explicitly note that
- The paper should be 4000-6000 words minimum
- Use ALL the evidence provided -- do not leave data on the table"""


# ══════════════════════════════════════════════════════════
# YOUTUBE SCRIPT PROMPT (EXPANDED)
# ══════════════════════════════════════════════════════════

SCRIPT_PROMPT = """You are a YouTube scriptwriter for a serious geopolitics channel.
The channel is known for DEEPLY RESEARCHED, citation-backed analysis with
EXCLUSIVE information from official sources that other channels miss.

Write a DETAILED, AUTHORITATIVE script from this research evidence.
You have access to full text from government websites and think tank reports --
use quotes and specific details that other YouTube channels won't have.

STRUCTURE (target: 15-20 minutes, 3000-4000 words):

TITLE: [Under 60 chars, compelling but not clickbait]
THUMBNAIL CONCEPT: [Specific visual concept with text overlay]

---

HOOK (15-20 seconds)
- One striking fact from the OFFICIAL sources that most people don't know
- NOT clickbait -- genuinely surprising or important
- Example: "A document published by [institution] three days ago contains
  a clause that changes everything about..."

COLD OPEN (30-45 seconds)
- Set the stakes: why should the viewer care RIGHT NOW?
- One sentence summary of what this video reveals
- [B-ROLL: specific suggestion]

CONTEXT SECTION (2-3 minutes)
- Historical background the viewer needs
- Key dates, treaties, previous incidents
- Use a timeline format for clarity
- [B-ROLL: maps, historical footage, document screenshots]
- [GRAPHIC: timeline with 5-8 key dates]

WHAT HAPPENED (3-4 minutes)
- The core developments, chronologically
- EVERY claim attributed: "According to Reuters...", "The MEA stated..."
- Include DIRECT QUOTES from officials: "In the words of Minister X, quote..."
- Use specific numbers and dates
- [B-ROLL: news footage, official photos, press conferences]

PRIMARY SOURCE DEEP-DIVE (3-4 minutes)
- What do the OFFICIAL DOCUMENTS actually say?
- Show the difference between headlines and the actual text
- Read key excerpts from communiques, resolutions, statements
- This is the section that makes the channel UNIQUE
- "Now here's what most coverage is missing..."
- [B-ROLL: document screenshots, highlighted text, official websites]

EVIDENCE DEEP-DIVE (2-3 minutes)
- Show the difference between what officials said and what media reported
- Cross-reference Twitter claims with official sources
- Highlight contradictions and what they mean
- "When we checked the actual [government/UN/NATO] statement..."
- [B-ROLL: side-by-side comparisons]

ANALYSIS (2-3 minutes)
- What does this mean? Who benefits?
- Present competing interpretations
- Draw from think tank analysis (cite specific reports)
- Include economic/strategic implications with numbers
- "Brookings argues... but the ORF takes the opposite view..."

COUNTERPOINT (1-2 minutes)
- The strongest opposing view
- What this analysis might be getting wrong
- "However, [analyst/institution] argues..." with specific reasoning
- What evidence would change the conclusion?

WHAT TO WATCH (1 minute)
- 3-5 specific things to monitor
- Upcoming meetings, deadlines, decisions with exact dates
- "If X happens before [date], it signals..."
- Indicators of escalation or de-escalation

CALL TO ACTION (15 seconds)
- Thought-provoking question for comments
- "What do you think [specific question]?"
- Tie the subscribe to being informed about this developing story

---

FORMAT RULES:
- Conversational but authoritative -- you sound like a well-read analyst, not a professor
- Mark citations: [Source: Reuters, Sep 2026], [Source: MEA India], etc.
- Mark visual cues: [B-ROLL: map of LAC region], [GRAPHIC: trade flow chart]
- Mark emphasis: **key phrase the speaker should stress**
- EVERY section must have at least 2 specific citations
- Include at least 5 direct quotes from officials/analysts
- Include at least 3 specific statistics or numbers
- Script should be 15-20 minutes when read aloud (~3000-4000 words)
- NEVER present disputed claims as facts -- always attribute
- End with an open question, not a definitive conclusion
- Sound like you have EXCLUSIVE access to primary documents (you do!)"""


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def merge_and_build(twitter_data: dict, research_data: dict) -> dict:
    topic = twitter_data.get("topic", research_data.get("topic", "Unknown"))
    console.print(f"\n[bold green]--- MERGE + AUDIT + BUILD ---[/]\n")
    console.print(f"  Topic: [bold]{topic}[/]")

    # Compile combined evidence (now includes scraping stats)
    combined = json.dumps({
        "topic": topic,
        "twitter_claims": twitter_data.get("claims", []),
        "twitter_summary": twitter_data.get("summary", {}),
        "twitter_speaker_breakdown": twitter_data.get("speaker_breakdown", {}),
        "twitter_scraped_articles": twitter_data.get("scraped_articles", []),
        "research_claims": research_data.get("claims", []),
        "research_summary": research_data.get("summary", {}),
        "synthesis": research_data.get("synthesis", {}),
        "all_sources": research_data.get("all_sources", []),
        "institutions_searched": research_data.get("institutions_searched", []),
        "scraping_stats": research_data.get("scraping_stats", {}),
    }, indent=2, ensure_ascii=False)

    twitter_count = len(twitter_data.get("claims", []))
    research_count = len(research_data.get("claims", []))
    twitter_scraped = twitter_data.get("scraping_stats", {}).get("pages_scraped", 0)
    research_scraped = research_data.get("scraping_stats", {}).get("pages_scraped", 0)
    total_words = (
        twitter_data.get("scraping_stats", {}).get("words_scraped", 0) +
        research_data.get("scraping_stats", {}).get("words_scraped", 0)
    )

    console.print(f"  Twitter claims: {twitter_count}")
    console.print(f"  Research claims: {research_count}")
    console.print(f"  Total claims to cross-reference: {twitter_count + research_count}")
    console.print(f"  Pages scraped (Twitter): {twitter_scraped}")
    console.print(f"  Pages scraped (Research): {research_scraped}")
    console.print(f"  Total words from scraping: {total_words:,}\n")

    # Cap combined to avoid token limits
    if len(combined) > 100000:
        combined = combined[:100000] + "\n\n[Evidence truncated at 100k chars]"

    # ── 1. Deep Cross-Reference Audit ──
    console.print("  Running deep cross-reference audit...")
    try:
        audit = claude(
            system=AUDIT_PROMPT,
            user=f"TOPIC: {topic}\n\nCOMBINED EVIDENCE ({twitter_count + research_count} claims, "
                 f"{twitter_scraped + research_scraped} pages scraped, {total_words:,} words):\n{combined}",
            max_tokens=16384,
        )
    except Exception as e:
        console.print(f"  [red]! Audit failed: {e}[/]")
        audit = f"# Audit Failed\n\nError: {e}\n\nRaw data available in JSON files."

    console.print(f"  Audit complete ({len(audit):,} chars)\n")

    # ── 2. Research Paper Draft ──
    console.print("  Building comprehensive research paper...")
    try:
        paper = claude(
            system=PAPER_PROMPT,
            user=f"TOPIC: {topic}\n\nVERIFIED EVIDENCE + AUDIT:\n{combined}\n\nAUDIT FINDINGS:\n{audit[:5000]}",
            max_tokens=16384,
        )
    except Exception as e:
        console.print(f"  [red]! Paper generation failed: {e}[/]")
        paper = f"# Paper Generation Failed\n\nError: {e}"

    console.print(f"  Paper complete ({len(paper):,} chars)\n")

    # ── 3. YouTube Script ──
    console.print("  Building detailed YouTube script...")
    try:
        script = gpt(
            system=SCRIPT_PROMPT,
            user=f"TOPIC: {topic}\n\nRESEARCH EVIDENCE:\n{combined}\n\nAUDIT NOTES:\n{audit[:3000]}",
            max_tokens=8192,
        )
    except Exception as e:
        console.print(f"  [red]! Script generation failed: {e}[/]")
        console.print("  Falling back to OpenRouter for script...")
        try:
            script = claude(
                system=SCRIPT_PROMPT,
                user=f"TOPIC: {topic}\n\nRESEARCH EVIDENCE:\n{combined}",
                max_tokens=8192,
            )
        except Exception as e2:
            script = f"# Script Generation Failed\n\nError: {e2}"

    console.print(f"  Script complete ({len(script):,} chars)\n")

    # ── Summary ──
    table = Table(title="Build Summary")
    table.add_column("Output", style="bold")
    table.add_column("Status")
    table.add_column("Size", justify="right")
    table.add_row("Audit Report", "[green]OK[/]", f"{len(audit):,} chars")
    table.add_row("Research Paper", "[green]OK[/]", f"{len(paper):,} chars")
    table.add_row("YouTube Script", "[green]OK[/]", f"{len(script):,} chars")
    table.add_row("Total output", "", f"{len(audit) + len(paper) + len(script):,} chars")
    console.print(table)
    console.print()

    return {
        "topic": topic,
        "audit": audit,
        "paper": paper,
        "script": script,
    }

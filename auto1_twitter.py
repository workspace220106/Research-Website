"""
AUTOMATION 1 — TWITTER / X INTELLIGENCE

Searches Twitter/X via Perplexity (no $5K/mo X API needed).
Extracts claims from officials, journalists, analysts, viral posts.
Classifies speakers, fact-checks each claim.

Usage:  python auto1_twitter.py "India-China LAC standoff 2026"
        Or imported by pipeline.py

LLMs used:
  - Perplexity sonar-pro → Twitter search (indexes X in real-time)
  - Claude Sonnet → claim extraction + speaker classification + fact-checking
"""

import json
import sys
import time
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from core.perplexity import perplexity_search
from core.claude import claude
from core.models import VERDICT_EMOJI

console = Console()


# ══════════════════════════════════════════════════════════
# TWITTER SEARCH ANGLES
# ══════════════════════════════════════════════════════════

def build_twitter_searches(topic: str) -> list:
    """Build multi-angle Twitter search queries."""
    return [
        {
            "angle": "Official government statements",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"official government minister spokesperson "
                f"ministry foreign affairs defense"
            ),
            "system": (
                "Search Twitter/X for OFFICIAL government posts about this topic. "
                "Focus on verified government accounts, ministers, spokespersons. "
                "Return: who posted (name, handle, role), exact claim, date, URL."
            ),
        },
        {
            "angle": "Journalist & wire service reports",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"journalist reporter correspondent breaking "
                f"Reuters AP BBC AFP Al Jazeera"
            ),
            "system": (
                "Search Twitter/X for posts from JOURNALISTS and NEWS correspondents. "
                "Focus on verified reporters, wire service accounts, breaking reports. "
                "Return: reporter name, outlet, what they reported, date, URL."
            ),
        },
        {
            "angle": "OSINT & analyst commentary",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"analyst OSINT expert geopolitics think tank "
                f"intelligence assessment"
            ),
            "system": (
                "Search Twitter/X for ANALYST and OSINT posts about this topic. "
                "Focus on geopolitical analysts, think tank researchers, OSINT accounts. "
                "Return: analyst name/handle, their analysis, evidence cited, URL."
            ),
        },
        {
            "angle": "Viral claims & trending narratives",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"viral trending claim disputed controversial "
                f"rumor unconfirmed"
            ),
            "system": (
                "Search Twitter/X for VIRAL and TRENDING claims about this topic. "
                "Focus on widely shared posts, disputed narratives, unconfirmed reports. "
                "Note engagement levels if visible. Flag anything that lacks a primary source."
            ),
        },
        {
            "angle": "Diplomatic & institutional accounts",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"embassy ambassador UN NATO EU BRICS G20 "
                f"diplomat delegation"
            ),
            "system": (
                "Search Twitter/X for posts from DIPLOMATIC and INSTITUTIONAL accounts. "
                "Focus on embassies, ambassadors, UN/NATO/EU/BRICS official accounts. "
                "Return: institution, statement, date, URL."
            ),
        },
    ]


# ══════════════════════════════════════════════════════════
# CLAIM EXTRACTION PROMPT
# ══════════════════════════════════════════════════════════

EXTRACT_PROMPT = """Extract every distinct factual claim from these Twitter/X
search results about a geopolitical topic.

For each claim return a JSON array:
[{
  "claim": "concise factual statement",
  "speaker": "who said it (name / handle / role)",
  "speaker_type": "official|journalist|analyst|general_user",
  "date": "when posted (YYYY-MM-DD if available, else 'unknown')",
  "url": "tweet URL if available, else empty string",
  "claim_type": "factual_event|statistic|attribution|causal|prediction",
  "engagement": "high|medium|low|unknown"
}]

RULES:
- Each claim must be a SEPARATE factual assertion
- Speaker classification determines credibility weight:
  official = highest (government account)
  journalist = high (verified reporter)
  analyst = medium (expert/OSINT)
  general_user = lowest (unverified account)
- If the same claim appears from multiple speakers, list EACH instance separately
  (this helps cross-reference later)
- Include predictions only if presented as likely or imminent
- DO NOT include pure opinions, jokes, or memes
- Return ONLY valid JSON array"""


# ══════════════════════════════════════════════════════════
# FACT-CHECK PROMPT
# ══════════════════════════════════════════════════════════

FACTCHECK_PROMPT = """You are fact-checking claims from Twitter/X about a geopolitical topic.

For each claim, assign a verification status based on the speaker type and evidence.

VERIFICATION RULES:
- Official government account + specific verifiable event = REPORTED
  (not VERIFIED unless independently confirmed by another source)
- Journalist from major outlet (Reuters/AP/BBC/AFP) = REPORTED
- Multiple independent sources (different outlets, not retweets) confirming = VERIFIED
- Sources giving conflicting accounts = DISPUTED
- Viral claim from general user with no corroboration = UNVERIFIED
- Analyst interpretation/prediction = REPORTED (it's expert opinion, not fact)

Return the same JSON array with these ADDED fields:
"verdict": "verified|reported|disputed|unverified",
"reasoning": "1-2 sentences explaining why this verdict",
"credibility_weight": 1-5 (5 = most credible),
"needs_verification": true/false (flag claims that should be checked against official sources)

Return ONLY valid JSON array."""


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def twitter_intel(topic: str) -> dict:
    console.print(f"\n[bold red]━━━ TWITTER / X INTELLIGENCE ━━━[/]\n")
    console.print(f"  Topic: [bold]{topic}[/]\n")

    searches = build_twitter_searches(topic)

    # ── Step 1: Multi-angle Perplexity searches ──
    twitter_data = []
    for i, s in enumerate(searches, 1):
        console.print(f"  [{i}/{len(searches)}] 🐦 {s['angle']}...")
        try:
            result = perplexity_search(s["query"], system=s["system"])
            twitter_data.append({
                "angle": s["angle"],
                "results": result["text"],
                "citations": result["citations"],
            })
        except Exception as e:
            console.print(f"    [red]⚠ Failed: {e}[/]")
            twitter_data.append({
                "angle": s["angle"],
                "results": f"Search failed: {e}",
                "citations": [],
            })
        time.sleep(1)

    # ── Step 2: Claude — Extract structured claims ──
    console.print(f"\n  🧠 Extracting claims with Claude...")

    raw_text = "\n\n".join([
        f"=== {d['angle']} ===\n{d['results']}"
        for d in twitter_data
    ])

    try:
        claims = claude(
            system=EXTRACT_PROMPT,
            user=f"TOPIC: {topic}\n\nTWITTER DATA:\n{raw_text}",
            json_mode=True,
        )
    except Exception as e:
        console.print(f"  [red]⚠ Claim extraction failed: {e}[/]")
        claims = []

    if not isinstance(claims, list):
        claims = []

    console.print(f"  Found [bold]{len(claims)}[/] claims\n")

    # ── Step 3: Claude — Fact-check in batches ──
    console.print(f"  ✅ Fact-checking {len(claims)} claims...")

    checked_claims = []
    batch_size = 5

    for i in range(0, len(claims), batch_size):
        batch = claims[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(claims) + batch_size - 1) // batch_size
        console.print(f"    Batch {batch_num}/{total_batches}...")

        try:
            verdicts = claude(
                system=FACTCHECK_PROMPT,
                user=json.dumps(batch, indent=2),
                json_mode=True,
            )
            if isinstance(verdicts, list):
                checked_claims.extend(verdicts)
            else:
                checked_claims.extend(batch)
        except Exception as e:
            console.print(f"    [red]⚠ Batch failed: {e}[/]")
            # Keep unchecked claims with default verdict
            for c in batch:
                c["verdict"] = "unverified"
                c["reasoning"] = "Fact-check failed"
                c["credibility_weight"] = 1
                c["needs_verification"] = True
            checked_claims.extend(batch)

        time.sleep(0.5)

    # ── Compile output ──
    all_citations = []
    for d in twitter_data:
        if isinstance(d["citations"], list):
            all_citations.extend(d["citations"])
    all_citations = list(set(all_citations))

    # Count verdicts
    verdict_counts = {}
    for c in checked_claims:
        v = c.get("verdict", "unverified")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

    # Count speaker types
    speaker_counts = {}
    for c in checked_claims:
        st = c.get("speaker_type", "unknown")
        speaker_counts[st] = speaker_counts.get(st, 0) + 1

    output = {
        "topic": topic,
        "source": "twitter",
        "timestamp": datetime.now().isoformat(),
        "claims": checked_claims,
        "raw_citations": all_citations,
        "summary": {
            "total_claims": len(checked_claims),
            **verdict_counts,
        },
        "speaker_breakdown": speaker_counts,
        "needs_verification": [
            c for c in checked_claims
            if c.get("needs_verification", False)
        ],
    }

    # ── Print summary ──
    console.print()
    table = Table(title="Twitter Intelligence Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total claims", str(len(checked_claims)))
    for v, count in sorted(verdict_counts.items()):
        emoji = VERDICT_EMOJI.get(v, "❓")
        color = {"verified": "green", "reported": "blue",
                 "disputed": "yellow", "unverified": "red"}.get(v, "white")
        table.add_row(f"{emoji} [{color}]{v.upper()}[/]", str(count))
    table.add_row("", "")
    for st, count in sorted(speaker_counts.items()):
        table.add_row(f"  {st}", str(count))
    table.add_row("", "")
    table.add_row("Unique source URLs", str(len(all_citations)))
    table.add_row("Need verification", str(len(output["needs_verification"])))
    console.print(table)

    # Flag high-priority unverified claims
    flagged = [c for c in checked_claims if c.get("verdict") in ("disputed", "unverified")
               and c.get("engagement") == "high"]
    if flagged:
        console.print(f"\n  [bold red]⚠ HIGH-ENGAGEMENT UNVERIFIED CLAIMS:[/]")
        for f_ in flagged:
            console.print(f"    🔴 {f_['claim'][:90]}")
            console.print(f"       Speaker: {f_.get('speaker', '?')} ({f_.get('speaker_type', '?')})")

    console.print()
    return output


# ── Standalone run ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python auto1_twitter.py \"topic\"[/]")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    result = twitter_intel(topic)

    slug = topic.lower().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out = Path("output") / f"{date}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "twitter_intel.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(f"  💾 Saved: {out}/twitter_intel.json\n")

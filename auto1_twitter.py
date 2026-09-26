"""
AUTOMATION 1 — TWITTER / X INTELLIGENCE + SCRAPLING

Searches Twitter/X via Tavily (no $5K/mo X API needed).
Scrapes full content from cited URLs for deeper context.
Extracts claims from officials, journalists, analysts, viral posts.
Classifies speakers, fact-checks each claim against scraped evidence.

Usage:  python auto1_twitter.py "India-China LAC standoff 2026"
        Or imported by pipeline.py

LLMs used:
  - Tavily -> Twitter/web search (free 1K/month)
  - Scrapling -> full content extraction from cited URLs
  - OpenRouter -> claim extraction + speaker classification + fact-checking
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
from core.scraper import scrape_urls, build_content_block
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
        {
            "angle": "Reactions from global south & non-western voices",
            "query": (
                f"site:x.com OR site:twitter.com {topic} "
                f"Africa Asia Latin America developing nations "
                f"reaction response criticism support"
            ),
            "system": (
                "Search Twitter/X for reactions from GLOBAL SOUTH and NON-WESTERN voices. "
                "Focus on African, Asian, Latin American officials, media, commentators. "
                "Return: who posted, their position/reaction, country/region, URL."
            ),
        },
    ]


# ══════════════════════════════════════════════════════════
# CLAIM EXTRACTION PROMPT
# ══════════════════════════════════════════════════════════

EXTRACT_PROMPT = """Extract every distinct factual claim from these Twitter/X
search results AND the full article text scraped from cited URLs.

For each claim return a JSON array:
[{
  "claim": "concise factual statement with specific details (names, dates, numbers)",
  "speaker": "who said it (name / handle / role)",
  "speaker_type": "official|journalist|analyst|general_user|institution",
  "date": "when posted (YYYY-MM-DD if available, else 'unknown')",
  "url": "source URL if available, else empty string",
  "claim_type": "factual_event|statistic|attribution|causal|prediction|policy_action|military_action|economic_data",
  "engagement": "high|medium|low|unknown",
  "context": "1-2 sentences of background context from the full article if available",
  "linked_article_title": "title of the linked article if the tweet cited one"
}]

RULES:
- Each claim must be a SEPARATE factual assertion
- Extract SPECIFIC details: exact quotes, numbers, dates, names of officials
- If the scraped article provides additional context beyond the tweet, include it
- Speaker classification determines credibility weight:
  official = highest (government account)
  institution = high (UN/NATO/EU/BRICS official)
  journalist = high (verified reporter)
  analyst = medium (expert/OSINT)
  general_user = lowest (unverified account)
- If the same claim appears from multiple speakers, list EACH instance
- Include predictions only if presented as likely or imminent
- DO NOT include pure opinions, jokes, or memes
- Return ONLY valid JSON array"""


# ══════════════════════════════════════════════════════════
# FACT-CHECK PROMPT
# ══════════════════════════════════════════════════════════

FACTCHECK_PROMPT = """You are fact-checking claims from Twitter/X about a geopolitical topic.
You also have access to full article text scraped from the URLs cited in tweets.

For each claim, assign a verification status based on the speaker type, evidence,
and whether the full article text corroborates it.

VERIFICATION RULES:
- Official government account + specific verifiable event = REPORTED
  (not VERIFIED unless independently confirmed by another source)
- Journalist from major outlet (Reuters/AP/BBC/AFP) = REPORTED
- Multiple independent sources (different outlets, not retweets) confirming = VERIFIED
- Full article text from official source corroborates tweet = VERIFIED
- Sources giving conflicting accounts = DISPUTED
- Viral claim from general user with no corroboration = UNVERIFIED
- Analyst interpretation/prediction = REPORTED (it's expert opinion, not fact)

Return the same JSON array with these ADDED fields:
"verdict": "verified|reported|disputed|unverified",
"reasoning": "2-3 sentences explaining why this verdict, citing specific evidence",
"credibility_weight": 1-5 (5 = most credible),
"needs_verification": true/false (flag claims that should be checked against official sources),
"corroborating_sources": ["list of other sources that support this claim"]

Return ONLY valid JSON array."""


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def twitter_intel(topic: str) -> dict:
    console.print(f"\n[bold red]--- TWITTER / X INTELLIGENCE ---[/]\n")
    console.print(f"  Topic: [bold]{topic}[/]\n")

    searches = build_twitter_searches(topic)

    # ── Phase 1: Multi-angle Tavily searches ──
    console.print("  [bold]Phase 1: Twitter search discovery[/]\n")
    twitter_data = []
    all_cited_urls = []

    for i, s in enumerate(searches, 1):
        console.print(f"  [{i}/{len(searches)}] {s['angle']}...")
        try:
            result = perplexity_search(s["query"], system=s["system"])
            citations = result.get("citations", [])
            twitter_data.append({
                "angle": s["angle"],
                "results": result["text"],
                "citations": citations,
                "tavily_results": result.get("results", []),
            })
            all_cited_urls.extend(citations)
        except Exception as e:
            console.print(f"    [red]! Failed: {e}[/]")
            twitter_data.append({
                "angle": s["angle"],
                "results": f"Search failed: {e}",
                "citations": [],
                "tavily_results": [],
            })
        time.sleep(1)

    unique_urls = list(set(all_cited_urls))
    console.print(f"\n  Found [bold]{len(unique_urls)}[/] unique cited URLs\n")

    # ── Phase 2: Scrape full content from cited URLs ──
    console.print("  [bold]Phase 2: Scrapling deep content from cited URLs[/]\n")

    # Filter out x.com/twitter.com URLs (can't scrape those)
    scrapeable_urls = [u for u in unique_urls if "x.com" not in u and "twitter.com" not in u]
    scraped_content = scrape_urls(scrapeable_urls[:20], max_workers=5, label="Cited articles")
    scraped_text = build_content_block(scraped_content)

    total_words = sum(r.get("word_count", 0) for r in scraped_content)
    console.print(f"  Scraped {len(scraped_content)} articles ({total_words:,} words)\n")

    # ── Phase 3: Extract structured claims with full context ──
    console.print("  [bold]Phase 3: Extracting claims (with full article context)[/]\n")

    raw_text = "\n\n".join([
        f"=== {d['angle']} ===\n{d['results']}"
        for d in twitter_data
    ])

    # Include Tavily raw content
    for d in twitter_data:
        for tr in d.get("tavily_results", []):
            if tr.get("raw_content") and len(tr["raw_content"]) > 200:
                raw_text += f"\n\n=== Full content: {tr['title']} ===\n{tr['raw_content'][:3000]}"

    # Add scraped full text
    if scraped_text:
        raw_text += f"\n\n=== SCRAPED FULL ARTICLE TEXT ===\n{scraped_text}"

    # Cap to avoid token limits
    if len(raw_text) > 80000:
        raw_text = raw_text[:80000] + "\n\n[Text truncated at 80k chars]"

    try:
        claims = claude(
            system=EXTRACT_PROMPT,
            user=f"TOPIC: {topic}\n\nTWITTER DATA + FULL ARTICLE TEXT:\n{raw_text}",
            json_mode=True,
            max_tokens=16384,
        )
    except Exception as e:
        console.print(f"  [red]! Claim extraction failed: {e}[/]")
        claims = []

    if not isinstance(claims, list):
        claims = []

    console.print(f"  Found [bold]{len(claims)}[/] claims\n")

    # ── Phase 4: Fact-check in batches ──
    console.print(f"  [bold]Phase 4: Fact-checking {len(claims)} claims[/]\n")

    checked_claims = []
    batch_size = 8

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
            console.print(f"    [red]! Batch failed: {e}[/]")
            for c in batch:
                c["verdict"] = "unverified"
                c["reasoning"] = "Fact-check failed"
                c["credibility_weight"] = 1
                c["needs_verification"] = True
            checked_claims.extend(batch)

        time.sleep(0.5)

    # ── Compile output ──
    all_citations = list(set(all_cited_urls))

    verdict_counts = {}
    for c in checked_claims:
        v = c.get("verdict", "unverified")
        verdict_counts[v] = verdict_counts.get(v, 0) + 1

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
        "scraping_stats": {
            "urls_found": len(unique_urls),
            "pages_scraped": len(scraped_content),
            "words_scraped": total_words,
        },
        "scraped_articles": [
            {"title": r.get("title", ""), "url": r.get("url", ""), "word_count": r.get("word_count", 0)}
            for r in scraped_content
        ],
    }

    # ── Print summary ──
    console.print()
    table = Table(title="Twitter Intelligence Summary")
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Total claims", str(len(checked_claims)))
    for v, count in sorted(verdict_counts.items()):
        emoji = VERDICT_EMOJI.get(v, "?")
        color = {"verified": "green", "reported": "blue",
                 "disputed": "yellow", "unverified": "red"}.get(v, "white")
        table.add_row(f"{emoji} [{color}]{v.upper()}[/]", str(count))
    table.add_row("", "")
    for st, count in sorted(speaker_counts.items()):
        table.add_row(f"  {st}", str(count))
    table.add_row("", "")
    table.add_row("Unique source URLs", str(len(all_citations)))
    table.add_row("Articles scraped", str(len(scraped_content)))
    table.add_row("Words scraped", f"{total_words:,}")
    table.add_row("Need verification", str(len(output["needs_verification"])))
    console.print(table)

    # Flag high-priority unverified claims
    flagged = [c for c in checked_claims if c.get("verdict") in ("disputed", "unverified")
               and c.get("engagement") == "high"]
    if flagged:
        console.print(f"\n  [bold red]! HIGH-ENGAGEMENT UNVERIFIED CLAIMS:[/]")
        for f_ in flagged:
            console.print(f"    >> {f_['claim'][:90]}")
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
    console.print(f"  Saved: {out}/twitter_intel.json\n")

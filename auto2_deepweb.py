"""
AUTOMATION 2 — DEEP WEB RESEARCH (EXPANDED + SCRAPLING)
Searches across government, intl orgs, think tanks, news wires.
Then SCRAPES full article content from every discovered URL.
Feeds bulk full-text evidence into synthesis for maximum detail.

Usage: python auto2_deepweb.py "India-China LAC standoff 2026"
       Or imported by pipeline.py
"""

import json, time, sys
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.table import Table
from core.gemini import gemini_search
from core.perplexity import perplexity_search
from core.claude import claude
from core.scraper import scrape_urls, build_content_block

console = Console()

# ══════════════════════════════════════════════════════════
# SOURCE REGISTRY — Every institutional domain, categorized
# ══════════════════════════════════════════════════════════

SOURCES = {

    # ── FOREIGN MINISTRIES & HEADS OF STATE ──
    "govt_india": {
        "label": "India (MEA, PMO, PIB)",
        "domains": "site:mea.gov.in OR site:pmindia.gov.in OR site:pib.gov.in",
        "tier": "PRIMARY",
    },
    "govt_china": {
        "label": "China (MFA, State Council)",
        "domains": "site:fmprc.gov.cn OR site:english.gov.cn OR site:xinhuanet.com",
        "tier": "PRIMARY",
    },
    "govt_us": {
        "label": "United States (State Dept, White House, DoD)",
        "domains": "site:state.gov OR site:whitehouse.gov OR site:defense.gov",
        "tier": "PRIMARY",
    },
    "govt_russia": {
        "label": "Russia (MFA, Kremlin)",
        "domains": "site:mid.ru OR site:kremlin.ru",
        "tier": "PRIMARY",
    },
    "govt_uk": {
        "label": "United Kingdom (FCDO, PM)",
        "domains": "site:gov.uk/government/organisations/foreign-commonwealth-development-office",
        "tier": "PRIMARY",
    },
    "govt_france": {
        "label": "France (Quai d'Orsay, Elysee)",
        "domains": "site:diplomatie.gouv.fr OR site:elysee.fr",
        "tier": "PRIMARY",
    },
    "govt_germany": {
        "label": "Germany (Auswaertiges Amt, Bundeskanzler)",
        "domains": "site:auswaertiges-amt.de OR site:bundeskanzler.de",
        "tier": "PRIMARY",
    },
    "govt_japan": {
        "label": "Japan (MOFA, PM)",
        "domains": "site:mofa.go.jp OR site:japan.kantei.go.jp",
        "tier": "PRIMARY",
    },

    # ── MULTILATERAL FORUMS ──
    "brics": {
        "label": "BRICS",
        "domains": "site:brics-russia.com OR site:brics2024.go.th OR site:brics-info.org",
        "tier": "PRIMARY",
    },
    "g7": {
        "label": "G7",
        "domains": "site:g7italy.it OR site:g7germany.de OR site:g7hiroshima.go.jp",
        "tier": "PRIMARY",
    },
    "g20": {
        "label": "G20",
        "domains": "site:g20.org OR site:g20.in OR site:g20brasil.org",
        "tier": "PRIMARY",
    },
    "sco": {
        "label": "SCO (Shanghai Cooperation Organisation)",
        "domains": "site:eng.sectsco.org OR site:sco-russia.ru",
        "tier": "PRIMARY",
    },
    "quad": {
        "label": "QUAD (US-India-Japan-Australia)",
        "domains": "",
        "tier": "PRIMARY",
    },
    "aukus": {
        "label": "AUKUS",
        "domains": "",
        "tier": "PRIMARY",
    },

    # ── INTERNATIONAL ORGANIZATIONS ──
    "un": {
        "label": "United Nations (GA, SC, Secretariat)",
        "domains": "site:un.org OR site:undocs.org OR site:press.un.org",
        "tier": "PRIMARY",
    },
    "nato": {
        "label": "NATO",
        "domains": "site:nato.int",
        "tier": "PRIMARY",
    },
    "eu": {
        "label": "European Union (EC, Council, EEAS)",
        "domains": "site:consilium.europa.eu OR site:ec.europa.eu OR site:eeas.europa.eu",
        "tier": "PRIMARY",
    },
    "asean": {
        "label": "ASEAN",
        "domains": "site:asean.org",
        "tier": "PRIMARY",
    },
    "au": {
        "label": "African Union",
        "domains": "site:au.int",
        "tier": "PRIMARY",
    },

    # ── COURTS & LEGAL ──
    "icj": {
        "label": "International Court of Justice",
        "domains": "site:icj-cij.org",
        "tier": "PRIMARY",
    },
    "icc": {
        "label": "International Criminal Court",
        "domains": "site:icc-cpi.int",
        "tier": "PRIMARY",
    },

    # ── ECONOMIC / FINANCIAL INSTITUTIONS ──
    "imf": {
        "label": "IMF",
        "domains": "site:imf.org",
        "tier": "PRIMARY",
    },
    "worldbank": {
        "label": "World Bank",
        "domains": "site:worldbank.org",
        "tier": "PRIMARY",
    },
    "wto": {
        "label": "WTO",
        "domains": "site:wto.org",
        "tier": "PRIMARY",
    },
    "oecd": {
        "label": "OECD",
        "domains": "site:oecd.org",
        "tier": "PRIMARY",
    },
    "adb": {
        "label": "Asian Development Bank",
        "domains": "site:adb.org",
        "tier": "PRIMARY",
    },
    "ndb": {
        "label": "New Development Bank (BRICS bank)",
        "domains": "site:ndb.int",
        "tier": "PRIMARY",
    },

    # ── THINK TANKS ──
    "think_tanks_us": {
        "label": "US Think Tanks",
        "domains": "site:brookings.edu OR site:csis.org OR site:carnegieendowment.org OR site:cfr.org OR site:rand.org",
        "tier": "RESEARCH",
    },
    "think_tanks_eu": {
        "label": "European Think Tanks",
        "domains": "site:chathamhouse.org OR site:iiss.org OR site:ecfr.eu OR site:swp-berlin.org",
        "tier": "RESEARCH",
    },
    "think_tanks_asia": {
        "label": "Asian Think Tanks",
        "domains": "site:orfonline.org OR site:idsa.in OR site:isas.nus.edu.sg OR site:rsis.edu.sg",
        "tier": "RESEARCH",
    },
    "sipri": {
        "label": "SIPRI (Arms/Conflict)",
        "domains": "site:sipri.org",
        "tier": "RESEARCH",
    },

    # ── NEWS WIRES ──
    "wires": {
        "label": "Wire Services",
        "domains": "site:reuters.com OR site:apnews.com OR site:france24.com",
        "tier": "JOURNALISM",
    },
    "broadcast": {
        "label": "Major Broadcasters",
        "domains": "site:bbc.com OR site:aljazeera.com OR site:dw.com",
        "tier": "JOURNALISM",
    },
    "india_media": {
        "label": "Indian Media",
        "domains": "site:thehindu.com OR site:indianexpress.com OR site:ndtv.com",
        "tier": "JOURNALISM",
    },
}


# ══════════════════════════════════════════════════════════
# SEARCH STRATEGY — Which sources to hit for which angle
# ══════════════════════════════════════════════════════════

def build_search_plan(topic: str) -> list:
    """Build a targeted search plan: Gemini for primary sources, Tavily for analysis."""

    plan = []

    # ── GEMINI SEARCHES (Google grounding -- best for .gov and .org domains) ──
    # 7 searches = well under Gemini's 20 req/day free limit

    govt_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k.startswith("govt_") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "Government foreign ministries",
        "query": f"{topic} ({govt_domains}) official statement press release",
    })

    forum_domains = []
    for key in ["brics", "g7", "g20", "sco"]:
        if SOURCES[key]["domains"]:
            forum_domains.append(SOURCES[key]["domains"])
    forums_str = " OR ".join(forum_domains)
    plan.append({
        "engine": "gemini",
        "label": "BRICS, G7, G20, SCO forums",
        "query": f"{topic} ({forums_str}) OR BRICS OR G7 OR G20 OR SCO "
                 f"summit communique declaration joint statement",
    })

    plan.append({
        "engine": "gemini",
        "label": "QUAD, AUKUS",
        "query": f"{topic} QUAD OR AUKUS statement meeting "
                 f"(site:state.gov OR site:mea.gov.in OR site:mofa.go.jp OR "
                 f"site:dfat.gov.au OR site:gov.uk)",
    })

    intl_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k in ("un", "nato", "eu", "asean", "au") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "UN, NATO, EU, ASEAN, African Union",
        "query": f"{topic} ({intl_domains}) resolution statement document",
    })

    plan.append({
        "engine": "gemini",
        "label": "ICJ, ICC (if relevant)",
        "query": f"{topic} (site:icj-cij.org OR site:icc-cpi.int) ruling order judgment",
    })

    econ_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k in ("imf", "worldbank", "wto", "oecd", "adb", "ndb") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "IMF, World Bank, WTO, OECD, ADB, NDB",
        "query": f"{topic} ({econ_domains}) report data outlook",
    })

    plan.append({
        "engine": "gemini",
        "label": "Summit documents & communiques",
        "query": f"{topic} summit communique declaration joint statement "
                 f"leaders outcome document 2025 2026",
    })

    # ── TAVILY SEARCHES (better for news, analysis, broader web) ──

    plan.append({
        "engine": "tavily",
        "label": "Wire services (Reuters, AP, AFP)",
        "query": f"{topic} Reuters OR AP OR AFP latest reporting",
    })

    plan.append({
        "engine": "tavily",
        "label": "US think tanks",
        "query": f"{topic} analysis Brookings OR CSIS OR Carnegie OR CFR OR RAND",
    })

    plan.append({
        "engine": "tavily",
        "label": "EU/Asia think tanks",
        "query": f"{topic} analysis Chatham House OR IISS OR ORF OR IDSA OR RSIS OR ECFR",
    })

    plan.append({
        "engine": "tavily",
        "label": "SIPRI + conflict/arms data",
        "query": f"{topic} SIPRI OR arms OR military OR conflict data",
    })

    plan.append({
        "engine": "tavily",
        "label": "Historical context & timeline",
        "query": f"{topic} background history context timeline chronology",
    })

    plan.append({
        "engine": "tavily",
        "label": "Counter-narratives & criticism",
        "query": f"{topic} criticism opposition disputed controversial counter-narrative",
    })

    plan.append({
        "engine": "tavily",
        "label": "Indian media coverage",
        "query": f"{topic} site:thehindu.com OR site:indianexpress.com OR site:ndtv.com",
    })

    return plan


# ══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ══════════════════════════════════════════════════════════

def deep_web_research(topic: str) -> dict:
    console.print(f"[bold blue]--- DEEP WEB RESEARCH (EXPANDED + SCRAPLING) ---[/]\n")
    console.print(f"  Topic: [bold]{topic}[/]\n")

    plan = build_search_plan(topic)

    # Show what we're searching
    table = Table(title="Search Plan", show_lines=False)
    table.add_column("#", style="dim", width=3)
    table.add_column("Engine", width=10)
    table.add_column("Source Category")
    for i, p in enumerate(plan, 1):
        engine_color = "cyan" if p["engine"] == "gemini" else "green"
        table.add_row(str(i), f"[{engine_color}]{p['engine']}[/]", p["label"])
    console.print(table)
    console.print()

    # ── Phase 1: Execute all searches ──
    console.print("  [bold]Phase 1: Search discovery[/]\n")
    all_results = []
    all_urls = []  # Collect every URL for scraping

    for i, p in enumerate(plan, 1):
        engine_icon = "[G]" if p["engine"] == "gemini" else "[T]"
        console.print(f"  [{i}/{len(plan)}] {engine_icon} {p['label']}...")

        try:
            if p["engine"] == "gemini":
                result = gemini_search(p["query"])
                urls = [s["url"] for s in result["sources"] if s.get("url")]
                all_results.append({
                    "label": p["label"],
                    "engine": "gemini",
                    "text": result["text"],
                    "sources": result["sources"],
                    "citations": urls,
                })
                all_urls.extend(urls)
            else:
                result = perplexity_search(p["query"])
                urls = result.get("citations", [])
                all_results.append({
                    "label": p["label"],
                    "engine": "tavily",
                    "text": result["text"],
                    "sources": [],
                    "citations": urls,
                    "tavily_results": result.get("results", []),
                })
                all_urls.extend(urls)
        except Exception as e:
            console.print(f"    [red]! Failed: {e}[/]")
            all_results.append({
                "label": p["label"],
                "engine": p["engine"],
                "text": f"Search failed: {e}",
                "sources": [],
                "citations": [],
            })

        time.sleep(1)

    # Deduplicate URLs
    unique_urls = list(set(all_urls))
    console.print(f"\n  Discovered [bold]{len(unique_urls)}[/] unique source URLs\n")

    # ── Phase 2: Deep content scraping with Scrapling ──
    console.print("  [bold]Phase 2: Scrapling deep content extraction[/]\n")

    # Separate URLs by tier for prioritized scraping
    govt_urls = [u for u in unique_urls if any(
        d in u for d in [".gov", ".mil", "un.org", "nato.int", "europa.eu",
                         "asean.org", "au.int", "icj-cij.org", "icc-cpi.int",
                         "imf.org", "worldbank.org", "wto.org", "oecd.org",
                         "adb.org", "ndb.int", "brics", "g20", "g7"]
    )]
    research_urls = [u for u in unique_urls if any(
        d in u for d in ["brookings.edu", "csis.org", "carnegie", "cfr.org",
                         "rand.org", "chathamhouse.org", "iiss.org", "sipri.org",
                         "orfonline.org", "idsa.in", "ecfr.eu", "swp-berlin.org"]
    )]
    news_urls = [u for u in unique_urls if u not in govt_urls and u not in research_urls]

    scraped_govt = scrape_urls(govt_urls, max_workers=5, label="Government/Intl Orgs")
    scraped_research = scrape_urls(research_urls, max_workers=5, label="Think Tanks/Research")
    scraped_news = scrape_urls(news_urls[:15], max_workers=5, label="News/Media")

    all_scraped = scraped_govt + scraped_research + scraped_news
    total_words = sum(r.get("word_count", 0) for r in all_scraped)
    console.print(f"\n  Total scraped: [bold]{len(all_scraped)}[/] pages, [bold]{total_words:,}[/] words\n")

    # ── Phase 3: Build comprehensive evidence package ──
    console.print("  [bold]Phase 3: Synthesizing all evidence[/]\n")

    # Build evidence blocks
    evidence_block = ""

    evidence_block += "\n\n### === PRIMARY SOURCES (Government / International Orgs) ===\n"
    for r in all_results:
        if r["engine"] == "gemini":
            evidence_block += f"\n--- {r['label']} ---\n{r['text']}\n"
            for s in r["sources"]:
                evidence_block += f"  Source: {s.get('title', '')} -- {s.get('url', '')}\n"

    evidence_block += "\n\n### === NEWS, ANALYSIS, THINK TANKS ===\n"
    for r in all_results:
        if r["engine"] == "tavily":
            evidence_block += f"\n--- {r['label']} ---\n{r['text']}\n"
            # Include Tavily raw content snippets
            for tr in r.get("tavily_results", []):
                if tr.get("raw_content") and len(tr["raw_content"]) > 200:
                    evidence_block += f"\n  [Full text from {tr['title']}]\n"
                    evidence_block += tr["raw_content"][:3000] + "\n"

    # Add scraped full-text content
    if scraped_govt:
        evidence_block += "\n\n### === SCRAPED: GOVERNMENT & INTL ORG FULL TEXT ===\n"
        evidence_block += build_content_block(scraped_govt)

    if scraped_research:
        evidence_block += "\n\n### === SCRAPED: THINK TANK & RESEARCH FULL TEXT ===\n"
        evidence_block += build_content_block(scraped_research)

    if scraped_news:
        evidence_block += "\n\n### === SCRAPED: NEWS & MEDIA FULL TEXT ===\n"
        evidence_block += build_content_block(scraped_news)

    # Collect ALL citations
    all_citations = list(set(all_urls))

    # Cap evidence to avoid token limits (~120k chars = ~30k tokens)
    if len(evidence_block) > 120000:
        evidence_block = evidence_block[:120000] + "\n\n[Evidence truncated at 120k chars]"

    console.print(f"  Evidence package: {len(evidence_block):,} chars from {len(all_citations)} sources\n")

    # ── Phase 4: LLM Synthesis with maximum detail ──
    console.print("  [bold]Phase 4: Deep synthesis (OpenRouter)[/]\n")

    research = claude(
        system="""You are a senior geopolitical analyst with access to FULL TEXT
articles from government websites, international organizations, wire services,
think tanks, and media outlets. You have been given the COMPLETE text of
scraped articles, not just snippets.

YOUR JOB: Extract EVERY piece of useful information. Do not summarize — be EXHAUSTIVE.

Given the full evidence package:

1. EXTRACT every single factual claim as a structured list.
   For each claim note:
   - claim text (be specific — include names, dates, numbers, quotes)
   - source_tier: PRIMARY (gov/UN/NATO/BRICS/G7/G20/EU/ASEAN/AU/courts/IMF/WB)
                   JOURNALISM (Reuters/AP/BBC/Al Jazeera)
                   RESEARCH (think tanks/SIPRI/academic)
   - source_name and URL
   - corroborated: true if multiple independent sources confirm
   - verdict: verified | reported | disputed | unverified
   - direct_quote: exact quote from source if available
   - date: when the event/statement occurred

2. BUILD an EXHAUSTIVE synthesis covering:
   - executive_summary (6-8 sentences, comprehensive)
   - background (historical context, 500+ words, with dates and specific events)
   - current_situation (what just happened, 800+ words, every detail)
   - key_actors: for EACH actor provide:
     * name and title
     * exact position stated (with direct quotes where available)
     * actions taken
     * underlying motivations (analysis)
     * source URLs
   - institutional_positions: EVERY official statement from BRICS/G7/G20/SCO/UN/NATO/EU
     with exact quotes from communiques and resolutions
   - timeline: COMPLETE chronological events with exact dates and sources
     (minimum 15 entries if data available)
   - economic_implications (trade figures, sanctions details, GDP impact, specific numbers)
   - military_security_implications (troop movements, defense spending, arms deals, exercises)
   - diplomatic_implications (treaties, agreements, diplomatic recalls, summits)
   - legal_dimensions (ICJ/ICC rulings, international law citations, treaty obligations)
   - regional_impact (how neighboring countries and regions are affected)
   - public_opinion (if available from scraped content — polls, protests, social media trends)
   - disputed_claims (what sources disagree on — list EACH contradiction with both sides)
   - unknowns (what is NOT yet established by evidence)
   - key_statistics: all numbers, percentages, financial figures mentioned
   - key_quotes: the most important direct quotes from officials and analysts

Return JSON:
{
  "claims": [{
    "claim": "...",
    "source_tier": "PRIMARY|JOURNALISM|RESEARCH",
    "source_name": "...",
    "source_url": "...",
    "corroborated": true/false,
    "verdict": "verified|reported|disputed|unverified",
    "direct_quote": "...",
    "date": "YYYY-MM-DD or approximate"
  }],
  "synthesis": {
    "executive_summary": "...",
    "background": "...",
    "current_situation": "...",
    "key_actors": "...",
    "institutional_positions": "...",
    "timeline": "...",
    "economic_implications": "...",
    "military_security_implications": "...",
    "diplomatic_implications": "...",
    "legal_dimensions": "...",
    "regional_impact": "...",
    "public_opinion": "...",
    "disputed_claims": "...",
    "unknowns": "...",
    "key_statistics": "...",
    "key_quotes": "..."
  },
  "all_sources": [{"title": "...", "url": "...", "tier": "...", "institution": "...", "word_count": N}],
  "institutions_searched": ["..."],
  "scraping_stats": {"pages_scraped": N, "total_words": N, "govt_pages": N, "research_pages": N, "news_pages": N}
}""",
        user=f"TOPIC: {topic}\n\nALL EVIDENCE (search results + full scraped articles):\n{evidence_block}",
        json_mode=True,
        max_tokens=16384,
    )

    research["topic"] = topic
    research["source"] = "deep_web"
    research["raw_citations"] = all_citations
    research["scraping_stats"] = {
        "pages_scraped": len(all_scraped),
        "total_words": total_words,
        "govt_pages": len(scraped_govt),
        "research_pages": len(scraped_research),
        "news_pages": len(scraped_news),
    }

    # Summary stats
    verdicts = [c["verdict"] for c in research.get("claims", [])]
    research["summary"] = {
        "total_claims": len(verdicts),
        "verified": verdicts.count("verified"),
        "reported": verdicts.count("reported"),
        "disputed": verdicts.count("disputed"),
        "unverified": verdicts.count("unverified"),
        "total_sources": len(all_citations),
        "search_batches": len(all_results),
        "pages_scraped": len(all_scraped),
        "words_scraped": total_words,
    }

    # Print summary
    console.print(f"  [bold green]Research complete[/]\n")

    summary_table = Table(title="Research Summary")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")
    summary_table.add_row("Total claims extracted", str(research["summary"]["total_claims"]))
    summary_table.add_row("[green]Verified[/]", str(research["summary"]["verified"]))
    summary_table.add_row("[blue]Reported[/]", str(research["summary"]["reported"]))
    summary_table.add_row("[yellow]Disputed[/]", str(research["summary"]["disputed"]))
    summary_table.add_row("[red]Unverified[/]", str(research["summary"]["unverified"]))
    summary_table.add_row("", "")
    summary_table.add_row("Unique source URLs", str(research["summary"]["total_sources"]))
    summary_table.add_row("Pages scraped", str(research["summary"]["pages_scraped"]))
    summary_table.add_row("Words scraped", f"{research['summary']['words_scraped']:,}")
    summary_table.add_row("Search batches", str(research["summary"]["search_batches"]))
    console.print(summary_table)

    if research.get("institutions_searched"):
        console.print(f"\n  Institutions with relevant data:")
        for inst in research["institutions_searched"]:
            console.print(f"     > {inst}")

    console.print()
    return research


# ── Standalone run ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python auto2_deepweb.py \"topic\"[/]")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    result = deep_web_research(topic)

    slug = topic.lower().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out = Path("output") / f"{date}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "deep_research.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(f"  Saved: {out}/deep_research.json\n")

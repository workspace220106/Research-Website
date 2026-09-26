"""
AUTOMATION 2 — DEEP WEB RESEARCH (EXPANDED)
Searches across:
  - Government foreign ministries (India, China, US, Russia, UK, France, Germany, Japan)
  - International orgs: UN, NATO, EU, ASEAN, AU
  - Multilateral forums: BRICS, G7, G20, SCO, QUAD, AUKUS
  - Courts: ICJ, ICC
  - Economic: IMF, World Bank, WTO, OECD, ADB, NDB
  - Think tanks: SIPRI, IISS, Brookings, Carnegie, CSIS, CFR, Chatham House
  - News wires: Reuters, AP, AFP, BBC, Al Jazeera
  - Conference/summit documents

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
        "label": "France (Quai d'Orsay, Élysée)",
        "domains": "site:diplomatie.gouv.fr OR site:elysee.fr",
        "tier": "PRIMARY",
    },
    "govt_germany": {
        "label": "Germany (Auswärtiges Amt, Bundeskanzler)",
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
        "note": "BRICS presidency rotates — domain changes yearly. Also search by name.",
    },
    "g7": {
        "label": "G7",
        "domains": "site:g7italy.it OR site:g7germany.de OR site:g7hiroshima.go.jp",
        "tier": "PRIMARY",
        "note": "G7 presidency rotates. 2025: Canada. Search 'G7 summit communique' as fallback.",
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
        "domains": "",  # No single site — search across member govt sites
        "tier": "PRIMARY",
        "note": "QUAD has no official website. Search member foreign ministries + 'Quad'.",
    },
    "aukus": {
        "label": "AUKUS",
        "domains": "",  # No single site
        "tier": "PRIMARY",
        "note": "Search US/UK/Australia defense departments + 'AUKUS'.",
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

    # ── GEMINI SEARCHES (Google grounding — best for .gov and .org domains) ──
    # 7 searches = well under Gemini's 20 req/day free limit

    # 1. Government foreign ministries
    govt_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k.startswith("govt_") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "Government foreign ministries",
        "query": f"{topic} ({govt_domains}) official statement press release",
    })

    # 2. BRICS + G7 + G20 + SCO + QUAD
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

    # 3. QUAD + AUKUS (no official sites — search by name across govt sites)
    plan.append({
        "engine": "gemini",
        "label": "QUAD, AUKUS",
        "query": f"{topic} QUAD OR AUKUS statement meeting "
                 f"(site:state.gov OR site:mea.gov.in OR site:mofa.go.jp OR "
                 f"site:dfat.gov.au OR site:gov.uk)",
    })

    # 4. UN + NATO + EU + ASEAN + African Union
    intl_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k in ("un", "nato", "eu", "asean", "au") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "UN, NATO, EU, ASEAN, African Union",
        "query": f"{topic} ({intl_domains}) resolution statement document",
    })

    # 5. International courts
    plan.append({
        "engine": "gemini",
        "label": "ICJ, ICC (if relevant)",
        "query": f"{topic} (site:icj-cij.org OR site:icc-cpi.int) ruling order judgment",
    })

    # 6. Economic institutions
    econ_domains = " OR ".join([
        v["domains"] for k, v in SOURCES.items()
        if k in ("imf", "worldbank", "wto", "oecd", "adb", "ndb") and v["domains"]
    ])
    plan.append({
        "engine": "gemini",
        "label": "IMF, World Bank, WTO, OECD, ADB, NDB",
        "query": f"{topic} ({econ_domains}) report data outlook",
    })

    # 7. Summit / conference documents (catch-all for rotating presidencies)
    plan.append({
        "engine": "gemini",
        "label": "Summit documents & communiqués",
        "query": f"{topic} summit communique declaration joint statement "
                 f"leaders outcome document 2025 2026",
    })

    # ── TAVILY SEARCHES (better for news, analysis, broader web) ──

    # 8. Wire services
    plan.append({
        "engine": "tavily",
        "label": "Wire services (Reuters, AP, AFP)",
        "query": f"{topic} Reuters OR AP OR AFP latest reporting",
    })

    # 9. Think tanks — US
    plan.append({
        "engine": "tavily",
        "label": "US think tanks",
        "query": f"{topic} analysis Brookings OR CSIS OR Carnegie OR CFR OR RAND",
    })

    # 10. Think tanks — Europe + Asia
    plan.append({
        "engine": "tavily",
        "label": "EU/Asia think tanks",
        "query": f"{topic} analysis Chatham House OR IISS OR ORF OR IDSA OR RSIS OR ECFR",
    })

    # 11. SIPRI + conflict-specific
    plan.append({
        "engine": "tavily",
        "label": "SIPRI + conflict/arms data",
        "query": f"{topic} SIPRI OR arms OR military OR conflict data",
    })

    # 12. Historical context + timeline
    plan.append({
        "engine": "tavily",
        "label": "Historical context & timeline",
        "query": f"{topic} background history context timeline chronology",
    })

    # 13. Counter-narratives + criticism
    plan.append({
        "engine": "tavily",
        "label": "Counter-narratives & criticism",
        "query": f"{topic} criticism opposition disputed controversial counter-narrative",
    })

    # 14. Indian media specifically
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
    console.print(f"[bold blue]━━━ DEEP WEB RESEARCH (EXPANDED) ━━━[/]\n")
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

    # ── Execute all searches ──
    all_results = []

    for i, p in enumerate(plan, 1):
        console.print(
            f"  [{i}/{len(plan)}] "
            f"{'🌐' if p['engine'] == 'gemini' else '🔍'} "
            f"{p['label']}..."
        )

        try:
            if p["engine"] == "gemini":
                result = gemini_search(p["query"])
                all_results.append({
                    "label": p["label"],
                    "engine": "gemini",
                    "text": result["text"],
                    "sources": result["sources"],
                    "citations": [s["url"] for s in result["sources"] if s.get("url")],
                })
            else:
                result = perplexity_search(p["query"])
                all_results.append({
                    "label": p["label"],
                    "engine": "tavily",
                    "text": result["text"],
                    "sources": [],
                    "citations": result["citations"] if isinstance(result["citations"], list) else [],
                })
        except Exception as e:
            console.print(f"    [red]⚠ Failed: {e}[/]")
            all_results.append({
                "label": p["label"],
                "engine": p["engine"],
                "text": f"Search failed: {e}",
                "sources": [],
                "citations": [],
            })

        time.sleep(1)  # Rate limit

    # ── Compile all evidence ──
    console.print(f"\n  🧠 OpenRouter: Synthesizing {len(all_results)} source batches...\n")

    evidence_block = ""

    evidence_block += "\n\n### === PRIMARY SOURCES (Government / International Orgs) ===\n"
    for r in all_results:
        if r["engine"] == "gemini":
            evidence_block += f"\n--- {r['label']} ---\n{r['text']}\n"
            for s in r["sources"]:
                evidence_block += f"  📎 {s.get('title', '')} — {s.get('url', '')}\n"

    evidence_block += "\n\n### === NEWS, ANALYSIS, THINK TANKS ===\n"
    for r in all_results:
        if r["engine"] == "tavily":
            evidence_block += f"\n--- {r['label']} ---\n{r['text']}\n"

    # Collect ALL citations
    all_citations = []
    for r in all_results:
        all_citations.extend(r["citations"])
    all_citations = list(set(all_citations))

    # ── Gemini: Structured synthesis + claim extraction ──
    research = claude(
        system="""You are a senior geopolitical analyst with access to
primary government sources, international organization documents,
wire services, and think tank analysis.

Given raw search results from multiple institutional sources:

1. EXTRACT every factual claim as a structured list.
   For each claim note:
   - claim text
   - source_tier: PRIMARY (gov/UN/NATO/BRICS/G7/G20/EU/ASEAN/AU/courts/IMF/WB)
                   JOURNALISM (Reuters/AP/BBC/Al Jazeera)
                   RESEARCH (think tanks/SIPRI/academic)
   - source_name and URL
   - corroborated: true if multiple independent sources confirm
   - verdict: verified | reported | disputed | unverified

2. BUILD a comprehensive synthesis:
   - executive_summary (4-5 sentences)
   - background (historical context, 200 words)
   - current_situation (what just happened, 300 words)
   - key_actors (each actor's position with source)
   - institutional_positions (what BRICS/G7/G20/SCO/UN/NATO/EU officially said)
   - timeline (chronological events with dates)
   - economic_implications
   - military_security_implications
   - diplomatic_implications
   - disputed_claims (what sources disagree on)
   - unknowns (what is NOT yet established by evidence)

Return JSON:
{
  "claims": [{
    "claim": "...",
    "source_tier": "PRIMARY|JOURNALISM|RESEARCH",
    "source_name": "...",
    "source_url": "...",
    "corroborated": true/false,
    "verdict": "verified|reported|disputed|unverified"
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
    "disputed_claims": "...",
    "unknowns": "..."
  },
  "all_sources": [{"title": "...", "url": "...", "tier": "...", "institution": "..."}],
  "institutions_searched": ["list of institutions that returned relevant results"]
}""",
        user=f"TOPIC: {topic}\n\nALL EVIDENCE:\n{evidence_block}",
        json_mode=True
    )

    research["topic"] = topic
    research["source"] = "deep_web"
    research["raw_citations"] = all_citations

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
    }

    # Print summary
    console.print(f"  [bold green]✅ Research complete[/]\n")

    summary_table = Table(title="Research Summary")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Value", justify="right")
    summary_table.add_row("Total claims extracted", str(research["summary"]["total_claims"]))
    summary_table.add_row("[green]Verified[/]", str(research["summary"]["verified"]))
    summary_table.add_row("[blue]Reported[/]", str(research["summary"]["reported"]))
    summary_table.add_row("[yellow]Disputed[/]", str(research["summary"]["disputed"]))
    summary_table.add_row("[red]Unverified[/]", str(research["summary"]["unverified"]))
    summary_table.add_row("Total unique sources", str(research["summary"]["total_sources"]))
    summary_table.add_row("Institutions searched", str(research["summary"]["search_batches"]))
    console.print(summary_table)

    # Show which institutions returned data
    if research.get("institutions_searched"):
        console.print(f"\n  📋 Institutions with relevant data:")
        for inst in research["institutions_searched"]:
            console.print(f"     ✓ {inst}")

    console.print()
    return research


# ── Standalone run ──
if __name__ == "__main__":
    if len(sys.argv) < 2:
        console.print("[red]Usage: python auto2_deepweb.py \"topic\"[/]")
        sys.exit(1)

    topic = " ".join(sys.argv[1:])
    result = deep_web_research(topic)

    # Save output
    slug = topic.lower().replace(" ", "-")[:40]
    date = datetime.now().strftime("%Y-%m-%d")
    out = Path("output") / f"{date}_{slug}"
    out.mkdir(parents=True, exist_ok=True)
    (out / "deep_research.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    console.print(f"  💾 Saved: {out}/deep_research.json\n")

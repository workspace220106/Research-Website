# GeoResearch Pipeline

One command → Twitter intel + deep web research + cross-reference audit + YouTube script + IEEE LaTeX paper.

## Setup (10 minutes)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up API keys
cp .env.example .env
# Edit .env and paste your keys

# 3. (Optional) Install LaTeX for PDF compilation
# Linux:
sudo apt install texlive-full
# Mac:
brew install --cask mactex
# Or skip this and upload .tex to Overleaf manually
```

## API Keys Needed

| Service | Cost | Get from |
|---------|------|----------|
| Claude (Anthropic) | Pay per use (~$0.50/run) | console.anthropic.com |
| Perplexity | Min $5 credit (~$0.30/run) | perplexity.ai/settings/api |
| Google Gemini | Free tier available | aistudio.google.com/apikey |
| OpenAI GPT-4o | Pay per use (~$0.15/run) | platform.openai.com/api-keys |

Total cost per full research run: ~$1.20

## Usage

### Full pipeline (all 4 automations)
```bash
python pipeline.py "India-China LAC standoff September 2026"
```

### Individual automations
```bash
python pipeline.py --twitter "BRICS summit reactions"
python pipeline.py --research "NATO expansion implications"
```

### Standalone files
```bash
python auto1_twitter.py "topic"
python auto2_deepweb.py "topic"
```

## What Each Automation Does

### Automation 1 — Twitter Intelligence
- **LLMs:** Perplexity sonar-pro + Claude Sonnet
- Searches X/Twitter for official statements, journalist reports, analyst commentary, viral claims
- Classifies speakers (official / journalist / analyst / general user)
- Fact-checks each claim
- Output: `twitter_intel.json`

### Automation 2 — Deep Web Research
- **LLMs:** Gemini 2.5 Flash (Google grounding) + Perplexity + Claude
- Searches 30+ institutional domains: government foreign ministries, BRICS, G7, G20, SCO, QUAD, UN, NATO, EU, ASEAN, AU, ICJ, ICC, IMF, World Bank, WTO, OECD, think tanks
- Source-tiered: PRIMARY → JOURNALISM → RESEARCH → SOCIAL
- Output: `deep_research.json`

### Automation 3 — Merge, Audit, Build
- **LLMs:** Claude Sonnet + GPT-4o
- Cross-references Twitter claims against official sources
- Flags contradictions, Twitter-only claims, overlooked official info
- Builds: research paper draft + YouTube script + audit report
- Output: `audit.md`, `paper_draft.md`, `script.md`

### Automation 4 — IEEE LaTeX Paper
- **LLMs:** Claude Sonnet
- Converts paper to IEEE conference format LaTeX
- Generates BibTeX references
- Compiles PDF (or provides files for Overleaf)
- Output: `paper.tex`, `refs.bib`, `paper.pdf`

## Output Structure

```
output/2026-09-25_india-china-lac-standoff/
├── twitter_intel.json     — Twitter claims + fact-check verdicts
├── deep_research.json     — Institutional research + sources
├── audit.md               — Cross-reference audit report
├── paper_draft.md         — Research paper (Markdown)
├── script.md              — YouTube script with citations
├── paper.tex              — IEEE format LaTeX
├── refs.bib               — BibTeX references
└── paper.pdf              — Compiled PDF
```

## Institutions Searched (Automation 2)

**Governments:** India (MEA, PMO, PIB), China (MFA), US (State, WH, DoD), Russia (MID, Kremlin), UK (FCDO), France, Germany, Japan

**Forums:** BRICS, G7, G20, SCO, QUAD, AUKUS

**International Orgs:** UN (GA, SC, press), NATO, EU (Council, Commission, EEAS), ASEAN, African Union

**Courts:** ICJ, ICC

**Economic:** IMF, World Bank, WTO, OECD, ADB, NDB (BRICS bank)

**Think Tanks:** Brookings, CSIS, Carnegie, CFR, RAND, Chatham House, IISS, ECFR, SWP Berlin, ORF, IDSA, ISAS, RSIS, SIPRI

**News:** Reuters, AP, AFP, BBC, Al Jazeera, DW, The Hindu, Indian Express, NDTV

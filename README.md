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
| Google Gemini 3.6 Flash | Free tier | aistudio.google.com/apikey |
| Tavily | Free (1K searches/mo) | app.tavily.com |
| Groq | Free tier | console.groq.com |
| OpenAI *(optional)* | Pay per use | platform.openai.com/api-keys |

Total cost per full research run: **Free** (within free-tier limits)

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
- **LLMs:** Tavily search + Gemini 3.6 Flash
- Searches X/Twitter for official statements, journalist reports, analyst commentary, viral claims
- Classifies speakers (official / journalist / analyst / general user)
- Fact-checks each claim
- Output: `twitter_intel.json`

### Automation 2 — Deep Web Research
- **LLMs:** Gemini 3.6 Flash (Google grounding) + Tavily + Gemini 3.6 Flash
- Searches 30+ institutional domains: government foreign ministries, BRICS, G7, G20, SCO, QUAD, UN, NATO, EU, ASEAN, AU, ICJ, ICC, IMF, World Bank, WTO, OECD, think tanks
- Source-tiered: PRIMARY → JOURNALISM → RESEARCH → SOCIAL
- Output: `deep_research.json`

### Automation 3 — Merge, Audit, Build
- **LLMs:** Gemini 3.6 Flash + GPT-4.1 / Groq Llama 3.3
- Cross-references Twitter claims against official sources
- Flags contradictions, Twitter-only claims, overlooked official info
- Builds: research paper draft + YouTube script + audit report
- Output: `audit.md`, `paper_draft.md`, `script.md`

### Automation 4 — IEEE LaTeX Paper
- **LLMs:** Gemini 3.6 Flash
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

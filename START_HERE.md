# GeoResearch Studio

A local frontend for the research pipeline in the supplied archive. It uses Literata for headings, Source Sans 3 for interface text, and JetBrains Mono for technical details. The palette is off-white, white, and black.

## Start on Windows

1. Install Python 3.10 or newer if needed.
2. In this folder, run `pip install -r requirements.txt` once.
3. Double-click `start.bat`, then open **http://127.0.0.1:8765** in your browser.
4. In **Settings**, enter your Anthropic, Perplexity, Google, and OpenAI API keys. The app saves them locally in `.env` and does not display them again.
5. Return to **New research**, enter a topic, and choose the type of run.

On macOS or Linux, use `python3 server.py` instead of `start.bat` after installing the requirements.

The app runs on `127.0.0.1` only. Each run gets its own folder under `runs/`, so later runs do not overwrite earlier work. Results can be previewed or downloaded from **Past research**. Complete runs make a YouTube script, audit, research draft, LaTeX paper, and a PDF when LaTeX is installed.

Research calls paid or metered API services. The original archive's cost estimate is approximate and may be outdated. The frontend itself does not call those services until you start a research run.

The supplied pipeline scripts and their original `README.md` are included unchanged. The only added runtime components are `server.py`, `static/`, and `start.bat`.

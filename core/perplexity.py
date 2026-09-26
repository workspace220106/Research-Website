"""
Tavily search wrapper (replaces Perplexity API).
Used for: Twitter/X search, news search, think tank search, general web search.
Same perplexity_search() function signature so the rest of the pipeline is unchanged.
Free tier: 1,000 searches/month.
"""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
TAVILY_URL = "https://api.tavily.com/search"


def perplexity_search(
    query: str,
    system: str = "",
    model: str = "sonar-pro",
) -> dict:
    """
    Search via Tavily (drop-in replacement for Perplexity).
    Returns: {"text": "...", "citations": [...], "results": [...]}
    The `model` param is kept for signature compatibility but unused.
    """
    payload = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "include_raw_content": True,
        "max_results": 10,
    }

    resp = httpx.post(TAVILY_URL, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    answer = data.get("answer", "")
    results = data.get("results", [])
    citations = [r["url"] for r in results if r.get("url")]

    # Build enriched results with raw content
    enriched = []
    for r in results:
        enriched.append({
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "content": r.get("content", ""),
            "raw_content": r.get("raw_content", ""),
            "score": r.get("score", 0),
        })

    if not answer and results:
        answer = "\n\n".join(
            f"{r.get('title', '')}: {r.get('content', '')}"
            for r in results
        )

    return {
        "text": answer,
        "citations": citations,
        "results": enriched,
    }

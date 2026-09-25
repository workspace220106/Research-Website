"""
Gemini API wrapper with Google Search grounding.
Used for: government websites, UN, NATO, EU, BRICS, G7, G20, conference docs.
Google grounding hits .gov and .org domains that Perplexity often misses.
"""

from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))


def gemini_search(
    query: str,
    model: str = "gemini-2.5-flash",
) -> dict:
    """
    Gemini with Google Search grounding.
    Returns: {"text": "...", "sources": [{"title": "...", "url": "..."}]}
    """
    try:
        resp = client.models.generate_content(
            model=model,
            contents=query,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                system_instruction=(
                    "You are a geopolitical research engine. "
                    "Search government websites, UN, NATO, EU, BRICS, G7, G20, "
                    "SCO, ASEAN, African Union, IMF, World Bank, think tanks, "
                    "and academic sources. "
                    "Always cite exact URLs for every factual statement. "
                    "Prioritize official primary sources over news. "
                    "Separate verified facts from interpretation. "
                    "If a source is a government press release or official "
                    "communiqué, explicitly note that."
                ),
            ),
        )

        # Extract grounding metadata (source URLs)
        sources = []
        candidate = resp.candidates[0] if resp.candidates else None

        if candidate and candidate.grounding_metadata:
            gm = candidate.grounding_metadata

            # Extract from grounding_chunks
            if hasattr(gm, "grounding_chunks") and gm.grounding_chunks:
                for chunk in gm.grounding_chunks:
                    if hasattr(chunk, "web") and chunk.web:
                        sources.append({
                            "title": getattr(chunk.web, "title", ""),
                            "url": getattr(chunk.web, "uri", ""),
                        })

            # Also extract from grounding_supports if available
            if hasattr(gm, "grounding_supports") and gm.grounding_supports:
                for support in gm.grounding_supports:
                    if hasattr(support, "grounding_chunk_indices"):
                        pass  # Already captured via grounding_chunks

        return {
            "text": resp.text if resp.text else "",
            "sources": sources,
        }

    except Exception as e:
        return {
            "text": f"Gemini search failed: {e}",
            "sources": [],
        }

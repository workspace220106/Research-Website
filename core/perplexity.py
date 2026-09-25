"""
Perplexity API wrapper.
Used for: Twitter/X search, news search, think tank search, general web search.
Uses OpenAI-compatible API.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

pplx = OpenAI(
    api_key=os.getenv("PERPLEXITY_API_KEY"),
    base_url="https://api.perplexity.ai",
)


def perplexity_search(
    query: str,
    system: str = "",
    model: str = "sonar-pro",
) -> dict:
    """
    Search via Perplexity sonar-pro.
    Returns: {"text": "...", "citations": [...]}
    """
    if not system:
        system = (
            "You are a geopolitical research assistant. "
            "Return detailed findings with specific sources, "
            "publisher names, and URLs. "
            "Prioritize primary sources and wire services."
        )

    resp = pplx.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": query},
        ],
    )

    choice = resp.choices[0].message
    citations = getattr(resp, "citations", [])

    return {
        "text": choice.content,
        "citations": citations if isinstance(citations, list) else [],
    }

"""
GPT / Groq wrapper.
Used for: YouTube script generation (better conversational tone).
Uses OpenAI if OPENAI_API_KEY is set, otherwise falls back to Groq (free).
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

_openai_key = os.getenv("OPENAI_API_KEY", "")
_groq_key = os.getenv("GROQ_API_KEY", "")

if _openai_key:
    client = OpenAI(api_key=_openai_key)
    _default_model = "gpt-4.1"
elif _groq_key:
    client = OpenAI(
        api_key=_groq_key,
        base_url="https://api.groq.com/openai/v1",
    )
    _default_model = "llama-3.3-70b-versatile"
else:
    client = None
    _default_model = "gpt-4.1"


def gpt(
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Single GPT/Groq call. Returns text. Auto-detects backend."""
    if client is None:
        raise RuntimeError(
            "No OPENAI_API_KEY or GROQ_API_KEY found. "
            "Set at least one in your .env file."
        )

    resp = client.chat.completions.create(
        model=model or _default_model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content

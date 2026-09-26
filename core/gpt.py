"""
NVIDIA NIM wrapper.
Used for: YouTube script generation (better conversational tone).
Uses NVIDIA NIM free API (OpenAI-compatible) with Llama 3.3 70B.
Falls back to Groq if no NVIDIA key.
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

_nvidia_key = os.getenv("NVIDIA_API_KEY", "")
_groq_key = os.getenv("GROQ_API_KEY", "")

if _nvidia_key:
    client = OpenAI(
        api_key=_nvidia_key,
        base_url="https://integrate.api.nvidia.com/v1",
    )
    _default_model = "meta/llama-3.3-70b-instruct"
elif _groq_key:
    client = OpenAI(
        api_key=_groq_key,
        base_url="https://api.groq.com/openai/v1",
    )
    _default_model = "llama-3.3-70b-versatile"
else:
    client = None
    _default_model = "meta/llama-3.3-70b-instruct"


def gpt(
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 4096,
) -> str:
    """Single NVIDIA NIM / Groq call. Returns text."""
    if client is None:
        raise RuntimeError(
            "No NVIDIA_API_KEY or GROQ_API_KEY found. "
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

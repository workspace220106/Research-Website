"""
GPT-4o API wrapper.
Used for: YouTube script generation (better conversational tone than Claude).
"""

from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()


def gpt(
    system: str,
    user: str,
    model: str = "gpt-4o",
    max_tokens: int = 4096,
) -> str:
    """Single GPT call. Returns text."""
    resp = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    )
    return resp.choices[0].message.content

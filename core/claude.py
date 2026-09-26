"""
OpenRouter wrapper (replaces Anthropic Claude).
Used for: claim extraction, verdict assignment, synthesis, LaTeX generation.
Same claude() function signature so the rest of the pipeline is unchanged.

Uses OpenRouter free models (OpenAI-compatible API).
"""

from openai import OpenAI
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

_api_key = os.getenv("OPENROUTER_API_KEY", "")
_groq_key = os.getenv("GROQ_API_KEY", "")
_nvidia_key = os.getenv("NVIDIA_API_KEY", "") or os.getenv("NIM_API_KEY", "")

_default_model = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct")

_MAX_RETRIES = 3
_BASE_DELAY = 3


def _get_client_and_model(preferred_model: str | None = None):
    """Return available OpenAI-compatible client and appropriate model."""
    if _api_key:
        return OpenAI(
            api_key=_api_key,
            base_url="https://openrouter.ai/api/v1",
        ), preferred_model or _default_model
    elif _groq_key:
        return OpenAI(
            api_key=_groq_key,
            base_url="https://api.groq.com/openai/v1",
        ), "llama-3.3-70b-versatile"
    elif _nvidia_key:
        return OpenAI(
            api_key=_nvidia_key,
            base_url="https://integrate.api.nvidia.com/v1",
        ), "meta/llama-3.3-70b-instruct"
    return None, None


def claude(
    system: str,
    user: str,
    json_mode: bool = False,
    model: str | None = None,
    max_tokens: int = 8192,
) -> str | dict:
    """
    Call LLM via OpenRouter (with fallback to Groq/NVIDIA).
    json_mode=True -> strips markdown fences and parses JSON.
    """
    client, effective_model = _get_client_and_model(model)
    if client is None:
        raise RuntimeError("No OPENROUTER_API_KEY, GROQ_API_KEY, or NVIDIA_API_KEY found. Set in your .env file.")

    last_err = None
    for attempt in range(_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model=effective_model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
            text = resp.choices[0].message.content or ""
            break
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "503" in err_str or "rate" in err_str.lower() or "overloaded" in err_str.lower():
                last_err = e
                delay = min(_BASE_DELAY * (2 ** attempt), 60)
                print(f"  ⏳ OpenRouter: {err_str[:50]}… retry {attempt+1}/{_MAX_RETRIES} in {delay}s")
                time.sleep(delay)
                continue
            raise
    else:
        raise last_err

    if json_mode:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1:
                start = text.find("[")
                end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not parse JSON from OpenRouter response: {e}")

    return text

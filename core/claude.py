"""
Gemini wrapper (replaces Anthropic Claude).
Used for: claim extraction, verdict assignment, synthesis, LaTeX generation.
Same claude() function signature so the rest of the pipeline is unchanged.
"""

from google import genai
from google.genai import types
import json
import os
import time
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

_MAX_RETRIES = 4
_BASE_DELAY = 5
_FALLBACK_MODELS = []


def claude(
    system: str,
    user: str,
    json_mode: bool = False,
    model: str = "gemini-3.8-flash",
    max_tokens: int = 8192,
) -> str | dict:
    """
    Single Gemini call (drop-in replacement for Claude).
    Falls back to older models if the primary is overloaded.
    json_mode=True -> strips markdown fences and parses JSON.
    """
    models_to_try = [model] + [m for m in _FALLBACK_MODELS if m != model]

    for current_model in models_to_try:
        last_err = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = client.models.generate_content(
                    model=current_model,
                    contents=user,
                    config=types.GenerateContentConfig(
                        system_instruction=system,
                        max_output_tokens=max_tokens,
                    ),
                )
                text = resp.text or ""
                if current_model != model:
                    print(f"  ✅ Succeeded with fallback model: {current_model}")
                break
            except Exception as e:
                err_str = str(e)
                if "503" in err_str or "429" in err_str or "UNAVAILABLE" in err_str or "overloaded" in err_str.lower():
                    last_err = e
                    delay = min(_BASE_DELAY * (2 ** attempt), 60)
                    print(f"  ⏳ {current_model}: {err_str[:50]}… retry {attempt+1}/{_MAX_RETRIES} in {delay}s")
                    time.sleep(delay)
                    continue
                raise
        else:
            print(f"  ⚠ {current_model} exhausted retries, trying next model…")
            continue
        break
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
            raise ValueError(f"Could not parse JSON from Gemini response: {e}")

    return text

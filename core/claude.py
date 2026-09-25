"""
Claude API wrapper.
Used for: claim extraction, verdict assignment, synthesis, LaTeX generation.
"""

import anthropic
import json
import os
from dotenv import load_dotenv

load_dotenv()

client = anthropic.Anthropic()


def claude(
    system: str,
    user: str,
    json_mode: bool = False,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 8192,
) -> str | dict:
    """
    Single Claude call.
    json_mode=True → strips markdown fences and parses JSON.
    """
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text

    if json_mode:
        text = text.strip()
        # Strip ```json ... ``` fences
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first and last line (the fences)
            text = "\n".join(lines[1:-1]).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            # Try to find JSON within the text
            start = text.find("{")
            end = text.rfind("}") + 1
            if start == -1:
                start = text.find("[")
                end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not parse JSON from Claude response: {e}")

    return text

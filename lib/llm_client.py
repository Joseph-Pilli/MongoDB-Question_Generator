"""OpenAI Chat Completions API client."""

import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
load_dotenv(ENV_PATH, override=True)

OPENAI_API_BASE = "https://api.openai.com/v1"

# Claude model names map to the closest OpenAI equivalent (Claude is not on OpenAI).
MODEL_ALIASES = {
    "sonnet 4.6": "gpt-4.1",
    "sonnet-4.6": "gpt-4.1",
    "claude sonnet 4.6": "gpt-4.1",
    "claude-sonnet-4.6": "gpt-4.1",
    "claude-sonnet-4-6": "gpt-4.1",
    "anthropic/claude-sonnet-4": "gpt-4.1",
    "anthropic/claude-sonnet-4.6": "gpt-4.1",
    "gpt-4o": "gpt-4o",
    "gpt-4.1": "gpt-4.1",
    "gpt-4.1-mini": "gpt-4.1-mini",
}

DEFAULT_MODEL = "gpt-4.1"


class LLMError(Exception):
    pass


def _api_key() -> str:
    key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        load_dotenv(ENV_PATH, override=True)
        key = (os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise LLMError(f"OPENAI_API_KEY is not set. Add it to {ENV_PATH}.")
    if not key.startswith("sk-"):
        raise LLMError("OPENAI_API_KEY must be an OpenAI key (starts with sk-).")
    return key


def _resolve_model() -> str:
    raw = (os.getenv("MODEL_NAME") or DEFAULT_MODEL).strip()
    return MODEL_ALIASES.get(raw.lower(), raw)


def call_llm(system_prompt: str, user_message: str, max_tokens: int = 16000) -> str:
    """Call OpenAI Chat Completions and return raw text."""
    api_key = _api_key()
    model = _resolve_model()

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                f"{OPENAI_API_BASE}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
    except httpx.RequestError as e:
        raise LLMError(f"Could not reach OpenAI API: {e}") from e

    if response.status_code >= 400:
        detail = response.text[:400]
        try:
            body = response.json()
            err = body.get("error") or {}
            detail = err.get("message") or detail
        except ValueError:
            pass
        raise LLMError(f"OpenAI API error ({response.status_code}): {detail}")

    try:
        data = response.json()
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise LLMError("Unexpected OpenAI API response format.") from e

    if not (text or "").strip():
        raise LLMError("Empty response from OpenAI model")
    return text.strip()


def provider_label() -> str:
    model = _resolve_model()
    return f"OpenAI · {model}"

"""Lazily initialized clients and router for heterogeneous agent models."""

import logging
import os

from google import genai
from google.genai import types

from backend.config import ConfigurationError, GEMINI_MODEL, get_gemini_api_key

logger = logging.getLogger("vertexflow")

OPEN_SOURCE_KEY_ENV_VAR = "OPEN_SOURCE_API_KEY"
OPEN_SOURCE_BASE_URL = "https://openrouter.ai/api/v1"
OPEN_SOURCE_MODEL = "deepseek/deepseek-v4-flash"

_gemini_client: genai.Client | None = None
_open_source_client = None


def get_client() -> genai.Client:
    """Return the shared Gemini client, creating it on first use.

    Creating the client lazily keeps the API server bootable without credentials,
    so a missing key surfaces as an actionable error on the failing request
    instead of an opaque crash at import time.
    """
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=get_gemini_api_key())
    return _gemini_client


def has_open_source_api_key() -> bool:
    """True when an OpenAI-compatible key (OpenRouter/Groq) is configured."""
    return bool((os.environ.get(OPEN_SOURCE_KEY_ENV_VAR) or "").strip())


def get_open_source_client():
    """Return the shared OpenAI-compatible client used for the coder models.

    `openai` is imported here rather than at module scope: it is an optional
    dependency, and a project that only has GEMINI_API_KEY must still boot.
    """
    global _open_source_client
    if _open_source_client is None:
        try:
            from openai import OpenAI
        except ModuleNotFoundError as exc:
            raise ConfigurationError(
                f"{OPEN_SOURCE_KEY_ENV_VAR} is set but the `openai` package is not installed. "
                "Run `uv add openai`, or remove the key from backend/.env to route the "
                "worker agents to Gemini instead."
            ) from exc
        _open_source_client = OpenAI(
            base_url=OPEN_SOURCE_BASE_URL,
            api_key=os.environ[OPEN_SOURCE_KEY_ENV_VAR].strip(),
        )
    return _open_source_client


# Agents that write code are the expensive ones, so they can be routed to a
# cheaper coder model. Everything else — and every agent when no open-source
# key is configured — uses Gemini.
CODER_ROLES = ("backend_worker", "frontend_worker")


def get_agent_llm_config(agent_role: str) -> dict:
    """Return the client, provider and model for an agent role.

    Falls back to Gemini when OPEN_SOURCE_API_KEY is absent, so the documented
    GEMINI_API_KEY-only setup keeps working.
    """
    if agent_role in CODER_ROLES and has_open_source_api_key():
        config = {
            "provider": "openai_compatible",
            "client": get_open_source_client(),
            "model": OPEN_SOURCE_MODEL,
        }
    else:
        config = {
            "provider": "gemini",
            "client": get_client(),
            "model": GEMINI_MODEL,
        }

    logger.info(
        "🤖 [MODEL ROUTER] Agent '%s' assigned to Provider: [%s] -> Model: '%s'",
        agent_role.upper(),
        config["provider"].upper(),
        config["model"],
    )

    return config


def generate_json(config: dict, prompt: str, system_prompt: str = "You are a precise JSON code generator.") -> str:
    """Run one completion on the configured provider and return the raw JSON text."""
    if config["provider"] == "openai_compatible":
        response = config["client"].chat.completions.create(
            model=config["model"],
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or ""

    response = config["client"].models.generate_content(
        model=config["model"],
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        ),
    )
    return response.text

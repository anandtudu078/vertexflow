"""Lazily initialized clients and router for heterogeneous agent models."""

import json
import logging
import os
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from backend.config import ConfigurationError, GEMINI_MODEL, get_gemini_api_key

logger = logging.getLogger("vertexflow")

# Gemini answers 503 UNAVAILABLE during demand spikes. A single flare used to
# abort a whole pipeline run, so transient statuses are retried with backoff
# and, when a second provider is configured, given one last round there.
RETRYABLE_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
MAX_ATTEMPTS = 4
INITIAL_BACKOFF_SECONDS = 3.0

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


# Dropped sockets and timeouts show up as transport errors with no status code,
# and the OpenAI SDK re-wraps them in its own connection error classes.
_TRANSIENT_ERROR_NAMES = frozenset({"APIConnectionError", "APITimeoutError", "InternalServerError"})


def _retry_reason(exc: BaseException) -> str | None:
    """Why `exc` is worth retrying (e.g. "503"), or None when it is fatal."""
    if isinstance(exc, genai_errors.APIError):
        status = getattr(exc, "code", None)
    else:
        # openai.APIStatusError, imported lazily by the SDK itself
        status = getattr(exc, "status_code", None)
    if status in RETRYABLE_STATUS_CODES:
        return str(status)

    if isinstance(exc, httpx.TransportError):
        return type(exc).__name__
    for cls in type(exc).__mro__:
        if cls.__name__ in _TRANSIENT_ERROR_NAMES:
            return cls.__name__
    return None


def _alternate_config(config: dict) -> dict | None:
    """The other configured provider, used once when the routed one stays down."""
    if config["provider"] == "gemini":
        if not has_open_source_api_key():
            return None
        try:
            client = get_open_source_client()
        except ConfigurationError:
            return None
        return {"provider": "openai_compatible", "client": client, "model": OPEN_SOURCE_MODEL}

    return {"provider": "gemini", "client": get_client(), "model": GEMINI_MODEL}


def _with_retries(config: dict, call) -> str:
    """Call the provider, retrying transient failures with exponential backoff."""
    last_exc: BaseException | None = None
    for attempt_number in range(1, MAX_ATTEMPTS + 1):
        try:
            return call(config)
        except Exception as exc:
            reason = _retry_reason(exc)
            if reason is None:
                raise
            last_exc = exc
            if attempt_number == MAX_ATTEMPTS:
                break
            delay = INITIAL_BACKOFF_SECONDS * 2 ** (attempt_number - 1)
            logger.warning(
                "⚠️ [MODEL ROUTER] Provider [%s] failed with %s (attempt %d/%d); retrying in %.0fs",
                config["provider"].upper(),
                reason,
                attempt_number,
                MAX_ATTEMPTS,
                delay,
            )
            time.sleep(delay)

    raise last_exc


def _generate(config: dict, call) -> str:
    """Run `call`, retrying transient failures and trying the other provider last."""
    try:
        return _with_retries(config, call)
    except Exception as exc:
        fallback = _alternate_config(config) if _retry_reason(exc) else None
        if fallback is None:
            raise
        logger.warning(
            "⚠️ [MODEL ROUTER] Provider [%s] is still unavailable, retrying on [%s] model '%s'",
            config["provider"].upper(),
            fallback["provider"].upper(),
            fallback["model"],
        )
        return _with_retries(fallback, call)


def generate_json(config: dict, prompt: str, system_prompt: str = "You are a precise JSON code generator.") -> str:
    """Run one completion on the configured provider and return the raw JSON text."""
    return _generate(config, lambda cfg: _complete(cfg, prompt, system_prompt))


def generate_structured(prompt: str, schema, agent_role: str) -> str:
    """Return JSON text matching `schema`, taken from the provider routed to `agent_role`.

    The planner agents and the auditor ask for a `response_schema` rather than the
    plain text route. They used to call the SDK directly, so a 503 flare there
    skipped every retry and killed the run.
    """

    # The fallback provider has no response_schema, so hand it the schema itself:
    # otherwise it invents field names and the caller's model_validate_json fails.
    schema_hint = "You are a precise JSON generator. Reply with a single bare JSON object only, using exactly these fields:\n" + (
        json.dumps(schema.model_json_schema()) if hasattr(schema, "model_json_schema") else "{}"
    )

    def call(config: dict) -> str:
        if config["provider"] == "openai_compatible":
            return _complete(config, prompt, schema_hint)
        response = config["client"].models.generate_content(
            model=config["model"],
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.2,
            ),
        )
        return response.text

    return _generate(get_agent_llm_config(agent_role), call)


def generate_model(prompt: str, model_cls, agent_role: str):
    """Return `model_cls` parsed from the provider's answer.

    A model that ignores the schema sometimes wraps the object in a one-element
    list; that is unwrapped instead of crashing on `**data`.
    """
    data = json.loads(generate_structured(prompt, model_cls, agent_role))
    if isinstance(data, list):
        data = next((item for item in data if isinstance(item, dict)), {})
    return model_cls.model_validate(data)


def _complete(config: dict, prompt: str, system_prompt: str) -> str:
    """One completion on the configured provider."""
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

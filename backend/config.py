"""Environment configuration shared by the API and the agent nodes."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Explicitly load backend/.env regardless of the process working directory.
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

API_KEY_ENV_VAR = "GEMINI_API_KEY"
MODEL_ENV_VAR = "GEMINI_MODEL"
DEFAULT_MODEL = "gemini-3.5-flash-lite"

# gemini-2.5-flash is deprecated (routes to gemini-3.5-flash-lite after Dec 1 2026).
# gemini-3.8-flash does not exist. The current stable model is gemini-3.5-flash-lite.
GEMINI_MODEL = (os.environ.get(MODEL_ENV_VAR) or DEFAULT_MODEL).strip() or DEFAULT_MODEL


class ConfigurationError(RuntimeError):
    """Raised when a required environment variable is missing or empty."""


def has_gemini_api_key() -> bool:
    """True when a Gemini API key is present in the environment."""
    return bool((os.environ.get(API_KEY_ENV_VAR) or "").strip())


def get_gemini_api_key() -> str:
    """Return the Gemini API key, or explain exactly how to provide it."""
    key = (os.environ.get(API_KEY_ENV_VAR) or "").strip()
    if not key:
        raise ConfigurationError(
            f"{API_KEY_ENV_VAR} is not set. Add it to backend/.env as "
            f"{API_KEY_ENV_VAR}=your-key, or export it in your shell, then restart the API."
        )
    return key

"""Lazily initialised Google GenAI client shared by the agent nodes."""

from google import genai

from backend.config import get_gemini_api_key

_client: genai.Client | None = None


def get_client() -> genai.Client:
    """Return the shared Gemini client, creating it on first use.

    Creating the client lazily keeps the API server bootable without credentials,
    so a missing key surfaces as an actionable error on the failing request
    instead of an opaque crash at import time.
    """
    global _client
    if _client is None:
        _client = genai.Client(api_key=get_gemini_api_key())
    return _client

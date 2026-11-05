"""Tests for the heterogeneous model router.

A Gemini-only setup (just GEMINI_API_KEY) must keep working: coder roles fall
back to Gemini when no open-source key is configured.
"""

import httpx
import pytest
from pydantic import BaseModel

from backend.agents import llm


@pytest.fixture(autouse=True)
def _reset_clients(monkeypatch):
    monkeypatch.setattr(llm, "_gemini_client", None)
    monkeypatch.setattr(llm, "_open_source_client", None)


@pytest.fixture(autouse=True)
def _no_backoff(monkeypatch):
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)


class _TransientError(Exception):
    """Stand-in for a provider error carrying a retryable HTTP status."""

    def __init__(self, status_code: int = 503):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code


def _gemini_config() -> dict:
    return {"provider": "gemini", "client": object(), "model": llm.GEMINI_MODEL}


def test_coder_roles_fall_back_to_gemini_without_an_open_source_key(monkeypatch):
    monkeypatch.delenv(llm.OPEN_SOURCE_KEY_ENV_VAR, raising=False)
    gemini = object()
    monkeypatch.setattr(llm, "get_client", lambda: gemini)

    config = llm.get_agent_llm_config("backend_worker")

    assert config["provider"] == "gemini"
    assert config["client"] is gemini
    assert config["model"] == llm.GEMINI_MODEL


def test_a_transient_provider_error_is_retried(monkeypatch):
    calls = []

    def fake_complete(config, prompt, system_prompt):
        calls.append(config["provider"])
        if len(calls) == 1:
            raise _TransientError(503)
        return '{"ok": true}'

    monkeypatch.setattr(llm, "_complete", fake_complete)

    assert llm.generate_json(_gemini_config(), "prompt") == '{"ok": true}'
    assert len(calls) == 2


def test_the_retry_budget_is_bounded_without_a_second_provider(monkeypatch):
    monkeypatch.delenv(llm.OPEN_SOURCE_KEY_ENV_VAR, raising=False)
    calls = []

    def always_503(config, prompt, system_prompt):
        calls.append(config["provider"])
        raise _TransientError(503)

    monkeypatch.setattr(llm, "_complete", always_503)

    with pytest.raises(_TransientError):
        llm.generate_json(_gemini_config(), "prompt")

    assert len(calls) == llm.MAX_ATTEMPTS


def test_the_other_provider_is_tried_when_the_first_stays_down(monkeypatch):
    monkeypatch.setenv(llm.OPEN_SOURCE_KEY_ENV_VAR, "test-key")
    monkeypatch.setattr(llm, "get_open_source_client", lambda: object())
    calls = []

    def gemini_down(config, prompt, system_prompt):
        calls.append(config["provider"])
        if config["provider"] == "gemini":
            raise _TransientError(503)
        return '{"fallback": true}'

    monkeypatch.setattr(llm, "_complete", gemini_down)

    assert llm.generate_json(_gemini_config(), "prompt") == '{"fallback": true}'
    assert calls.count("gemini") == llm.MAX_ATTEMPTS
    assert calls[-1] == "openai_compatible"


class _FakeModels:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def generate_content(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return type("Response", (), {"text": outcome})()


class _FakeClient:
    def __init__(self, models):
        self.models = models


class _Answer(BaseModel):
    ok: bool


def test_schema_constrained_calls_share_the_retry_budget(monkeypatch):
    models = _FakeModels([_TransientError(503), '{"ok": true}'])
    monkeypatch.setattr(
        llm,
        "get_agent_llm_config",
        lambda role: {"provider": "gemini", "client": _FakeClient(models), "model": llm.GEMINI_MODEL},
    )

    assert llm.generate_structured("prompt", _Answer, "ceo") == '{"ok": true}'
    assert models.calls == 2


def test_a_dropped_connection_is_retried(monkeypatch):
    calls = []

    def fake_complete(config, prompt, system_prompt):
        calls.append(config["provider"])
        if len(calls) == 1:
            raise httpx.ReadError("connection reset")
        return '{"ok": true}'

    monkeypatch.setattr(llm, "_complete", fake_complete)

    assert llm.generate_json(_gemini_config(), "prompt") == '{"ok": true}'
    assert len(calls) == 2


def test_a_fatal_provider_error_is_not_retried(monkeypatch):
    calls = []

    def bad_request(config, prompt, system_prompt):
        calls.append(config["provider"])
        raise _TransientError(400)

    monkeypatch.setattr(llm, "_complete", bad_request)

    with pytest.raises(_TransientError):
        llm.generate_json(_gemini_config(), "prompt")

    assert len(calls) == 1


def test_coder_roles_use_the_open_source_model_when_a_key_is_configured(monkeypatch):
    monkeypatch.setenv(llm.OPEN_SOURCE_KEY_ENV_VAR, "test-key")
    client = object()
    monkeypatch.setattr(llm, "get_open_source_client", lambda: client)

    config = llm.get_agent_llm_config("frontend_worker")

    assert config["provider"] == "openai_compatible"
    assert config["client"] is client
    assert config["model"] == llm.OPEN_SOURCE_MODEL


def test_non_coder_roles_always_use_gemini(monkeypatch):
    monkeypatch.setenv(llm.OPEN_SOURCE_KEY_ENV_VAR, "test-key")
    gemini = object()
    monkeypatch.setattr(llm, "get_client", lambda: gemini)

    config = llm.get_agent_llm_config("security_auditor")

    assert config["provider"] == "gemini"
    assert config["client"] is gemini
    assert config["model"] == llm.GEMINI_MODEL

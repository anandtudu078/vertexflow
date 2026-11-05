"""Tests for the heterogeneous model router.

A Gemini-only setup (just GEMINI_API_KEY) must keep working: coder roles fall
back to Gemini when no open-source key is configured.
"""

import pytest

from backend.agents import llm


@pytest.fixture(autouse=True)
def _reset_clients(monkeypatch):
    monkeypatch.setattr(llm, "_gemini_client", None)
    monkeypatch.setattr(llm, "_open_source_client", None)


def test_coder_roles_fall_back_to_gemini_without_an_open_source_key(monkeypatch):
    monkeypatch.delenv(llm.OPEN_SOURCE_KEY_ENV_VAR, raising=False)
    gemini = object()
    monkeypatch.setattr(llm, "get_client", lambda: gemini)

    config = llm.get_agent_llm_config("backend_worker")

    assert config["provider"] == "gemini"
    assert config["client"] is gemini
    assert config["model"] == llm.GEMINI_MODEL


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

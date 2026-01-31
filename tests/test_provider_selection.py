import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nanocode import resolve_provider, select_provider


def test_explicit_provider_required(monkeypatch):
    monkeypatch.setenv("VSELLM_API_URL", "http://vsellm")
    monkeypatch.setenv("VSELLM_MODEL", "vsellm-model")
    monkeypatch.setenv("OLLAMA_API_URL", "http://ollama")
    monkeypatch.setenv("OLLAMA_MODEL", "ollama-model")
    monkeypatch.delenv("NANOCODE_PROVIDER", raising=False)
    monkeypatch.delenv("NANOCODE_ALLOW_IMPLICIT_PROVIDER", raising=False)

    with pytest.raises(ValueError, match="NANOCODE_PROVIDER must be set"):
        resolve_provider()


def test_explicit_provider_selected_over_others(monkeypatch):
    monkeypatch.setenv("NANOCODE_PROVIDER", "vsellm")
    monkeypatch.setenv("VSELLM_API_URL", "https://api.vsellm.example/v1")
    monkeypatch.setenv("VSELLM_MODEL", "gpt-5-nano")
    monkeypatch.setenv("OLLAMA_API_URL", "http://ollama")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    monkeypatch.setenv("VLLM_API_URL", "http://vllm")
    monkeypatch.delenv("VLLM_MODEL", raising=False)

    provider = select_provider("vsellm")

    assert provider["name"] == "VSELLM"
    assert provider["model"] == "gpt-5-nano"
    assert provider["api_url"].endswith("/chat/completions")


def test_missing_model_fails(monkeypatch):
    monkeypatch.setenv("NANOCODE_PROVIDER", "vllm")
    monkeypatch.setenv("VLLM_API_URL", "http://vllm")
    monkeypatch.delenv("VLLM_MODEL", raising=False)

    with pytest.raises(ValueError, match="vllm requires VLLM_MODEL"):
        select_provider("vllm")


def test_legacy_implicit_mode(monkeypatch, capsys):
    monkeypatch.delenv("NANOCODE_PROVIDER", raising=False)
    monkeypatch.setenv("NANOCODE_ALLOW_IMPLICIT_PROVIDER", "1")
    monkeypatch.delenv("VSELLM_API_URL", raising=False)
    monkeypatch.delenv("OLLAMA_API_URL", raising=False)
    monkeypatch.setenv("VLLM_API_URL", "http://vllm")
    monkeypatch.setenv("VLLM_MODEL", "vllm-model")

    provider = resolve_provider()
    captured = capsys.readouterr()

    assert "WARNING: implicit provider selection is deprecated" in captured.err
    assert provider["name"] == "vLLM"

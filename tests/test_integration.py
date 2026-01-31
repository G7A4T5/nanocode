import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nanocode import normalize_ollama_url, normalize_vllm_url, normalize_vsellm_url


def _post_json(url, payload, headers=None, timeout=10):
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    try:
        response = urllib.request.urlopen(request, timeout=timeout)
    except urllib.error.HTTPError as err:
        return None, err
    except urllib.error.URLError as err:
        return None, err
    except Exception as err:  # pragma: no cover - unexpected environments
        return None, err
    return json.loads(response.read()), None


def test_vsellm_integration():
    api_url = os.environ.get("VSELLM_API_URL", "").strip()
    model = os.environ.get("VSELLM_MODEL", "").strip()
    api_key = os.environ.get("VSELLM_API_KEY", "").strip()
    if not (api_url and model and api_key):
        pytest.skip("VSELLM env vars not configured")
    url = normalize_vsellm_url(api_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with the single word: Привет"}],
        "stream": False,
    }
    data, err = _post_json(url, payload, headers={"Authorization": f"Bearer {api_key}"})
    if err:
        pytest.skip(f"VSELLM unavailable: {err}")
    content = data["choices"][0]["message"].get("content", "")
    assert "Привет" in content


def test_ollama_integration():
    api_url = os.environ.get("OLLAMA_API_URL", "").strip()
    model = os.environ.get("OLLAMA_MODEL", "").strip()
    if not (api_url and model):
        pytest.skip("Ollama env vars not configured")
    url = normalize_ollama_url(api_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with hi"}],
        "stream": False,
    }
    data, err = _post_json(url, payload)
    if err:
        pytest.skip(f"Ollama unavailable: {err}")
    content = data.get("message", {}).get("content", "")
    assert content.strip()


def test_vllm_integration():
    api_url = os.environ.get("VLLM_API_URL", "").strip()
    model = os.environ.get("VLLM_MODEL", "").strip()
    if not (api_url and model):
        pytest.skip("vLLM env vars not configured")
    url = normalize_vllm_url(api_url)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with hi"}],
        "stream": False,
    }
    headers = {}
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    if openrouter_key:
        headers["Authorization"] = f"Bearer {openrouter_key}"
    data, err = _post_json(url, payload, headers=headers)
    if err:
        pytest.skip(f"vLLM unavailable: {err}")
    content = data["choices"][0]["message"].get("content", "")
    assert content.strip()

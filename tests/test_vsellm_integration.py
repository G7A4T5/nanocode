import json
import sys
import urllib.request
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

import nanocode


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode()


def test_vsellm_call_api_request(monkeypatch):
    monkeypatch.setenv("VSELLM_KEY", "vsellm-test")
    monkeypatch.delenv("MODEL", raising=False)
    captured = {}

    def fake_urlopen(request):
        captured["request"] = request
        return FakeResponse({"choices": [{"message": {"content": "ok"}}]})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    response = nanocode.call_api([{"role": "user", "content": "hi"}], "system")

    request = captured["request"]
    assert request.full_url == "https://api.vsellm.ru/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer vsellm-test"

    body = json.loads(request.data.decode())
    assert body["model"] == "openai/gpt-5-nano"
    assert response["choices"][0]["message"]["content"] == "ok"


def test_vsellm_tool_call_flow(monkeypatch):
    monkeypatch.setenv("VSELLM_KEY", "vsellm-test")
    messages = []
    tool_call_response = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {"name": "read", "arguments": "{}"},
                        }
                    ],
                }
            }
        ]
    }
    final_response = {"choices": [{"message": {"content": "done"}}]}
    calls = []

    def fake_call_api(msgs, system_prompt):
        calls.append([dict(item) for item in msgs])
        if len(calls) == 1:
            return tool_call_response
        return final_response

    monkeypatch.setattr(nanocode, "call_api", fake_call_api)
    monkeypatch.setattr(nanocode, "run_tool", lambda name, args: "tool-output")

    nanocode.run_openai_loop(messages, "system")

    assert calls[1][-1] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": "tool-output",
    }

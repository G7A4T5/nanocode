import importlib
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def reload_nanocode(monkeypatch, env):
    for key in list(env.keys()):
        if env[key] is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, env[key])
    sys.modules.pop("nanocode", None)
    return importlib.import_module("nanocode")


def test_call_api_headers_url_and_default_model(monkeypatch):
    nanocode = reload_nanocode(
        monkeypatch, {"VSELLM_KEY": "test-key", "MODEL": None}
    )
    captured = {}

    def fake_urlopen(request):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["data"] = request.data

        class Response:
            def read(self):
                return b'{"choices":[{"message":{"content":"hi"}}]}'

        return Response()

    monkeypatch.setattr(nanocode.urllib.request, "urlopen", fake_urlopen)

    nanocode.call_api([{"role": "user", "content": "hi"}], "system")

    payload = json.loads(captured["data"].decode())
    assert captured["auth"] == "Bearer test-key"
    assert captured["url"] == "https://api.vsellm.ru/v1/chat/completions"
    assert payload["model"] == "openai/gpt-5-nano"


def test_tool_call_loop_sends_results(monkeypatch):
    nanocode = reload_nanocode(monkeypatch, {"MODEL": None})
    messages = [{"role": "user", "content": "hi"}]
    responses = [
        {
            "choices": [
                {
                    "message": {
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "read",
                                    "arguments": "{\"path\": \"README.md\"}",
                                },
                            }
                        ],
                    }
                }
            ]
        },
        {"choices": [{"message": {"content": "done"}}]},
    ]
    seen_messages = []

    def fake_call_api(current_messages, system_prompt):
        seen_messages.append(json.loads(json.dumps(current_messages)))
        return responses.pop(0)

    def fake_run_tool(name, args):
        return "tool output"

    nanocode.run_agentic_loop(
        messages,
        "system",
        call_api_fn=fake_call_api,
        run_tool_fn=fake_run_tool,
        output=lambda *_args, **_kwargs: None,
    )

    assert len(seen_messages) == 2
    second_messages = seen_messages[1]
    tool_messages = [msg for msg in second_messages if msg.get("role") == "tool"]
    assert tool_messages == [
        {"role": "tool", "tool_call_id": "call_1", "content": "tool output"}
    ]
    assistant_messages = [
        msg for msg in second_messages if msg.get("role") == "assistant"
    ]
    assert assistant_messages[-1]["tool_calls"][0]["id"] == "call_1"

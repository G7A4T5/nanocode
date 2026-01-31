import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from nanocode import (
    messages_to_ollama,
    messages_to_openai,
    normalize_ollama_url,
    normalize_vllm_url,
    normalize_vsellm_url,
    parse_ollama_response,
    parse_openai_response,
    tools_to_ollama,
    tools_to_openai,
)


def sample_tools():
    return [
        {
            "name": "read",
            "description": "Read file",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]


def sample_messages():
    return [
        {"role": "user", "content": "Hello"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "Use tool"},
                {
                    "type": "tool_use",
                    "id": "call-1",
                    "name": "read",
                    "input": {"path": "foo.txt"},
                },
            ],
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "call-1",
                    "content": "data",
                }
            ],
        },
    ]


def test_normalize_vsellm_url():
    assert (
        normalize_vsellm_url("https://api.vsellm.ru/v1")
        == "https://api.vsellm.ru/v1/chat/completions"
    )
    assert (
        normalize_vsellm_url("https://api.vsellm.ru/v1/chat/completions")
        == "https://api.vsellm.ru/v1/chat/completions"
    )


def test_normalize_ollama_url():
    assert normalize_ollama_url("http://localhost:11434") == "http://localhost:11434/api/chat"
    assert (
        normalize_ollama_url("http://localhost:11434/api/chat")
        == "http://localhost:11434/api/chat"
    )


def test_normalize_vllm_url():
    assert normalize_vllm_url("http://localhost:8000") == "http://localhost:8000/v1/chat/completions"
    assert (
        normalize_vllm_url("http://localhost:8000/v1")
        == "http://localhost:8000/v1/chat/completions"
    )
    assert (
        normalize_vllm_url("http://localhost:8000/v1/chat/completions")
        == "http://localhost:8000/v1/chat/completions"
    )


def test_tools_to_openai():
    converted = tools_to_openai(sample_tools())
    assert converted == [
        {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read file",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }
    ]


def test_tools_to_ollama():
    assert tools_to_ollama(sample_tools()) == tools_to_openai(sample_tools())


def test_messages_to_openai():
    converted = messages_to_openai(sample_messages(), "system")
    assert converted[0] == {"role": "system", "content": "system"}
    assistant = converted[2]
    assert assistant["role"] == "assistant"
    assert assistant["content"] == "Use tool"
    assert assistant["tool_calls"][0]["function"]["name"] == "read"
    tool_message = converted[3]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call-1"
    assert tool_message["content"] == "data"


def test_messages_to_ollama():
    converted = messages_to_ollama(sample_messages(), "system")
    assert converted[0] == {"role": "system", "content": "system"}
    assistant = converted[2]
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"][0]["function"]["name"] == "read"
    tool_message = converted[3]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_name"] == "read"


def test_parse_openai_response_text():
    response = {"choices": [{"message": {"content": "Hi"}}]}
    parsed = parse_openai_response(response)
    assert parsed["content"] == [{"type": "text", "text": "Hi"}]


def test_parse_openai_response_tool_calls():
    response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "call-1",
                            "function": {"name": "read", "arguments": json.dumps({"path": "x"})},
                        }
                    ]
                }
            }
        ]
    }
    parsed = parse_openai_response(response)
    assert parsed["content"][0]["type"] == "tool_use"
    assert parsed["content"][0]["name"] == "read"
    assert parsed["content"][0]["input"] == {"path": "x"}


def test_parse_ollama_response():
    response = {
        "message": {
            "content": "Hello",
            "tool_calls": [
                {"function": {"name": "read", "arguments": json.dumps({"path": "y"})}}
            ],
        }
    }
    parsed = parse_ollama_response(response)
    assert parsed["content"][0] == {"type": "text", "text": "Hello"}
    assert parsed["content"][1]["type"] == "tool_use"
    assert parsed["content"][1]["input"] == {"path": "y"}

#!/usr/bin/env python3
"""nanocode - minimal claude code alternative"""

import glob as globlib, json, os, re, subprocess, sys, urllib.request

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")
VSELLM_API_URL = os.environ.get("VSELLM_API_URL", "").strip()
VSELLM_MODEL = os.environ.get("VSELLM_MODEL", "").strip()
VSELLM_API_KEY = os.environ.get("VSELLM_API_KEY", "").strip()
OLLAMA_API_URL = os.environ.get("OLLAMA_API_URL", "").strip()
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "").strip()
VLLM_API_URL = os.environ.get("VLLM_API_URL", "").strip()
VLLM_MODEL = os.environ.get("VLLM_MODEL", "").strip()


def normalize_vsellm_url(url):
    trimmed = url.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return trimmed


def normalize_ollama_url(url):
    trimmed = url.rstrip("/")
    if trimmed.endswith("/api/chat"):
        return trimmed
    return f"{trimmed}/api/chat"


def normalize_vllm_url(url):
    trimmed = url.rstrip("/")
    if trimmed.endswith("/chat/completions"):
        return trimmed
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return f"{trimmed}/v1/chat/completions"


def select_provider():
    if VSELLM_API_URL:
        return {
            "name": "VSELLM",
            "kind": "openai",
            "api_url": normalize_vsellm_url(VSELLM_API_URL),
            "model": VSELLM_MODEL,
            "headers": {"Authorization": f"Bearer {VSELLM_API_KEY}"} if VSELLM_API_KEY else {},
            "extra": {},
        }
    if OLLAMA_API_URL:
        return {
            "name": "Ollama",
            "kind": "ollama",
            "api_url": normalize_ollama_url(OLLAMA_API_URL),
            "model": OLLAMA_MODEL,
            "headers": {},
            "extra": {},
        }
    if VLLM_API_URL:
        headers = {"Authorization": f"Bearer {OPENROUTER_KEY}"} if OPENROUTER_KEY else {}
        return {
            "name": "vLLM",
            "kind": "openai",
            "api_url": normalize_vllm_url(VLLM_API_URL),
            "model": VLLM_MODEL,
            "headers": headers,
            "extra": {"parallel_tool_calls": False},
        }
    return {
        "name": "OpenRouter" if OPENROUTER_KEY else "Anthropic",
        "kind": "anthropic",
        "api_url": "https://openrouter.ai/api/v1/messages" if OPENROUTER_KEY else "https://api.anthropic.com/v1/messages",
        "model": os.environ.get("MODEL", "anthropic/claude-opus-4.5" if OPENROUTER_KEY else "claude-opus-4-5"),
        "headers": {"Authorization": f"Bearer {OPENROUTER_KEY}"} if OPENROUTER_KEY else {"x-api-key": os.environ.get("ANTHROPIC_API_KEY", "")},
        "extra": {},
    }


PROVIDER = select_provider()
API_URL = PROVIDER["api_url"]
MODEL = PROVIDER["model"]

# ANSI colors
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)


# --- Tool implementations ---


def read(args):
    lines = open(args["path"], encoding="utf-8", errors="replace").readlines()
    offset = args.get("offset", 0)
    limit = args.get("limit", len(lines))
    selected = lines[offset : offset + limit]
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


def write(args):
    with open(args["path"], "w", encoding="utf-8", errors="replace") as f:
        f.write(args["content"])
    return "ok"


def edit(args):
    text = open(args["path"], encoding="utf-8", errors="replace").read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = (
        text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    )
    with open(args["path"], "w", encoding="utf-8", errors="replace") as f:
        f.write(replacement)
    return "ok"


def glob(args):
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def grep(args):
    pattern = re.compile(args["pat"])
    hits = []
    for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
        try:
            for line_num, line in enumerate(open(filepath, encoding="utf-8", errors="replace"), 1):
                if pattern.search(line):
                    hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
        except Exception:
            pass
    return "\n".join(hits[:50]) or "none"


def bash(args):
    proc = subprocess.Popen(
        args["cmd"], shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f"  {DIM}│ {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")
    return "".join(output_lines).strip() or "(empty)"


# --- Tool definitions: (description, schema, function) ---

TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
}


def run_tool(name, args):
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            properties[param_name] = {
                "type": "integer" if base_type == "number" else base_type
            }
            if not is_optional:
                required.append(param_name)
        result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return result


def tools_to_openai(tools):
    converted = []
    for tool in tools:
        converted.append(
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"],
                },
            }
        )
    return converted


def tools_to_ollama(tools):
    return tools_to_openai(tools)


def _tool_name_map(messages):
    mapping = {}
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    mapping[block.get("id")] = block.get("name")
    return mapping


def messages_to_openai(messages, system_prompt):
    converted = [{"role": "system", "content": system_prompt}]
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text_parts = []
            tool_calls = []
            for block in content:
                if block["type"] == "text":
                    text_parts.append(block["text"])
                if block["type"] == "tool_use":
                    tool_calls.append(
                        {
                            "id": block["id"],
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        }
                    )
            converted.append(
                {
                    "role": "assistant",
                    "content": "\n".join(text_parts),
                    **({"tool_calls": tool_calls} if tool_calls else {}),
                }
            )
            continue
        for block in content:
            if block["type"] == "tool_result":
                converted.append(
                    {
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block["content"],
                    }
                )
            elif block["type"] == "text":
                converted.append({"role": "user", "content": block["text"]})
    return converted


def messages_to_ollama(messages, system_prompt):
    converted = [{"role": "system", "content": system_prompt}]
    name_map = _tool_name_map(messages)
    for message in messages:
        role = message.get("role")
        content = message.get("content")
        if isinstance(content, str):
            converted.append({"role": role, "content": content})
            continue
        if role == "assistant":
            text_parts = []
            tool_calls = []
            for block in content:
                if block["type"] == "text":
                    text_parts.append(block["text"])
                if block["type"] == "tool_use":
                    tool_calls.append(
                        {
                            "type": "function",
                            "function": {
                                "name": block["name"],
                                "arguments": json.dumps(block["input"]),
                            },
                        }
                    )
            converted.append(
                {
                    "role": "assistant",
                    "content": "\n".join(text_parts),
                    **({"tool_calls": tool_calls} if tool_calls else {}),
                }
            )
            continue
        for block in content:
            if block["type"] == "tool_result":
                tool_name = name_map.get(block["tool_use_id"], block["tool_use_id"])
                converted.append(
                    {
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": block["content"],
                    }
                )
            elif block["type"] == "text":
                converted.append({"role": "user", "content": block["text"]})
    return converted


def parse_openai_response(response):
    message = response.get("choices", [{}])[0].get("message", {})
    blocks = []
    content = message.get("content")
    if content:
        blocks.append({"type": "text", "text": content})
    for tool_call in message.get("tool_calls", []) or []:
        function = tool_call.get("function", {})
        arguments = function.get("arguments", "{}")
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
        except Exception:
            parsed = {}
        blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id", ""),
                "name": function.get("name", ""),
                "input": parsed,
            }
        )
    return {"content": blocks}


def parse_ollama_response(response):
    message = response.get("message", {})
    blocks = []
    content = message.get("content")
    if content:
        blocks.append({"type": "text", "text": content})
    for tool_call in message.get("tool_calls", []) or []:
        function = tool_call.get("function", {})
        arguments = function.get("arguments", "{}")
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
        except Exception:
            parsed = {}
        blocks.append(
            {
                "type": "tool_use",
                "id": tool_call.get("id", function.get("name", "")),
                "name": function.get("name", ""),
                "input": parsed,
            }
        )
    return {"content": blocks}


def call_api(messages, system_prompt):
    if PROVIDER["kind"] == "openai":
        payload = {
            "model": MODEL,
            "messages": messages_to_openai(messages, system_prompt),
            "tools": tools_to_openai(make_schema()),
            "stream": False,
            **PROVIDER["extra"],
        }
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **PROVIDER["headers"]},
        )
        response = urllib.request.urlopen(request, timeout=60)
        return parse_openai_response(json.loads(response.read()))
    if PROVIDER["kind"] == "ollama":
        payload = {
            "model": MODEL,
            "messages": messages_to_ollama(messages, system_prompt),
            "tools": tools_to_ollama(make_schema()),
            "stream": False,
        }
        request = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json", **PROVIDER["headers"]},
        )
        response = urllib.request.urlopen(request, timeout=60)
        return parse_ollama_response(json.loads(response.read()))
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(
            {
                "model": MODEL,
                "max_tokens": 8192,
                "system": system_prompt,
                "messages": messages,
                "tools": make_schema(),
            }
        ).encode(),
        headers={
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            **PROVIDER["headers"],
        },
    )
    response = urllib.request.urlopen(request, timeout=60)
    return json.loads(response.read())


def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def configure_stdio():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    if os.name == "nt":
        try:
            subprocess.run(
                "chcp 65001",
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass


def main():
    configure_stdio()
    print(f"{BOLD}nanocode{RESET} | {DIM}{MODEL} ({PROVIDER['name']}) | {os.getcwd()}{RESET}\n")
    messages = []
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}❯{RESET} ").strip()
            print(separator())
            if not user_input:
                continue
            if user_input in ("/q", "exit"):
                break
            if user_input == "/c":
                messages = []
                print(f"{GREEN}⏺ Cleared conversation{RESET}")
                continue

            messages.append({"role": "user", "content": user_input})

            # agentic loop: keep calling API until no more tool calls
            while True:
                response = call_api(messages, system_prompt)
                content_blocks = response.get("content", [])
                tool_results = []

                for block in content_blocks:
                    if block["type"] == "text":
                        print(f"\n{CYAN}⏺{RESET} {render_markdown(block['text'])}")

                    if block["type"] == "tool_use":
                        tool_name = block["name"]
                        tool_args = block["input"]
                        arg_preview = str(list(tool_args.values())[0])[:50]
                        print(
                            f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})"
                        )

                        result = run_tool(tool_name, tool_args)
                        result_lines = result.split("\n")
                        preview = result_lines[0][:60]
                        if len(result_lines) > 1:
                            preview += f" ... +{len(result_lines) - 1} lines"
                        elif len(result_lines[0]) > 60:
                            preview += "..."
                        print(f"  {DIM}⎿  {preview}{RESET}")

                        tool_results.append(
                            {
                                "type": "tool_result",
                                "tool_use_id": block["id"],
                                "content": result,
                            }
                        )

                messages.append({"role": "assistant", "content": content_blocks})

                if not tool_results:
                    break
                messages.append({"role": "user", "content": tool_results})

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()

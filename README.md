# nanocode

Minimal Claude Code alternative. Single Python file, zero dependencies, ~250 lines.

Built using Claude Code, then used to build itself.

![screenshot](screenshot.png)

## Features

- Full agentic loop with tool use
- Tools: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- Conversation history
- Colored terminal output

## Usage

```bash
export NANOCODE_PROVIDER="anthropic"
export ANTHROPIC_API_KEY="your-key"
python nanocode.py
```

### Provider selection (explicit)

Provider selection is now explicit to remove hidden priority when multiple backends are configured.
Set `NANOCODE_PROVIDER` to one of: `vsellm`, `ollama`, `vllm`, `openrouter`, `anthropic`.

All requests are non-streaming to keep behavior deterministic.

To temporarily allow the legacy implicit selection order, set:

```bash
export NANOCODE_ALLOW_IMPLICIT_PROVIDER=1
```

### OpenRouter

Use [OpenRouter](https://openrouter.ai) to access any model:

```bash
export NANOCODE_PROVIDER="openrouter"
export OPENROUTER_API_KEY="your-key"
python nanocode.py
```

To use a different model:

```bash
export NANOCODE_PROVIDER="openrouter"
export OPENROUTER_API_KEY="your-key"
export MODEL="openai/gpt-5.2"
python nanocode.py
```

### VSELLM (OpenAI-compatible proxy)

```bash
export NANOCODE_PROVIDER="vsellm"
export VSELLM_API_URL="https://api.vsellm.ru/v1"
export VSELLM_MODEL="openai/gpt-5-nano"
export VSELLM_API_KEY="your-key"
python nanocode.py
```

### Ollama

```bash
export NANOCODE_PROVIDER="ollama"
export OLLAMA_API_URL="http://localhost:11434"
export OLLAMA_MODEL="llama3.1"
python nanocode.py
```

### vLLM (OpenAI-compatible)

```bash
export NANOCODE_PROVIDER="vllm"
export VLLM_API_URL="http://localhost:8000"
export VLLM_MODEL="your-model"
python nanocode.py
```

## Commands

- `/c` - Clear conversation
- `/q` or `exit` - Quit

## Tools

| Tool | Description |
|------|-------------|
| `read` | Read file with line numbers, offset/limit |
| `write` | Write content to file |
| `edit` | Replace string in file (must be unique) |
| `glob` | Find files by pattern, sorted by mtime |
| `grep` | Search files for regex |
| `bash` | Run shell command |

## Example

```
────────────────────────────────────────
❯ what files are here?
────────────────────────────────────────

⏺ Glob(**/*.py)
  ⎿  nanocode.py

⏺ There's one Python file: nanocode.py
```

## UTF-8 console support

nanocode now reconfigures stdin/stdout/stderr to UTF-8 (with safe replacement) and
attempts to switch Windows console code pages to UTF-8. This improves Cyrillic
input/output reliability in Windows PowerShell and Ubuntu bash.

## License

MIT

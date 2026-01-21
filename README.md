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
export VSELLM_KEY="your-key"
python nanocode.py
```

By default, nanocode uses `openai/gpt-5-nano`. Override with `MODEL` if needed:

```bash
export VSELLM_KEY="your-key"
export MODEL="openai/gpt-5.2"
python nanocode.py
```

VSELLM is OpenAI-compatible and uses the `/v1/chat/completions` endpoint.

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

## License

MIT

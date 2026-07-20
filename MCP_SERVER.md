# Code Style course as an MCP server

This repo ships a small [MCP](https://modelcontextprotocol.io) server,
[`codestyle_mcp.py`](codestyle_mcp.py), that exposes the course guidelines to a
coding assistant (Claude Code, Cursor, Codex, Claude Desktop, …). Instead of
pasting docs into a chat, your assistant can ask the server what the course says
and get answers grounded in *these* guidelines — including which practices
matter at which development stage.

## What it exposes

**Tools**

| Tool | What it does |
| --- | --- |
| `codestyle_list_topics` | List all topics; optionally filter to a stage. |
| `codestyle_get_guideline` | Fetch the full markdown of one guideline. |
| `codestyle_search` | Keyword search across every guideline. |
| `codestyle_guidance_for_stage` | Group all topics by importance (🏅/💡/🐌) for a stage. |

**Resources**

- `codestyle://guideline/{name}` — each guideline's raw markdown, addressable by
  filename (`pathlib.md`), stem (`pathlib`), or topic name.

The content comes from [`README.md`](README.md) and [`docs/`](docs); no build
step, no database, no embeddings.

## Requirements

- [`uv`](https://docs.astral.sh/uv/)
- Python 3.10+

## Install

`uv` can run the server straight from its URL: it downloads the single script,
provisions Python and the `mcp` package from the script's own
[PEP 723](https://peps.python.org/pep-0723/) metadata, and the server fetches
its guidelines from the repo over HTTP. The URL is:

```
https://raw.githubusercontent.com/raoulg/codestyle/main/codestyle_mcp.py
```

Add it to your assistant with one of the following.

### Claude Code

```bash
claude mcp add codestyle -- uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/main/codestyle_mcp.py
```

### Cursor

Add to `.cursor/mcp.json` (per-project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "codestyle": {
      "command": "uv",
      "args": ["run", "--no-project", "https://raw.githubusercontent.com/raoulg/codestyle/main/codestyle_mcp.py"]
    }
  }
}
```

### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.codestyle]
command = "uv"
args = ["run", "--no-project", "https://raw.githubusercontent.com/raoulg/codestyle/main/codestyle_mcp.py"]
```

### Claude Desktop

Add to `claude_desktop_config.json` (Settings → Developer → Edit Config), then
restart the app:

```json
{
  "mcpServers": {
    "codestyle": {
      "command": "uv",
      "args": ["run", "--no-project", "https://raw.githubusercontent.com/raoulg/codestyle/main/codestyle_mcp.py"]
    }
  }
}
```

## Try it

Ask your assistant things like:

- "Using the codestyle server, what matters at the *explore* stage?"
- "Get the guideline on typehinting."
- "Search the codestyle guidelines for *pydantic settings*."

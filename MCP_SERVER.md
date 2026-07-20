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
| `codestyle_review_rubric` | The method for a *leveled* code review (see below). |

**Prompts**

- `review` — a one-command leveled code review. Takes an optional `target`
  (a path or description; defaults to the current project).

**Resources**

- `codestyle://guideline/{name}` — each guideline's raw markdown, addressable by
  filename (`pathlib.md`), stem (`pathlib`), or topic name.

The content comes from [`README.md`](README.md) and [`docs/`](docs); no build
step, no database, no embeddings.

## Requirements

- [`uv`](https://docs.astral.sh/uv/)
- Python 3.10+

## Install

`uv` runs the server straight from a URL: it downloads the single script,
provisions Python and the `mcp` package from the script's own
[PEP 723](https://peps.python.org/pep-0723/) metadata, and the server fetches
its guidelines from the repo over HTTP.

You pin a version with `CODESTYLE_REF` — a git tag. That one variable selects
both the script (in the URL) and the guidelines it fetches (inside the script),
so the whole cohort runs exactly the same thing and the two can't drift apart.
The current release is **`v0.2.0`**; add it to your assistant with one of the
following.

### Claude Code

```bash
claude mcp add codestyle -e CODESTYLE_REF=v0.2.0 -- \
  sh -c 'uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/$CODESTYLE_REF/codestyle_mcp.py'
```

### Cursor

Add to `.cursor/mcp.json` (per-project) or `~/.cursor/mcp.json` (global):

```json
{
  "mcpServers": {
    "codestyle": {
      "command": "sh",
      "args": ["-c", "uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/$CODESTYLE_REF/codestyle_mcp.py"],
      "env": { "CODESTYLE_REF": "v0.2.0" }
    }
  }
}
```

### Codex

Add to `~/.codex/config.toml`:

```toml
[mcp_servers.codestyle]
command = "sh"
args = ["-c", "uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/$CODESTYLE_REF/codestyle_mcp.py"]
env = { CODESTYLE_REF = "v0.2.0" }
```

### Claude Desktop

Add to `claude_desktop_config.json` (Settings → Developer → Edit Config), then
restart the app:

```json
{
  "mcpServers": {
    "codestyle": {
      "command": "sh",
      "args": ["-c", "uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/$CODESTYLE_REF/codestyle_mcp.py"],
      "env": { "CODESTYLE_REF": "v0.2.0" }
    }
  }
}
```

(The `sh` wrapper is for macOS/Linux; on Windows, drop `sh -c` and put the tag
directly in the URL instead, keeping the `CODESTYLE_REF` env value in sync.)

## Update to a new version

Pick the newest tag from the [releases](https://github.com/raoulg/codestyle/tags),
then point `CODESTYLE_REF` at it. Because the tag lives in the URL, switching
tags fetches the new script automatically — no cache clearing needed.

**Claude Code** — re-running `add` errors if the server already exists, so
remove first, then add with the new tag (change `v0.2.0` to the target):

```bash
claude mcp remove codestyle -s user
claude mcp add codestyle -s user -e CODESTYLE_REF=v0.2.0 -- \
  sh -c 'uv run --no-project https://raw.githubusercontent.com/raoulg/codestyle/$CODESTYLE_REF/codestyle_mcp.py'
```

**Cursor / Codex / Claude Desktop** — edit the `CODESTYLE_REF` value in the
config to the new tag.

Then **restart your assistant** so it relaunches the server. Confirm the new
version is live: in Claude Code, `claude mcp get codestyle` shows the pinned
`CODESTYLE_REF`.

## Review your code

The server can review your code against the course and coach your *next* step,
rather than dumping every rule on you at once. It figures out what you already
do well, then focuses on the lowest few guidelines you don't meet yet.

- In clients that surface MCP prompts (e.g. Claude Code), run the `review`
  prompt — in Claude Code that's `/codestyle:review` (optionally name a path).
- In any client, just ask: **"Review my code using the codestyle guidelines."**
  Your assistant will call `codestyle_review_rubric` and follow it.

As you improve, the focus moves up the ladder on its own — master avoiding
hardcoded values and the next review moves on to folders, settings, classes, and
so on.

## Other things to try

- "Using the codestyle server, what matters at the *explore* stage?"
- "Get the guideline on typehinting."
- "Search the codestyle guidelines for *pydantic settings*."

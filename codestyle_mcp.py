#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp[cli]>=2,<3"]
# ///
"""MCP server that exposes the Code Style course as tools and resources.

The course is a curated set of markdown guidelines in `docs/`, indexed by the
README's topic/stage matrix. Rather than dumping all of it into a coding
assistant's context, this server lets an assistant:

- list the topics (optionally filtered to what matters at a given stage),
- fetch the full text of a single guideline,
- search across all guidelines by keyword,
- ask "what should I care about at stage X?" using the course's own
  Explore -> Consolidate -> Cooperate -> Deploy model.

It reads the docs from disk when they sit next to this script, so editing a
`docs/*.md` file or the README table is all that's needed to update what the
server serves. When the script is launched on its own (e.g. run directly from a
URL with `uv run`, with no course files nearby), it transparently fetches the
same content from the public repo over HTTP instead. Either way: no build step,
no embeddings, no database.
"""

from __future__ import annotations

import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

from mcp.server.mcpserver import MCPServer
from pydantic import BaseModel, ConfigDict, Field

# --------------------------------------------------------------------------- #
# Paths and course model
# --------------------------------------------------------------------------- #

REPO_ROOT = Path(__file__).resolve().parent
DOCS_DIR = REPO_ROOT / "docs"
README = REPO_ROOT / "README.md"

# If the course files aren't next to this script, fetch them from the public
# repo over HTTP. This is what makes the zero-clone one-liner work:
#   uv run --no-project <RAW_BASE>/codestyle_mcp.py
#
# CODESTYLE_REF selects which git ref (branch, tag, or commit) to fetch content
# from; it defaults to "main". Point the launch URL at the same ref and both the
# script and its content stay pinned together — see MCP_SERVER.md.
CODESTYLE_REF = os.environ.get("CODESTYLE_REF", "main")
RAW_BASE = f"https://raw.githubusercontent.com/raoulg/codestyle/{CODESTYLE_REF}"
LOCAL = README.is_file() and DOCS_DIR.is_dir()

# Cache for content fetched over HTTP (unused in local mode).
_remote_cache: dict[str, str] = {}


def _load_text(rel_path: str) -> str:
    """Load a course file's text, relative to the repo root.

    e.g. `_load_text("README.md")` or `_load_text("docs/pathlib.md")`.

    Local files are read fresh on each call, so edits show up without a
    restart. Remote files are fetched once and cached.
    """
    if LOCAL:
        return (REPO_ROOT / rel_path).read_text(encoding="utf-8")
    if rel_path not in _remote_cache:
        with urllib.request.urlopen(f"{RAW_BASE}/{rel_path}", timeout=30) as resp:
            _remote_cache[rel_path] = resp.read().decode("utf-8")
    return _remote_cache[rel_path]

# The four development stages from the course, in order.
STAGES: tuple[str, ...] = ("explore", "consolidate", "cooperate", "deploy")

# The classifier emoji used in the README matrix and what they mean.
CLASSIFIER_MEANING: dict[str, str] = {
    "🐌": "might slow you down at this stage",
    "💡": "probably a good idea at this stage",
    "🏅": "a must at this stage",
}

mcp = MCPServer("codestyle_mcp")


# --------------------------------------------------------------------------- #
# Loading the index from the README table
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Topic:
    """One row of the README topic/stage matrix."""

    name: str  # human-readable topic name, e.g. "never hardcode"
    doc: Optional[str]  # doc filename, e.g. "never_hardcode.md" (None if no doc)
    classifiers: dict[str, str]  # stage -> emoji, e.g. {"explore": "💡", ...}


# Matches a README matrix row:
#   | [never hardcode](docs/never_hardcode.md) | 💡 | 🏅 | 🏅 | 🏅 |
#   | Makefiles or shell scripts               | 🐌 | 💡 | 💡 | 🏅 |
# The first cell is the topic (optionally a markdown link into docs/), the next
# four cells are the per-stage classifiers.
_ROW = re.compile(
    r"^\|\s*(?P<topic>.+?)\s*\|"
    r"\s*(?P<explore>[🐌💡🏅])\s*\|"
    r"\s*(?P<consolidate>[🐌💡🏅])\s*\|"
    r"\s*(?P<cooperate>[🐌💡🏅])\s*\|"
    r"\s*(?P<deploy>[🐌💡🏅])\s*\|\s*$"
)
_LINK = re.compile(r"\[(?P<text>.+?)\]\(docs/(?P<file>.+?\.md)\)")


def _load_topics() -> list[Topic]:
    """Parse the README matrix into an ordered list of Topics."""
    topics: list[Topic] = []
    for line in _load_text("README.md").splitlines():
        row = _ROW.match(line)
        if not row:
            continue
        raw_topic = row.group("topic")
        link = _LINK.search(raw_topic)
        if link:
            name, doc = link.group("text"), link.group("file")
        else:
            name, doc = raw_topic.strip(), None
        topics.append(
            Topic(
                name=name,
                doc=doc,
                classifiers={stage: row.group(stage) for stage in STAGES},
            )
        )
    return topics


# Loaded once at startup; the corpus is tiny and static per process.
TOPICS: list[Topic] = _load_topics()
# Map a few forms of a name/filename to its Topic for forgiving lookups.
_BY_KEY: dict[str, Topic] = {}
for _t in TOPICS:
    _BY_KEY[_t.name.lower()] = _t
    if _t.doc:
        _BY_KEY[_t.doc.lower()] = _t
        _BY_KEY[_t.doc[:-3].lower()] = _t  # without ".md"


def _find_topic(query: str) -> Optional[Topic]:
    """Resolve a topic by name, filename, or stem (case-insensitive)."""
    key = query.strip().lower()
    if key in _BY_KEY:
        return _BY_KEY[key]
    # Fall back to a partial match on the display name.
    for topic in TOPICS:
        if key in topic.name.lower():
            return topic
    return None


# --------------------------------------------------------------------------- #
# Input models and shared formatting
# --------------------------------------------------------------------------- #


class Stage(str, Enum):
    """A development stage from the course model."""

    explore = "explore"
    consolidate = "consolidate"
    cooperate = "cooperate"
    deploy = "deploy"


class ListTopicsInput(BaseModel):
    """Input for listing course topics."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stage: Optional[Stage] = Field(
        default=None,
        description=(
            "Optional stage filter. When set, only topics that are a good idea "
            "(💡) or a must (🏅) at that stage are returned. One of: "
            "explore, consolidate, cooperate, deploy."
        ),
    )


class GetGuidelineInput(BaseModel):
    """Input for fetching a single guideline."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    topic: str = Field(
        ...,
        description=(
            "Topic to fetch. Accepts the display name ('never hardcode'), the "
            "doc filename ('never_hardcode.md'), or its stem ('never_hardcode')."
        ),
        min_length=1,
        max_length=200,
    )


class SearchInput(BaseModel):
    """Input for searching across all guidelines."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description="Keyword(s) to search for across every guideline's text.",
        min_length=2,
        max_length=200,
    )
    limit: int = Field(
        default=5,
        description="Maximum number of matching guidelines to return.",
        ge=1,
        le=20,
    )


class StageInput(BaseModel):
    """Input for the stage-guidance tool."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    stage: Stage = Field(
        ...,
        description="Stage to get guidance for: explore, consolidate, cooperate, or deploy.",
    )


class ReviewRubricInput(BaseModel):
    """Input for the review-rubric tool."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    focus_rungs: int = Field(
        default=3,
        description=(
            "How many of the lowest unmet guidelines to focus the review on, so "
            "a beginner isn't overwhelmed. Defaults to 3 (a small cluster)."
        ),
        ge=1,
        le=6,
    )


def _read_doc(filename: str) -> str:
    """Read a doc file's text, raising a clear error if it is missing.

    Works whether the docs are local or fetched from the public repo; any
    failure to obtain the file is normalised to FileNotFoundError.
    """
    try:
        return _load_text(f"docs/{filename}")
    except (OSError, urllib.error.URLError) as exc:
        raise FileNotFoundError(filename) from exc


def _doc_url(filename: str) -> str:
    """Browsable GitHub URL for a guideline (rendered markdown, for humans).

    Uses the same ref the server is pinned to, so a link always points at the
    exact text the reader is being coached on.
    """
    return f"https://github.com/raoulg/codestyle/blob/{CODESTYLE_REF}/docs/{filename}"


def _topic_ref(topic: Topic) -> str:
    """A markdown link to a topic's online guideline, or a plain note."""
    if topic.doc:
        return f"[{topic.doc}]({_doc_url(topic.doc)})"
    return "(no online doc)"


def _area(topic: Topic) -> str:
    """Which development stage 'owns' a topic — the area of the map it sits in.

    Derived from the README classifiers so it tracks the table. The four stages
    are AREAS on a rough map, not a strict 1..N ranking: a topic that is already
    a must (🏅) by *consolidate* is a foundation you adopt while still exploring
    ("explore"); one that only becomes a must at *deploy* is "deploy"; the rest
    become a must at *cooperate* — those safe to start early (💡 at explore) are
    "consolidate", the ones that would slow you down early (🐌) are "cooperate".
    """
    classifiers = topic.classifiers
    first_must = next((s for s in STAGES if classifiers[s] == "🏅"), "deploy")
    if first_must in ("explore", "consolidate"):
        return "explore"
    if first_must == "deploy":
        return "deploy"
    return "consolidate" if classifiers["explore"] == "💡" else "cooperate"


def _topic_line(topic: Topic, stage: Optional[str] = None) -> str:
    """One-line summary of a topic for list output, with an online link."""
    if stage:
        emoji = topic.classifiers[stage]
        tail = f"{emoji} ({CLASSIFIER_MEANING[emoji]})"
    else:
        tail = " ".join(f"{s}:{topic.classifiers[s]}" for s in STAGES)
    return f"- **{topic.name}** — {_topic_ref(topic)} — {tail}"


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@mcp.tool(
    name="codestyle_list_topics",
    annotations={
        "title": "List code-style topics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def codestyle_list_topics(params: ListTopicsInput) -> str:
    """List the code-style topics in the course, with their per-stage importance.

    Use this to discover what guidelines exist before fetching one with
    codestyle_get_guideline. Optionally filter to the topics that matter at a
    given development stage.

    Args:
        params (ListTopicsInput):
            - stage (Optional[Stage]): if set, keep only topics rated 💡 or 🏅
              at that stage.

    Returns:
        str: Markdown bullet list. Each line has the topic name, its doc
        filename, and either the per-stage classifiers (no filter) or the
        classifier for the requested stage.
    """
    if params.stage is None:
        lines = ["# Code-style topics", ""]
        lines += [_topic_line(t) for t in TOPICS]
        return "\n".join(lines)

    stage = params.stage.value
    relevant = [t for t in TOPICS if t.classifiers[stage] in ("💡", "🏅")]
    lines = [f"# Topics that matter at the '{stage}' stage", ""]
    lines += [_topic_line(t, stage) for t in relevant]
    return "\n".join(lines)


@mcp.tool(
    name="codestyle_get_guideline",
    annotations={
        "title": "Get a code-style guideline",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def codestyle_get_guideline(params: GetGuidelineInput) -> str:
    """Fetch the full markdown of one code-style guideline.

    Args:
        params (GetGuidelineInput):
            - topic (str): display name, filename, or stem of the guideline.

    Returns:
        str: The guideline's full markdown, prefixed with its stage ratings.
        If the topic is not found, returns an error listing valid topic names.
        If the topic exists but has no doc (e.g. "Makefiles or shell scripts"),
        says so.
    """
    topic = _find_topic(params.topic)
    if topic is None:
        names = ", ".join(t.name for t in TOPICS)
        return (
            f"Error: no topic matching '{params.topic}'. "
            f"Call codestyle_list_topics first. Known topics: {names}"
        )
    if topic.doc is None:
        return (
            f"'{topic.name}' is a topic in the matrix but has no dedicated doc. "
            "See the README for context."
        )
    try:
        body = _read_doc(topic.doc)
    except FileNotFoundError:
        return f"Error: doc file '{topic.doc}' is listed in the README but missing on disk."

    ratings = " ".join(f"{s}:{topic.classifiers[s]}" for s in STAGES)
    header = (
        f"# {topic.name}\n\n"
        f"_Stage ratings — {ratings}_\n"
        f"_Further reading (share this link): {_doc_url(topic.doc)}_\n\n"
    )
    return header + body


@mcp.tool(
    name="codestyle_search",
    annotations={
        "title": "Search code-style guidelines",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def codestyle_search(params: SearchInput) -> str:
    """Search every guideline for keyword(s) and return the best matches.

    Ranking is simple term-frequency: guidelines are scored by how many times
    the query terms appear. Good for "where does the course talk about X?".

    Args:
        params (SearchInput):
            - query (str): one or more keywords.
            - limit (int): max guidelines to return (1-20, default 5).

    Returns:
        str: Markdown list of matching guidelines, each with a match count and
        a short snippet around the first hit. "No matches" if nothing is found.
    """
    terms = [t for t in params.query.lower().split() if t]
    scored: list[tuple[int, Topic, str]] = []

    for topic in TOPICS:
        if not topic.doc:
            continue
        try:
            text = _read_doc(topic.doc)
        except FileNotFoundError:
            continue
        lower = text.lower()
        score = sum(lower.count(term) for term in terms)
        if score == 0:
            continue
        # Snippet around the first matching term.
        first = min(
            (lower.find(term) for term in terms if lower.find(term) != -1),
            default=-1,
        )
        start = max(0, first - 80)
        snippet = text[start : first + 120].replace("\n", " ").strip()
        scored.append((score, topic, snippet))

    if not scored:
        return f"No matches for '{params.query}'."

    scored.sort(key=lambda item: item[0], reverse=True)
    lines = [f"# Search results for '{params.query}'", ""]
    for score, topic, snippet in scored[: params.limit]:
        lines.append(f"## {topic.name} — {score} hit(s)")
        lines.append(f"Further reading: {_doc_url(topic.doc)}")
        lines.append(f"…{snippet}…")
        lines.append("")
    return "\n".join(lines)


@mcp.tool(
    name="codestyle_guidance_for_stage",
    annotations={
        "title": "Get code-style guidance for a stage",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def codestyle_guidance_for_stage(params: StageInput) -> str:
    """Summarize what to focus on at a given development stage.

    This encodes the course's core idea: the right practice depends on where you
    are (Explore -> Consolidate -> Cooperate -> Deploy). It groups topics into
    "must" (🏅), "good idea" (💡), and "may slow you down" (🐌) for the stage.

    Args:
        params (StageInput):
            - stage (Stage): explore, consolidate, cooperate, or deploy.

    Returns:
        str: Markdown grouping every topic by its classifier at that stage, so
        an assistant can prioritise advice appropriately.
    """
    stage = params.stage.value
    buckets: dict[str, list[Topic]] = {"🏅": [], "💡": [], "🐌": []}
    for topic in TOPICS:
        buckets[topic.classifiers[stage]].append(topic)

    lines = [f"# Code-style guidance for the '{stage}' stage", ""]
    for emoji in ("🏅", "💡", "🐌"):
        heading = CLASSIFIER_MEANING[emoji].capitalize()
        lines.append(f"## {emoji} {heading}")
        if buckets[emoji]:
            for topic in buckets[emoji]:
                lines.append(f"- {topic.name} — {_topic_ref(topic)}")
        else:
            lines.append("- (none)")
        lines.append("")
    return "\n".join(lines)


AREA_BLURB: dict[str, str] = {
    "explore": "Explore — foundations worth adopting from day one",
    "consolidate": "Consolidate — organising code you've decided to keep",
    "cooperate": "Cooperate — making it readable and safe for others to build on",
    "deploy": "Deploy — hardening it into an extensible library",
}


def _map_by_area() -> list[str]:
    """The guidelines grouped into the four development-stage AREAS.

    The areas form a rough map (Explore -> Deploy), NOT a strict 1..N ranking:
    within an area the topics are peers, and a later area is not simply 'better'.
    """
    lines: list[str] = []
    for stage in STAGES:
        lines.append(f"### {AREA_BLURB[stage]}")
        for topic in TOPICS:
            if _area(topic) == stage:
                lines.append(f"- {topic.name} — {_topic_ref(topic)}")
        lines.append("")
    return lines


@mcp.tool(
    name="codestyle_review_rubric",
    annotations={
        "title": "Get the leveled code-review rubric",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def codestyle_review_rubric(params: ReviewRubricInput) -> str:
    """Return the method for reviewing a learner's code against this course.

    This is the entry point for a *leveled* review: instead of auditing all
    guidelines at once, the reviewer meets the learner where they are and coaches
    the next small step. Call this first, then follow it against the learner's
    actual code (which you read with your own file tools).

    Args:
        params (ReviewRubricInput):
            - focus_rungs (int): how many unmet guidelines to focus on (1-6,
              default 3).

    Returns:
        str: Markdown containing the review method, the guardrails, and the map
        of the four stage-areas (built live from the course's README, each topic
        linked to its guideline online).
    """
    n = params.focus_rungs
    parts = [
        "# Reviewing a learner's code against the Code Style course",
        "",
        "You are a supportive mentor. The goal is the learner's GROWTH, not a "
        "complete audit. Meet them where they are and coach the next small step.",
        "",
        "## How the guidelines are organised",
        "",
        "The guidelines fall into four development-stage AREAS — Explore, "
        "Consolidate, Cooperate, Deploy — shown on the map below. Treat these as a "
        "rough map, not a strict ranking: the areas are loosely ordered (Explore "
        "is more foundational than Deploy), but WITHIN an area the topics are peers "
        "— e.g. Open-Closed and ABC/Protocol are both Deploy-area concerns; neither "
        "is 'more advanced' than the other. Never imply a strict 1..N ordering.",
        "",
        "## Method",
        "",
        "1. Read the learner's code with your own file tools.",
        "2. Locate them on the map: find the highest area where their code is "
        "mostly solid, and the lowest area with real gaps. For each guideline near "
        "that edge, judge whether the code ✅ meets it, 🟡 partly meets it, or ❌ "
        "does not yet. When unsure what a guideline requires, call "
        "`codestyle_get_guideline` (or read `codestyle://guideline/{name}`) first.",
        "3. Open with encouragement: name 1-3 things they ALREADY do well, and say "
        "which area that puts them in. Learners need to know what to keep doing.",
        f"4. Pick the growth edge: the {n} most valuable unmet-or-partial "
        "guidelines, drawn from the lowest area that still has gaps (spill into the "
        "next area only if the lower one is solid). These, and ONLY these, are the "
        "focus. Do not sweep the whole map.",
        "5. For each focus item:",
        "   - Quote a short, concrete snippet from THEIR code that shows the gap.",
        "   - Give a one-sentence 'what it is and why it helps' for the principle.",
        "   - Show a small, concrete fix (a few lines) in their own code's style.",
        "   - Add a **Further reading** link — the guideline's URL from the map "
        "below (or from `codestyle_get_guideline`) — so they can read more.",
        "6. Close with one line of \"what's next\": name the AREA (or a peer topic "
        "in it) they grow into next — so they see the path, without teaching it yet.",
        "",
        "## Guardrails",
        "",
        "- Never overwhelm. If they still hardcode paths, start in the Explore area; "
        "Deploy-area concerns (open-closed, ABCs) can wait until foundations are solid.",
        "- Refer to guidelines by NAME and AREA, never by a rung number — there is "
        "no strict 1..N ladder, and within an area topics are peers.",
        "- Always include the guideline link when you reference one; a learner who "
        "wants to go deeper should be one click away.",
        "- Match your depth to their level; a first-week student and a "
        "nearly-deploying one need different reviews.",
        "- Be specific and kind. Every point ties to their actual code, never "
        "generic advice. Show before/after over long explanations.",
        "",
        "## The map — four areas (topics within an area are peers)",
        "",
    ]
    parts += _map_by_area()
    return "\n".join(parts)


@mcp.prompt(
    name="review",
    description="Review my code against the Code Style course, leveled to where I am.",
)
def review_prompt(target: str = "the code in the current project") -> str:
    """A one-command leveled code review.

    Args:
        target: what to review (a path, a file, or a description). Defaults to
            the current project.
    """
    return (
        f"Please review {target} against the Code Style course, as a supportive "
        "mentor coaching my next step.\n\n"
        "Step 1: call the `codestyle_review_rubric` tool to get the review method "
        "and the map of stage-areas.\n"
        "Step 2: follow it exactly against my actual code — tell me what I already "
        "do well, then give focused, encouraging feedback on only a few guidelines "
        "I don't meet yet, each with a link to read more. Don't overwhelm me with "
        "everything at once."
    )


# --------------------------------------------------------------------------- #
# Resources — each guideline is also addressable by URI
# --------------------------------------------------------------------------- #


@mcp.resource("codestyle://guideline/{name}")
def guideline_resource(name: str) -> str:
    """Expose a guideline's raw markdown as an MCP resource.

    `name` may be the doc filename ('never_hardcode.md'), its stem, or the
    topic display name — the same lookup as codestyle_get_guideline.
    """
    topic = _find_topic(name)
    if topic is None or topic.doc is None:
        raise FileNotFoundError(f"No guideline named '{name}'")
    return _read_doc(topic.doc)


if __name__ == "__main__":
    mcp.run()

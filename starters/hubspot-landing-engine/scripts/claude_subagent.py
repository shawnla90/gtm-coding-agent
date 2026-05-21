"""Claude subagent wrapper.

Two routes:

  PATH A - `claude` CLI subprocess (default).
      Inherits your Claude Code Max session. No API key needed.
      Bills against subscription, not metered tokens. The pattern is
      documented in this repo's engine/claude-subprocess.md.

  PATH B - anthropic SDK (when --use-sdk is passed or ANTHROPIC_API_KEY is set
      and the CLI is unavailable).
      Routes through the official Python SDK. Useful for CI, non-Mac runners,
      or any environment where the CLI isn't installed.

Each subagent takes a column prompt file + input context, returns parsed JSON
matching the column's output_schema.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

DEFAULT_TIMEOUT_SEC = 180


@dataclass
class ColumnSpec:
    slug: str
    model: str
    inputs: list[str]
    output_schema: dict
    body: str  # the prompt body after frontmatter

    @property
    def system_prompt(self) -> str:
        return (
            "You are a focused B2B GTM analyst. Return ONLY valid JSON matching "
            "the schema. No prose, no preamble, no markdown fences.\n\n"
            f"Schema: {json.dumps(self.output_schema)}\n\n"
            f"{self.body.strip()}"
        )


def load_column(column_file: Path) -> ColumnSpec:
    """Parse a column prompt file (frontmatter YAML + markdown body)."""
    text = column_file.read_text()
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError(f"{column_file}: missing YAML frontmatter")
    fm = yaml.safe_load(m.group(1))
    return ColumnSpec(
        slug=fm["column_slug"],
        model=fm.get("model", "sonnet"),
        inputs=fm.get("inputs", []),
        output_schema=fm.get("output_schema", {}),
        body=m.group(2),
    )


def _cli_available() -> bool:
    return shutil.which("claude") is not None


def _run_cli(model: str, system: str, user: str, timeout: int = DEFAULT_TIMEOUT_SEC) -> str:
    """Path A: shell out to the claude CLI in --print mode."""
    prompt = f"{system}\n\n---\n\n{user}"
    result = subprocess.run(
        ["claude", "--print", "--model", model],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (exit={result.returncode}): {result.stderr[:400]}"
        )
    return result.stdout.strip()


def _run_sdk(model: str, system: str, user: str, timeout: int = DEFAULT_TIMEOUT_SEC) -> str:
    """Path B: anthropic Python SDK."""
    # Local import so the starter still works without the SDK installed if you
    # never use this path.
    from anthropic import Anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set and the claude CLI is unavailable. "
            "Either set the key, install the CLI (brew install anthropic/tap/claude-code), "
            "or remove --use-sdk."
        )
    client = Anthropic(api_key=api_key, timeout=timeout)
    # Map "opus | sonnet | haiku" hint to current model IDs. Update when new
    # models drop; the values here track Claude 4.x.
    model_map = {
        "opus": "claude-opus-4-7",
        "sonnet": "claude-sonnet-4-6",
        "haiku": "claude-haiku-4-5-20251001",
    }
    model_id = model_map.get(model, "claude-sonnet-4-6")
    message = client.messages.create(
        model=model_id,
        max_tokens=2000,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()


def _strip_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json fences. Strip them."""
    text = text.strip()
    fence_match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def run_column(
    column: ColumnSpec,
    context: dict,
    *,
    use_sdk: bool = False,
    model_override: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    retries: int = 2,
) -> dict:
    """Run one column subagent. Returns parsed JSON matching the schema."""
    model = model_override or column.model
    system = column.system_prompt
    user = "Context for this account:\n\n" + json.dumps(context, indent=2)

    route = _run_sdk if (use_sdk or not _cli_available()) else _run_cli

    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            raw = route(model, system, user, timeout=timeout)
            parsed = json.loads(_strip_fences(raw))
            return parsed
        except (json.JSONDecodeError, RuntimeError) as e:
            last_err = e
            # Make the retry prompt nudge the model toward strict JSON.
            user = (
                "Context for this account (your previous response failed to parse as "
                "JSON; return ONLY a JSON object, no fences, no commentary):\n\n"
                + json.dumps(context, indent=2)
            )
    raise RuntimeError(
        f"Column '{column.slug}' failed after {retries + 1} attempts. Last error: {last_err}"
    )

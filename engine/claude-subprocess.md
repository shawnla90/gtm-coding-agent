# Claude as a subprocess

**Used in:** Nexus Intel starter (`scripts/analyze_content.py`, `scripts/generate_insights.py`).

Most GTM code calls Claude via the hosted API: import the SDK, pay per token, round-trip to the cloud. That is the right default for real-time chat, agent loops, or anything user-facing. For batch analysis (turning scraped content into structured signals), a subprocess to the `claude` CLI is faster, cheaper, and easier to reason about.

## The pattern

```python
import json
import subprocess

def analyze(content: dict) -> dict:
    prompt = build_prompt(content)  # your signal taxonomy + the content
    result = subprocess.run(
        ["claude", "--print", "--model", "opus"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=300,
    )
    return json.loads(result.stdout)
```

`--print` makes the CLI emit the full response to stdout and exit. `--model` selects the tier (opus for quality, sonnet for balance, haiku for cost). Batch dozens of items in parallel with `asyncio.subprocess` or a thread pool.

## Why not the SDK

The hosted API charges per input and output token on every call. For a batch analysis job sending 50 content items through Claude, the SDK round-trip has three costs: token spend, network latency, and rate limits.

The `claude` CLI uses your active Claude.com subscription. You pay a flat monthly fee rather than metered tokens. For bulk batch work that runs overnight on your own machine, the subscription economics win by an order of magnitude.

The other win is composition. Subprocess output is pipeable. You can run `python3 scripts/scrape_*.py | python3 scripts/analyze_content.py | tee analysis-log.jsonl` and the whole pipeline is a Unix pipe. Try that with an SDK.

## When NOT to use this

- **User-facing chat or agents.** Use the SDK. Subprocess is too slow for interactive loops.
- **Production serverless.** You can't shell out to `claude` inside a Vercel or Railway function. The CLI isn't in the runtime.
- **When you need streaming.** The subprocess call blocks until the full response is returned. For interactive chat, use `anthropic.messages.stream()`.

## Installation

```bash
# Mac
brew install anthropic/tap/claude-code

# Linux
curl -fsSL https://claude.ai/install.sh | bash

# Then authenticate
claude login
```

Installs the `claude` CLI globally. `claude --print <prompt>` is the one-shot mode we use in subprocess calls.

## Handling failures

The CLI exits with a non-zero code on auth failures, rate limits, or model errors. Always check `result.returncode` and log `result.stderr` for diagnostics. Build a retry with exponential backoff for transient failures.

```python
for attempt in range(3):
    result = subprocess.run(...)
    if result.returncode == 0:
        return json.loads(result.stdout)
    time.sleep(2 ** attempt)
raise RuntimeError(f"Claude subprocess failed: {result.stderr}")
```

## Timeouts

Opus on a 10-post batch can take 2 to 3 minutes. Set `timeout=300` on your subprocess call. If you batch more aggressively (20+ items), raise it to 600. A hung subprocess is worse than a failed one. It blocks your cron.

## Piping content in

If your prompt is longer than your shell's `ARG_MAX` (roughly 100 KB on macOS, 2 MB on Linux), pass it via stdin:

```python
result = subprocess.run(
    ["claude", "--print", "--model", "opus"],
    input=prompt,          # bytes or str; goes to stdin
    capture_output=True,
    text=True,
)
```

This is what `analyze_content.py` does. The full content payload plus system prompt routinely exceeds 50 KB per call.

## Cost sanity check

At Shawn's running rate (Max plan, about 6 parallel Claude Code sessions, nightly batch analysis across 5 intel instances): zero per-token cost for batch work, flat monthly subscription. Running the same workload via the SDK would cost roughly $30 to $50 per day in Opus output tokens. Over a month, the subprocess pattern saves $900 to $1,500.

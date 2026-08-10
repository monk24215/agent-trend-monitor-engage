"""Wire a REAL model into the engine. This is the ONE place credentials live.

SETUP (do these four things — see the README section 'Going live'):
  1. pip install anthropic
  2. Get an API key from https://console.anthropic.com  (Settings -> API Keys)
  3. Set it as an environment variable named ANTHROPIC_API_KEY
  4. Run:  python -m tmea.provider   (a self-test), then run the pipeline normally.

Once this file's set_up() has been called, every llm() call in the engine uses
the real model. Nothing else in the codebase changes. To go back to the mock,
just don't call set_up() (or unset the env var).
"""
from __future__ import annotations
import os
from .llm import set_provider

MODEL = "claude-sonnet-4-6"   # good balance of quality/speed/cost for headlines
MAX_TOKENS = 200              # headlines are short; keep calls cheap


def _make_caller():
    """Returns a function (prompt:str) -> str that calls Claude."""
    from anthropic import Anthropic  # imported here so the engine runs without it
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Set the environment variable first.\n"
            "  Windows (PowerShell):  $env:ANTHROPIC_API_KEY='sk-...'\n"
            "  Windows (cmd):         set ANTHROPIC_API_KEY=sk-...\n"
            "  macOS/Linux:           export ANTHROPIC_API_KEY=sk-...")
    client = Anthropic(api_key=key)

    def call(prompt: str) -> str:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        # concatenate any text blocks the model returns
        return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()

    return call


def set_up() -> None:
    """Register the real Claude provider. Call this before run() to go live."""
    set_provider(_make_caller())


if __name__ == "__main__":
    # Self-test: proves your key + install work before you run the whole pipeline.
    set_up()
    from .llm import llm
    print("Testing real model call...")
    out = llm("Write one short survival-blog headline about fire-starting.",
              purpose="selftest")
    print("MODEL SAID:", out)
    print("\nSuccess — real provider works. Now run:  python -m tmea.run")

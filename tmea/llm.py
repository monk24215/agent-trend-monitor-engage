"""The single model seam. Every model call in the whole engine goes through
llm(). Swap providers here and nowhere else — this is the ONE fixed dependency
point, kept deliberately at the edge so the spine stays deterministic.

Design:
- `llm(prompt, *, purpose, ctx)` is the only entry point the agents use.
- A provider is any callable: (prompt:str) -> str. Register one with set_provider().
- If none is registered, the deterministic MOCK runs, so the pipeline works
  end-to-end today with zero credentials and identical shapes to real output.
- Every call is logged (prompt + response + purpose) so the model's judgment
  is part of the audit trail — no holes in history where the reasoning happened.
"""
from __future__ import annotations
import hashlib
from typing import Callable, Optional

_provider: Optional[Callable[[str], str]] = None


def set_provider(fn: Callable[[str], str]) -> None:
    """Register the real model. `fn` takes a prompt string, returns text.
    Example (Claude, pseudo):
        set_provider(lambda p: anthropic_client.messages.create(...).content[0].text)
    """
    global _provider
    _provider = fn


def _mock(prompt: str) -> str:
    """Deterministic stand-in. Same prompt -> same output, so runs are
    reproducible and testable. It echoes a stable, structured line derived
    from the prompt hash — enough for the pipeline to flow and be inspected."""
    h = hashlib.sha256(prompt.encode()).hexdigest()[:8]
    return f"[MOCK:{h}] " + prompt.strip().splitlines()[-1][:120]


def llm(prompt: str, *, purpose: str = "", ctx=None) -> str:
    """The only model entry point. `ctx` (a RunContext) if given captures the
    call into the build log."""
    provider = _provider or _mock
    used = "real" if _provider else "mock"
    response = provider(prompt)
    if ctx is not None:
        ctx.log("llm_call", {"purpose": purpose, "provider": used,
                             "prompt": prompt, "response": response})
    return response

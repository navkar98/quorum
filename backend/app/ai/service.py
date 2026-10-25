"""AI service facade. Chooses a provider and guarantees a safe deterministic fallback.

If QUORUM_LLM_API_KEY is set, an LLMProvider is attempted with a timeout; on any failure
or timeout we fall back to the RulesProvider and the result is labeled kind="rules".

The service never performs authority actions (approve alerts, set statuses). It only
returns advisory analysis.
"""
from __future__ import annotations

from typing import Optional

from .. import config
from .base import Analysis
from .rules import RulesProvider

_rules = RulesProvider()


def get_provider_name() -> str:
    return "llm+rules-fallback" if config.LLM_API_KEY else "rules"


def analyze(text: Optional[str], image_path: Optional[str]) -> Analysis:
    # Input size guard — treat as untrusted.
    if text and len(text) > 5000:
        text = text[:5000]

    if config.LLM_API_KEY:
        try:
            from .llm import LLMProvider

            result = LLMProvider().analyze_report(text, image_path)
            if result is not None:
                result.kind = "ai"
                return result
        except Exception:
            # Fall through to deterministic rules; label stays "rules".
            pass

    return _rules.analyze_report(text, image_path)

"""Optional LLM provider (modular opt-in).

Enabled only when QUORUM_LLM_API_KEY is set. This is a thin, timeout-wrapped stub that
shows the intended integration point. It deliberately returns None if it cannot produce
a trustworthy result so service.py falls back to the deterministic RulesProvider.

Kiro CLI note: before relying on Kiro CLI for headless text/image analysis, its support
must be verified. Until verified, this provider is a placeholder and the default path is
rules-only, so the demo always works offline.
"""
from __future__ import annotations

from typing import Optional

from .. import config
from .base import Analysis
from .rules import RulesProvider


class LLMProvider:
    name = "llm"

    def analyze_report(
        self, text: Optional[str], image_path: Optional[str]
    ) -> Optional[Analysis]:
        # Placeholder: a real implementation would call an inference API here within
        # config.LLM_TIMEOUT_SEC. We intentionally return None so the service falls
        # back to deterministic rules rather than fabricating AI output.
        _ = (text, image_path, config.LLM_TIMEOUT_SEC)
        return None


# Reuse the rules lexicons for any hybrid enrichment if desired later.
_rules = RulesProvider()

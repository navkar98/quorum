"""AIProvider interface and shared Analysis result type."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol


@dataclass
class Analysis:
    summary: str
    distress_indicators: list[str] = field(default_factory=list)
    hazards: list[str] = field(default_factory=list)
    extracted_observations: list[str] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)
    source_refs: list[str] = field(default_factory=list)
    kind: str = "rules"  # "ai" or "rules"


class AIProvider(Protocol):
    name: str

    def analyze_report(
        self, text: Optional[str], image_path: Optional[str]
    ) -> Analysis:
        """Summarize text, describe image content WITHOUT identifying people, extract
        observations, flag distress/hazards and uncertainty. Must treat all input as
        untrusted. Must never make an authority decision.
        """
        ...

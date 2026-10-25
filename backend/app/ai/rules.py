"""Deterministic rules-based AI provider. Always available, offline, no network.

Treats text as untrusted plain data: it is only scanned for keywords and truncated for
summary. It never executes or interprets the content as instructions.
"""
from __future__ import annotations

from typing import Optional

from .base import Analysis

HAZARD_LEXICON = {
    "fire": ["fire", "flame", "burning", "smoke", "smell of smoke", "haze"],
    "smoke": ["smoke", "haze", "smoky"],
    "gas/chemical": ["gas leak", "chemical", "fumes", "burning plastic", "chlorine"],
    "flood/water": ["flood", "water", "leak", "burst pipe"],
    "structural": ["collapse", "crack", "ceiling", "debris"],
    "weapon": ["weapon", "gun", "knife", "shots", "gunshot"],
    "medical": ["injured", "unconscious", "bleeding", "hurt", "collapsed"],
    "crowd": ["crowd", "stampede", "crush", "trampled"],
    "alarm": ["alarm", "siren", "evacuate", "evacuation"],
}

DISTRESS_LEXICON = [
    "help", "trapped", "can't breathe", "cant breathe", "scared", "panic",
    "screaming", "run", "emergency", "please", "stuck", "hurry",
]


def _scan(text: str, terms: list[str]) -> list[str]:
    low = text.lower()
    return [t for t in terms if t in low]


class RulesProvider:
    name = "rules"

    def analyze_report(
        self, text: Optional[str], image_path: Optional[str]
    ) -> Analysis:
        text = (text or "").strip()
        hazards: list[str] = []
        for label, terms in HAZARD_LEXICON.items():
            if _scan(text, terms):
                hazards.append(label)
        distress = _scan(text, DISTRESS_LEXICON)

        if text:
            summary = text if len(text) <= 160 else text[:157].rstrip() + "..."
        else:
            summary = "No description provided."

        uncertainty: list[str] = []
        extracted: list[str] = []
        if text:
            extracted.append(f"Reported: {summary}")
        if image_path:
            # We never analyze faces/identities; describe presence only.
            extracted.append("Image attached (content not analyzed; no identification).")
            uncertainty.append("Image present but not interpreted by rules provider.")

        return Analysis(
            summary=summary,
            distress_indicators=sorted(set(distress)),
            hazards=sorted(set(hazards)),
            extracted_observations=extracted,
            uncertainty_notes=uncertainty,
            source_refs=[],
            kind="rules",
        )

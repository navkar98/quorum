"""Modular AI layer. Default is a deterministic rules provider that always works
offline; an optional LLM provider can be enabled via env var and falls back to rules
on timeout or error.
"""
from .service import analyze, get_provider_name

__all__ = ["analyze", "get_provider_name"]

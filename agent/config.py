#!/usr/bin/env python3
"""Runtime configuration for the Notely AI PM analytics agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


DEFAULT_OLLAMA_MODEL = "llama3.1:8b"
DEFAULT_OPENAI_MODEL = "gpt-4.1-mini"


@dataclass(frozen=True)
class AgentConfig:
    """Configuration values that can be changed without editing agent logic."""

    provider: str
    model: str
    temperature: float = 0.0
    max_tool_rounds: int = 4
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: Optional[str] = None

    @classmethod
    def from_env(cls) -> "AgentConfig":
        provider = os.getenv("NOTELY_LLM_PROVIDER", "ollama").strip().lower()
        default_model = DEFAULT_OPENAI_MODEL if provider == "openai" else DEFAULT_OLLAMA_MODEL
        return cls(
            provider=provider,
            model=os.getenv("NOTELY_LLM_MODEL", default_model).strip(),
            temperature=float(os.getenv("NOTELY_LLM_TEMPERATURE", "0")),
            max_tool_rounds=int(os.getenv("NOTELY_MAX_TOOL_ROUNDS", "4")),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/"),
            openai_base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

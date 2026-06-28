#!/usr/bin/env python3
"""LLM provider adapters for Ollama and OpenAI chat-style tool calling."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agent.config import AgentConfig


class LLMProviderError(RuntimeError):
    """Raised when an LLM provider cannot complete a request."""


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class ProviderResponse:
    content: str
    assistant_message: Dict[str, Any]
    tool_calls: List[ToolCall]
    raw: Dict[str, Any]


class BaseProvider:
    """Small common interface used by the PM analytics agent."""

    def __init__(self, config: AgentConfig) -> None:
        self.config = config

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ProviderResponse:
        raise NotImplementedError

    def tool_result_message(self, call: ToolCall, content: str) -> Dict[str, Any]:
        return {
            "role": "tool",
            "tool_call_id": call.id,
            "name": call.name,
            "content": content,
        }


class OllamaProvider(BaseProvider):
    """Provider for local Ollama models such as llama3.1:8b."""

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ProviderResponse:
        payload = {
            "model": self.config.model,
            "messages": self._prepare_messages(messages),
            "stream": False,
            "options": {"temperature": self.config.temperature},
        }
        if tools:
            payload["tools"] = tools
        raw = _post_json(f"{self.config.ollama_base_url}/api/chat", payload)
        message = raw.get("message", {})
        tool_calls = _parse_ollama_tool_calls(message.get("tool_calls") or [])
        return ProviderResponse(
            content=message.get("content") or "",
            assistant_message=self._normalize_assistant_message(message, tool_calls),
            tool_calls=tool_calls,
            raw=raw,
        )

    def _prepare_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        prepared = []
        for message in messages:
            role = message["role"]
            if role == "tool":
                prepared.append(
                    {
                        "role": "tool",
                        "content": message.get("content", ""),
                        "name": message.get("name", ""),
                    }
                )
                continue
            clean_message = {"role": role, "content": message.get("content", "")}
            if message.get("tool_calls"):
                clean_message["tool_calls"] = [
                    {
                        "function": {
                            "name": call["function"]["name"],
                            "arguments": _loads_json_object(call["function"].get("arguments", {})),
                        }
                    }
                    for call in message["tool_calls"]
                ]
            prepared.append(clean_message)
        return prepared

    def _normalize_assistant_message(
        self,
        message: Dict[str, Any],
        tool_calls: List[ToolCall],
    ) -> Dict[str, Any]:
        normalized = {"role": "assistant", "content": message.get("content") or ""}
        if tool_calls:
            normalized["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments, ensure_ascii=True),
                    },
                }
                for call in tool_calls
            ]
        return normalized


class OpenAIProvider(BaseProvider):
    """Provider for OpenAI Chat Completions style tool calling."""

    def chat(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> ProviderResponse:
        if not self.config.openai_api_key:
            raise LLMProviderError("OPENAI_API_KEY is not set.")
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        raw = _post_json(
            f"{self.config.openai_base_url}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.config.openai_api_key}"},
        )
        message = raw["choices"][0]["message"]
        tool_calls = _parse_openai_tool_calls(message.get("tool_calls") or [])
        return ProviderResponse(
            content=message.get("content") or "",
            assistant_message=message,
            tool_calls=tool_calls,
            raw=raw,
        )


def build_provider(config: AgentConfig) -> BaseProvider:
    provider = config.provider.lower()
    if provider == "ollama":
        return OllamaProvider(config)
    if provider == "openai":
        return OpenAIProvider(config)
    raise LLMProviderError(f"Unsupported provider: {config.provider}. Use ollama or openai.")


def _post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    request_headers = {"Content-Type": "application/json"}
    request_headers.update(headers or {})
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=request_headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise LLMProviderError(f"Provider HTTP error {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise LLMProviderError(f"Provider connection failed: {exc.reason}") from exc


def _parse_openai_tool_calls(raw_calls: List[Dict[str, Any]]) -> List[ToolCall]:
    calls = []
    for idx, raw_call in enumerate(raw_calls):
        function = raw_call.get("function", {})
        calls.append(
            ToolCall(
                id=raw_call.get("id") or f"call_{idx}",
                name=function.get("name", ""),
                arguments=_loads_json_object(function.get("arguments", "{}")),
            )
        )
    return calls


def _parse_ollama_tool_calls(raw_calls: List[Dict[str, Any]]) -> List[ToolCall]:
    calls = []
    for idx, raw_call in enumerate(raw_calls):
        function = raw_call.get("function", {})
        calls.append(
            ToolCall(
                id=raw_call.get("id") or f"ollama_call_{idx}",
                name=function.get("name", ""),
                arguments=_loads_json_object(function.get("arguments", {})),
            )
        )
    return calls


def _loads_json_object(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        if not value.strip():
            return {}
        parsed = json.loads(value)
        if isinstance(parsed, dict):
            return parsed
    raise LLMProviderError(f"Tool arguments must be a JSON object, got: {value!r}")

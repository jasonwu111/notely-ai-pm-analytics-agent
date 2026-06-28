#!/usr/bin/env python3
"""Command-line demo for the Notely AI PM Analytics Agent with an LLM provider.

Default provider is Ollama, which runs locally and avoids API cost.

Examples:
    python3 llm_agent_demo.py --check
    python3 llm_agent_demo.py "Why did iOS activation drop in mid May 2026?"
    NOTELY_LLM_PROVIDER=openai OPENAI_API_KEY=... python3 llm_agent_demo.py "Summarize weekly PM metrics."
"""

from __future__ import annotations

import argparse
import sys
from pprint import pprint

from agent.config import AgentConfig
from agent.pm_agent import PMAnalyticsAgent
from agent.providers import LLMProviderError
from agent.tool_registry import TOOL_SCHEMAS


DEFAULT_QUESTION = "Why did iOS activation and upload completion change around mid May 2026?"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Notely AI PM analytics LLM agent.")
    parser.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    parser.add_argument("--check", action="store_true", help="Print configuration and tool names without calling an LLM.")
    parser.add_argument("--show-trace", action="store_true", help="Show tool calls and compact tool outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = AgentConfig.from_env()

    if args.check:
        print("Agent configuration")
        pprint(
            {
                "provider": config.provider,
                "model": config.model,
                "temperature": config.temperature,
                "max_tool_rounds": config.max_tool_rounds,
                "ollama_base_url": config.ollama_base_url,
                "openai_base_url": config.openai_base_url,
                "openai_api_key_set": bool(config.openai_api_key),
            }
        )
        print("\nAvailable function-calling tools")
        for schema in TOOL_SCHEMAS:
            print("-", schema["function"]["name"])
        return

    agent = PMAnalyticsAgent.from_env()
    try:
        result = agent.ask(args.question)
    except LLMProviderError as exc:
        print("\nLLM provider error")
        print(str(exc))
        if config.provider == "ollama":
            print(
                "\nYou are using the Ollama provider. Make sure Ollama is installed, "
                "the local server is running, and the selected model has been pulled.\n\n"
                "Try these commands in Terminal:\n"
                "  ollama --version\n"
                f"  ollama pull {config.model}\n"
                "  ollama serve\n\n"
                "Then open another Terminal window and rerun this demo."
            )
        elif config.provider == "openai":
            print(
                "\nYou are using the OpenAI provider. Check OPENAI_API_KEY, "
                "model access, billing, and rate limits."
            )
        sys.exit(1)

    print("\nQuestion")
    print(result.question)
    print("\nAnswer")
    print(result.answer)

    if args.show_trace:
        print("\nTool trace")
        for idx, step in enumerate(result.trace, start=1):
            print(f"\n{idx}. {step.tool_name}")
            pprint(step.arguments)
            print(step.output_preview)


if __name__ == "__main__":
    main()

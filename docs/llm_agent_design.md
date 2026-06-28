# LLM Agent API Layer

This document explains the first LLM-backed version of the Notely AI PM Analytics Agent.

## Why This Layer Exists

The project already has deterministic analytics tools in `agent/tools.py`. Those tools can list tables, describe schemas, run safe read-only SQL, calculate trusted metrics, return weekly report rows, and retrieve product context.

The LLM layer adds a reasoning loop on top:

1. A PM asks a natural-language question.
2. The LLM decides which analytics tool to call.
3. Python executes the trusted tool locally.
4. The tool result goes back to the LLM.
5. The LLM writes a business-facing answer.

This is function calling: the LLM does not directly touch the database. It requests a known function with structured arguments, and Python decides what is allowed.

## File Map

- `agent/config.py`: reads provider, model, API key, base URLs, and behavior settings from environment variables.
- `agent/tool_registry.py`: exposes the existing Python tools as function-calling schemas and executes approved tool calls.
- `agent/providers.py`: contains provider adapters for Ollama and OpenAI.
- `agent/pm_agent.py`: contains the actual agent loop.
- `llm_agent_demo.py`: command-line demo for testing the agent.
- `notebooks/04_llm_agent_api_layer.ipynb`: learning notebook for this layer.

## Default Local Setup: Ollama / Llama

Ollama runs a model locally on your machine, so it is useful for cheap repeated testing.

Install Ollama from its official website, then run:

```bash
ollama --version
ollama pull llama3.1:8b
ollama serve
```

In another terminal, from the project root:

```bash
export NOTELY_LLM_PROVIDER=ollama
export NOTELY_LLM_MODEL=llama3.1:8b
python3 llm_agent_demo.py --check
python3 llm_agent_demo.py --show-trace "Why did iOS activation change around mid May 2026?"
```

If your laptop is slow with `llama3.1:8b`, try a smaller local model and change `NOTELY_LLM_MODEL`.

To check whether the Ollama local server is reachable:

```bash
curl http://localhost:11434/api/tags
```

If you see `Connection refused`, the agent code is fine but the Ollama server is not running. Start it with `ollama serve`, or open the Ollama desktop app if you installed the macOS app.

## OpenAI Setup Later

The code is already structured so OpenAI can be used later without rewriting the agent loop.

```bash
export NOTELY_LLM_PROVIDER=openai
export OPENAI_API_KEY="your_api_key_here"
export NOTELY_LLM_MODEL=gpt-4.1-mini
python3 llm_agent_demo.py --show-trace "Give me the latest weekly PM report."
```

Do not put a real API key into source code. Use environment variables.

## Environment Variables

- `NOTELY_LLM_PROVIDER`: `ollama` or `openai`. Defaults to `ollama`.
- `NOTELY_LLM_MODEL`: model name. Defaults to `llama3.1:8b` for Ollama.
- `OLLAMA_BASE_URL`: defaults to `http://localhost:11434`.
- `OPENAI_API_KEY`: required only when provider is `openai`.
- `OPENAI_BASE_URL`: defaults to `https://api.openai.com/v1`.
- `NOTELY_LLM_TEMPERATURE`: defaults to `0`.
- `NOTELY_MAX_TOOL_ROUNDS`: max function-calling rounds. Defaults to `4`.

## What To Test First

Good first questions:

```text
What tables are available in the database?
```

```text
Why did iOS activation change around mid May 2026?
```

```text
Compare paid conversion rate by acquisition channel in June 2026.
```

```text
Give me a PM-style weekly report for the week starting 2026-06-01.
```

## Debugging Mental Model

If the answer looks wrong, inspect the tool trace first.

- If the tool call is wrong, improve the system prompt or tool descriptions.
- If the tool output is right but the final answer is weak, improve the final-answer instructions.
- If the SQL is wrong, use trusted metric tools instead of letting the model write SQL.
- If the provider fails, check local Ollama status or API key/rate limits.
- If Ollama returns `Connection refused`, start the Ollama server before running `llm_agent_demo.py`.

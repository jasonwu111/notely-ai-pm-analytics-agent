# Notely AI PM Analytics Agent

Notely AI PM Analytics Agent is a portfolio project for building an AI-powered analytics copilot for product managers.

The fictional product, Notely AI, is an AI meeting assistant. Users can upload meeting recordings, generate transcripts, produce AI summaries, extract action items, share meeting notes, and upgrade from a free plan to a Pro subscription.

The project goal is to simulate a realistic product analytics environment, then build an agent that can:

- Answer product metric questions in natural language.
- Generate and safely execute SQL against a local analytics database.
- Explain funnel, retention, engagement, and monetization changes.
- Produce weekly and monthly PM business reports.
- Use product documentation, event taxonomy, metric definitions, release notes, experiment notes, and incident logs as RAG context.

## Planned Scope

1. Define the product story and user journeys.
2. Define event taxonomy, metrics, and report requirements.
3. Generate simulated product analytics data with embedded business storylines.
4. Create a local SQLite analytics database.
5. Validate the data with hand-written SQL.
6. Build a SQL analytics agent.
7. Add RAG over product docs and incident logs.
8. Add automated weekly and monthly reporting.

## Project Assets

The `assets/` folder contains early visual mockups for explaining the product and analytics reporting experience:

- `notely-ai-product-mockup.png`: high-level mockup of the Notely AI product experience.
- `notely-ai-weekly-report-mockup.png`: high-level mockup of the automated PM weekly report.
- `notely-ai-er-diagram.svg`: source-of-truth ER diagram for the analytics database.
- `notely-ai-er-diagram.png`: PNG export of the ER diagram for presentations and notebooks.

To regenerate the ER diagram:

```bash
python3 scripts/generate_er_diagram.py
```

## Current Data Simulation

The first simulated database is a local SQLite file at:

```text
data/notely_ai.sqlite
```

It includes:

- 19K+ simulated users.
- 330K+ product events.
- Sessions, experiments, subscriptions, invoices, payments, and support tickets.
- A `product_calendar` table with launches, incidents, experiments, pricing changes, and campaign changes.

To regenerate the database:

```bash
python3 scripts/generate_data.py
```

To validate the embedded business storylines:

```bash
sqlite3 -header -column data/notely_ai.sqlite ".read sql/validation_queries.sql"
```

The simulation intentionally includes:

- iOS upload bug from 2026-05-10 to 2026-05-17.
- Action items feature launch on 2026-04-15.
- Free plan limit change on 2026-05-25.
- Paid search quality decline starting 2026-06-01.
- Onboarding flow v2 experiment from 2026-03-01 to 2026-04-30.

## Exploration Notebook

The `notebooks/` folder contains a starter exploration notebook:

- `01_table_exploration.ipynb`: connects to the SQLite database, lists tables, previews schemas, samples rows, and runs starter analysis queries for activation, retention, paid search quality, onboarding experiments, billing persistence, and weekly PM report metrics.
- `02_metric_analysis.ipynb`: turns the tables into business analysis. It walks through activation, iOS upload reliability, paid search quality, onboarding experiment impact, action items retention, the Free limit change, and the weekly PM report prototype.
- `03_agent_tool_layer.ipynb`: explains and demonstrates the deterministic Python tools that the future AI agent can call.
- `04_llm_agent_api_layer.ipynb`: explains the first LLM-backed agent layer, including provider config, function schemas, and how Ollama/OpenAI can be swapped.

## Metric Layer

The `sql/metrics/` folder contains reusable SQL definitions for the first metric layer:

- `growth_metrics.sql`
- `activation_metrics.sql`
- `engagement_metrics.sql`
- `retention_metrics.sql`
- `monetization_metrics.sql`

The `sql/reports/` folder contains report-level SQL:

- `weekly_pm_report.sql`

These SQL files are the bridge between manual analytics and the future AI agent. Later, function-calling tools can invoke trusted metric logic instead of asking the model to invent metric definitions from scratch.

## Agent Tool Layer

The `agent/` folder contains the local tool layer:

- `agent/tools.py`: deterministic Python functions for listing tables, describing schemas, safely running read-only SQL, retrieving trusted metrics, retrieving weekly report rows, and retrieving product context.
- `agent_demo.py`: a small command-line demo that exercises the tool layer without using an LLM.

To run the local tool demo:

```bash
python3 agent_demo.py
```

This layer is the direct precursor to function calling. The next step is to expose these functions to an LLM so it can decide which tool to call for a PM question.

## LLM Agent Layer

The first LLM-backed agent layer is provider-based, so local Ollama testing and later OpenAI API testing can use the same agent loop.

Key files:

- `agent/config.py`: reads provider, model, API keys, base URLs, temperature, and max tool rounds from environment variables.
- `agent/tool_registry.py`: converts the deterministic Python tools into function-calling schemas and dispatches approved tool calls.
- `agent/providers.py`: contains provider adapters for Ollama and OpenAI.
- `agent/pm_agent.py`: runs the function-calling loop.
- `llm_agent_demo.py`: command-line demo for asking PM analytics questions through an LLM.

To inspect the configuration without calling an LLM:

```bash
python3 llm_agent_demo.py --check
```

For local Ollama testing:

```bash
ollama pull llama3.1:8b
ollama serve
export NOTELY_LLM_PROVIDER=ollama
export NOTELY_LLM_MODEL=llama3.1:8b
python3 llm_agent_demo.py --show-trace "Why did iOS activation change around mid May 2026?"
```

For OpenAI testing later:

```bash
export NOTELY_LLM_PROVIDER=openai
export OPENAI_API_KEY="your_api_key_here"
export NOTELY_LLM_MODEL=gpt-4.1-mini
python3 llm_agent_demo.py --show-trace "Give me the PM weekly report for 2026-06-01."
```

Real API keys should stay in environment variables and should not be committed to the repo.

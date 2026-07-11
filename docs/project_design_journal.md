# Project Design Journal

This file captures the learning path behind the Notely AI PM Analytics Agent project. It is not the final teaching guide. It is a running memory of design decisions so the final guide can explain the project from first principles.

## Current Learning Arc

1. Start with a realistic product story before writing code.
2. Define user journeys and funnels so the simulated data has business meaning.
3. Define event taxonomy so every product behavior has a consistent name and payload.
4. Generate a local analytics database with known storylines embedded in the data.
5. Explore the database with SQL and a notebook before building an agent.
6. Create an ER diagram so the table relationships are easy to explain.
7. Build a metric layer so business metrics have trusted definitions.
8. Use analysis notebooks to turn raw tables into business reasoning.
9. Build an agent tool layer so trusted SQL and metric logic can be called through Python functions.
10. Expose those Python tools to an AI agent through function calling.
11. Keep the LLM provider replaceable so local Llama/Ollama testing, OpenAI testing, and future providers can share the same agent loop.
12. Improve local-Ollama reliability by adding stricter prompt instructions and higher-level analytical tools for common PM workflows.
13. Add V3 trend tools so the agent can answer weekly/monthly standard metric questions without misusing group_by.
14. Later, use RAG so the agent can retrieve product context, incident logs, experiment notes, and metric definitions.

## Important Concept Distinctions

### Metric Layer vs Function Calling

The metric layer defines how metrics are calculated. It is the business logic and SQL layer.

Function calling is how an agent invokes tools. A future agent may call a function such as `get_metric("activation_rate")`, and that function can rely on the metric layer to run trusted SQL.

### Table Exploration vs Analysis Notebook

The table exploration notebook answers: what data exists, what tables exist, and what do the rows look like?

The analysis notebook answers: what business stories can we explain with this data?

### Agent Tool Layer vs Function Calling

The agent tool layer is normal Python code. It defines deterministic functions such as `list_tables`, `describe_table`, `run_sql`, `get_metric`, `get_weekly_report`, and `get_product_context`.

Function calling is the later step where the LLM is allowed to call those functions with structured arguments. The tool layer can be tested without an LLM first, which makes the final agent safer and easier to debug.

### Provider Layer vs Agent Loop

The provider layer knows how to talk to a model service. In this project, `agent/providers.py` currently supports local Ollama and OpenAI-style chat tool calling.

The agent loop knows the workflow: receive a PM question, ask the model what tool to call, run the tool, return the tool result to the model, and ask for a final answer.

Keeping these separate means the project can start with free local Llama testing through Ollama, then switch to OpenAI later by changing environment variables instead of rewriting the agent.

### Why Start With Ollama

The user's OpenAI free-tier API limits are enough for small demos, but they are tight for repeated agent testing because one PM question may require multiple model calls. Ollama lets the project test prompts, tool schemas, and agent control flow locally without spending API credits or hitting daily request limits.


### Prompting vs Higher-Level Tools

The first LLM-backed demo successfully connected Ollama to the local tool layer, but the answer quality was incomplete: the model retrieved product context, then suggested a fake SQL query instead of pulling the actual activation metric.

The fix is not only "use a stronger model." The project now treats this as an agent reliability problem:

- Prompt constraints tell the model not to invent SQL, tables, columns, or numbers.
- The metric-change SOP tells the model what analysis path to follow.
- The `diagnose_metric_change` tool packages a common PM workflow into one trusted function: before/after metric comparison, adjacent funnel metric check, and product context retrieval.

This is an important agent design lesson: when a workflow is repeatable, put the workflow into a tool instead of forcing the LLM to rediscover every step.


### Trend Tools vs Ad-Hoc SQL

A new class of PM questions asks for a metric over time, such as weekly activation rate from April through June. This is not a `group_by` problem; it is a time-grain problem.

The V3 fix adds `get_metric_timeseries` and `analyze_metric_trend` so standard metrics can be analyzed by day, week, or month. This keeps the agent on trusted metric definitions while expanding the kinds of stakeholder questions it can answer.

This is different from the future V4 safe SQL analyst. V3 answers standardized metric trend questions. V4 will handle more flexible ad-hoc SQL questions after stronger schema-reading and SQL-safety workflows are added.

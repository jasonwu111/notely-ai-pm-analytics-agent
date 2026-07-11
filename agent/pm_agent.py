#!/usr/bin/env python3
"""Agent loop that lets an LLM call trusted Notely AI analytics tools."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agent.config import AgentConfig
from agent.providers import BaseProvider, build_provider
from agent.tool_registry import TOOL_SCHEMAS, execute_tool, tool_result_to_text


SYSTEM_PROMPT = """You are the Notely AI PM Analytics Agent.

Your job is to help product managers answer analytics questions using the
available tools and the local SQLite analytics database.

Core rules:
- Never invent numbers, tables, columns, SQL, experiments, incidents, or metric definitions.
- Do not recommend SQL against tables or columns that are not present in tool output.
- If the user asks why a metric changed, dropped, improved, moved, spiked, or dipped, call diagnose_metric_change first whenever the metric can be mapped to an available metric.
- If the user asks for a metric trend, weekly/monthly/daily metric values, or whether a metric is increasing/decreasing over time, call analyze_metric_trend first.
- Treat time grain as grain, not group_by. Use grain for day/week/month and group_by only for dimensions such as platform or acquisition_channel.
- For metric-change answers, use evidence from tool output before giving a cause.
- Use get_metric for direct metric questions and get_product_context for launches, incidents, experiments, pricing changes, and campaigns.
- Use run_sql only when the trusted metric tools cannot answer the question.
- If a needed number is missing, say which tool or query is needed instead of guessing.

Metric-change analysis SOP:
1. Identify the metric, segment, approximate change date, and comparison window.
2. Pull before/after metric values with diagnose_metric_change or get_metric.
3. Check adjacent funnel metrics returned by the tool.
4. Check product context in the same date range.
5. Explain the likely driver using the evidence, and call out uncertainty.

Metric-trend analysis SOP:
1. Identify the metric, date range, time grain, and optional segment.
2. Pull the time series with analyze_metric_trend.
3. Summarize direction, first/last values, largest high/low periods, and any mixed movement.
4. Mention product context only when it plausibly explains an inflection point.

Answer format for metric-change questions:
- Start with the short answer.
- Include before vs after values and the absolute/relative change when present.
- Name the most plausible driver and why it connects to the metric.
- Add caveats or next checks if the evidence is incomplete.

Answer format for trend questions:
- Start with whether the trend is increasing, decreasing, flat, or mixed.
- Include the date range, grain, first value, last value, and relative change when present.
- Highlight the highest and lowest periods.
- Do not say group_by is unsupported when the user is asking for week/month/day; use grain instead.
"""


@dataclass
class AgentTraceStep:
    tool_name: str
    arguments: Dict[str, Any]
    output_preview: str


@dataclass
class AgentAnswer:
    question: str
    answer: str
    trace: List[AgentTraceStep] = field(default_factory=list)


class PMAnalyticsAgent:
    """Provider-agnostic PM analytics agent."""

    def __init__(
        self,
        provider: BaseProvider,
        max_tool_rounds: int = 4,
        system_prompt: str = SYSTEM_PROMPT,
    ) -> None:
        self.provider = provider
        self.max_tool_rounds = max_tool_rounds
        self.system_prompt = system_prompt

    @classmethod
    def from_env(cls) -> "PMAnalyticsAgent":
        config = AgentConfig.from_env()
        return cls(
            provider=build_provider(config),
            max_tool_rounds=config.max_tool_rounds,
        )

    def ask(self, question: str, history: Optional[List[Dict[str, Any]]] = None) -> AgentAnswer:
        messages = [{"role": "system", "content": self.system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        trace: List[AgentTraceStep] = []
        final_answer = ""

        for _ in range(self.max_tool_rounds):
            response = self.provider.chat(messages, tools=TOOL_SCHEMAS)
            messages.append(response.assistant_message)

            if not response.tool_calls:
                final_answer = response.content
                break

            for call in response.tool_calls:
                payload = execute_tool(call.name, call.arguments)
                payload_text = tool_result_to_text(payload)
                messages.append(self.provider.tool_result_message(call, payload_text))
                trace.append(
                    AgentTraceStep(
                        tool_name=call.name,
                        arguments=call.arguments,
                        output_preview=payload_text[:1200],
                    )
                )

        if not final_answer:
            messages.append(
                {
                    "role": "user",
                    "content": "Please give the best final answer now using the tool results already provided.",
                }
            )
            response = self.provider.chat(messages, tools=[])
            final_answer = response.content

        return AgentAnswer(question=question, answer=final_answer, trace=trace)

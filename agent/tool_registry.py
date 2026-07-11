#!/usr/bin/env python3
"""Function-calling schemas and dispatch for Notely AI analytics tools."""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from agent import tools as analytics_tools


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_tables",
            "description": "List available analytics database tables and row counts.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "describe_table",
            "description": "Describe one table's columns, primary key fields, and logical relationships.",
            "parameters": {
                "type": "object",
                "properties": {
                    "table_name": {
                        "type": "string",
                        "description": "Name of the table to inspect.",
                    }
                },
                "required": ["table_name"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_sql",
            "description": "Run one safe read-only SELECT or WITH SQL query against the local analytics database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "A single read-only SQLite SELECT or WITH query.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return. Defaults to 100 and cannot exceed 5000.",
                    },
                },
                "required": ["sql"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metric",
            "description": "Return a trusted product metric for a date range, optionally grouped by a supported segment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "enum": analytics_tools.available_metrics(),
                    },
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                    "group_by": {
                        "type": ["string", "null"],
                        "enum": [
                            "platform",
                            "device_type",
                            "country",
                            "region",
                            "acquisition_channel",
                            "user_segment",
                            "plan_type",
                            None,
                        ],
                    },
                },
                "required": ["metric_name", "start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weekly_report",
            "description": "Return rows from the reusable weekly PM report SQL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "week_start": {
                        "type": ["string", "null"],
                        "description": "Optional week start date in YYYY-MM-DD format.",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum rows to return.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_context",
            "description": "Retrieve launches, incidents, experiments, pricing changes, and campaigns in a date range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": "string",
                        "description": "Start date in YYYY-MM-DD format.",
                    },
                    "end_date": {
                        "type": "string",
                        "description": "End date in YYYY-MM-DD format.",
                    },
                },
                "required": ["start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_metric_timeseries",
            "description": "Return a trusted metric as a day/week/month time series. Use for weekly, monthly, daily, over-time, and trend-table requests.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "enum": analytics_tools.available_metrics()},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
                    "grain": {"type": "string", "enum": ["day", "week", "month"], "description": "Time grain for the series."},
                    "group_by": {
                        "type": ["string", "null"],
                        "enum": ["platform", "device_type", "country", "region", "acquisition_channel", "user_segment", "plan_type", None],
                        "description": "Optional segment dimension, not the time grain."
                    },
                    "segment": {"type": ["string", "null"], "description": "Optional segment value to filter to, for example iOS or paid_search."},
                },
                "required": ["metric_name", "start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_metric_trend",
            "description": "Analyze whether a trusted metric is increasing, decreasing, flat, or mixed over day/week/month periods. Use first for trend questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "enum": analytics_tools.available_metrics()},
                    "start_date": {"type": "string", "description": "Start date in YYYY-MM-DD format."},
                    "end_date": {"type": "string", "description": "End date in YYYY-MM-DD format."},
                    "grain": {"type": "string", "enum": ["day", "week", "month"], "description": "Time grain for the trend."},
                    "group_by": {
                        "type": ["string", "null"],
                        "enum": ["platform", "device_type", "country", "region", "acquisition_channel", "user_segment", "plan_type", None],
                        "description": "Optional segment dimension, not the time grain."
                    },
                    "segment": {"type": ["string", "null"], "description": "Optional segment value to filter to, for example iOS or paid_search."},
                },
                "required": ["metric_name", "start_date", "end_date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "diagnose_metric_change",
            "description": (
                "Diagnose why a known metric changed around a date. "
                "Returns before/after metric values, adjacent funnel metrics, and product context. "
                "Use this first for PM questions phrased as why did a metric change, drop, improve, or move."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {
                        "type": "string",
                        "enum": analytics_tools.available_metrics(),
                    },
                    "change_date": {
                        "type": "string",
                        "description": "Approximate change date in YYYY-MM-DD format.",
                    },
                    "segment": {
                        "type": ["string", "null"],
                        "description": "Optional segment value, for example iOS, web, paid_search, or SMB.",
                    },
                    "group_by": {
                        "type": ["string", "null"],
                        "enum": [
                            "platform",
                            "device_type",
                            "country",
                            "region",
                            "acquisition_channel",
                            "user_segment",
                            "plan_type",
                            None,
                        ],
                        "description": "Dimension that segment belongs to. Optional for common segments such as iOS, android, web, paid_search, and SMB.",
                    },
                    "window_days": {
                        "type": "integer",
                        "description": "Days before and after the change date to compare. Defaults to 7.",
                    },
                },
                "required": ["metric_name", "change_date"],
                "additionalProperties": False,
            },
        },
    },
]


TOOL_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "list_tables": analytics_tools.list_tables,
    "describe_table": analytics_tools.describe_table,
    "run_sql": analytics_tools.run_sql,
    "get_metric": analytics_tools.get_metric,
    "get_metric_timeseries": analytics_tools.get_metric_timeseries,
    "analyze_metric_trend": analytics_tools.analyze_metric_trend,
    "get_weekly_report": analytics_tools.get_weekly_report,
    "get_product_context": analytics_tools.get_product_context,
    "diagnose_metric_change": analytics_tools.diagnose_metric_change,
}


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a registered analytics tool and return a serializable envelope."""
    if name not in TOOL_FUNCTIONS:
        return {"ok": False, "error": f"Unknown tool: {name}"}
    try:
        result = TOOL_FUNCTIONS[name](**arguments)
        return {"ok": True, "tool_name": name, "result": result}
    except Exception as exc:  # Keep tool failures visible to the model.
        return {"ok": False, "tool_name": name, "error": str(exc)}


def tool_result_to_text(payload: Dict[str, Any]) -> str:
    """Serialize tool results in a compact format for the LLM."""
    return json.dumps(payload, ensure_ascii=True, default=str)

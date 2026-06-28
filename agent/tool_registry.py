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
]


TOOL_FUNCTIONS: Dict[str, Callable[..., Any]] = {
    "list_tables": analytics_tools.list_tables,
    "describe_table": analytics_tools.describe_table,
    "run_sql": analytics_tools.run_sql,
    "get_metric": analytics_tools.get_metric,
    "get_weekly_report": analytics_tools.get_weekly_report,
    "get_product_context": analytics_tools.get_product_context,
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

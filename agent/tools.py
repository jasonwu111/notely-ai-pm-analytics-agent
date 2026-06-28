#!/usr/bin/env python3
"""Local analytics tools for the Notely AI PM Analytics Agent.

This module is intentionally LLM-free. It contains deterministic Python
functions that the future AI agent can call through function calling.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "notely_ai.sqlite"
WEEKLY_REPORT_SQL_PATH = PROJECT_ROOT / "sql" / "reports" / "weekly_pm_report.sql"

BLOCKED_SQL_WORDS = {
    "alter",
    "attach",
    "create",
    "delete",
    "detach",
    "drop",
    "insert",
    "pragma",
    "replace",
    "truncate",
    "update",
    "vacuum",
}

LOGICAL_RELATIONSHIPS = {
    "sessions": [{"column": "user_id", "references": "users.user_id"}],
    "events": [
        {"column": "user_id", "references": "users.user_id"},
        {"column": "session_id", "references": "sessions.session_id"},
    ],
    "experiments": [{"column": "user_id", "references": "users.user_id"}],
    "subscriptions": [{"column": "user_id", "references": "users.user_id"}],
    "billing_invoices": [
        {"column": "subscription_id", "references": "subscriptions.subscription_id"},
        {"column": "user_id", "references": "users.user_id"},
    ],
    "payments": [
        {"column": "invoice_id", "references": "billing_invoices.invoice_id"},
        {"column": "subscription_id", "references": "subscriptions.subscription_id"},
        {"column": "user_id", "references": "users.user_id"},
    ],
    "support_tickets": [{"column": "user_id", "references": "users.user_id"}],
    "product_calendar": [],
    "users": [],
}


class ToolError(ValueError):
    """Raised when an analytics tool receives an unsafe or invalid request."""


def connect(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Open a SQLite connection with row dictionaries."""
    path = Path(db_path or DEFAULT_DB_PATH)
    if not path.exists():
        raise ToolError(f"Database does not exist: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [dict(row) for row in rows]


def list_tables(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Return all user-created tables with row counts."""
    with connect(db_path) as conn:
        tables = rows_to_dicts(
            conn.execute(
                """
                SELECT name AS table_name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            ).fetchall()
        )
        for table in tables:
            table_name = table["table_name"]
            table["row_count"] = conn.execute(f'SELECT COUNT(*) AS n FROM "{table_name}"').fetchone()["n"]
        return tables


def describe_table(table_name: str, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Return columns, primary keys, and logical foreign keys for a table."""
    safe_table = validate_identifier(table_name)
    with connect(db_path) as conn:
        exists = conn.execute(
            """
            SELECT 1
            FROM sqlite_master
            WHERE type = 'table' AND name = ?
            """,
            (safe_table,),
        ).fetchone()
        if not exists:
            raise ToolError(f"Unknown table: {table_name}")
        columns = rows_to_dicts(conn.execute(f'PRAGMA table_info("{safe_table}")').fetchall())
    return {
        "table_name": safe_table,
        "columns": [
            {
                "name": col["name"],
                "type": col["type"],
                "not_null": bool(col["notnull"]),
                "primary_key": bool(col["pk"]),
            }
            for col in columns
        ],
        "logical_foreign_keys": LOGICAL_RELATIONSHIPS.get(safe_table, []),
    }


def validate_identifier(identifier: str) -> str:
    """Validate a SQL identifier used as a table or column name."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", identifier):
        raise ToolError(f"Invalid SQL identifier: {identifier}")
    return identifier


def validate_select_sql(sql: str) -> str:
    """Validate that a query is a single read-only SELECT/WITH statement."""
    cleaned = sql.strip()
    if not cleaned:
        raise ToolError("SQL query is empty.")
    if ";" in cleaned.rstrip(";"):
        raise ToolError("Only one SQL statement is allowed.")

    statement = cleaned[:-1].strip() if cleaned.endswith(";") else cleaned
    first_word_match = re.match(r"^\s*([A-Za-z]+)", statement)
    if not first_word_match:
        raise ToolError("Could not parse SQL query.")
    first_word = first_word_match.group(1).lower()
    if first_word not in {"select", "with"}:
        raise ToolError("Only SELECT or WITH queries are allowed.")

    tokens = {token.lower() for token in re.findall(r"\b[A-Za-z_]+\b", statement)}
    blocked = sorted(tokens.intersection(BLOCKED_SQL_WORDS))
    if blocked:
        raise ToolError(f"Blocked SQL keyword(s): {', '.join(blocked)}")
    return statement


def add_limit(sql: str, limit: int) -> str:
    """Add a LIMIT clause when the query does not already have one."""
    if limit <= 0 or limit > 5000:
        raise ToolError("Limit must be between 1 and 5000.")
    if re.search(r"\blimit\s+\d+\b", sql, flags=re.IGNORECASE):
        return sql
    return f"SELECT * FROM ({sql}) AS limited_result LIMIT {limit}"


def run_sql(sql: str, limit: int = 100, db_path: Optional[Path] = None) -> Dict[str, Any]:
    """Run a safe read-only SQL query and return rows as dictionaries."""
    safe_sql = add_limit(validate_select_sql(sql), limit)
    with connect(db_path) as conn:
        try:
            rows = conn.execute(safe_sql).fetchall()
        except sqlite3.Error as exc:
            raise ToolError(f"SQL execution failed: {exc}") from exc
    return {
        "sql": safe_sql,
        "row_count": len(rows),
        "rows": rows_to_dicts(rows),
    }


def get_metric(
    metric_name: str,
    start_date: str,
    end_date: str,
    group_by: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return a trusted metric query result.

    Supported metric names:
    - new_users
    - active_users
    - activation_rate
    - upload_completion_rate
    - summaries_per_active_user
    - paid_conversion_rate
    - billing_persistence
    """
    validate_date(start_date)
    validate_date(end_date)
    if start_date > end_date:
        raise ToolError("start_date must be before or equal to end_date.")

    metric = metric_name.strip().lower()
    group_clause = build_group_clause(group_by)
    sql = metric_sql(metric, start_date, end_date, group_clause)
    result = run_sql(sql, limit=500, db_path=db_path)
    result["metric_name"] = metric
    result["start_date"] = start_date
    result["end_date"] = end_date
    result["group_by"] = group_by
    return result


def validate_date(value: str) -> None:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ToolError(f"Date must use YYYY-MM-DD format: {value}")


def build_group_clause(group_by: Optional[str]) -> Dict[str, str]:
    if not group_by:
        return {
            "select": "'overall' AS segment",
            "group": "",
            "join_select": "'overall' AS segment",
        }

    allowed = {
        "platform": "u.platform",
        "device_type": "u.device_type",
        "country": "u.country",
        "region": "u.region",
        "acquisition_channel": "u.acquisition_channel",
        "user_segment": "u.user_segment",
        "plan_type": "e.plan_type",
    }
    key = group_by.strip().lower()
    if key not in allowed:
        raise ToolError(f"Unsupported group_by: {group_by}. Supported values: {', '.join(sorted(allowed))}")
    expr = allowed[key]
    return {
        "select": f"{expr} AS segment",
        "group": "segment",
        "join_select": f"{expr} AS segment",
    }


def metric_sql(metric: str, start_date: str, end_date: str, group_clause: Dict[str, str]) -> str:
    segment_select = group_clause["select"]
    group_by = group_clause["group"]
    group_sql = f"GROUP BY {group_by}" if group_by else ""

    if metric == "new_users":
        return f"""
        SELECT
          {segment_select},
          COUNT(*) AS new_users
        FROM users u
        WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
        {group_sql}
        ORDER BY new_users DESC
        """

    if metric == "active_users":
        return f"""
        SELECT
          {segment_select},
          COUNT(DISTINCT e.user_id) AS active_users
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_date BETWEEN '{start_date}' AND '{end_date}'
        {group_sql}
        ORDER BY active_users DESC
        """

    if metric == "activation_rate":
        return f"""
        WITH user_activation AS (
          SELECT
            u.user_id,
            {segment_select},
            MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
            MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
            MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
          FROM users u
          LEFT JOIN events e
            ON u.user_id = e.user_id
           AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
          WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY u.user_id, segment
        )
        SELECT
          segment,
          COUNT(*) AS new_users,
          SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) AS activated_users,
          ROUND(1.0 * SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 3) AS activation_rate
        FROM user_activation
        GROUP BY segment
        ORDER BY activation_rate DESC
        """

    if metric == "upload_completion_rate":
        return f"""
        SELECT
          {segment_select},
          COUNT(CASE WHEN e.event_name = 'recording_upload_started' THEN 1 END) AS upload_starts,
          COUNT(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 END) AS upload_completions,
          ROUND(
            1.0 * COUNT(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 END)
            / NULLIF(COUNT(CASE WHEN e.event_name = 'recording_upload_started' THEN 1 END), 0),
            3
          ) AS upload_completion_rate
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_date BETWEEN '{start_date}' AND '{end_date}'
          AND e.event_name IN ('recording_upload_started', 'recording_upload_completed')
        {group_sql}
        ORDER BY upload_completion_rate DESC
        """

    if metric == "summaries_per_active_user":
        return f"""
        SELECT
          {segment_select},
          COUNT(DISTINCT e.user_id) AS active_users,
          COUNT(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 END) AS summaries_generated,
          ROUND(1.0 * COUNT(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 END) / NULLIF(COUNT(DISTINCT e.user_id), 0), 2) AS summaries_per_active_user
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_date BETWEEN '{start_date}' AND '{end_date}'
        {group_sql}
        ORDER BY summaries_per_active_user DESC
        """

    if metric == "paid_conversion_rate":
        return f"""
        WITH user_paid AS (
          SELECT
            u.user_id,
            {segment_select},
            MAX(CASE WHEN s.subscription_start_date BETWEEN u.signup_date AND date(u.signup_date, '+30 day') THEN 1 ELSE 0 END) AS paid_30d
          FROM users u
          LEFT JOIN events e ON u.user_id = e.user_id
          LEFT JOIN subscriptions s ON u.user_id = s.user_id
          WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY u.user_id, segment
        )
        SELECT
          segment,
          COUNT(*) AS users,
          SUM(paid_30d) AS paid_users_30d,
          ROUND(1.0 * SUM(paid_30d) / NULLIF(COUNT(*), 0), 3) AS paid_conversion_rate_30d
        FROM user_paid
        GROUP BY segment
        ORDER BY paid_conversion_rate_30d DESC
        """

    if metric == "billing_persistence":
        return f"""
        SELECT
          'overall' AS segment,
          COUNT(*) AS invoices,
          SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
          ROUND(AVG(CASE WHEN status = 'paid' THEN 1.0 ELSE 0.0 END), 3) AS billing_persistence
        FROM billing_invoices
        WHERE invoice_date BETWEEN '{start_date}' AND '{end_date}'
        """

    raise ToolError(
        "Unsupported metric_name. Supported values: "
        "new_users, active_users, activation_rate, upload_completion_rate, "
        "summaries_per_active_user, paid_conversion_rate, billing_persistence"
    )


def get_weekly_report(
    week_start: Optional[str] = None,
    limit: int = 20,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return weekly PM report rows, optionally filtered to one week."""
    if week_start:
        validate_date(week_start)
    sql = WEEKLY_REPORT_SQL_PATH.read_text().strip().rstrip(";")
    if week_start:
        sql = f"SELECT * FROM ({sql}) AS weekly_report WHERE week_start = '{week_start}'"
    result = run_sql(sql, limit=limit, db_path=db_path)
    result["week_start"] = week_start
    return result


def get_product_context(
    start_date: str,
    end_date: str,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return product launches, incidents, experiments, pricing changes, and campaigns in a date range."""
    validate_date(start_date)
    validate_date(end_date)
    sql = f"""
    SELECT
      calendar_date,
      event_type,
      title,
      description,
      affected_area
    FROM product_calendar
    WHERE calendar_date BETWEEN '{start_date}' AND '{end_date}'
    ORDER BY calendar_date
    """
    result = run_sql(sql, limit=100, db_path=db_path)
    result["start_date"] = start_date
    result["end_date"] = end_date
    return result


def available_metrics() -> List[str]:
    """Return supported metric names."""
    return [
        "new_users",
        "active_users",
        "activation_rate",
        "upload_completion_rate",
        "summaries_per_active_user",
        "paid_conversion_rate",
        "billing_persistence",
    ]

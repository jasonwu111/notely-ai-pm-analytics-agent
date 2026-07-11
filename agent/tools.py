#!/usr/bin/env python3
"""Local analytics tools for the Notely AI PM Analytics Agent.

This module is intentionally LLM-free. It contains deterministic Python
functions that the future AI agent can call through function calling.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime, timedelta
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


def get_metric_timeseries(
    metric_name: str,
    start_date: str,
    end_date: str,
    grain: str = "week",
    group_by: Optional[str] = None,
    segment: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return a trusted metric as a day/week/month time series."""
    validate_date(start_date)
    validate_date(end_date)
    if start_date > end_date:
        raise ToolError("start_date must be before or equal to end_date.")

    metric = metric_name.strip().lower()
    if metric not in available_metrics():
        raise ToolError(f"Unsupported metric_name: {metric_name}")
    safe_grain = validate_grain(grain)
    if segment and not group_by:
        group_by = infer_group_by_for_segment(segment)

    sql = metric_timeseries_sql(metric, start_date, end_date, safe_grain, group_by)
    result = run_sql(sql, limit=1000, db_path=db_path)
    rows = filter_rows_by_segment(result["rows"], segment)
    result["rows"] = rows
    result["row_count"] = len(rows)
    result["metric_name"] = metric
    result["start_date"] = start_date
    result["end_date"] = end_date
    result["grain"] = safe_grain
    result["group_by"] = group_by
    result["segment"] = segment
    result["value_key"] = metric_value_key(metric)
    return result


def analyze_metric_trend(
    metric_name: str,
    start_date: str,
    end_date: str,
    grain: str = "week",
    group_by: Optional[str] = None,
    segment: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Return metric time series plus a simple trend summary."""
    series = get_metric_timeseries(
        metric_name=metric_name,
        start_date=start_date,
        end_date=end_date,
        grain=grain,
        group_by=group_by,
        segment=segment,
        db_path=db_path,
    )
    value_key = series["value_key"]
    rows = [row for row in series["rows"] if row.get(value_key) is not None]
    summary = summarize_trend(rows, value_key)
    product_context = get_product_context(start_date, end_date, db_path=db_path)
    return {
        "metric_name": series["metric_name"],
        "start_date": start_date,
        "end_date": end_date,
        "grain": series["grain"],
        "group_by": series["group_by"],
        "segment": segment or "overall",
        "value_key": value_key,
        "timeseries": series,
        "trend_summary": summary,
        "product_context": product_context,
        "interpretation_guidance": [
            "Use the timeseries rows as the source of truth.",
            "State whether the trend is increasing, decreasing, mixed, or flat based on trend_summary.",
            "Mention product_context only when the dates plausibly explain jumps, drops, or inflection points.",
            "Do not describe time grain as group_by. Time grain is grain, such as week or month.",
        ],
    }


def diagnose_metric_change(
    metric_name: str,
    change_date: str,
    segment: Optional[str] = None,
    group_by: Optional[str] = None,
    window_days: int = 7,
    db_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Diagnose a metric change with before/after metrics and product context.

    This higher-level tool is designed for PM questions such as:
    "Why did iOS activation rate change around mid May?"

    It reduces LLM planning burden by enforcing a repeatable analytics path:
    - compare the target metric before and after the change date
    - retrieve product context around the same period
    - retrieve adjacent funnel metrics when useful
    """
    metric = metric_name.strip().lower()
    if metric not in available_metrics():
        raise ToolError(f"Unsupported metric_name: {metric_name}")
    validate_date(change_date)
    if window_days < 1 or window_days > 30:
        raise ToolError("window_days must be between 1 and 30.")

    if segment and not group_by:
        group_by = infer_group_by_for_segment(segment)

    change_dt = parse_date(change_date)
    before_start = format_date(change_dt - timedelta(days=window_days))
    before_end = format_date(change_dt - timedelta(days=1))
    after_start = change_date
    after_end = format_date(change_dt + timedelta(days=window_days))

    target_before = get_metric(metric, before_start, before_end, group_by=group_by, db_path=db_path)
    target_after = get_metric(metric, after_start, after_end, group_by=group_by, db_path=db_path)
    target_comparison = compare_metric_results(
        metric,
        target_before,
        target_after,
        segment=segment,
        before_label=f"{before_start} to {before_end}",
        after_label=f"{after_start} to {after_end}",
    )

    adjacent_metric_results = []
    for adjacent_metric in adjacent_metrics_for(metric):
        adjacent_before = get_metric(adjacent_metric, before_start, before_end, group_by=group_by, db_path=db_path)
        adjacent_after = get_metric(adjacent_metric, after_start, after_end, group_by=group_by, db_path=db_path)
        adjacent_metric_results.append(
            compare_metric_results(
                adjacent_metric,
                adjacent_before,
                adjacent_after,
                segment=segment,
                before_label=f"{before_start} to {before_end}",
                after_label=f"{after_start} to {after_end}",
            )
        )

    product_context = get_product_context(before_start, after_end, db_path=db_path)

    return {
        "metric_name": metric,
        "change_date": change_date,
        "segment": segment or "overall",
        "group_by": group_by,
        "window_days": window_days,
        "analysis_windows": {
            "before": {"start_date": before_start, "end_date": before_end},
            "after": {"start_date": after_start, "end_date": after_end},
        },
        "target_metric": target_comparison,
        "adjacent_metrics": adjacent_metric_results,
        "product_context": product_context,
        "interpretation_guidance": [
            "Use the target_metric before/after delta as the main evidence.",
            "Use adjacent_metrics to explain likely funnel drivers.",
            "Use product_context only when the dates and affected_area plausibly connect to the metric.",
            "Do not mention tables, columns, or SQL that are not present in tool output.",
        ],
    }


def validate_grain(grain: str) -> str:
    safe_grain = grain.strip().lower()
    if safe_grain not in {"day", "week", "month"}:
        raise ToolError("grain must be day, week, or month.")
    return safe_grain


def period_start_expr(date_expr: str, grain: str) -> str:
    if grain == "day":
        return f"date({date_expr})"
    if grain == "week":
        return f"date({date_expr}, '-' || ((CAST(strftime('%w', {date_expr}) AS INTEGER) + 6) % 7) || ' days')"
    if grain == "month":
        return f"date({date_expr}, 'start of month')"
    raise ToolError("grain must be day, week, or month.")


def metric_timeseries_sql(
    metric: str,
    start_date: str,
    end_date: str,
    grain: str,
    group_by: Optional[str],
) -> str:
    group_clause = build_group_clause(group_by)
    segment_select = group_clause["select"]
    group_sql = ", segment" if group_by else ""
    order_sql = "period_start, segment"

    if metric == "new_users":
        period_expr = period_start_expr("u.signup_date", grain)
        return f"""
        SELECT
          {period_expr} AS period_start,
          {segment_select},
          COUNT(*) AS new_users
        FROM users u
        WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY period_start{group_sql}
        ORDER BY {order_sql}
        """

    if metric == "active_users":
        period_expr = period_start_expr("e.event_date", grain)
        return f"""
        SELECT
          {period_expr} AS period_start,
          {segment_select},
          COUNT(DISTINCT e.user_id) AS active_users
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY period_start{group_sql}
        ORDER BY {order_sql}
        """

    if metric == "activation_rate":
        period_expr = period_start_expr("u.signup_date", grain)
        return f"""
        WITH user_activation AS (
          SELECT
            u.user_id,
            {period_expr} AS period_start,
            {segment_select},
            MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
            MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
            MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
          FROM users u
          LEFT JOIN events e
            ON u.user_id = e.user_id
           AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
          WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY u.user_id, period_start, segment
        )
        SELECT
          period_start,
          segment,
          COUNT(*) AS new_users,
          SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) AS activated_users,
          ROUND(1.0 * SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0), 3) AS activation_rate
        FROM user_activation
        GROUP BY period_start, segment
        ORDER BY {order_sql}
        """

    if metric == "upload_completion_rate":
        period_expr = period_start_expr("e.event_date", grain)
        return f"""
        SELECT
          {period_expr} AS period_start,
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
        GROUP BY period_start{group_sql}
        ORDER BY {order_sql}
        """

    if metric == "summaries_per_active_user":
        period_expr = period_start_expr("e.event_date", grain)
        return f"""
        SELECT
          {period_expr} AS period_start,
          {segment_select},
          COUNT(DISTINCT e.user_id) AS active_users,
          COUNT(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 END) AS summaries_generated,
          ROUND(1.0 * COUNT(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 END) / NULLIF(COUNT(DISTINCT e.user_id), 0), 2) AS summaries_per_active_user
        FROM events e
        JOIN users u ON e.user_id = u.user_id
        WHERE e.event_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY period_start{group_sql}
        ORDER BY {order_sql}
        """

    if metric == "paid_conversion_rate":
        period_expr = period_start_expr("u.signup_date", grain)
        return f"""
        WITH user_paid AS (
          SELECT
            u.user_id,
            {period_expr} AS period_start,
            {segment_select},
            MAX(CASE WHEN s.subscription_start_date BETWEEN u.signup_date AND date(u.signup_date, '+30 day') THEN 1 ELSE 0 END) AS paid_30d
          FROM users u
          LEFT JOIN events e ON u.user_id = e.user_id
          LEFT JOIN subscriptions s ON u.user_id = s.user_id
          WHERE u.signup_date BETWEEN '{start_date}' AND '{end_date}'
          GROUP BY u.user_id, period_start, segment
        )
        SELECT
          period_start,
          segment,
          COUNT(*) AS users,
          SUM(paid_30d) AS paid_users_30d,
          ROUND(1.0 * SUM(paid_30d) / NULLIF(COUNT(*), 0), 3) AS paid_conversion_rate_30d
        FROM user_paid
        GROUP BY period_start, segment
        ORDER BY {order_sql}
        """

    if metric == "billing_persistence":
        period_expr = period_start_expr("bi.invoice_date", grain)
        if group_by:
            return f"""
            SELECT
              {period_expr} AS period_start,
              {segment_select},
              COUNT(*) AS invoices,
              SUM(CASE WHEN bi.status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
              ROUND(AVG(CASE WHEN bi.status = 'paid' THEN 1.0 ELSE 0.0 END), 3) AS billing_persistence
            FROM billing_invoices bi
            JOIN users u ON bi.user_id = u.user_id
            WHERE bi.invoice_date BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY period_start{group_sql}
            ORDER BY {order_sql}
            """
        return f"""
        SELECT
          {period_expr} AS period_start,
          'overall' AS segment,
          COUNT(*) AS invoices,
          SUM(CASE WHEN bi.status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
          ROUND(AVG(CASE WHEN bi.status = 'paid' THEN 1.0 ELSE 0.0 END), 3) AS billing_persistence
        FROM billing_invoices bi
        WHERE bi.invoice_date BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY period_start
        ORDER BY period_start, segment
        """

    raise ToolError(f"Unsupported metric_name: {metric}")


def filter_rows_by_segment(rows: List[Dict[str, Any]], segment: Optional[str]) -> List[Dict[str, Any]]:
    if not segment:
        return rows
    target = segment.strip().lower()
    return [row for row in rows if str(row.get("segment", "")).strip().lower() == target]


def summarize_trend(rows: List[Dict[str, Any]], value_key: str) -> Dict[str, Any]:
    if not rows:
        return {
            "direction": "insufficient_data",
            "points": 0,
            "message": "No rows were returned for this metric trend.",
        }

    ordered = sorted(rows, key=lambda row: row["period_start"])
    first = ordered[0]
    last = ordered[-1]
    first_value = first.get(value_key)
    last_value = last.get(value_key)
    absolute_change = None
    relative_change_pct = None
    direction = "insufficient_data"
    if first_value is not None and last_value is not None:
        absolute_change = round(last_value - first_value, 4)
        if first_value != 0:
            relative_change_pct = round(100.0 * (last_value - first_value) / first_value, 1)
        if absolute_change > 0.01:
            direction = "increasing"
        elif absolute_change < -0.01:
            direction = "decreasing"
        else:
            direction = "flat"

    values = [row for row in ordered if row.get(value_key) is not None]
    max_row = max(values, key=lambda row: row[value_key]) if values else {}
    min_row = min(values, key=lambda row: row[value_key]) if values else {}
    positive_steps = 0
    negative_steps = 0
    for previous, current in zip(ordered, ordered[1:]):
        if previous.get(value_key) is None or current.get(value_key) is None:
            continue
        delta = current[value_key] - previous[value_key]
        if delta > 0:
            positive_steps += 1
        elif delta < 0:
            negative_steps += 1
    if direction in {"increasing", "decreasing"} and positive_steps > 0 and negative_steps > 0:
        direction = f"mixed_but_{direction}"

    return {
        "direction": direction,
        "points": len(ordered),
        "first_period": first.get("period_start"),
        "first_value": first_value,
        "last_period": last.get("period_start"),
        "last_value": last_value,
        "absolute_change": absolute_change,
        "relative_change_pct": relative_change_pct,
        "positive_steps": positive_steps,
        "negative_steps": negative_steps,
        "max_period": max_row.get("period_start"),
        "max_value": max_row.get(value_key),
        "min_period": min_row.get("period_start"),
        "min_value": min_row.get(value_key),
    }


def infer_group_by_for_segment(segment: str) -> str:
    normalized = segment.strip().lower()
    platform_values = {"ios", "android", "web"}
    acquisition_values = {"organic", "paid_search", "referral", "sales", "content"}
    user_segment_values = {"individual", "smb", "mid_market", "enterprise"}
    if normalized in platform_values:
        return "platform"
    if normalized in acquisition_values:
        return "acquisition_channel"
    if normalized in user_segment_values:
        return "user_segment"
    raise ToolError(
        "Could not infer group_by for segment. Provide group_by explicitly, "
        "for example platform, acquisition_channel, or user_segment."
    )


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def format_date(value: datetime) -> str:
    return value.strftime("%Y-%m-%d")


def metric_value_key(metric_name: str) -> str:
    keys = {
        "new_users": "new_users",
        "active_users": "active_users",
        "activation_rate": "activation_rate",
        "upload_completion_rate": "upload_completion_rate",
        "summaries_per_active_user": "summaries_per_active_user",
        "paid_conversion_rate": "paid_conversion_rate_30d",
        "billing_persistence": "billing_persistence",
    }
    return keys[metric_name]


def find_metric_row(result: Dict[str, Any], segment: Optional[str]) -> Dict[str, Any]:
    rows = result.get("rows", [])
    if not rows:
        return {}
    if not segment:
        return rows[0]
    target = segment.strip().lower()
    for row in rows:
        if str(row.get("segment", "")).strip().lower() == target:
            return row
    return {}


def compare_metric_results(
    metric_name: str,
    before_result: Dict[str, Any],
    after_result: Dict[str, Any],
    segment: Optional[str],
    before_label: str,
    after_label: str,
) -> Dict[str, Any]:
    value_key = metric_value_key(metric_name)
    before_row = find_metric_row(before_result, segment)
    after_row = find_metric_row(after_result, segment)
    before_value = before_row.get(value_key)
    after_value = after_row.get(value_key)
    absolute_change = None
    relative_change_pct = None
    if before_value is not None and after_value is not None:
        absolute_change = round(after_value - before_value, 4)
        if before_value != 0:
            relative_change_pct = round(100.0 * (after_value - before_value) / before_value, 1)

    return {
        "metric_name": metric_name,
        "value_key": value_key,
        "segment": segment or "overall",
        "before": {
            "window": before_label,
            "row": before_row,
            "value": before_value,
        },
        "after": {
            "window": after_label,
            "row": after_row,
            "value": after_value,
        },
        "absolute_change": absolute_change,
        "relative_change_pct": relative_change_pct,
    }


def adjacent_metrics_for(metric_name: str) -> List[str]:
    if metric_name == "activation_rate":
        return ["upload_completion_rate"]
    if metric_name == "paid_conversion_rate":
        return ["activation_rate", "summaries_per_active_user"]
    if metric_name == "summaries_per_active_user":
        return ["active_users"]
    return []


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

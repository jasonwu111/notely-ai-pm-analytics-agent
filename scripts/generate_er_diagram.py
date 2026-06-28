#!/usr/bin/env python3
"""Generate a deterministic SVG ER diagram for the Notely AI schema."""

from __future__ import annotations

from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_PATH = ROOT / "assets" / "notely-ai-er-diagram.svg"


TABLES = {
    "users": {
        "x": 70,
        "y": 285,
        "w": 330,
        "columns": [
            "PK user_id",
            "signup_timestamp",
            "signup_date",
            "country, region",
            "acquisition_channel",
            "campaign_name",
            "platform, device_type",
            "user_segment",
            "company_size",
            "plan_type_at_signup",
            "onboarding_flow_variant",
        ],
    },
    "sessions": {
        "x": 520,
        "y": 105,
        "w": 340,
        "columns": [
            "PK session_id",
            "FK user_id -> users.user_id",
            "session_start, session_end",
            "session_date",
            "session_duration_seconds",
            "entry_page",
            "traffic_source",
            "platform, device_type",
        ],
    },
    "events": {
        "x": 520,
        "y": 425,
        "w": 360,
        "columns": [
            "PK event_id",
            "FK user_id -> users.user_id",
            "FK session_id -> sessions.session_id",
            "event_timestamp",
            "event_date",
            "event_name",
            "platform, device_type",
            "country",
            "plan_type",
            "user_segment",
            "properties JSON",
        ],
    },
    "experiments": {
        "x": 520,
        "y": 805,
        "w": 350,
        "columns": [
            "PK assignment_id",
            "FK user_id -> users.user_id",
            "experiment_name",
            "variant",
            "assigned_date",
            "exposed_date",
        ],
    },
    "subscriptions": {
        "x": 1010,
        "y": 235,
        "w": 340,
        "columns": [
            "PK subscription_id",
            "FK user_id -> users.user_id",
            "subscription_start_date",
            "subscription_end_date",
            "status",
            "plan",
            "monthly_price",
            "billing_cycle",
            "cancel_reason",
        ],
    },
    "billing_invoices": {
        "x": 1435,
        "y": 130,
        "w": 355,
        "columns": [
            "PK invoice_id",
            "FK subscription_id -> subscriptions.subscription_id",
            "FK user_id -> users.user_id",
            "invoice_date",
            "billing_period_start",
            "billing_period_end",
            "amount",
            "status",
            "paid_date",
        ],
    },
    "payments": {
        "x": 1435,
        "y": 530,
        "w": 355,
        "columns": [
            "PK payment_id",
            "FK invoice_id -> billing_invoices.invoice_id",
            "FK subscription_id -> subscriptions.subscription_id",
            "FK user_id -> users.user_id",
            "payment_date",
            "amount",
            "status",
            "failure_reason",
        ],
    },
    "support_tickets": {
        "x": 1010,
        "y": 805,
        "w": 340,
        "columns": [
            "PK ticket_id",
            "FK user_id -> users.user_id",
            "created_date",
            "category",
            "sentiment",
            "status",
            "resolution_time_hours",
            "platform",
        ],
    },
    "product_calendar": {
        "x": 70,
        "y": 805,
        "w": 340,
        "columns": [
            "calendar_date",
            "event_type",
            "title",
            "description",
            "affected_area",
            "logical key: calendar_date + title",
        ],
    },
}


RELATIONSHIPS = [
    ("users", "sessions", "user_id", "logical FK", False),
    ("users", "events", "user_id", "logical FK", False),
    ("sessions", "events", "session_id", "logical FK", False),
    ("users", "experiments", "user_id", "logical FK", False),
    ("users", "subscriptions", "user_id", "logical FK", False),
    ("subscriptions", "billing_invoices", "subscription_id", "logical FK", False),
    ("billing_invoices", "payments", "invoice_id", "logical FK", False),
    ("subscriptions", "payments", "subscription_id", "logical FK", False),
    ("users", "support_tickets", "user_id", "logical FK", False),
    ("users", "billing_invoices", "user_id", "logical FK", True),
    ("users", "payments", "user_id", "logical FK", True),
    ("product_calendar", "events", "context for RCA/RAG", "no FK", True),
]


def table_height(table_name: str) -> int:
    return 52 + 24 * len(TABLES[table_name]["columns"])


def anchor(table_name: str, side: str) -> tuple[int, int]:
    t = TABLES[table_name]
    x = t["x"]
    y = t["y"]
    w = t["w"]
    h = table_height(table_name)
    if side == "left":
        return x, y + h // 2
    if side == "right":
        return x + w, y + h // 2
    if side == "top":
        return x + w // 2, y
    if side == "bottom":
        return x + w // 2, y + h
    raise ValueError(side)


def best_sides(src: str, dst: str) -> tuple[str, str]:
    sx = TABLES[src]["x"]
    dx = TABLES[dst]["x"]
    sy = TABLES[src]["y"]
    dy = TABLES[dst]["y"]
    if abs(sx - dx) > abs(sy - dy):
        return ("right", "left") if sx < dx else ("left", "right")
    return ("bottom", "top") if sy < dy else ("top", "bottom")


def line_path(src: str, dst: str) -> str:
    src_side, dst_side = best_sides(src, dst)
    x1, y1 = anchor(src, src_side)
    x2, y2 = anchor(dst, dst_side)
    if src_side in {"left", "right"}:
        mid_x = (x1 + x2) // 2
        return f"M{x1},{y1} C{mid_x},{y1} {mid_x},{y2} {x2},{y2}"
    mid_y = (y1 + y2) // 2
    return f"M{x1},{y1} C{x1},{mid_y} {x2},{mid_y} {x2},{y2}"


def label_point(src: str, dst: str) -> tuple[int, int]:
    src_side, dst_side = best_sides(src, dst)
    x1, y1 = anchor(src, src_side)
    x2, y2 = anchor(dst, dst_side)
    return (x1 + x2) // 2, (y1 + y2) // 2


def render_table(name: str, table: dict) -> str:
    x = table["x"]
    y = table["y"]
    w = table["w"]
    h = table_height(name)
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="table-box"/>',
        f'<rect x="{x}" y="{y}" width="{w}" height="42" rx="10" class="table-header"/>',
        f'<path d="M{x},{y + 34} h{w} v8 h-{w} z" class="table-header-fill"/>',
        f'<text x="{x + 16}" y="{y + 27}" class="table-title">{escape(name)}</text>',
    ]
    cy = y + 66
    for col in table["columns"]:
        css = "col"
        prefix = ""
        if col.startswith("PK "):
            css = "col pk"
            prefix = "PK"
            col_text = col[3:]
        elif col.startswith("FK "):
            css = "col fk"
            prefix = "FK"
            col_text = col[3:]
        else:
            col_text = col
        if prefix:
            parts.append(f'<text x="{x + 16}" y="{cy}" class="badge {prefix.lower()}">{prefix}</text>')
            parts.append(f'<text x="{x + 58}" y="{cy}" class="{css}">{escape(col_text)}</text>')
        else:
            parts.append(f'<text x="{x + 16}" y="{cy}" class="{css}">{escape(col_text)}</text>')
        cy += 24
    return "\n".join(parts)


def render_relationships() -> str:
    parts = []
    for src, dst, key, kind, dashed in RELATIONSHIPS:
        path = line_path(src, dst)
        dash = " dashed" if dashed else ""
        parts.append(f'<path d="{path}" class="relationship{dash}" marker-end="url(#arrow)"/>')
        lx, ly = label_point(src, dst)
        label = f"1 to many: {key}" if kind != "no FK" else key
        parts.append(f'<rect x="{lx - 86}" y="{ly - 14}" width="172" height="24" rx="8" class="rel-label-bg"/>')
        parts.append(f'<text x="{lx}" y="{ly + 4}" class="rel-label">{escape(label)}</text>')
    return "\n".join(parts)


def render_svg() -> str:
    table_markup = "\n".join(render_table(name, table) for name, table in TABLES.items())
    rel_markup = render_relationships()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1860" height="1180" viewBox="0 0 1860 1180">
  <defs>
    <marker id="arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="#475569"/>
    </marker>
    <style>
      .bg {{ fill: #f8fafc; }}
      .title {{ font: 700 34px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
      .subtitle {{ font: 15px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #475569; }}
      .table-box {{ fill: #ffffff; stroke: #cbd5e1; stroke-width: 1.5; filter: drop-shadow(0 8px 18px rgba(15, 23, 42, 0.08)); }}
      .table-header {{ fill: #0f766e; }}
      .table-header-fill {{ fill: #0f766e; }}
      .table-title {{ font: 700 18px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #ffffff; }}
      .col {{ font: 14px ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; fill: #334155; }}
      .pk {{ font-weight: 700; fill: #7c2d12; }}
      .fk {{ fill: #075985; }}
      .badge {{ font: 700 11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
      .badge.pk {{ fill: #ea580c; }}
      .badge.fk {{ fill: #0284c7; }}
      .relationship {{ fill: none; stroke: #475569; stroke-width: 2; opacity: 0.86; }}
      .relationship.dashed {{ stroke-dasharray: 8 7; opacity: 0.58; }}
      .rel-label-bg {{ fill: #f8fafc; stroke: #cbd5e1; stroke-width: 1; opacity: 0.96; }}
      .rel-label {{ font: 12px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #334155; text-anchor: middle; }}
      .legend-box {{ fill: #ffffff; stroke: #cbd5e1; stroke-width: 1.2; }}
      .legend-title {{ font: 700 14px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #0f172a; }}
      .legend-text {{ font: 13px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #475569; }}
    </style>
  </defs>

  <rect width="1860" height="1180" class="bg"/>
  <text x="70" y="60" class="title">Notely AI Analytics Database ER Diagram</text>
  <text x="70" y="88" class="subtitle">Logical primary keys and foreign-key relationships for the simulated PM analytics warehouse. SQLite constraints are not enforced in DDL; this diagram shows the intended relational model.</text>

  <rect x="1435" y="35" width="355" height="70" rx="10" class="legend-box"/>
  <text x="1455" y="62" class="legend-title">Legend</text>
  <text x="1455" y="86" class="legend-text">PK = primary key, FK = logical foreign key, dashed = contextual/non-FK link</text>

  {rel_markup}

  {table_markup}
</svg>
'''


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(render_svg(), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""Small local demo for the Notely AI agent tool layer.

Run from the project root:

    python3 agent_demo.py
"""

from pprint import pprint

from agent.tools import (
    describe_table,
    get_metric,
    get_product_context,
    get_weekly_report,
    list_tables,
    run_sql,
)


def print_section(title: str) -> None:
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def print_rows(result, max_rows: int = 5) -> None:
    print("SQL:")
    print(result["sql"])
    print(f"\nRows returned: {result['row_count']}")
    pprint(result["rows"][:max_rows])


def main() -> None:
    print_section("1. List Tables")
    pprint(list_tables())

    print_section("2. Describe events Table")
    pprint(describe_table("events"))

    print_section("3. Safe SQL Query")
    print_rows(
        run_sql(
            """
            SELECT event_name, COUNT(*) AS events
            FROM events
            GROUP BY 1
            ORDER BY events DESC
            """,
            limit=10,
        )
    )

    print_section("4. Metric Tool: Activation Rate by Platform")
    print_rows(get_metric("activation_rate", "2026-05-01", "2026-05-31", group_by="platform"))

    print_section("5. Metric Tool: Paid Conversion by Acquisition Channel")
    print_rows(get_metric("paid_conversion_rate", "2026-06-01", "2026-06-26", group_by="acquisition_channel"))

    print_section("6. Product Context")
    print_rows(get_product_context("2026-05-01", "2026-06-05"))

    print_section("7. Weekly PM Report")
    print_rows(get_weekly_report("2026-06-01"))


if __name__ == "__main__":
    main()


# Database Schema

The first version of the project uses SQLite because it is built into Python and does not require any extra installation. The schema is intentionally close to a real product analytics warehouse so it can later be moved to DuckDB, Postgres, or BigQuery.

The visual ER diagram is available in:

- `assets/notely-ai-er-diagram.svg`
- `assets/notely-ai-er-diagram.png`

SQLite does not enforce foreign-key constraints in the generated DDL. The ER diagram shows the intended logical primary-key and foreign-key relationships used by the analytics agent and sample queries.

## Entity Relationship Overview

```text
users
  -> events
  -> sessions
  -> experiments
  -> support_tickets
  -> subscriptions
        -> billing_invoices
              -> payments

product_calendar
```

## Tables

### users

One row per registered user.

| Column | Type | Description |
| --- | --- | --- |
| `user_id` | text | Unique user ID. |
| `signup_timestamp` | text | Signup timestamp. |
| `signup_date` | text | Signup date. |
| `country` | text | User country. |
| `region` | text | Geographic region. |
| `acquisition_channel` | text | Signup channel. |
| `campaign_name` | text | Marketing campaign name. |
| `platform` | text | Primary platform at signup. |
| `device_type` | text | Primary device type. |
| `user_segment` | text | User persona. |
| `company_size` | text | Company size bucket. |
| `plan_type_at_signup` | text | Initial plan type, usually Free. |
| `onboarding_flow_variant` | text | Assigned onboarding experiment variant when applicable. |

### sessions

One row per product session.

| Column | Type | Description |
| --- | --- | --- |
| `session_id` | text | Unique session ID. |
| `user_id` | text | User ID. |
| `session_start` | text | Session start timestamp. |
| `session_end` | text | Session end timestamp. |
| `session_date` | text | Session date. |
| `session_duration_seconds` | integer | Session duration. |
| `entry_page` | text | Entry page or product surface. |
| `traffic_source` | text | Traffic source. |
| `platform` | text | Platform. |
| `device_type` | text | Device type. |

### events

Append-only product event table.

| Column | Type | Description |
| --- | --- | --- |
| `event_id` | text | Unique event ID. |
| `user_id` | text | User ID. |
| `session_id` | text | Session ID. |
| `event_timestamp` | text | Event timestamp. |
| `event_date` | text | Event date. |
| `event_name` | text | Event name from the taxonomy. |
| `platform` | text | Platform. |
| `device_type` | text | Device type. |
| `country` | text | User country. |
| `plan_type` | text | Plan type at the time of event. |
| `user_segment` | text | User segment. |
| `properties` | text | JSON-encoded event properties. |

### experiments

Experiment assignment table.

| Column | Type | Description |
| --- | --- | --- |
| `assignment_id` | text | Unique assignment ID. |
| `user_id` | text | User ID. |
| `experiment_name` | text | Experiment name. |
| `variant` | text | Experiment variant. |
| `assigned_date` | text | Assignment date. |
| `exposed_date` | text | First exposure date. |

### subscriptions

One row per Pro subscription.

| Column | Type | Description |
| --- | --- | --- |
| `subscription_id` | text | Unique subscription ID. |
| `user_id` | text | User ID. |
| `subscription_start_date` | text | Subscription start date. |
| `subscription_end_date` | text | Cancellation or end date. |
| `status` | text | `active` or `cancelled`. |
| `plan` | text | Subscription plan. |
| `monthly_price` | real | Monthly price. |
| `billing_cycle` | text | Monthly or annual. |
| `cancel_reason` | text | Cancellation reason when applicable. |

### billing_invoices

Invoices generated for subscriptions.

| Column | Type | Description |
| --- | --- | --- |
| `invoice_id` | text | Unique invoice ID. |
| `subscription_id` | text | Subscription ID. |
| `user_id` | text | User ID. |
| `invoice_date` | text | Invoice date. |
| `billing_period_start` | text | Period start date. |
| `billing_period_end` | text | Period end date. |
| `amount` | real | Invoice amount. |
| `status` | text | `paid`, `failed`, or `open`. |
| `paid_date` | text | Paid date when paid. |

### payments

Payment attempts tied to invoices.

| Column | Type | Description |
| --- | --- | --- |
| `payment_id` | text | Unique payment ID. |
| `invoice_id` | text | Invoice ID. |
| `subscription_id` | text | Subscription ID. |
| `user_id` | text | User ID. |
| `payment_date` | text | Payment attempt date. |
| `amount` | real | Payment amount. |
| `status` | text | `succeeded` or `failed`. |
| `failure_reason` | text | Failure reason when applicable. |

### support_tickets

Support ticket table.

| Column | Type | Description |
| --- | --- | --- |
| `ticket_id` | text | Unique ticket ID. |
| `user_id` | text | User ID. |
| `created_date` | text | Ticket creation date. |
| `category` | text | Support category. |
| `sentiment` | text | User sentiment. |
| `status` | text | Ticket status. |
| `resolution_time_hours` | real | Resolution time. |
| `platform` | text | Platform. |

### product_calendar

Known product events used for RAG and root-cause analysis.

| Column | Type | Description |
| --- | --- | --- |
| `calendar_date` | text | Event date. |
| `event_type` | text | `launch`, `incident`, `experiment`, `pricing`, or `campaign`. |
| `title` | text | Short title. |
| `description` | text | Business context. |
| `affected_area` | text | Product area or metric likely affected. |

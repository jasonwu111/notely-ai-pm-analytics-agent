-- Weekly PM report prototype for Notely AI.
-- This query produces one row per week with growth, activation, engagement, monetization,
-- and billing-health metrics. It is a SQL-only prototype for the future Report Agent.

WITH weekly_signups AS (
  SELECT
    date(signup_date, 'weekday 1', '-7 days') AS week_start,
    COUNT(*) AS new_users
  FROM users
  GROUP BY 1
),
weekly_activation AS (
  SELECT
    signup_week AS week_start,
    COUNT(*) AS activation_cohort_users,
    SUM(activated) AS activated_users,
    ROUND(1.0 * SUM(activated) / NULLIF(COUNT(*), 0), 3) AS activation_rate
  FROM (
    SELECT
      u.user_id,
      date(u.signup_date, 'weekday 1', '-7 days') AS signup_week,
      CASE
        WHEN MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) = 1
         AND MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) = 1
         AND MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) = 1
        THEN 1 ELSE 0
      END AS activated
    FROM users u
    LEFT JOIN events e
      ON u.user_id = e.user_id
     AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
    GROUP BY 1, 2
  )
  GROUP BY 1
),
weekly_events AS (
  SELECT
    date(event_date, 'weekday 1', '-7 days') AS week_start,
    COUNT(DISTINCT user_id) AS active_users,
    COUNT(CASE WHEN event_name = 'recording_upload_started' THEN 1 END) AS upload_starts,
    COUNT(CASE WHEN event_name = 'recording_upload_completed' THEN 1 END) AS completed_uploads,
    COUNT(CASE WHEN event_name = 'ai_summary_generated' THEN 1 END) AS summaries_generated,
    COUNT(CASE WHEN event_name = 'action_items_generated' THEN 1 END) AS action_items_generated,
    COUNT(CASE WHEN event_name = 'summary_shared' THEN 1 END) AS summaries_shared,
    COUNT(CASE WHEN event_name = 'paywall_viewed' THEN 1 END) AS paywall_views,
    COUNT(CASE WHEN event_name = 'subscription_started' THEN 1 END) AS subscription_starts
  FROM events
  GROUP BY 1
),
weekly_billing AS (
  SELECT
    date(invoice_date, 'weekday 1', '-7 days') AS week_start,
    COUNT(*) AS invoices,
    SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
    ROUND(AVG(CASE WHEN status = 'paid' THEN 1.0 ELSE 0.0 END), 3) AS billing_persistence
  FROM billing_invoices
  GROUP BY 1
),
weekly_mrr AS (
  SELECT
    date(subscription_start_date, 'weekday 1', '-7 days') AS week_start,
    COUNT(*) AS new_paid_users,
    ROUND(SUM(monthly_price), 2) AS new_mrr
  FROM subscriptions
  GROUP BY 1
)
SELECT
  s.week_start,
  s.new_users,
  e.active_users,
  a.activation_rate,
  e.upload_starts,
  e.completed_uploads,
  ROUND(1.0 * e.completed_uploads / NULLIF(e.upload_starts, 0), 3) AS upload_completion_rate,
  ROUND(1.0 * e.completed_uploads / NULLIF(e.active_users, 0), 2) AS uploads_per_active_user,
  e.summaries_generated,
  ROUND(1.0 * e.summaries_generated / NULLIF(e.active_users, 0), 2) AS summaries_per_active_user,
  e.action_items_generated,
  e.summaries_shared,
  e.paywall_views,
  e.subscription_starts,
  COALESCE(m.new_paid_users, 0) AS new_paid_users,
  COALESCE(m.new_mrr, 0) AS new_mrr,
  b.billing_persistence
FROM weekly_signups s
LEFT JOIN weekly_activation a ON s.week_start = a.week_start
LEFT JOIN weekly_events e ON s.week_start = e.week_start
LEFT JOIN weekly_mrr m ON s.week_start = m.week_start
LEFT JOIN weekly_billing b ON s.week_start = b.week_start
WHERE s.week_start >= '2026-04-01'
ORDER BY s.week_start;


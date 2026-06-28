-- Validation queries for the simulated Notely AI analytics database.
-- Run these after scripts/generate_data.py creates data/notely_ai.sqlite.

-- 1. Weekly activation by platform.
-- This should show an iOS activation dip around the 2026-05-10 upload bug.
WITH signup_cohort AS (
  SELECT
    u.user_id,
    date(u.signup_date, 'weekday 1', '-7 days') AS signup_week,
    u.platform,
    MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
    MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
    MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
  FROM users u
  LEFT JOIN events e
    ON u.user_id = e.user_id
   AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
  GROUP BY 1, 2, 3
)
SELECT
  signup_week,
  platform,
  COUNT(*) AS new_users,
  ROUND(AVG(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1.0 ELSE 0.0 END), 3) AS activation_rate
FROM signup_cohort
WHERE signup_week BETWEEN '2026-04-20' AND '2026-06-01'
GROUP BY 1, 2
ORDER BY 1, 2;

-- 2. Upload failures and support tickets by platform around the iOS incident.
SELECT
  e.event_date,
  e.platform,
  COUNT(*) AS upload_failures
FROM events e
WHERE e.event_name = 'recording_upload_failed'
  AND e.event_date BETWEEN '2026-05-05' AND '2026-05-22'
GROUP BY 1, 2
ORDER BY 1, 2;

SELECT
  created_date,
  platform,
  category,
  COUNT(*) AS tickets
FROM support_tickets
WHERE created_date BETWEEN '2026-05-05' AND '2026-05-22'
  AND category = 'upload_failed'
GROUP BY 1, 2, 3
ORDER BY 1, 2;

-- 3. Paid search quality before and after 2026-06-01.
WITH user_outcomes AS (
  SELECT
    u.user_id,
    CASE WHEN u.signup_date >= '2026-06-01' THEN 'after_2026_06_01' ELSE 'before_2026_06_01' END AS period,
    u.acquisition_channel,
    MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS activated_proxy,
    MAX(CASE WHEN e.event_name = 'subscription_started' THEN 1 ELSE 0 END) AS became_paid
  FROM users u
  LEFT JOIN events e ON u.user_id = e.user_id
  WHERE u.signup_date BETWEEN '2026-05-01' AND '2026-06-26'
  GROUP BY 1, 2, 3
)
SELECT
  period,
  acquisition_channel,
  COUNT(*) AS signups,
  ROUND(AVG(activated_proxy), 3) AS summary_generation_rate,
  ROUND(AVG(became_paid), 3) AS paid_conversion_rate
FROM user_outcomes
GROUP BY 1, 2
ORDER BY 1, signups DESC;

-- 4. Onboarding experiment impact.
WITH experiment_users AS (
  SELECT
    x.variant,
    u.user_id,
    MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
    MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
    MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
  FROM experiments x
  JOIN users u ON x.user_id = u.user_id
  LEFT JOIN events e
    ON u.user_id = e.user_id
   AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
  WHERE x.experiment_name = 'onboarding_flow_v2'
  GROUP BY 1, 2
)
SELECT
  variant,
  COUNT(*) AS users,
  ROUND(AVG(has_workspace), 3) AS workspace_rate,
  ROUND(AVG(has_upload), 3) AS upload_rate,
  ROUND(AVG(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1.0 ELSE 0.0 END), 3) AS activation_rate
FROM experiment_users
GROUP BY 1
ORDER BY 1;

-- 5. D7 retention by action item usage.
WITH base AS (
  SELECT
    u.user_id,
    u.signup_date,
    MAX(CASE WHEN e.event_name = 'action_items_generated' THEN 1 ELSE 0 END) AS used_action_items
  FROM users u
  LEFT JOIN events e ON u.user_id = e.user_id
  WHERE u.signup_date BETWEEN '2026-04-15' AND '2026-06-10'
  GROUP BY 1, 2
),
retention AS (
  SELECT
    b.user_id,
    b.used_action_items,
    CASE WHEN COUNT(e.event_id) > 0 THEN 1 ELSE 0 END AS retained_d7
  FROM base b
  LEFT JOIN events e
    ON b.user_id = e.user_id
   AND e.event_date BETWEEN date(b.signup_date, '+7 day') AND date(b.signup_date, '+13 day')
  GROUP BY 1, 2
)
SELECT
  used_action_items,
  COUNT(*) AS users,
  ROUND(AVG(retained_d7), 3) AS d7_retention
FROM retention
GROUP BY 1;

-- 6. Free-limit change impact.
WITH cohorts AS (
  SELECT
    u.user_id,
    CASE WHEN u.signup_date >= '2026-05-25' THEN 'after_limit_change' ELSE 'before_limit_change' END AS period,
    MAX(CASE WHEN e.event_name = 'usage_limit_reached' THEN 1 ELSE 0 END) AS hit_usage_limit,
    MAX(CASE WHEN e.event_name = 'paywall_viewed' THEN 1 ELSE 0 END) AS saw_paywall,
    MAX(CASE WHEN e.event_name = 'subscription_started' THEN 1 ELSE 0 END) AS became_paid
  FROM users u
  LEFT JOIN events e ON u.user_id = e.user_id
  WHERE u.signup_date BETWEEN '2026-05-01' AND '2026-06-20'
  GROUP BY 1, 2
)
SELECT
  period,
  COUNT(*) AS users,
  ROUND(AVG(hit_usage_limit), 3) AS usage_limit_rate,
  ROUND(AVG(saw_paywall), 3) AS paywall_view_rate,
  ROUND(AVG(became_paid), 3) AS paid_conversion_rate
FROM cohorts
GROUP BY 1;


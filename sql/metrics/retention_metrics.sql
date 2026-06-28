-- Retention metrics for Notely AI.

-- 1. Signup-month D1 and D7 retention.
WITH base AS (
  SELECT
    user_id,
    signup_date,
    substr(signup_date, 1, 7) AS signup_month
  FROM users
),
retention AS (
  SELECT
    b.user_id,
    b.signup_month,
    MAX(CASE WHEN e.event_date = date(b.signup_date, '+1 day') THEN 1 ELSE 0 END) AS retained_d1,
    MAX(CASE WHEN e.event_date BETWEEN date(b.signup_date, '+7 day') AND date(b.signup_date, '+13 day') THEN 1 ELSE 0 END) AS retained_d7
  FROM base b
  LEFT JOIN events e ON b.user_id = e.user_id
  GROUP BY 1, 2
)
SELECT
  signup_month,
  COUNT(*) AS users,
  ROUND(AVG(retained_d1), 3) AS d1_retention,
  ROUND(AVG(retained_d7), 3) AS d7_retention
FROM retention
GROUP BY 1
ORDER BY 1;

-- 2. D7 retention by action item usage after launch.
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

-- 3. Second summary rate by signup month.
WITH summary_events AS (
  SELECT
    u.user_id,
    substr(u.signup_date, 1, 7) AS signup_month,
    COUNT(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 END) AS summaries_14d
  FROM users u
  LEFT JOIN events e
    ON u.user_id = e.user_id
   AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+14 day')
  GROUP BY 1, 2
)
SELECT
  signup_month,
  COUNT(*) AS users,
  ROUND(AVG(CASE WHEN summaries_14d >= 2 THEN 1.0 ELSE 0.0 END), 3) AS second_summary_rate
FROM summary_events
GROUP BY 1
ORDER BY 1;


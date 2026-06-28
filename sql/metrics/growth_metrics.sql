-- Growth metrics for Notely AI.
-- These queries are written for SQLite and can be adapted to DuckDB/Postgres later.

-- 1. Monthly new users.
SELECT
  substr(signup_date, 1, 7) AS signup_month,
  COUNT(*) AS new_users
FROM users
GROUP BY 1
ORDER BY 1;

-- 2. Weekly new users by acquisition channel.
SELECT
  date(signup_date, 'weekday 1', '-7 days') AS signup_week,
  acquisition_channel,
  COUNT(*) AS new_users
FROM users
GROUP BY 1, 2
ORDER BY 1, 3 DESC;

-- 3. Weekly active users.
SELECT
  date(event_date, 'weekday 1', '-7 days') AS activity_week,
  COUNT(DISTINCT user_id) AS active_users
FROM events
GROUP BY 1
ORDER BY 1;

-- 4. Signup mix by user segment.
SELECT
  user_segment,
  COUNT(*) AS users,
  ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_users
FROM users
GROUP BY 1
ORDER BY users DESC;


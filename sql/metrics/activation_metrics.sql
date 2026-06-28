-- Activation and funnel metrics for Notely AI.
-- Activation definition:
-- A new user is activated if they complete workspace_created,
-- recording_upload_completed, and ai_summary_generated within 7 days of signup.

-- 1. Overall activation rate by signup month.
WITH user_activation AS (
  SELECT
    u.user_id,
    substr(u.signup_date, 1, 7) AS signup_month,
    MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
    MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
    MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
  FROM users u
  LEFT JOIN events e
    ON u.user_id = e.user_id
   AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
  GROUP BY 1, 2
)
SELECT
  signup_month,
  COUNT(*) AS new_users,
  SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) AS activated_users,
  ROUND(1.0 * SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) / COUNT(*), 3) AS activation_rate
FROM user_activation
GROUP BY 1
ORDER BY 1;

-- 2. Activation rate by platform and signup week.
WITH user_activation AS (
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
FROM user_activation
GROUP BY 1, 2
ORDER BY 1, 2;

-- 3. First value funnel.
WITH user_steps AS (
  SELECT
    u.user_id,
    MAX(CASE WHEN e.event_name = 'workspace_created' THEN 1 ELSE 0 END) AS has_workspace,
    MAX(CASE WHEN e.event_name = 'recording_upload_completed' THEN 1 ELSE 0 END) AS has_upload,
    MAX(CASE WHEN e.event_name = 'ai_summary_generated' THEN 1 ELSE 0 END) AS has_summary
  FROM users u
  LEFT JOIN events e
    ON u.user_id = e.user_id
   AND e.event_date BETWEEN u.signup_date AND date(u.signup_date, '+7 day')
  GROUP BY 1
)
SELECT 'signup_completed' AS funnel_step, COUNT(*) AS users, 1.000 AS step_rate FROM user_steps
UNION ALL
SELECT 'workspace_created', SUM(has_workspace), ROUND(1.0 * SUM(has_workspace) / COUNT(*), 3) FROM user_steps
UNION ALL
SELECT 'recording_upload_completed', SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 THEN 1 ELSE 0 END), ROUND(1.0 * SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 THEN 1 ELSE 0 END) / COUNT(*), 3) FROM user_steps
UNION ALL
SELECT 'ai_summary_generated', SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END), ROUND(1.0 * SUM(CASE WHEN has_workspace = 1 AND has_upload = 1 AND has_summary = 1 THEN 1 ELSE 0 END) / COUNT(*), 3) FROM user_steps;

-- 4. Upload completion rate by platform and week.
SELECT
  date(event_date, 'weekday 1', '-7 days') AS event_week,
  platform,
  COUNT(CASE WHEN event_name = 'recording_upload_started' THEN 1 END) AS upload_starts,
  COUNT(CASE WHEN event_name = 'recording_upload_completed' THEN 1 END) AS upload_completions,
  ROUND(
    1.0 * COUNT(CASE WHEN event_name = 'recording_upload_completed' THEN 1 END)
    / NULLIF(COUNT(CASE WHEN event_name = 'recording_upload_started' THEN 1 END), 0),
    3
  ) AS upload_completion_rate
FROM events
WHERE event_name IN ('recording_upload_started', 'recording_upload_completed')
GROUP BY 1, 2
ORDER BY 1, 2;


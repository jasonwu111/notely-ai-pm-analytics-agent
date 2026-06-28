-- Engagement metrics for Notely AI.

-- 1. Weekly completed uploads and summaries per active user.
WITH weekly_events AS (
  SELECT
    date(event_date, 'weekday 1', '-7 days') AS activity_week,
    COUNT(DISTINCT user_id) AS active_users,
    COUNT(CASE WHEN event_name = 'recording_upload_completed' THEN 1 END) AS completed_uploads,
    COUNT(CASE WHEN event_name = 'ai_summary_generated' THEN 1 END) AS summaries_generated,
    COUNT(CASE WHEN event_name = 'action_items_generated' THEN 1 END) AS action_items_generated,
    COUNT(CASE WHEN event_name = 'summary_shared' THEN 1 END) AS summaries_shared,
    COUNT(CASE WHEN event_name = 'integration_connected' THEN 1 END) AS integrations_connected
  FROM events
  GROUP BY 1
)
SELECT
  activity_week,
  active_users,
  completed_uploads,
  ROUND(1.0 * completed_uploads / NULLIF(active_users, 0), 2) AS uploads_per_active_user,
  summaries_generated,
  ROUND(1.0 * summaries_generated / NULLIF(active_users, 0), 2) AS summaries_per_active_user,
  action_items_generated,
  summaries_shared,
  integrations_connected
FROM weekly_events
ORDER BY 1;

-- 2. Feature adoption by plan type.
SELECT
  plan_type,
  COUNT(DISTINCT user_id) AS active_users,
  COUNT(DISTINCT CASE WHEN event_name = 'action_items_generated' THEN user_id END) AS action_item_users,
  COUNT(DISTINCT CASE WHEN event_name = 'integration_connected' THEN user_id END) AS integration_users,
  COUNT(DISTINCT CASE WHEN event_name = 'summary_shared' THEN user_id END) AS sharing_users,
  ROUND(1.0 * COUNT(DISTINCT CASE WHEN event_name = 'action_items_generated' THEN user_id END) / NULLIF(COUNT(DISTINCT user_id), 0), 3) AS action_item_adoption_rate,
  ROUND(1.0 * COUNT(DISTINCT CASE WHEN event_name = 'integration_connected' THEN user_id END) / NULLIF(COUNT(DISTINCT user_id), 0), 3) AS integration_adoption_rate,
  ROUND(1.0 * COUNT(DISTINCT CASE WHEN event_name = 'summary_shared' THEN user_id END) / NULLIF(COUNT(DISTINCT user_id), 0), 3) AS sharing_rate
FROM events
WHERE event_date >= '2026-04-15'
GROUP BY 1
ORDER BY 1;

-- 3. Engagement by user segment.
SELECT
  user_segment,
  COUNT(DISTINCT user_id) AS active_users,
  COUNT(CASE WHEN event_name = 'recording_upload_completed' THEN 1 END) AS completed_uploads,
  COUNT(CASE WHEN event_name = 'ai_summary_generated' THEN 1 END) AS summaries_generated,
  COUNT(CASE WHEN event_name = 'summary_shared' THEN 1 END) AS summaries_shared
FROM events
GROUP BY 1
ORDER BY active_users DESC;


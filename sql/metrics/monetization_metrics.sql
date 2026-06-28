-- Monetization and billing metrics for Notely AI.

-- 1. Monthly new paid users and new MRR.
SELECT
  substr(subscription_start_date, 1, 7) AS subscription_month,
  COUNT(*) AS new_paid_users,
  ROUND(SUM(monthly_price), 2) AS new_mrr
FROM subscriptions
GROUP BY 1
ORDER BY 1;

-- 2. Paid conversion rate by signup month.
WITH user_paid AS (
  SELECT
    u.user_id,
    substr(u.signup_date, 1, 7) AS signup_month,
    MAX(CASE WHEN s.subscription_start_date BETWEEN u.signup_date AND date(u.signup_date, '+30 day') THEN 1 ELSE 0 END) AS paid_30d
  FROM users u
  LEFT JOIN subscriptions s ON u.user_id = s.user_id
  GROUP BY 1, 2
)
SELECT
  signup_month,
  COUNT(*) AS users,
  SUM(paid_30d) AS paid_users_30d,
  ROUND(1.0 * SUM(paid_30d) / COUNT(*), 3) AS paid_conversion_rate_30d
FROM user_paid
GROUP BY 1
ORDER BY 1;

-- 3. Paid conversion by acquisition channel around the paid search scale-up.
WITH user_paid AS (
  SELECT
    u.user_id,
    CASE WHEN u.signup_date >= '2026-06-01' THEN 'after_2026_06_01' ELSE 'before_2026_06_01' END AS period,
    u.acquisition_channel,
    MAX(CASE WHEN s.subscription_start_date BETWEEN u.signup_date AND date(u.signup_date, '+30 day') THEN 1 ELSE 0 END) AS paid_30d
  FROM users u
  LEFT JOIN subscriptions s ON u.user_id = s.user_id
  WHERE u.signup_date BETWEEN '2026-05-01' AND '2026-06-26'
  GROUP BY 1, 2, 3
)
SELECT
  period,
  acquisition_channel,
  COUNT(*) AS signups,
  ROUND(AVG(paid_30d), 3) AS paid_conversion_rate_30d
FROM user_paid
GROUP BY 1, 2
ORDER BY 1, signups DESC;

-- 4. Billing persistence by invoice month.
SELECT
  substr(invoice_date, 1, 7) AS invoice_month,
  COUNT(*) AS invoices,
  SUM(CASE WHEN status = 'paid' THEN 1 ELSE 0 END) AS paid_invoices,
  SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_invoices,
  ROUND(AVG(CASE WHEN status = 'paid' THEN 1.0 ELSE 0.0 END), 3) AS billing_persistence
FROM billing_invoices
GROUP BY 1
ORDER BY 1;

-- 5. Cancellation rate by subscription start month.
SELECT
  substr(subscription_start_date, 1, 7) AS subscription_month,
  COUNT(*) AS subscriptions,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled_subscriptions,
  ROUND(AVG(CASE WHEN status = 'cancelled' THEN 1.0 ELSE 0.0 END), 3) AS cancellation_rate
FROM subscriptions
GROUP BY 1
ORDER BY 1;


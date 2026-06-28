# Metric Definitions

## Growth Metrics

### New Users

Number of users who completed signup during the selected time period.

Formula:

```text
count(distinct user_id) where signup_date is in the selected period
```

Default dimensions:

- acquisition channel
- platform
- country
- user segment

### Active Users

Number of users who triggered at least one product event during the selected time period.

## Activation Metrics

### Activation Rate

Share of new users who reach the first value moment within 7 days of signup.

Numerator:

- Users who completed `workspace_created`, `recording_upload_completed`, and `ai_summary_generated` within 7 days of signup.

Denominator:

- Users who completed signup during the selected cohort period.

Default dimensions:

- acquisition channel
- platform
- device type
- country
- user segment

### Upload Completion Rate

Share of upload attempts that finish successfully.

Formula:

```text
recording_upload_completed / recording_upload_started
```

### Summary Generation Rate

Share of activated users who generate at least one AI summary.

## Engagement Metrics

### Uploads Per Active User

Average number of completed meeting uploads per active user.

Formula:

```text
count(recording_upload_completed events) / count(distinct active users)
```

### Summaries Per Active User

Average number of AI summaries generated per active user.

### Action Item Adoption Rate

Share of users who generate at least one action item after generating a summary.

## Retention Metrics

### D1 Retention

Share of new users who return 1 day after signup.

### D7 Retention

Share of new users who return 7 days after signup.

### Second Summary Rate

Share of users who generate a second AI summary within 14 days of signup.

## Monetization Metrics

### Free-to-Pro Conversion Rate

Share of Free users who start a Pro subscription.

### Paid Conversion Rate

Share of new users who become paid subscribers within 30 days of signup.

### New Paid Orders

Number of new subscriptions started in the selected time period.

### Monthly Recurring Revenue

Total monthly recurring revenue from active paid subscriptions.

### Billing Persistence

Share of paid subscriptions that renew successfully and remain active through the next billing period.

Formula:

```text
renewed subscriptions / subscriptions eligible for renewal
```

### Cancellation Rate

Share of paid subscribers who cancel during the selected time period.

## Reporting Notes

Every metric should support comparison against:

- Previous week
- Previous month
- Same weekday-adjusted prior period, when useful
- Segment-level breakdowns


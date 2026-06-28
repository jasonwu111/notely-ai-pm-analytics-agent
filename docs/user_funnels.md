# User Funnels

## First Value Funnel

This funnel measures whether a new user reaches the first meaningful product value.

Steps:

1. `landing_page_viewed`
2. `signup_started`
3. `signup_completed`
4. `onboarding_started`
5. `workspace_created`
6. `recording_upload_started`
7. `recording_upload_completed`
8. `transcript_generated`
9. `ai_summary_generated`
10. `action_items_generated`
11. `summary_shared`

## Activation Definition

A user is activated if they complete the following within 7 days of signup:

- `workspace_created`
- `recording_upload_completed`
- `ai_summary_generated`

This definition captures the minimum journey from account creation to the first clear product value.

## Monetization Funnel

This funnel measures the path from free usage to paid subscription.

Steps:

1. Free user signs up.
2. User generates at least one AI summary.
3. User reaches a monthly usage limit or attempts to use a Pro feature.
4. `paywall_viewed`
5. `pricing_page_viewed`
6. `checkout_started`
7. `subscription_started`

## Retention Funnel

This funnel measures whether users come back after the first value moment.

Steps:

1. `signup_completed`
2. `ai_summary_generated`
3. User returns within 1 day.
4. User returns within 7 days.
5. User generates a second summary.
6. User connects an integration.
7. User shares a summary.

## Feature Adoption Funnel

This funnel measures adoption of advanced AI and collaboration features.

Steps:

1. `ai_summary_generated`
2. `action_items_generated`
3. `action_item_edited`
4. `summary_shared`
5. `integration_connected`
6. `integration_sync_completed`

## Funnel Analysis Questions

- Which funnel step has the highest drop-off?
- Do iOS, Android, and desktop users drop off at different steps?
- Does onboarding flow v2 improve activation?
- Do users who generate action items retain better?
- Do users who connect integrations convert to Pro at higher rates?
- Does hitting the free usage limit increase upgrades or cause churn?


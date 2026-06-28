# Data Storylines

The simulated data should include realistic product stories. These stories make the analytics agent useful because it can discover, explain, and validate real business patterns.

## Story 1: iOS Upload Bug

Time period:

- 2026-05-10 to 2026-05-17

Business event:

- A bug in the iOS upload flow causes more upload failures.

Expected data impact:

- Lower `recording_upload_completed` rate for iOS users.
- Higher `recording_upload_failed` events for iOS users.
- Lower activation rate for iOS users.
- More support tickets with category `upload_failed`.

PM question:

```text
Why did activation rate drop in mid-May?
```

Expected agent insight:

```text
The activation drop was mainly driven by iOS users. Upload completion declined during the same period, while upload_failed support tickets increased. This aligns with the iOS upload incident.
```

## Story 2: Paid Search User Quality Decline

Time period:

- 2026-06-01 onward

Business event:

- Paid search campaigns bring more signups, but the traffic quality is lower.

Expected data impact:

- More new users from paid search.
- Lower activation rate for paid search users.
- Lower paid conversion rate for paid search users.
- Overall conversion may decline despite signup growth.

PM question:

```text
Why did signups increase but paid conversion decline?
```

Expected agent insight:

```text
The growth came largely from paid search, but paid search users had lower activation and subscription rates. The channel mix shift pulled down overall conversion.
```

## Story 3: Onboarding Flow Experiment

Experiment:

- `onboarding_flow_v2`

Variants:

- Variant A: standard onboarding.
- Variant B: guided setup that encourages users to upload their first recording.

Expected data impact:

- Variant B improves `workspace_created`.
- Variant B improves `recording_upload_completed`.
- Variant B improves activation rate.
- Variant B may increase time spent in onboarding.
- Lift is stronger on desktop than mobile.

PM question:

```text
Did the new onboarding flow improve activation?
```

Expected agent insight:

```text
Variant B improved activation, mostly by increasing upload completion. The lift was stronger on desktop than mobile.
```

## Story 4: Action Items Feature Launch

Launch date:

- 2026-04-15

Business event:

- Notely AI launches AI-generated action items as a Pro feature.

Expected data impact:

- `action_items_generated` increases after launch.
- Users who generate action items have higher D7 retention.
- Users who generate action items are more likely to share summaries.
- Pro users adopt the feature faster than Free users.

PM question:

```text
Did the action items feature improve retention or paid conversion?
```

Expected agent insight:

```text
Users who generated action items had higher D7 retention and were more likely to share summaries. This suggests the feature may be associated with stronger engagement.
```

## Story 5: Free Limit and Paywall Change

Change date:

- 2026-05-25

Business event:

- Free plan monthly summary limit changes from 10 to 5.

Expected data impact:

- More `usage_limit_reached` events.
- More `paywall_viewed` events.
- Slight increase in new Pro subscriptions.
- Possible decline in Free user D7 retention.

PM question:

```text
Did reducing the free limit help monetization or hurt retention?
```

Expected agent insight:

```text
The free limit change increased paywall exposure and new subscriptions, but Free user retention declined. This suggests a monetization and user experience tradeoff.
```

## Story 6: Weekly Reporting Spike

Time period:

- Any Monday weekly report after a major product event.

Business event:

- The reporting agent should detect metric movements without being explicitly asked a question.

Expected data impact:

- Weekly reports surface the same storylines through scheduled analysis.

PM question:

```text
What changed in the business this week?
```

Expected agent insight:

```text
The report should identify the largest metric changes, explain drivers, and suggest follow-up questions.
```


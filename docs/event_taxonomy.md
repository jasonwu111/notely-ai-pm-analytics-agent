# Event Taxonomy

## Common Event Fields

Every event should include:

- `event_id`
- `user_id`
- `session_id`
- `event_timestamp`
- `event_date`
- `event_name`
- `platform`
- `device_type`
- `country`
- `plan_type`
- `user_segment`
- `properties`

## Acquisition and Signup Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `landing_page_viewed` | User views the public marketing page. | `acquisition_channel`, `campaign_name`, `referrer` |
| `signup_started` | User begins account creation. | `signup_method` |
| `signup_completed` | User successfully creates an account. | `signup_method` |
| `email_verified` | User verifies email address. | `verification_method` |

## Onboarding Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `onboarding_started` | User starts onboarding flow. | `flow_version` |
| `use_case_selected` | User selects their primary use case. | `selected_use_case` |
| `workspace_created` | User creates a personal or team workspace. | `workspace_type`, `team_size` |
| `team_invite_sent` | User invites a teammate. | `num_invites` |
| `onboarding_completed` | User finishes onboarding. | `flow_version`, `time_to_complete_seconds` |

## Meeting Upload and Processing Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `recording_upload_started` | User starts uploading a meeting recording. | `file_type`, `recording_length_minutes` |
| `recording_upload_completed` | Upload succeeds. | `file_type`, `recording_length_minutes` |
| `recording_upload_failed` | Upload fails. | `failure_reason`, `file_type` |
| `transcript_generation_started` | Transcript processing begins. | `language` |
| `transcript_generated` | Transcript is generated. | `processing_time_seconds`, `language` |
| `transcript_generation_failed` | Transcript generation fails. | `failure_reason` |

## AI Feature Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `ai_summary_generated` | AI meeting summary is generated. | `summary_type`, `model_quality_score` |
| `summary_regenerated` | User regenerates the summary. | `reason` |
| `action_items_generated` | AI extracts action items. | `num_action_items` |
| `action_item_edited` | User edits an extracted action item. | `edit_count` |
| `key_topics_generated` | AI extracts key meeting topics. | `num_topics` |
| `meeting_sentiment_generated` | AI summarizes meeting sentiment. | `sentiment_score` |

## Sharing and Collaboration Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `summary_viewed` | User opens a generated summary. | `source` |
| `summary_shared` | User shares summary with others. | `share_destination`, `num_recipients` |
| `comment_added` | User adds a comment. | `comment_type` |
| `team_member_invited` | User invites a teammate to the workspace. | `role` |

## Integration Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `integration_page_viewed` | User views integrations page. | `source` |
| `integration_connected` | User connects an integration. | `integration_name` |
| `integration_sync_completed` | Integration sync succeeds. | `integration_name` |
| `integration_sync_failed` | Integration sync fails. | `integration_name`, `failure_reason` |

Supported integrations:

- Slack
- Notion
- Google Docs
- Google Calendar

## Monetization Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `usage_limit_reached` | Free user reaches monthly usage limit. | `limit_type`, `limit_value` |
| `paywall_viewed` | User sees a paywall. | `paywall_reason` |
| `pricing_page_viewed` | User views pricing page. | `source` |
| `checkout_started` | User starts checkout. | `plan`, `billing_cycle` |
| `subscription_started` | User becomes a paid subscriber. | `plan`, `monthly_price` |
| `subscription_cancelled` | User cancels subscription. | `cancel_reason` |
| `subscription_renewed` | Paid subscription renews. | `billing_cycle`, `monthly_price` |

## Support and Reliability Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `support_ticket_created` | User creates a support ticket. | `category`, `sentiment` |
| `support_ticket_resolved` | Ticket is resolved. | `resolution_time_hours` |
| `error_message_shown` | User sees an error message. | `error_code`, `surface` |

Support categories:

- `upload_failed`
- `transcript_quality`
- `billing_issue`
- `integration_failed`
- `slow_processing`
- `account_access`

## Experiment Events

| Event | Meaning | Example Properties |
| --- | --- | --- |
| `experiment_assigned` | User is assigned to an experiment. | `experiment_name`, `variant` |
| `experiment_exposed` | User is exposed to experimental experience. | `experiment_name`, `variant` |


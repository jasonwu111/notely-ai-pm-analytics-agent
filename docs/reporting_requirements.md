# Reporting Requirements

## Goal

The reporting feature should allow the agent to generate weekly and monthly PM business reports automatically.

The report should combine SQL-based metric snapshots with AI-generated commentary. The commentary must be grounded in metric changes, product context, experiments, incidents, and release notes.

## Report Modes

### Weekly PM Report

Audience:

- Product managers
- Growth team
- Data science portfolio reviewers

Purpose:

- Summarize the latest product health.
- Detect major changes.
- Explain likely drivers.
- Recommend follow-up analyses.

### Monthly Business Review

Audience:

- Product, growth, and leadership stakeholders

Purpose:

- Summarize broader business trends.
- Review growth, activation, engagement, retention, and monetization.
- Highlight product wins, risks, and experiments.

## Weekly Report Sections

### 1. Executive Summary

Short summary of the most important changes.

Expected output:

- 3 to 5 bullet points.
- Clear directionality.
- Mention likely driver when evidence exists.

### 2. Growth

Metrics:

- New users
- Signup completion rate
- Acquisition channel mix

Breakdowns:

- acquisition channel
- platform
- country
- user segment

### 3. Activation Funnel

Metrics:

- activation rate
- upload completion rate
- summary generation rate
- first value completion

Funnel:

```text
signup_completed
→ workspace_created
→ recording_upload_completed
→ ai_summary_generated
```

### 4. Engagement

Metrics:

- active users
- completed uploads
- uploads per active user
- AI summaries generated
- summaries per active user
- action items generated
- integration connections

### 5. Monetization

Metrics:

- Free users
- Pro subscribers
- paywall views
- pricing page views
- checkout starts
- new paid orders
- paid conversion rate
- monthly recurring revenue
- billing persistence
- cancellation rate

### 6. Retention

Metrics:

- D1 retention
- D7 retention
- second summary rate
- returning users

### 7. Segment Deep Dive

The agent should identify the segments contributing most to metric movements.

Common segments:

- platform
- device type
- acquisition channel
- country
- user segment
- plan type

### 8. AI Insights and Follow-ups

The agent should answer:

- What changed?
- Which segment drove the change?
- Is there a known product release, experiment, or incident that explains it?
- What should the PM investigate next?

## Monthly Report Additions

Monthly reports should include:

- Month-over-month growth.
- New vs returning user mix.
- Cohort retention.
- Pro subscriber base changes.
- Net revenue movement.
- Experiment readout summary.
- Product quality and support trends.

## Report Generation Workflow

1. Load metric definitions.
2. Run predefined SQL queries.
3. Compare current period with previous period.
4. Flag large or unusual changes.
5. Retrieve relevant product docs, release notes, experiments, and incidents.
6. Generate a grounded written report.
7. Save the report output.
8. Display the report in the app or export it as Markdown/PDF.

## Future Reporting Tables

Potential tables:

- `report_runs`
- `report_sections`
- `report_metric_snapshots`
- `daily_product_metrics`
- `daily_funnel_metrics`
- `daily_billing_metrics`
- `daily_segment_metrics`


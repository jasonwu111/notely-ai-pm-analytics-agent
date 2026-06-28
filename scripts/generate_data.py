#!/usr/bin/env python3
"""Generate a local SQLite analytics database for the Notely AI project."""

from __future__ import annotations

import json
import math
import random
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "notely_ai.sqlite"

START_DATE = date(2025, 1, 1)
END_DATE = date(2026, 6, 26)

ACTION_ITEMS_LAUNCH = date(2026, 4, 15)
IOS_BUG_START = date(2026, 5, 10)
IOS_BUG_END = date(2026, 5, 17)
FREE_LIMIT_CHANGE = date(2026, 5, 25)
PAID_SEARCH_QUALITY_DECLINE = date(2026, 6, 1)
ONBOARDING_EXPERIMENT_START = date(2026, 3, 1)
ONBOARDING_EXPERIMENT_END = date(2026, 4, 30)

RANDOM_SEED = 42


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def daterange(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def choose_weighted(options):
    total = sum(weight for _, weight in options)
    pick = random.random() * total
    cumulative = 0.0
    for value, weight in options:
        cumulative += weight
        if pick <= cumulative:
            return value
    return options[-1][0]


def random_timestamp(day: date, start_hour: int = 8, end_hour: int = 21) -> datetime:
    hour = random.randint(start_hour, end_hour)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    return datetime(day.year, day.month, day.day, hour, minute, second)


def add_days(ts: datetime, days: int, hours: int = 0, minutes: int = 0) -> datetime:
    return ts + timedelta(days=days, hours=hours, minutes=minutes)


def iso_date(value) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    return value.isoformat()


def iso_ts(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat(sep=" ")


@dataclass
class User:
    user_id: str
    signup_timestamp: datetime
    signup_date: date
    country: str
    region: str
    acquisition_channel: str
    campaign_name: str
    platform: str
    device_type: str
    user_segment: str
    company_size: str
    onboarding_flow_variant: Optional[str]


class Generator:
    def __init__(self):
        random.seed(RANDOM_SEED)
        self.user_counter = 0
        self.event_counter = 0
        self.session_counter = 0
        self.subscription_counter = 0
        self.invoice_counter = 0
        self.payment_counter = 0
        self.ticket_counter = 0
        self.assignment_counter = 0

        self.users = []
        self.sessions = []
        self.events = []
        self.experiments = []
        self.subscriptions = []
        self.billing_invoices = []
        self.payments = []
        self.support_tickets = []

    def next_id(self, prefix: str, attr: str) -> str:
        value = getattr(self, attr) + 1
        setattr(self, attr, value)
        return f"{prefix}_{value:07d}"

    def add_session(self, user: User, start_ts: datetime, entry_page: str, traffic_source: str, duration_seconds: int | None = None) -> str:
        session_id = self.next_id("ses", "session_counter")
        duration = duration_seconds or random.randint(120, 1600)
        end_ts = start_ts + timedelta(seconds=duration)
        self.sessions.append(
            (
                session_id,
                user.user_id,
                iso_ts(start_ts),
                iso_ts(end_ts),
                start_ts.date().isoformat(),
                duration,
                entry_page,
                traffic_source,
                user.platform,
                user.device_type,
            )
        )
        return session_id

    def add_event(self, user: User, session_id: str, ts: datetime, event_name: str, plan_type: str = "Free", properties: Optional[dict] = None):
        event_id = self.next_id("evt", "event_counter")
        self.events.append(
            (
                event_id,
                user.user_id,
                session_id,
                iso_ts(ts),
                ts.date().isoformat(),
                event_name,
                user.platform,
                user.device_type,
                user.country,
                plan_type,
                user.user_segment,
                json.dumps(properties or {}, sort_keys=True),
            )
        )

    def add_ticket(self, user: User, created_date: date, category: str, sentiment: str = "negative"):
        ticket_id = self.next_id("tkt", "ticket_counter")
        resolution_hours = round(random.uniform(1.0, 72.0), 1)
        self.support_tickets.append(
            (
                ticket_id,
                user.user_id,
                created_date.isoformat(),
                category,
                sentiment,
                "resolved",
                resolution_hours,
                user.platform,
            )
        )

    def generate(self):
        for signup_day in daterange(START_DATE, END_DATE):
            daily_count = self.daily_signup_count(signup_day)
            for _ in range(daily_count):
                user = self.create_user(signup_day)
                self.users.append(user)
                self.simulate_user(user)

    def daily_signup_count(self, day: date) -> int:
        day_index = (day - START_DATE).days
        growth = 24 + day_index / 23
        weekday_factor = 1.12 if day.weekday() < 4 else 0.82
        seasonality = 1 + 0.10 * math.sin(day_index / 31)
        if day >= date(2026, 4, 15):
            seasonality += 0.05
        if day >= PAID_SEARCH_QUALITY_DECLINE:
            seasonality += 0.18
        mean = growth * weekday_factor * seasonality
        return max(8, int(random.gauss(mean, mean * 0.16)))

    def create_user(self, signup_day: date) -> User:
        self.user_counter += 1
        user_id = f"usr_{self.user_counter:07d}"
        signup_ts = random_timestamp(signup_day)
        country = choose_weighted(
            [
                ("US", 45),
                ("UK", 10),
                ("CA", 8),
                ("DE", 7),
                ("IN", 8),
                ("AU", 6),
                ("BR", 5),
                ("JP", 5),
                ("Other", 6),
            ]
        )
        region = {
            "US": "North America",
            "CA": "North America",
            "UK": "Europe",
            "DE": "Europe",
            "IN": "APAC",
            "AU": "APAC",
            "JP": "APAC",
            "BR": "LATAM",
            "Other": "Other",
        }[country]
        channel = choose_weighted(self.channel_weights(signup_day))
        platform = choose_weighted([("desktop", 54), ("iOS", 26), ("Android", 20)])
        device_type = "desktop" if platform == "desktop" else "mobile"
        segment = choose_weighted(
            [
                ("product_manager", 29),
                ("founder", 12),
                ("sales", 18),
                ("consultant", 15),
                ("student", 15),
                ("operations", 11),
            ]
        )
        company_size = choose_weighted(
            [
                ("1", 18),
                ("2-10", 24),
                ("11-50", 25),
                ("51-200", 19),
                ("201-1000", 10),
                ("1000+", 4),
            ]
        )
        campaign_name = self.campaign_name(channel, signup_day)
        variant = None
        if ONBOARDING_EXPERIMENT_START <= signup_day <= ONBOARDING_EXPERIMENT_END:
            variant = choose_weighted([("A_standard", 50), ("B_guided_setup", 50)])
        return User(
            user_id=user_id,
            signup_timestamp=signup_ts,
            signup_date=signup_day,
            country=country,
            region=region,
            acquisition_channel=channel,
            campaign_name=campaign_name,
            platform=platform,
            device_type=device_type,
            user_segment=segment,
            company_size=company_size,
            onboarding_flow_variant=variant,
        )

    def channel_weights(self, signup_day: date):
        if signup_day >= PAID_SEARCH_QUALITY_DECLINE:
            return [
                ("paid_search", 34),
                ("organic_search", 24),
                ("referral", 13),
                ("content", 10),
                ("social", 10),
                ("email", 5),
                ("partner", 4),
            ]
        return [
            ("organic_search", 31),
            ("paid_search", 18),
            ("referral", 17),
            ("content", 13),
            ("social", 10),
            ("email", 7),
            ("partner", 4),
        ]

    def campaign_name(self, channel: str, signup_day: date) -> str:
        if channel == "paid_search" and signup_day >= PAID_SEARCH_QUALITY_DECLINE:
            return "jun_2026_scale_paid_search"
        if channel == "paid_search":
            return "always_on_paid_search"
        if channel == "content":
            return "meeting_productivity_blog"
        if channel == "email":
            return "newsletter"
        if channel == "partner":
            return "productivity_partner"
        return "none"

    def simulate_user(self, user: User):
        current_plan = "Free"
        session_id = self.add_session(user, user.signup_timestamp, "landing_page", user.acquisition_channel)
        self.add_event(user, session_id, user.signup_timestamp - timedelta(minutes=4), "landing_page_viewed", current_plan, {"campaign_name": user.campaign_name})
        self.add_event(user, session_id, user.signup_timestamp - timedelta(minutes=2), "signup_started", current_plan, {"signup_method": "email"})
        self.add_event(user, session_id, user.signup_timestamp, "signup_completed", current_plan, {"signup_method": "email"})

        if user.onboarding_flow_variant:
            assignment_id = self.next_id("asg", "assignment_counter")
            self.experiments.append(
                (
                    assignment_id,
                    user.user_id,
                    "onboarding_flow_v2",
                    user.onboarding_flow_variant,
                    user.signup_date.isoformat(),
                    user.signup_date.isoformat(),
                )
            )
            self.add_event(
                user,
                session_id,
                add_days(user.signup_timestamp, 0, minutes=1),
                "experiment_assigned",
                current_plan,
                {"experiment_name": "onboarding_flow_v2", "variant": user.onboarding_flow_variant},
            )
            self.add_event(
                user,
                session_id,
                add_days(user.signup_timestamp, 0, minutes=2),
                "experiment_exposed",
                current_plan,
                {"experiment_name": "onboarding_flow_v2", "variant": user.onboarding_flow_variant},
            )

        onboarding_p = 0.88
        if random.random() < onboarding_p:
            self.add_event(user, session_id, add_days(user.signup_timestamp, 0, minutes=3), "onboarding_started", current_plan, {"flow_version": user.onboarding_flow_variant or "default"})
            self.add_event(user, session_id, add_days(user.signup_timestamp, 0, minutes=4), "use_case_selected", current_plan, {"selected_use_case": user.user_segment})

        workspace_p = self.workspace_probability(user)
        has_workspace = random.random() < workspace_p
        if has_workspace:
            self.add_event(user, session_id, add_days(user.signup_timestamp, 0, minutes=6), "workspace_created", current_plan, {"workspace_type": "team" if user.company_size != "1" else "personal"})

        upload_start_p = 0.80 if has_workspace else 0.18
        upload_started = random.random() < upload_start_p
        first_summary_ts = None
        used_action_items = False
        connected_integration = False
        shared_summary = False
        upload_ts = add_days(user.signup_timestamp, random.randint(0, 5), hours=random.randint(0, 4))

        if upload_started and upload_ts.date() <= END_DATE:
            meeting_session_id = self.add_session(user, upload_ts, "workspace", user.acquisition_channel)
            self.add_event(user, meeting_session_id, upload_ts, "recording_upload_started", current_plan, self.recording_properties())
            upload_success_p = self.upload_success_probability(user, upload_ts.date())
            if random.random() < upload_success_p:
                self.add_event(user, meeting_session_id, add_days(upload_ts, 0, minutes=5), "recording_upload_completed", current_plan, self.recording_properties())
                self.add_event(user, meeting_session_id, add_days(upload_ts, 0, minutes=7), "transcript_generation_started", current_plan, {"language": "en"})
                if random.random() < 0.97:
                    self.add_event(user, meeting_session_id, add_days(upload_ts, 0, minutes=11), "transcript_generated", current_plan, {"language": "en", "processing_time_seconds": random.randint(80, 420)})
                    if random.random() < self.summary_probability(user):
                        first_summary_ts = add_days(upload_ts, 0, minutes=13)
                        self.add_event(user, meeting_session_id, first_summary_ts, "ai_summary_generated", current_plan, {"summary_type": "basic", "model_quality_score": round(random.uniform(0.72, 0.96), 2)})
                        used_action_items = self.maybe_action_items(user, meeting_session_id, first_summary_ts, current_plan)
                        connected_integration = self.maybe_integration(user, meeting_session_id, first_summary_ts, current_plan)
                        shared_summary = self.maybe_share(user, meeting_session_id, first_summary_ts, current_plan, used_action_items)
            else:
                self.add_event(user, meeting_session_id, add_days(upload_ts, 0, minutes=4), "recording_upload_failed", current_plan, {"failure_reason": self.upload_failure_reason(user, upload_ts.date())})
                if random.random() < (0.45 if IOS_BUG_START <= upload_ts.date() <= IOS_BUG_END and user.platform == "iOS" else 0.18):
                    self.add_ticket(user, upload_ts.date(), "upload_failed")

        subscription_id = None
        subscription_start = None
        if first_summary_ts:
            subscription_id, subscription_start = self.maybe_subscribe(user, first_summary_ts, used_action_items, connected_integration)
            self.simulate_retention_and_usage(user, first_summary_ts, subscription_start, used_action_items, connected_integration, shared_summary)

        if subscription_id and subscription_start:
            self.simulate_billing(user, subscription_id, subscription_start, used_action_items)

    def workspace_probability(self, user: User) -> float:
        p = 0.70
        if user.user_segment in {"product_manager", "founder", "operations"}:
            p += 0.08
        if user.acquisition_channel in {"referral", "email", "partner"}:
            p += 0.05
        if user.onboarding_flow_variant == "B_guided_setup":
            p += 0.09 if user.platform == "desktop" else 0.03
        if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
            p -= 0.12
        if user.user_segment == "student":
            p -= 0.08
        return clamp(p, 0.20, 0.93)

    def upload_success_probability(self, user: User, upload_day: date) -> float:
        p = 0.88
        if user.platform in {"iOS", "Android"}:
            p -= 0.05
        if user.onboarding_flow_variant == "B_guided_setup":
            p += 0.05
        if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
            p -= 0.07
        if IOS_BUG_START <= upload_day <= IOS_BUG_END and user.platform == "iOS":
            p -= 0.36
        return clamp(p, 0.25, 0.96)

    def summary_probability(self, user: User) -> float:
        p = 0.91
        if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
            p -= 0.05
        if user.user_segment == "student":
            p -= 0.04
        return clamp(p, 0.60, 0.98)

    def recording_properties(self) -> dict:
        return {
            "file_type": choose_weighted([("mp3", 40), ("m4a", 30), ("wav", 20), ("mp4", 10)]),
            "recording_length_minutes": random.randint(8, 55),
        }

    def upload_failure_reason(self, user: User, upload_day: date) -> str:
        if IOS_BUG_START <= upload_day <= IOS_BUG_END and user.platform == "iOS":
            return "ios_retry_bug"
        return choose_weighted([("network_timeout", 35), ("unsupported_file", 20), ("file_too_large", 20), ("unknown_error", 25)])

    def maybe_action_items(self, user: User, session_id: str, summary_ts: datetime, plan_type: str) -> bool:
        if summary_ts.date() < ACTION_ITEMS_LAUNCH:
            return False
        p = 0.20
        if user.user_segment in {"product_manager", "founder", "operations"}:
            p += 0.10
        if user.platform == "desktop":
            p += 0.05
        if random.random() < clamp(p, 0.05, 0.55):
            self.add_event(user, session_id, add_days(summary_ts, 0, minutes=2), "action_items_generated", plan_type, {"num_action_items": random.randint(2, 9)})
            if random.random() < 0.42:
                self.add_event(user, session_id, add_days(summary_ts, 0, minutes=5), "action_item_edited", plan_type, {"edit_count": random.randint(1, 4)})
            return True
        return False

    def maybe_integration(self, user: User, session_id: str, summary_ts: datetime, plan_type: str) -> bool:
        p = 0.16
        if user.user_segment in {"product_manager", "founder", "operations", "sales"}:
            p += 0.07
        if user.company_size not in {"1", "2-10"}:
            p += 0.05
        if random.random() < clamp(p, 0.03, 0.45):
            integration = choose_weighted([("Slack", 38), ("Notion", 28), ("Google Docs", 20), ("Google Calendar", 14)])
            self.add_event(user, session_id, add_days(summary_ts, 0, minutes=3), "integration_page_viewed", plan_type, {"source": "summary_page"})
            self.add_event(user, session_id, add_days(summary_ts, 0, minutes=6), "integration_connected", plan_type, {"integration_name": integration})
            if random.random() < 0.91:
                self.add_event(user, session_id, add_days(summary_ts, 0, minutes=8), "integration_sync_completed", plan_type, {"integration_name": integration})
            else:
                self.add_event(user, session_id, add_days(summary_ts, 0, minutes=8), "integration_sync_failed", plan_type, {"integration_name": integration, "failure_reason": "oauth_error"})
                if random.random() < 0.25:
                    self.add_ticket(user, summary_ts.date(), "integration_failed")
            return True
        return False

    def maybe_share(self, user: User, session_id: str, summary_ts: datetime, plan_type: str, used_action_items: bool) -> bool:
        p = 0.22 + (0.12 if used_action_items else 0)
        if user.user_segment in {"product_manager", "sales", "consultant"}:
            p += 0.06
        if random.random() < clamp(p, 0.05, 0.60):
            self.add_event(user, session_id, add_days(summary_ts, 0, minutes=4), "summary_shared", plan_type, {"share_destination": choose_weighted([("Slack", 40), ("Notion", 25), ("email", 20), ("link", 15)]), "num_recipients": random.randint(1, 8)})
            return True
        return False

    def maybe_subscribe(self, user: User, first_summary_ts: datetime, used_action_items: bool, connected_integration: bool):
        paywall_p = 0.23
        if first_summary_ts.date() >= FREE_LIMIT_CHANGE:
            paywall_p += 0.16
        if used_action_items or connected_integration:
            paywall_p += 0.10
        if user.user_segment == "student":
            paywall_p -= 0.06
        paywall_seen = random.random() < clamp(paywall_p, 0.06, 0.70)
        checkout_seen = False
        subscribe = False
        subscription_ts = None
        session_id = self.add_session(user, add_days(first_summary_ts, random.randint(0, 10), hours=random.randint(0, 3)), "pricing", user.acquisition_channel)

        if first_summary_ts.date() >= FREE_LIMIT_CHANGE and random.random() < 0.35:
            self.add_event(user, session_id, add_days(first_summary_ts, random.randint(1, 16)), "usage_limit_reached", "Free", {"limit_type": "monthly_summaries", "limit_value": 5})

        if paywall_seen:
            paywall_ts = add_days(first_summary_ts, random.randint(0, 18), hours=random.randint(0, 4))
            if paywall_ts.date() <= END_DATE:
                self.add_event(user, session_id, paywall_ts, "paywall_viewed", "Free", {"paywall_reason": "usage_limit_or_pro_feature"})
                self.add_event(user, session_id, add_days(paywall_ts, 0, minutes=1), "pricing_page_viewed", "Free", {"source": "paywall"})
                checkout_p = 0.38
                if used_action_items or connected_integration:
                    checkout_p += 0.14
                if user.user_segment in {"product_manager", "founder", "consultant"}:
                    checkout_p += 0.08
                if user.user_segment == "student":
                    checkout_p -= 0.18
                checkout_seen = random.random() < clamp(checkout_p, 0.05, 0.72)
                if checkout_seen:
                    self.add_event(user, session_id, add_days(paywall_ts, 0, minutes=3), "checkout_started", "Free", {"plan": "Pro", "billing_cycle": "monthly"})
                    subscribe_p = 0.44
                    if first_summary_ts.date() >= FREE_LIMIT_CHANGE:
                        subscribe_p += 0.12
                    if used_action_items:
                        subscribe_p += 0.09
                    if connected_integration:
                        subscribe_p += 0.07
                    if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
                        subscribe_p -= 0.16
                    if user.user_segment == "student":
                        subscribe_p -= 0.18
                    subscribe = random.random() < clamp(subscribe_p, 0.04, 0.78)
                    if subscribe:
                        subscription_ts = add_days(paywall_ts, 0, minutes=6)
                        self.add_event(user, session_id, subscription_ts, "subscription_started", "Pro", {"plan": "Pro", "monthly_price": 18, "billing_cycle": "monthly"})

        if subscribe and subscription_ts and subscription_ts.date() <= END_DATE:
            subscription_id = self.next_id("sub", "subscription_counter")
            return subscription_id, subscription_ts.date()
        return None, None

    def simulate_retention_and_usage(self, user: User, first_summary_ts: datetime, subscription_start: Optional[date], used_action_items: bool, connected_integration: bool, shared_summary: bool):
        d1_p = 0.28 + (0.17 if used_action_items else 0) + (0.10 if connected_integration else 0)
        d7_p = 0.20 + (0.19 if used_action_items else 0) + (0.14 if connected_integration else 0) + (0.08 if shared_summary else 0)
        if user.user_segment == "student":
            d1_p -= 0.06
            d7_p -= 0.08
        if user.signup_date >= FREE_LIMIT_CHANGE and subscription_start is None:
            d7_p -= 0.06
        if random.random() < clamp(d1_p, 0.05, 0.75):
            self.add_return_session(user, first_summary_ts.date() + timedelta(days=1), "summary_viewed", "Free")
        if random.random() < clamp(d7_p, 0.03, 0.82):
            self.add_return_session(user, first_summary_ts.date() + timedelta(days=random.randint(7, 13)), "summary_viewed", "Free")

        current = user.signup_date.replace(day=1)
        current = (current + timedelta(days=32)).replace(day=1)
        while current <= END_DATE:
            if current < user.signup_date:
                current = (current + timedelta(days=32)).replace(day=1)
                continue
            monthly_active_p = 0.18
            if first_summary_ts:
                monthly_active_p += 0.20
            if subscription_start and current >= subscription_start.replace(day=1):
                monthly_active_p += 0.22
            if used_action_items:
                monthly_active_p += 0.07
            if connected_integration:
                monthly_active_p += 0.08
            if user.user_segment == "student":
                monthly_active_p -= 0.10
            if current >= FREE_LIMIT_CHANGE.replace(day=1) and subscription_start is None:
                monthly_active_p -= 0.04
            if random.random() < clamp(monthly_active_p, 0.02, 0.82):
                meetings = 1 + (1 if random.random() < 0.34 else 0) + (1 if subscription_start and random.random() < 0.24 else 0)
                for _ in range(meetings):
                    meeting_day = date(current.year, current.month, random.randint(1, min(27, self.days_in_month(current))))
                    if user.signup_date <= meeting_day <= END_DATE:
                        plan_type = "Pro" if subscription_start and meeting_day >= subscription_start else "Free"
                        self.add_meeting_usage(user, meeting_day, plan_type, used_action_items)
            current = (current + timedelta(days=32)).replace(day=1)

    def add_return_session(self, user: User, day: date, event_name: str, plan_type: str):
        if day > END_DATE:
            return
        ts = random_timestamp(day)
        session_id = self.add_session(user, ts, "dashboard", user.acquisition_channel)
        self.add_event(user, session_id, ts, event_name, plan_type, {"source": "return_visit"})

    def add_meeting_usage(self, user: User, meeting_day: date, plan_type: str, previously_used_action_items: bool):
        ts = random_timestamp(meeting_day)
        session_id = self.add_session(user, ts, "workspace", user.acquisition_channel)
        self.add_event(user, session_id, ts, "recording_upload_started", plan_type, self.recording_properties())
        if random.random() < self.upload_success_probability(user, meeting_day):
            self.add_event(user, session_id, add_days(ts, 0, minutes=5), "recording_upload_completed", plan_type, self.recording_properties())
            self.add_event(user, session_id, add_days(ts, 0, minutes=10), "transcript_generated", plan_type, {"language": "en", "processing_time_seconds": random.randint(80, 480)})
            self.add_event(user, session_id, add_days(ts, 0, minutes=13), "ai_summary_generated", plan_type, {"summary_type": "advanced" if plan_type == "Pro" else "basic", "model_quality_score": round(random.uniform(0.72, 0.98), 2)})
            if meeting_day >= ACTION_ITEMS_LAUNCH:
                p = 0.18 + (0.28 if plan_type == "Pro" else 0) + (0.12 if previously_used_action_items else 0)
                if random.random() < clamp(p, 0.03, 0.80):
                    self.add_event(user, session_id, add_days(ts, 0, minutes=15), "action_items_generated", plan_type, {"num_action_items": random.randint(2, 10)})
            if random.random() < (0.16 if plan_type == "Free" else 0.34):
                self.add_event(user, session_id, add_days(ts, 0, minutes=18), "summary_shared", plan_type, {"share_destination": choose_weighted([("Slack", 40), ("Notion", 25), ("email", 20), ("link", 15)]), "num_recipients": random.randint(1, 12)})
        else:
            self.add_event(user, session_id, add_days(ts, 0, minutes=4), "recording_upload_failed", plan_type, {"failure_reason": self.upload_failure_reason(user, meeting_day)})
            if random.random() < 0.12:
                self.add_ticket(user, meeting_day, "upload_failed")

    def simulate_billing(self, user: User, subscription_id: str, subscription_start: date, used_action_items: bool):
        monthly_price = 18.0
        billing_cycle = "monthly"
        status = "active"
        end_date = None
        cancel_reason = None
        period_start = subscription_start
        months_active = 0

        while period_start <= END_DATE:
            months_active += 1
            invoice_id = self.next_id("inv", "invoice_counter")
            period_end = min(period_start + timedelta(days=30), END_DATE)
            payment_success_p = 0.965
            if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
                payment_success_p -= 0.045
            if user.user_segment == "student":
                payment_success_p -= 0.06
            paid = random.random() < clamp(payment_success_p, 0.78, 0.99)
            paid_date = period_start + timedelta(days=random.randint(0, 2)) if paid else None
            self.billing_invoices.append(
                (
                    invoice_id,
                    subscription_id,
                    user.user_id,
                    period_start.isoformat(),
                    period_start.isoformat(),
                    period_end.isoformat(),
                    monthly_price,
                    "paid" if paid else "failed",
                    paid_date.isoformat() if paid_date else None,
                )
            )
            payment_id = self.next_id("pay", "payment_counter")
            self.payments.append(
                (
                    payment_id,
                    invoice_id,
                    subscription_id,
                    user.user_id,
                    (paid_date or period_start).isoformat(),
                    monthly_price,
                    "succeeded" if paid else "failed",
                    None if paid else choose_weighted([("card_declined", 45), ("insufficient_funds", 35), ("expired_card", 20)]),
                )
            )

            cancel_p = 0.025
            if user.user_segment == "student":
                cancel_p += 0.05
            if user.acquisition_channel == "paid_search" and user.signup_date >= PAID_SEARCH_QUALITY_DECLINE:
                cancel_p += 0.025
            if used_action_items:
                cancel_p -= 0.012
            if months_active >= 2 and random.random() < clamp(cancel_p, 0.005, 0.18):
                status = "cancelled"
                end_date = period_end
                cancel_reason = choose_weighted([("too_expensive", 34), ("not_using_enough", 34), ("missing_feature", 16), ("switched_tool", 16)])
                cancel_ts = random_timestamp(end_date)
                session_id = self.add_session(user, cancel_ts, "billing", user.acquisition_channel)
                self.add_event(user, session_id, cancel_ts, "subscription_cancelled", "Pro", {"cancel_reason": cancel_reason})
                break

            if period_start + timedelta(days=31) <= END_DATE:
                renewal_ts = random_timestamp(period_start + timedelta(days=30))
                session_id = self.add_session(user, renewal_ts, "billing", user.acquisition_channel, duration_seconds=random.randint(30, 180))
                self.add_event(user, session_id, renewal_ts, "subscription_renewed", "Pro", {"billing_cycle": billing_cycle, "monthly_price": monthly_price})

            period_start = period_start + timedelta(days=30)

        self.subscriptions.append(
            (
                subscription_id,
                user.user_id,
                subscription_start.isoformat(),
                end_date.isoformat() if end_date else None,
                status,
                "Pro",
                monthly_price,
                billing_cycle,
                cancel_reason,
            )
        )

    def days_in_month(self, day: date) -> int:
        next_month = (day.replace(day=28) + timedelta(days=4)).replace(day=1)
        return (next_month - timedelta(days=1)).day

    def product_calendar_rows(self):
        return [
            ("2026-03-01", "experiment", "Onboarding flow v2 begins", "A/B test comparing standard onboarding with guided setup.", "activation"),
            ("2026-04-15", "launch", "Action items feature launch", "Pro-oriented AI action item extraction launches.", "feature_adoption"),
            ("2026-05-10", "incident", "iOS upload retry bug begins", "iOS version 2.3.1 introduced an upload retry bug.", "upload_completion"),
            ("2026-05-17", "incident", "iOS upload retry bug resolved", "iOS version 2.3.2 fixed the upload retry bug.", "upload_completion"),
            ("2026-05-25", "pricing", "Free summary limit changed", "Free plan monthly AI summary limit changed from 10 to 5.", "monetization"),
            ("2026-06-01", "campaign", "Paid search scale-up", "Growth team increased paid search spend, bringing more but lower-intent signups.", "acquisition_quality"),
        ]

    def write_sqlite(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists():
            DB_PATH.unlink()
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        self.create_tables(cur)
        cur.executemany(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    u.user_id,
                    iso_ts(u.signup_timestamp),
                    u.signup_date.isoformat(),
                    u.country,
                    u.region,
                    u.acquisition_channel,
                    u.campaign_name,
                    u.platform,
                    u.device_type,
                    u.user_segment,
                    u.company_size,
                    "Free",
                    u.onboarding_flow_variant,
                )
                for u in self.users
            ],
        )
        cur.executemany("INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", self.sessions)
        cur.executemany("INSERT INTO events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", self.events)
        cur.executemany("INSERT INTO experiments VALUES (?, ?, ?, ?, ?, ?)", self.experiments)
        cur.executemany("INSERT INTO subscriptions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", self.subscriptions)
        cur.executemany("INSERT INTO billing_invoices VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", self.billing_invoices)
        cur.executemany("INSERT INTO payments VALUES (?, ?, ?, ?, ?, ?, ?, ?)", self.payments)
        cur.executemany("INSERT INTO support_tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?)", self.support_tickets)
        cur.executemany("INSERT INTO product_calendar VALUES (?, ?, ?, ?, ?)", self.product_calendar_rows())
        self.create_indexes(cur)
        conn.commit()
        conn.close()

    def create_tables(self, cur):
        cur.executescript(
            """
            CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                signup_timestamp TEXT NOT NULL,
                signup_date TEXT NOT NULL,
                country TEXT NOT NULL,
                region TEXT NOT NULL,
                acquisition_channel TEXT NOT NULL,
                campaign_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                device_type TEXT NOT NULL,
                user_segment TEXT NOT NULL,
                company_size TEXT NOT NULL,
                plan_type_at_signup TEXT NOT NULL,
                onboarding_flow_variant TEXT
            );

            CREATE TABLE sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_start TEXT NOT NULL,
                session_end TEXT NOT NULL,
                session_date TEXT NOT NULL,
                session_duration_seconds INTEGER NOT NULL,
                entry_page TEXT NOT NULL,
                traffic_source TEXT NOT NULL,
                platform TEXT NOT NULL,
                device_type TEXT NOT NULL
            );

            CREATE TABLE events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                session_id TEXT NOT NULL,
                event_timestamp TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_name TEXT NOT NULL,
                platform TEXT NOT NULL,
                device_type TEXT NOT NULL,
                country TEXT NOT NULL,
                plan_type TEXT NOT NULL,
                user_segment TEXT NOT NULL,
                properties TEXT NOT NULL
            );

            CREATE TABLE experiments (
                assignment_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                experiment_name TEXT NOT NULL,
                variant TEXT NOT NULL,
                assigned_date TEXT NOT NULL,
                exposed_date TEXT NOT NULL
            );

            CREATE TABLE subscriptions (
                subscription_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                subscription_start_date TEXT NOT NULL,
                subscription_end_date TEXT,
                status TEXT NOT NULL,
                plan TEXT NOT NULL,
                monthly_price REAL NOT NULL,
                billing_cycle TEXT NOT NULL,
                cancel_reason TEXT
            );

            CREATE TABLE billing_invoices (
                invoice_id TEXT PRIMARY KEY,
                subscription_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                invoice_date TEXT NOT NULL,
                billing_period_start TEXT NOT NULL,
                billing_period_end TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                paid_date TEXT
            );

            CREATE TABLE payments (
                payment_id TEXT PRIMARY KEY,
                invoice_id TEXT NOT NULL,
                subscription_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                payment_date TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                failure_reason TEXT
            );

            CREATE TABLE support_tickets (
                ticket_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_date TEXT NOT NULL,
                category TEXT NOT NULL,
                sentiment TEXT NOT NULL,
                status TEXT NOT NULL,
                resolution_time_hours REAL NOT NULL,
                platform TEXT NOT NULL
            );

            CREATE TABLE product_calendar (
                calendar_date TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                affected_area TEXT NOT NULL
            );
            """
        )

    def create_indexes(self, cur):
        cur.executescript(
            """
            CREATE INDEX idx_users_signup_date ON users(signup_date);
            CREATE INDEX idx_users_channel ON users(acquisition_channel);
            CREATE INDEX idx_events_user_date ON events(user_id, event_date);
            CREATE INDEX idx_events_name_date ON events(event_name, event_date);
            CREATE INDEX idx_events_platform_date ON events(platform, event_date);
            CREATE INDEX idx_sessions_user_date ON sessions(user_id, session_date);
            CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
            CREATE INDEX idx_invoices_subscription ON billing_invoices(subscription_id);
            CREATE INDEX idx_tickets_date_category ON support_tickets(created_date, category);
            """
        )

    def print_summary(self):
        print(f"Created {DB_PATH}")
        print(f"Users: {len(self.users):,}")
        print(f"Sessions: {len(self.sessions):,}")
        print(f"Events: {len(self.events):,}")
        print(f"Experiment assignments: {len(self.experiments):,}")
        print(f"Subscriptions: {len(self.subscriptions):,}")
        print(f"Invoices: {len(self.billing_invoices):,}")
        print(f"Payments: {len(self.payments):,}")
        print(f"Support tickets: {len(self.support_tickets):,}")


def main():
    generator = Generator()
    generator.generate()
    generator.write_sqlite()
    generator.print_summary()


if __name__ == "__main__":
    main()

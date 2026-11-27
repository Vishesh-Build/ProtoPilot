"""
UI/UX Pro Max Design Intelligence Engine for ProtoPilot.

Transforms captured client meeting requirements into a domain-calibrated,
human-grade design system (style, palette tokens, typography hierarchy,
layout proportions, data visualization rules, authentic sample entities,
and anti-AI-slop guardrails) used by the Interface Designer, Google Stitch,
Prototype Builder, and resilient Prototype Synthesizer.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ThemeTokens:
    bg: str
    surface: str
    elevated: str
    hover: str
    border: str
    border_strong: str
    text: str
    muted: str
    accent: str
    accent2: str
    accent_contrast: str
    accent_soft: str
    success: str
    warning: str
    danger: str
    shadow: str


@dataclass(frozen=True)
class DesignProfile:
    domain: str
    style_name: str
    default_mode: str  # "light" | "dark"
    brand_default: str
    tagline: str
    workspace_label: str
    chart_title: str
    chart_subtitle: str
    chart_kind: str
    cta_label: str
    font_display: str
    font_body: str
    radius_card: str
    radius_control: str
    light_tokens: ThemeTokens
    dark_tokens: ThemeTokens
    kpi_labels: tuple[str, str, str, str]
    kpi_7d_usd: tuple[str, str, str, str]
    kpi_30d_usd: tuple[str, str, str, str]
    kpi_90d_usd: tuple[str, str, str, str]
    kpi_7d_inr: tuple[str, str, str, str]
    kpi_30d_inr: tuple[str, str, str, str]
    kpi_90d_inr: tuple[str, str, str, str]
    deltas: tuple[str, str, str, str]
    insights: tuple[tuple[str, str], tuple[str, str]]
    sample_owners_global: tuple[str, ...]
    sample_owners_in: tuple[str, ...]
    anti_patterns: tuple[str, ...]


_FONT_MODERN_UI = '"Inter", "Segoe UI Variable Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
_FONT_EDITORIAL_DISPLAY = '"Plus Jakarta Sans", "Segoe UI Variable Display", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'


DESIGN_CATALOG: dict[str, DesignProfile] = {
    "fintech": DesignProfile(
        domain="fintech",
        style_name="Mercury / Stripe Financial Precision",
        default_mode="light",
        brand_default="LedgerCraft",
        tagline="Automated Cashflow, Mandates & Spend Intelligence",
        workspace_label="Transactions & Rules",
        chart_title="Net Inflow vs Outflow",
        chart_subtitle="Verified daily settlement & expense curve",
        chart_kind="Dual-series comparison with horizontal gridlines, formatted Y-axis currency ticks, and Nov 2026 dates",
        cta_label="New Entry",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="12px",
        radius_control="8px",
        light_tokens=ThemeTokens(
            bg="#F8FAFC",
            surface="#FFFFFF",
            elevated="#F1F5F9",
            hover="rgba(15, 23, 42, 0.035)",
            border="#E2E8F0",
            border_strong="#CBD5E1",
            text="#0F172A",
            muted="#64748B",
            accent="#047857",
            accent2="#1D4ED8",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(4, 120, 87, 0.09)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)",
        ),
        dark_tokens=ThemeTokens(
            bg="#0A0C10",
            surface="#11141B",
            elevated="#181C25",
            hover="rgba(255, 255, 255, 0.045)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#F4F5F7",
            muted="#9CA3AF",
            accent="#10B981",
            accent2="#60A5FA",
            accent_contrast="#04150F",
            accent_soft="rgba(16, 185, 129, 0.12)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Net Cashflow", "Monthly Inflow", "Operating Spend", "Active Auto-Rules"),
        kpi_7d_usd=("$4,820", "$11,400", "$6,580", "18 Rules"),
        kpi_30d_usd=("$19,450", "$46,800", "$27,350", "24 Rules"),
        kpi_90d_usd=("$58,920", "$142,100", "$83,180", "31 Rules"),
        kpi_7d_inr=("₹1,42,800", "₹3,18,500", "₹1,75,700", "18 Active"),
        kpi_30d_inr=("₹5,84,250", "₹12,90,000", "₹7,05,750", "24 Active"),
        kpi_90d_inr=("₹18,12,600", "₹38,40,000", "₹20,27,400", "31 Active"),
        deltas=("+12.4% vs prior", "+6.2% inflow", "-4.1% burn", "100% synced"),
        insights=(
            ("Recurring SaaS Overlap Found", "2 duplicate subscriptions total ₹3,499/mo — consolidate under Finance > Rules."),
            ("Auto-Reconciliation Active", "98.2% of incoming UPI and bank settlements tagged within 15 seconds."),
        ),
        sample_owners_global=("Stripe Settlement", "AWS Cloud Billing", "Figma Team", "Uber Business", "Gusto Payroll", "Slack Pro"),
        sample_owners_in=("Razorpay Settlement", "AWS Mumbai", "Zomato Corporate", "BESCOM Power", "Apollo Pharmacy", "Airtel Fiber"),
        anti_patterns=(
            "NO glowing neon cyan wave chart without Y-axis ticks, X-axis dates, or horizontal gridlines",
            "NO hardcoded 'Oct 24, 2023' or 'Whole Foods Market' placeholder rows",
            "Match currency to client locale (₹ INR when UPI/GST/India is mentioned; $ USD otherwise)",
            "Display 6-8 populated ledger rows visible in the main view — never a 1-row empty card",
        ),
    ),
    "healthcare": DesignProfile(
        domain="healthcare",
        style_name="Calm Clinical Editorial Clean",
        default_mode="light",
        brand_default="MedAxis Care",
        tagline="Outpatient Queue, Clinical Records & Pharmacy Operations",
        workspace_label="Patients & Appointments",
        chart_title="Daily Consultation Throughput",
        chart_subtitle="Scheduled vs completed clinical visits across departments",
        chart_kind="Grouped bar or clean area trend with Y-axis visit counts, horizontal guides, and today's shift slots",
        cta_label="Book Slot",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="12px",
        radius_control="8px",
        light_tokens=ThemeTokens(
            bg="#F6FAFA",
            surface="#FFFFFF",
            elevated="#ECF5F4",
            hover="rgba(15, 118, 110, 0.04)",
            border="#DCEAE8",
            border_strong="#B8D4D0",
            text="#0F172A",
            muted="#526462",
            accent="#0F766E",
            accent2="#0284C7",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(15, 118, 110, 0.10)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(15, 23, 42, 0.05)",
        ),
        dark_tokens=ThemeTokens(
            bg="#0A1014",
            surface="#11191F",
            elevated="#17232B",
            hover="rgba(255, 255, 255, 0.04)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#F1F5F9",
            muted="#94A3B8",
            accent="#14B8A6",
            accent2="#38BDF8",
            accent_contrast="#041514",
            accent_soft="rgba(20, 184, 166, 0.12)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Active Care Queue", "On-Time Consults", "Verified Prescriptions", "Median Wait Time"),
        kpi_7d_usd=("148", "96.4%", "142 Issued", "4.2 min"),
        kpi_30d_usd=("612", "97.2%", "598 Issued", "3.8 min"),
        kpi_90d_usd=("1,890", "97.9%", "1,845 Issued", "3.4 min"),
        kpi_7d_inr=("148", "96.4%", "142 Issued", "4.2 min"),
        kpi_30d_inr=("612", "97.2%", "598 Issued", "3.8 min"),
        kpi_90d_inr=("1,890", "97.9%", "1,845 Issued", "3.4 min"),
        deltas=("+9.4% weekly", "+2.6% SLA", "NABH Ready", "-18% faster"),
        insights=(
            ("Expiring Batch Alert (3 SKUs)", "Amoxicillin 500mg & ORS stock batches cross 30-day threshold — reorder queued."),
            ("Follow-Up Reminders Sent", "WhatsApp & SMS slot confirmations delivered for 42 morning OPD visits."),
        ),
        sample_owners_global=("Dr. Elena Vance", "Nurse Rachel Kim", "Lab Diagnostics", "Pharmacy Desk", "Triage Station 2", "Radiology Wing"),
        sample_owners_in=("Dr. Kavita Mehta", "Dr. Rohan Deshmukh", "Thyrocare Lab", "Dispensing Desk", "OPD Triage 2", "Dr. Ananya Rao"),
        anti_patterns=(
            "AVOID dark cyberpunk neon themes for healthcare unless explicitly requested — use calm high-contrast daylight paper",
            "Use WCAG AA >= 4.5:1 contrast on clinical status pills and medication alerts",
        ),
    ),
    "commerce": DesignProfile(
        domain="commerce",
        style_name="Editorial Retail & Storefront Studio",
        default_mode="light",
        brand_default="ShelfCraft",
        tagline="Catalog Merchandising, Orders & Fulfillment Control",
        workspace_label="Orders & Inventory",
        chart_title="Gross Revenue & Order Volume",
        chart_subtitle="Daily checkout conversion and dispatch fulfillment",
        chart_kind="Clean bar or area revenue chart with Y-axis revenue ticks and category conversion share",
        cta_label="Add Item",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="10px",
        radius_control="8px",
        light_tokens=ThemeTokens(
            bg="#FAF9F6",
            surface="#FFFFFF",
            elevated="#F3EFE8",
            hover="rgba(24, 24, 27, 0.035)",
            border="#E6E0D6",
            border_strong="#CFC6B8",
            text="#18181B",
            muted="#57534E",
            accent="#C2410C",
            accent2="#0F766E",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(194, 65, 12, 0.09)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(24, 24, 27, 0.06)",
        ),
        dark_tokens=ThemeTokens(
            bg="#0D0C0B",
            surface="#161412",
            elevated="#1F1C19",
            hover="rgba(255, 255, 255, 0.045)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#FAFAF9",
            muted="#A8A29E",
            accent="#F97316",
            accent2="#14B8A6",
            accent_contrast="#1A0800",
            accent_soft="rgba(249, 115, 22, 0.13)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.38)",
        ),
        kpi_labels=("Gross Order Value", "On-Time Dispatch", "Active Catalog SKUs", "Repeat Buyers"),
        kpi_7d_usd=("$18,420", "98.1%", "124 Live", "68.4%"),
        kpi_30d_usd=("$76,950", "98.6%", "142 Live", "71.2%"),
        kpi_90d_usd=("$228,400", "99.1%", "168 Live", "74.5%"),
        kpi_7d_inr=("₹2,48,600", "98.1%", "124 Live", "68.4%"),
        kpi_30d_inr=("₹9,84,200", "98.6%", "142 Live", "71.2%"),
        kpi_90d_inr=("₹28,45,000", "99.1%", "168 Live", "74.5%"),
        deltas=("+16.8% growth", "+1.9% SLA", "3 low stock", "+4.2% repeat"),
        insights=(
            ("Evening Demand Surge Ready", "Express dispatch lanes and stock safety thresholds calibrated for peak orders."),
            ("Low-Inventory Restock Trigger", "3 top-selling SKUs dropped below 14-day cover — vendor PO draft ready."),
        ),
        sample_owners_global=("Order #ORD-4821", "Order #ORD-4822", "Warehouse East", "VIP Dispatch", "Catalog Ops", "Returns Desk"),
        sample_owners_in=("Delhivery Express", "BlueDart Priority", "Mumbai Hub", "Pune Kitchen", "Jaipur Artisan SKU", "Razorpay COD"),
        anti_patterns=(
            "Include clear price/stock alignment (`tabular-nums`), warm readable contrast, and distinct status badges",
            "Avoid generic purple gradients or empty image boxes",
        ),
    ),
    "education": DesignProfile(
        domain="education",
        style_name="Modern Academic Studio (Notion / Linear Craft)",
        default_mode="light",
        brand_default="CohortFlow",
        tagline="Interactive Learning Cohorts, Assessments & Student Progress",
        workspace_label="Courses & Cohorts",
        chart_title="Cohort Completion & Weekly Activity",
        chart_subtitle="Lessons completed vs assessment scores across active batches",
        chart_kind="Weekly bar comparison with completion rate trend",
        cta_label="Create Module",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="10px",
        radius_control="8px",
        light_tokens=ThemeTokens(
            bg="#F9FAFB",
            surface="#FFFFFF",
            elevated="#F1F5F9",
            hover="rgba(37, 99, 235, 0.04)",
            border="#E5E7EB",
            border_strong="#CBD5E1",
            text="#111827",
            muted="#6B7280",
            accent="#2563EB",
            accent2="#7C3AED",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(37, 99, 235, 0.09)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(17, 24, 39, 0.05)",
        ),
        dark_tokens=ThemeTokens(
            bg="#0B0D12",
            surface="#13161E",
            elevated="#1B1F2A",
            hover="rgba(255, 255, 255, 0.04)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.17)",
            text="#F3F4F6",
            muted="#9CA3AF",
            accent="#3B82F6",
            accent2="#A78BFA",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(59, 130, 246, 0.13)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Active Learners", "Module Completion", "Avg Quiz Score", "Pending Reviews"),
        kpi_7d_usd=("1,240", "88.4%", "86.2%", "14"),
        kpi_30d_usd=("1,480", "91.2%", "88.5%", "9"),
        kpi_90d_usd=("1,820", "93.0%", "90.1%", "5"),
        kpi_7d_inr=("1,240", "88.4%", "86.2%", "14"),
        kpi_30d_inr=("1,480", "91.2%", "88.5%", "9"),
        kpi_90d_inr=("1,820", "93.0%", "90.1%", "5"),
        deltas=("+11% enrolled", "+4.2% completion", "+3.1 pts", "SLA on track"),
        insights=(
            ("Module 4 Drop-Off Check", "82% of learners finish quizzes under 12 mins — hint cards improved pass rate."),
            ("Mentor Office Hours Ready", "34 doubts resolved today with automatic recap notes published."),
        ),
        sample_owners_global=("Prof. Maya Lin", "Cohort B-2026", "Lab Grading", "Study Group A", "Capstone Review", "Mentor Desk"),
        sample_owners_in=("Prof. Siddharth Nair", "Batch CS-2026", "Viva Queue", "Lab Assignment 4", "Placement Prep", "Doubt Desk"),
        anti_patterns=("Bright distraction-free light paper for reading comprehension; clear milestone progress bars",),
    ),
    "logistics": DesignProfile(
        domain="logistics",
        style_name="Industrial Dispatch & Fleet Telemetry",
        default_mode="light",
        brand_default="RoutePulse",
        tagline="Live Fleet Routing, Hub Utilization & Delivery SLA",
        workspace_label="Shipments & Routes",
        chart_title="On-Time Delivery & Hub Load",
        chart_subtitle="Completed dispatches vs scheduled SLA windows",
        chart_kind="Bar + trend comparison with clear hub SLA metrics",
        cta_label="Dispatch Load",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="10px",
        radius_control="7px",
        light_tokens=ThemeTokens(
            bg="#F1F5F9",
            surface="#FFFFFF",
            elevated="#E8EEF5",
            hover="rgba(3, 105, 161, 0.04)",
            border="#CBD5E1",
            border_strong="#94A3B8",
            text="#0F172A",
            muted="#475569",
            accent="#0369A1",
            accent2="#EA580C",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(3, 105, 161, 0.09)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(15, 23, 42, 0.06)",
        ),
        dark_tokens=ThemeTokens(
            bg="#0A0E14",
            surface="#111822",
            elevated="#192230",
            hover="rgba(255, 255, 255, 0.04)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#F1F5F9",
            muted="#94A3B8",
            accent="#38BDF8",
            accent2="#FB923C",
            accent_contrast="#06141E",
            accent_soft="rgba(56, 189, 248, 0.12)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Active Shipments", "On-Time SLA", "Fleet Utilization", "Exceptions Open"),
        kpi_7d_usd=("342", "97.4%", "89.2%", "3"),
        kpi_30d_usd=("1,480", "98.1%", "91.4%", "5"),
        kpi_90d_usd=("4,310", "98.5%", "92.8%", "7"),
        kpi_7d_inr=("342", "97.4%", "89.2%", "3"),
        kpi_30d_inr=("1,480", "98.1%", "91.4%", "5"),
        kpi_90d_inr=("4,310", "98.5%", "92.8%", "7"),
        deltas=("+12% volume", "+1.4% SLA", "Optimal load", "2 resolved today"),
        insights=(
            ("West Corridor Weather Reroute", "4 vans shifted to NH-48 bypass saving 42 mins average transit time."),
            ("Cold-Chain Telemetry Stable", "All 12 refrigerated containers holding 2.8°C to 3.4°C inside threshold."),
        ),
        sample_owners_global=("Fleet Unit 14", "Hub Chicago", "Route North-7", "Priority Cargo", "Dock B-04", "Customs Clear"),
        sample_owners_in=("Bhiwandi Hub", "Surat Corridor", "NH-48 Express", "Pune Cold Chain", "JNPT Gate 3", "Ahmedabad Linehaul"),
        anti_patterns=("High-contrast tabular data density with clear route identifiers and SLA pills",),
    ),
    "hospitality": DesignProfile(
        domain="hospitality",
        style_name="Serene Editorial Concierge",
        default_mode="light",
        brand_default="Velora Desk",
        tagline="Reservations, Guest Experience & Service Schedule",
        workspace_label="Bookings & Schedule",
        chart_title="Occupancy & Booking Velocity",
        chart_subtitle="Confirmed reservations vs capacity across peak hours",
        chart_kind="Clean area trend with formatted occupancy % Y-axis and slot utilization",
        cta_label="New Booking",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="12px",
        radius_control="8px",
        light_tokens=ThemeTokens(
            bg="#FBF9F5",
            surface="#FFFFFF",
            elevated="#F4EFE6",
            hover="rgba(28, 25, 23, 0.035)",
            border="#E7DFD3",
            border_strong="#D4C7B5",
            text="#1C1917",
            muted="#57534E",
            accent="#0F766E",
            accent2="#B45309",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(15, 118, 110, 0.09)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 3px rgba(28, 25, 23, 0.06)",
        ),
        dark_tokens=ThemeTokens(
            bg="#100E0C",
            surface="#191613",
            elevated="#24201B",
            hover="rgba(255, 255, 255, 0.04)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#FAF8F5",
            muted="#A8A29E",
            accent="#2DD4BF",
            accent2="#FBBF24",
            accent_contrast="#081C18",
            accent_soft="rgba(45, 212, 191, 0.12)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Confirmed Bookings", "Seat / Room Occupancy", "Check-In Ready", "Guest Rating"),
        kpi_7d_usd=("128", "84.6%", "98%", "4.9 / 5"),
        kpi_30d_usd=("542", "87.2%", "99%", "4.9 / 5"),
        kpi_90d_usd=("1,610", "89.1%", "99%", "4.9 / 5"),
        kpi_7d_inr=("128", "84.6%", "98%", "4.9 / 5"),
        kpi_30d_inr=("542", "87.2%", "99%", "4.9 / 5"),
        kpi_90d_inr=("1,610", "89.1%", "99%", "4.9 / 5"),
        deltas=("+14% weekend", "+5.1% yield", "Zero wait", "42 new reviews"),
        insights=(
            ("Saturday Prime Slots 92% Booked", "Enable waitlist auto-offer for 6–9 PM cancellations."),
            ("VIP Preferences Synced", "Check-in notes and loyalty perks attached to 8 arriving guests."),
        ),
        sample_owners_global=("Suite 402", "Front Concierge", "Spa Wing", "Chef Table 6", "VIP Lounge", "Housekeeping"),
        sample_owners_in=("Studio 04", "Front Desk", "Wellness Wing", "Terrace Dining", "Member Lounge", "Concierge Lead"),
        anti_patterns=("Use warm editorial linen/ivory surfaces rather than cold dark terminal styles",),
    ),
    "saas": DesignProfile(
        domain="saas",
        style_name="Linear / Notion Porcelain Minimalist",
        default_mode="light",
        brand_default="WorkGrid",
        tagline="Unified Operations, Automation & Client Workflows",
        workspace_label="Workflows & Operations",
        chart_title="Operational Velocity & SLA Trend",
        chart_subtitle="Completed workflow items and automation reliability",
        chart_kind="Clean area trend + category bar breakdown with labeled Y-axis & dates",
        cta_label="Create Workflow",
        font_display=_FONT_EDITORIAL_DISPLAY,
        font_body=_FONT_MODERN_UI,
        radius_card="10px",
        radius_control="7px",
        light_tokens=ThemeTokens(
            bg="#FAFAFA",
            surface="#FFFFFF",
            elevated="#F4F4F5",
            hover="rgba(24, 24, 27, 0.035)",
            border="#E4E4E7",
            border_strong="#D4D4D8",
            text="#18181B",
            muted="#71717A",
            accent="#2563EB",
            accent2="#4F46E5",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(37, 99, 235, 0.08)",
            success="#059669",
            warning="#D97706",
            danger="#DC2626",
            shadow="0 1px 2px rgba(0, 0, 0, 0.05)",
        ),
        dark_tokens=ThemeTokens(
            bg="#09090B",
            surface="#111114",
            elevated="#18181D",
            hover="rgba(255, 255, 255, 0.04)",
            border="rgba(255, 255, 255, 0.09)",
            border_strong="rgba(255, 255, 255, 0.18)",
            text="#FAFAFA",
            muted="#A1A1AA",
            accent="#3B82F6",
            accent2="#818CF8",
            accent_contrast="#FFFFFF",
            accent_soft="rgba(59, 130, 246, 0.13)",
            success="#34D399",
            warning="#FBBF24",
            danger="#F87171",
            shadow="0 8px 24px rgba(0, 0, 0, 0.35)",
        ),
        kpi_labels=("Active Workflows", "Automation Rate", "Weekly Actions", "Reliability SLA"),
        kpi_7d_usd=("12", "94.6%", "1,284", "99.4%"),
        kpi_30d_usd=("18", "96.2%", "5,410", "99.6%"),
        kpi_90d_usd=("26", "97.4%", "16,820", "99.8%"),
        kpi_7d_inr=("12", "94.6%", "1,284", "99.4%"),
        kpi_30d_inr=("18", "96.2%", "5,410", "99.6%"),
        kpi_90d_inr=("26", "97.4%", "16,820", "99.8%"),
        deltas=("All operational", "+5.4% automated", "+18.4% throughput", "Zero blockers"),
        insights=(
            ("Approval Queue Automated", "Routine client approvals routed automatically based on priority rules."),
            ("Team Audit Trail Synced", "Role permissions and export readiness verified across active workspaces."),
        ),
        sample_owners_global=("Operations Lead", "Automation Engine", "QA Lead", "Platform Team", "Success Desk", "Billing Ops"),
        sample_owners_in=("Priya Sharma", "Arjun Patel", "Neha Verma", "Automation Engine", "Rohan Kulkarni", "Ops Desk"),
        anti_patterns=(
            "Restrained monochrome surfaces with one purposeful Cobalt/Indigo primary accent — NO rainbow neon gradients",
        ),
    ),
}


def resolve_design_system(
    corpus: str,
    features: list[dict[str, str]] | None = None,
    explicit_brand: str = "",
) -> dict:
    """
    Applies the UI/UX Pro Max design resolution pipeline:
    1. Analyze product domain, theme preference, locale/currency, and auth presence.
    2. Select matched DesignProfile (style, light/dark tokens, typography, chart spec, entities).
    3. Return structured Design System dict ready for UI agent, Stitch, LLM Prototype, and Fallback.
    """
    low = (corpus or "").lower()

    if any(k in low for k in ("upi", "expense", "fintech", "bank", "ledger", "payment", "invoice", "budget", "wallet", "finance", "gst", "tax", "payroll", "trading")):
        domain = "fintech"
    elif any(k in low for k in ("patient", "clinic", "hospital", "doctor", "health", "medical", "telehealth", "diagnosis", "pharmacy", "medicine", "prescription")):
        domain = "healthcare"
    elif any(k in low for k in ("order", "delivery", "restaurant", "menu", "cart", "checkout", "shop", "commerce", "catalog", "store", "retail", "inventory", "pos")):
        domain = "commerce"
    elif any(k in low for k in ("student", "course", "lms", "classroom", "quiz", "assignment", "college", "school", "teacher", "learning", "cohort", "exam")):
        domain = "education"
    elif any(k in low for k in ("fleet", "shipment", "logistics", "warehouse", "supply chain", "parcel", "freight", "courier", "dispatch")):
        domain = "logistics"
    elif any(k in low for k in ("hotel", "salon", "spa", "wellness", "booking", "reservation", "real estate", "property", "travel", "resort")):
        domain = "hospitality"
    else:
        domain = "saas"

    profile = DESIGN_CATALOG[domain]

    explicit_dark = any(k in low for k in ("dark mode", "dark theme", "dark ui", "obsidian", "midnight theme", "night mode"))
    explicit_light = any(k in low for k in ("light mode", "light theme", "daylight", "white background", "minimal light"))

    # Default to clean Daylight Editorial so prototypes don't all look like dark AI neon templates,
    # while faithfully respecting explicit dark mode requests with restrained Linear/Mercury craft.
    mode = "dark" if (explicit_dark and not explicit_light) else profile.default_mode
    is_india = any(k in low for k in ("upi", "gst", "inr", "₹", "rupee", "bhim", "razorpay", "aadhaar", "pan card", "india", "hindi", "gujarati"))
    has_auth = any(k in low for k in ("otp", "login", "auth", "sign in", "verification", "mobile number", "password", "sso", "2fa"))

    website_signals = (
        "website", "web site", "storefront", "landing page", "marketplace",
        "e-commerce", "ecommerce", "shopping cart", "add to cart", "wishlist",
        "product catalog", "food ordering", "food delivery", "restaurant website",
        "hotel booking", "travel booking", "trip booking", "course platform",
        "online store", "checkout flow", "booking website", "portfolio site",
        "saas landing", "real estate listing", "property listing", "catalog",
    )
    dashboard_signals = (
        "admin dashboard", "analytics dashboard", "telemetry", "expense tracker",
        "kpi dashboard", "operations dashboard", "internal tool", "ledger",
        "monitoring console",
    )
    has_web = any(k in low for k in website_signals)
    has_dash_only = any(k in low for k in dashboard_signals) and not any(
        k in low for k in ("website", "storefront", "landing page", "marketplace", "e-commerce", "ecommerce", "shopping cart")
    )
    layout_mode = "website" if (has_web and not has_dash_only) else "dashboard"

    product_name = (explicit_brand or "").strip()
    if not product_name:
        m = re.search(
            r"(?:Product|Project|Platform|App|Brand)\s*Name\s*[:\-]\s*\*?\*?([^\n\r*|#`]{2,38})",
            corpus or "",
            re.IGNORECASE,
        )
        if m:
            cand = m.group(1).strip(" *`\"'—-")
            if cand and "enterprise application" not in cand.lower():
                product_name = cand
    if not product_name:
        if domain == "saas" and features:
            words = re.sub(r"[^a-zA-Z0-9\s]", "", features[0].get("title", "")).split()[:3]
            product_name = " ".join(words) or profile.brand_default
        else:
            product_name = profile.brand_default

    active_tokens = profile.dark_tokens if mode == "dark" else profile.light_tokens

    return {
        "domain": domain,
        "layout_mode": layout_mode,
        "style_name": profile.style_name,
        "mode": mode,
        "prefer_light": mode == "light",
        "locale": "IN" if is_india else "US",
        "currency_symbol": "₹" if is_india else "$",
        "has_auth": has_auth,
        "product_name": product_name,
        "profile": profile,
        "tokens": active_tokens,
        "owners": profile.sample_owners_in if is_india else profile.sample_owners_global,
    }


def build_ui_design_brief(requirements_block: str, corpus: str = "") -> str:
    """Produces a concise UI/UX Pro Max Design System brief for the Interface Designer agent."""
    ds = resolve_design_system(f"{requirements_block}\n{corpus}")
    p: DesignProfile = ds["profile"]
    t: ThemeTokens = ds["tokens"]
    currency_note = "₹ INR (Indian numbering e.g. ₹14,250, realistic Indian entities)" if ds["locale"] == "IN" else "$ USD (formatted e.g. $4,250.00)"
    layout_note = (
        "**CONSUMER WEBSITE** (Sticky Top Navbar + Split Hero with Finder/CTA + Filterable Catalog/Offer Cards Grid + Quick-View Modal + Slide-Over Cart/Booking Drawer + Pricing/Reviews + FAQ + Footer — NEVER build a sidebar admin dashboard)"
        if ds["layout_mode"] == "website"
        else "**OPERATIONAL WORKSPACE / DASHBOARD** (Left Navigation Rail + Sticky Topbar + 4 KPI Cards + Labeled Chart + 6-8 Populated Table Rows + Inspector Drawer)"
    )
    return (
        "## UI/UX Pro Max Design System Recommendation\n"
        f"- **Layout Archetype**: {layout_note}\n"
        f"- **Product Domain**: {ds['domain'].title()} | **Recommended Style**: {p.style_name}\n"
        f"- **Default Mode**: `{ds['mode'].upper()}` (provide a smooth Light/Dark switcher supporting both themes)\n"
        f"- **Palette Tokens**: bg=`{t.bg}`, surface=`{t.surface}`, elevated=`{t.elevated}`, border=`{t.border}`, "
        f"text=`{t.text}`, muted=`{t.muted}`, primary-accent=`{t.accent}`, secondary-accent=`{t.accent2}`\n"
        f"- **Typography & Radius**: Display `{p.font_display}` + Body `{p.font_body}` with `tabular-nums`, "
        f"card radius `{p.radius_card}`, control radius `{p.radius_control}`\n"
        f"- **Chart Architecture**: {p.chart_kind}\n"
        f"- **Locale & Entities**: {currency_note}; use current 2026 dates (e.g. `27 Nov 2026`, `Today`, `Yesterday`) "
        f"and authentic actors ({', '.join(ds['owners'][:4])})\n"
        f"- **Anti-Patterns to Avoid**: {'; '.join(p.anti_patterns)}"
    )


def build_prototype_design_brief(requirements_block: str, corpus: str = "") -> str:
    """Produces a crisp executable UI/UX craft contract for Prototype Builder & Stitch."""
    ds = resolve_design_system(f"{requirements_block}\n{corpus}")
    p: DesignProfile = ds["profile"]
    lt = p.light_tokens
    dt = p.dark_tokens
    mode_rule = (
        f"START IN `{ds['mode'].upper()}` MODE by default (match `body` class accordingly). "
        "Include a subtle Light/Dark toggle in the topbar (`<input id='light-theme-toggle'>`)."
    )
    if ds["layout_mode"] == "website":
        arch_rules = (
            "- Layout Archetype: CONSUMER WEBSITE (DO NOT output a sidebar-plus-4-KPI-card admin dashboard!).\n"
            "  Build a real multi-section consumer web app with: (1) Sticky 64px Top Navbar (logo, page nav links Home/Catalog/Compare/Orders, search bar, Light/Dark toggle, Wishlist count, interactive Cart/Booking Bag drawer trigger, Account/OTP modal trigger); "
            "(2) Editorial Split Hero Banner (bold display headline, value prop, live search/filter bar, trust metrics, crisp bespoke SVG vector scene); "
            "(3) Interactive Category Chips + Sort + 6-9 rich Product/Service/Listing Cards (bespoke inline SVG artwork, ratings, tags, price in tabular-nums, Quick-View modal, Wishlist heart toggle, Add to Cart/Book button); "
            "(4) Slide-over Shopping Cart / Booking Drawer (quantity +/-, promo code e.g. WELCOME10, live subtotal/tax calculation, Express Checkout modal creating live tracked orders); "
            "(5) Customer Testimonials / Comparison + Expandable FAQ Accordion + Clean Multi-Column Website Footer."
        )
    else:
        arch_rules = (
            "- Layout Archetype: OPERATIONAL DASHBOARD.\n"
            "  Visual Restraint: Crisp 1px hairline borders, NO glowing neon radial background blobs, NO rainbow gradients on cards, "
            "NO oversized empty chart boxes (keep chart height compact ~220px-250px so 6+ ledger/data rows are immediately visible below it!).\n"
            f"  Real Chart Craft: Crisp SVG horizontal gridlines, formatted Y-axis scale ticks (e.g. {ds['currency_symbol']}0, {ds['currency_symbol']}25k), X-axis 2026 dates, subtle <= 0.14 fill opacity, hover tooltips."
        )

    return (
        f"DESIGN SYSTEM SPEC ({p.style_name} — Make it look crafted by a senior human product designer, NOT an AI dark neon clone):\n"
        f"- Domain: {ds['domain'].title()} | Layout Mode: {ds['layout_mode'].upper()} | Brand Suggestion: {ds['product_name']} | Currency/Locale: {ds['currency_symbol']} ({ds['locale']})\n"
        f"- {mode_rule}\n"
        f"- Light Tokens: --bg:{lt.bg}; --surface:{lt.surface}; --elevated:{lt.elevated}; --border:{lt.border}; --text:{lt.text}; --muted:{lt.muted}; --accent:{lt.accent}; --accent2:{lt.accent2};\n"
        f"- Dark Tokens: --bg:{dt.bg}; --surface:{dt.surface}; --elevated:{dt.elevated}; --border:{dt.border}; --text:{dt.text}; --muted:{dt.muted}; --accent:{dt.accent}; --accent2:{dt.accent2};\n"
        f"{arch_rules}\n"
        f"- Authentic Content: Populate 6-9 domain-authentic items/cards using {', '.join(ds['owners'][:5])} and 2026 dates (ZERO 'Whole Foods Market', ZERO 'Oct 24, 2023', ZERO 'John Doe', ZERO emoji UI icons — use clean 16px hairline <svg> icons)."
    )

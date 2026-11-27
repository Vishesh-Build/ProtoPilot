"""
Human-Grade SaaS Prototype Synthesizer powered by the UI/UX Pro Max design system.

Used when upstream LLMs exhaust or return incomplete/auth-gate stubs. Renders a
domain-calibrated, responsive, interactive web application with calibrated Light
or Dark surface palettes, crisp Lucide-style inline SVG icons, formatted multi-series
charts with gridlines & hover tooltips, authentic regional records, interactive
slide-over drawers, modals, and zero AI/developer clichés.
"""

from __future__ import annotations

import html as html_lib
import json
import re

from app.agents.design_system import DesignProfile, ThemeTokens, resolve_design_system


def _parse_requirements(requirements_block: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    if not requirements_block:
        return items
    for raw_line in requirements_block.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue
        prio_match = re.match(r"^-\s*\[([^\]]+)\]\s*(.*)$", line)
        priority = prio_match.group(1).strip().title() if prio_match else "Medium"
        clean = prio_match.group(2).strip() if prio_match else line.lstrip("- ").strip()
        cat_match = re.search(r"\(([^)]+)\)$", clean)
        category = cat_match.group(1).strip() if cat_match else "Core"
        title = re.sub(r"\s*\([^)]+\)$", "", clean).strip()
        if title:
            items.append({"title": title, "category": category, "priority": priority})
    return items


def _css_vars_block(tokens: ThemeTokens, profile: DesignProfile) -> str:
    return (
        f"--bg: {tokens.bg}; "
        f"--surface: {tokens.surface}; "
        f"--elevated: {tokens.elevated}; "
        f"--hover: {tokens.hover}; "
        f"--border: {tokens.border}; "
        f"--border-strong: {tokens.border_strong}; "
        f"--text: {tokens.text}; "
        f"--muted: {tokens.muted}; "
        f"--accent: {tokens.accent}; "
        f"--accent2: {tokens.accent2}; "
        f"--accent-contrast: {tokens.accent_contrast}; "
        f"--accent-soft: {tokens.accent_soft}; "
        f"--success: {tokens.success}; "
        f"--warning: {tokens.warning}; "
        f"--danger: {tokens.danger}; "
        f"--shadow: {tokens.shadow}; "
        f"--font-display: {profile.font_display}; "
        f"--font-body: {profile.font_body}; "
        f"--radius-card: {profile.radius_card}; "
        f"--radius-control: {profile.radius_control};"
    )


def build_executive_prototype_html(
    states: dict | None = None,
    requirements_block: str = "",
) -> str:
    """
    Renders a domain-matched, responsive, multi-view interactive HTML5 application
    guided by UI/UX Pro Max palette, typography, and chart craft rules.
    """
    features = _parse_requirements(requirements_block)
    if not features:
        features = [
            {"title": "Role-Based Access & Identity Verification", "category": "Security", "priority": "High"},
            {"title": "Real-Time Operational Telemetry Dashboard", "category": "Analytics", "priority": "High"},
            {"title": "Automated Approval & Status Routing", "category": "Automation", "priority": "High"},
            {"title": "Filterable Operations & Detail Inspector", "category": "Operations", "priority": "Medium"},
            {"title": "Instant Alerts & Theme Controls", "category": "Workspace", "priority": "Medium"},
        ]

    pm_text = ((states or {}).get("pm").output or "") if states and "pm" in states else ""
    ui_text = ((states or {}).get("ui").output or "") if states and "ui" in states else ""
    combined_corpus = f"{pm_text}\n{ui_text}\n{requirements_block}"

    ds = resolve_design_system(combined_corpus, features=features)
    profile: DesignProfile = ds["profile"]
    owners: tuple[str, ...] = ds["owners"]
    currency = ds["currency_symbol"]
    is_inr = ds["locale"] == "IN"

    # Build at least 6 authentic, varied records grounded in client requirements + domain context
    dates_2026 = ["27 Nov 2026", "26 Nov 2026", "25 Nov 2026", "24 Nov 2026", "23 Nov 2026", "22 Nov 2026", "21 Nov 2026", "20 Nov 2026"]
    status_cycle = ["Active", "Verified", "In Review", "Active", "Scheduled", "Verified"]
    records = []
    for idx, feat in enumerate(features[:10], start=1):
        owner = owners[(idx - 1) % len(owners)]
        metric_val = (
            f"{currency}{12_400 + idx * 3_150:,}" if ds["domain"] in ("fintech", "commerce") else f"{93 + (idx % 6)}.{(idx * 4) % 9}%"
        )
        records.append({
            "id": f"REC-{200 + idx}",
            "title": feat["title"],
            "category": feat["category"],
            "priority": feat["priority"] if feat["priority"] in ("High", "Medium", "Low") else "Medium",
            "status": status_cycle[(idx - 1) % len(status_cycle)],
            "owner": owner,
            "updated": dates_2026[(idx - 1) % len(dates_2026)],
            "score": metric_val,
            "notes": f"Managed by {owner} under {feat['category']}. Use the controls below to advance status or inspect audit history.",
        })

    # Pad to 6 minimum visible rows with cohesive domain companion entries if fewer than 6 captured
    pad_titles = {
        "fintech": ("Daily Settlement Sweep", "Reconciliation"),
        "healthcare": ("Outpatient Follow-Up Queue", "Patient Care"),
        "commerce": ("Express Dispatch Cutoff Audit", "Fulfillment"),
        "education": ("Weekly Cohort Assessment Check", "Academic"),
        "logistics": ("Hub SLA Corridor Check", "Routing"),
        "hospitality": ("Prime Slot Waitlist Sync", "Concierge"),
        "saas": ("Automated Compliance Snapshot", "Governance"),
    }
    base_pad = pad_titles.get(ds["domain"], ("Operational Audit Rule", "Operations"))
    while len(records) < 6:
        idx = len(records) + 1
        owner = owners[(idx - 1) % len(owners)]
        metric_val = (
            f"{currency}{8_950 + idx * 2_400:,}" if ds["domain"] in ("fintech", "commerce") else f"{94 + (idx % 5)}.{(idx * 3) % 9}%"
        )
        records.append({
            "id": f"REC-{200 + idx}",
            "title": f"{owner} — {base_pad[0]}",
            "category": base_pad[1],
            "priority": "Medium" if idx % 2 == 0 else "High",
            "status": status_cycle[(idx - 1) % len(status_cycle)],
            "owner": owner,
            "updated": dates_2026[(idx - 1) % len(dates_2026)],
            "score": metric_val,
            "notes": f"Verified operational check routed through {owner}.",
        })

    if is_inr:
        kpi_7d, kpi_30d, kpi_90d = list(profile.kpi_7d_inr), list(profile.kpi_30d_inr), list(profile.kpi_90d_inr)
    else:
        kpi_7d, kpi_30d, kpi_90d = list(profile.kpi_7d_usd), list(profile.kpi_30d_usd), list(profile.kpi_90d_usd)

    y_prefix = currency if ds["domain"] in ("fintech", "commerce") else ""
    y_suffix = "" if y_prefix else "%"

    payload = {
        "domain": ds["domain"],
        "styleName": ds["style_name"],
        "productName": ds["product_name"],
        "tagline": profile.tagline,
        "workspaceLabel": profile.workspace_label,
        "chartTitle": profile.chart_title,
        "chartSubtitle": profile.chart_subtitle,
        "yPrefix": y_prefix,
        "ySuffix": y_suffix,
        "yMax": 120000 if y_prefix else 100,
        "kpiLabels": list(profile.kpi_labels),
        "kpis": {"7d": kpi_7d, "30d": kpi_30d, "90d": kpi_90d},
        "deltas": list(profile.deltas),
        "insights": [list(pair) for pair in profile.insights],
        "hasAuth": ds["has_auth"],
        "preferLight": ds["prefer_light"],
        "records": records,
    }

    safe_name = html_lib.escape(ds["product_name"])
    safe_tagline = html_lib.escape(profile.tagline)
    safe_ws = html_lib.escape(profile.workspace_label)
    safe_cta = html_lib.escape(profile.cta_label)
    light_vars = _css_vars_block(profile.light_tokens, profile)
    dark_vars = _css_vars_block(profile.dark_tokens, profile)
    light_checked = "checked" if ds["prefer_light"] else ""
    body_cls = "" if ds["prefer_light"] else "dark-theme"
    auth_badge_display = "inline-flex" if ds["has_auth"] else "none"
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    template = _HTML_TEMPLATE
    replacements = {
        "__SAFE_TITLE__": safe_name,
        "__SAFE_TAGLINE__": safe_tagline,
        "__WORKSPACE_LABEL__": safe_ws,
        "__CHART_TITLE__": html_lib.escape(profile.chart_title),
        "__CHART_SUBTITLE__": html_lib.escape(profile.chart_subtitle),
        "__STYLE_BADGE__": html_lib.escape(ds["style_name"]),
        "__CTA_LABEL__": safe_cta,
        "__LIGHT_VARS__": light_vars,
        "__DARK_VARS__": dark_vars,
        "__BODY_CLASS__": body_cls,
        "__LIGHT_CHECKED__": light_checked,
        "__AUTH_BADGE_DISPLAY__": auth_badge_display,
        "__DATA_JSON__": data_json,
    }
    for key, val in replacements.items():
        template = template.replace(key, val)
    return template


_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__SAFE_TITLE__ — Workspace</title>
<style>
  :root {
    __LIGHT_VARS__
  }
  body.dark-theme {
    __DARK_VARS__
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; font-family: var(--font-body); }
  body { background: var(--bg); color: var(--text); display: flex; overflow: hidden; -webkit-font-smoothing: antialiased; transition: background 0.18s ease, color 0.18s ease; }
  .num { font-variant-numeric: tabular-nums; }

  /* Crisp Minimal Sidebar */
  aside { width: 228px; background: var(--surface); border-right: 1px solid var(--border); display: flex; flex-direction: column; flex-shrink: 0; }
  .brand { padding: 16px; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 10px; }
  .brand-mark { width: 30px; height: 30px; border-radius: var(--radius-control); background: var(--accent); display: flex; align-items: center; justify-content: center; color: var(--accent-contrast); font-family: var(--font-display); font-weight: 700; font-size: 13px; flex-shrink: 0; }
  .brand-name { font-family: var(--font-display); font-size: 14px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; letter-spacing: -0.015em; }
  .brand-sub { font-size: 11px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .nav-list { list-style: none; padding: 12px 10px; flex: 1; display: flex; flex-direction: column; gap: 3px; overflow-y: auto; }
  .nav-group { font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); padding: 10px 10px 4px; }
  .nav-item { display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: var(--radius-control); color: var(--muted); font-size: 13px; font-weight: 500; cursor: pointer; transition: background 0.12s, color 0.12s; user-select: none; }
  .nav-item:hover { background: var(--hover); color: var(--text); }
  .nav-item.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
  .nav-item svg { width: 16px; height: 16px; flex-shrink: 0; stroke: currentColor; fill: none; stroke-width: 1.85; stroke-linecap: round; stroke-linejoin: round; }
  .aside-card { margin: 12px; padding: 11px 12px; border-radius: var(--radius-card); background: var(--elevated); border: 1px solid var(--border); font-size: 11.5px; color: var(--muted); line-height: 1.45; }
  .aside-dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--success); margin-right: 6px; }

  /* Main Layout */
  main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
  header.topbar { height: 58px; padding: 0 22px; background: var(--surface); border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-shrink: 0; }
  .top-left { display: flex; align-items: center; gap: 12px; min-width: 0; }
  .page-title { font-family: var(--font-display); font-size: 15.5px; font-weight: 700; color: var(--text); letter-spacing: -0.015em; white-space: nowrap; }
  .page-crumb { font-size: 12px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .top-actions { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .search-global { background: var(--elevated); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 6px 12px; font-size: 12.5px; width: 210px; outline: none; transition: border-color 0.15s; }
  .search-global:focus { border-color: var(--accent); background: var(--surface); }
  .btn { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 6px 12px; font-size: 12.5px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: border-color 0.12s, background 0.12s; white-space: nowrap; }
  .btn:hover { border-color: var(--border-strong); background: var(--elevated); }
  .btn svg { width: 14px; height: 14px; stroke: currentColor; fill: none; stroke-width: 1.9; stroke-linecap: round; stroke-linejoin: round; }
  .btn-primary { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); font-weight: 600; }
  .btn-primary:hover { opacity: 0.92; background: var(--accent); border-color: var(--accent); }
  .auth-chip { background: var(--accent-soft); color: var(--accent); border: 1px solid var(--border); border-radius: 999px; padding: 5px 11px; font-size: 11.5px; font-weight: 600; cursor: pointer; align-items: center; gap: 6px; }
  .notif-wrap { position: relative; }
  .notif-badge { position: absolute; top: 5px; right: 7px; width: 6px; height: 6px; border-radius: 50%; background: var(--danger); }
  .notif-pop { position: absolute; right: 0; top: 38px; width: 290px; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius-card); box-shadow: var(--shadow); padding: 12px; display: none; z-index: 40; }
  .notif-pop.open { display: block; }
  .notif-item { padding: 8px 6px; border-bottom: 1px solid var(--border); font-size: 12px; color: var(--text); }
  .notif-item:last-child { border-bottom: none; }

  /* Content Canvas */
  .view-area { flex: 1; overflow-y: auto; overflow-x: hidden; padding: 20px 24px 34px; }
  .view-pane { display: none; max-width: 1260px; margin: 0 auto; min-width: 0; }
  .view-pane.active { display: block; }

  /* Page Subheader Row */
  .hero-strip { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }
  .hero-strip > div { min-width: 0; max-width: 100%; }
  .hero-kicker { font-size: 11px; font-weight: 600; color: var(--accent); margin-bottom: 3px; letter-spacing: 0.02em; }
  .hero-h { font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--text); letter-spacing: -0.02em; }
  .hero-p { font-size: 12.5px; color: var(--muted); margin-top: 2px; }

  /* KPI Grid */
  .kpi-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
  .kpi-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 15px 16px; box-shadow: var(--shadow); min-width: 0; }
  .kpi-top { display: flex; align-items: center; justify-content: space-between; font-size: 12px; color: var(--muted); font-weight: 500; margin-bottom: 6px; }
  .kpi-val { font-family: var(--font-display); font-size: 22px; font-weight: 700; color: var(--text); letter-spacing: -0.02em; }
  .kpi-foot { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; gap: 8px; min-width: 0; }
  .delta-pill { font-size: 11px; font-weight: 600; color: var(--accent); background: var(--accent-soft); padding: 2px 8px; border-radius: 6px; white-space: nowrap; }

  /* Panels & Proportional Bento */
  .bento-2 { display: grid; grid-template-columns: 1.5fr 1fr; gap: 14px; margin-bottom: 16px; }
  .bento-2 > *, .panel { min-width: 0; }
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 16px 18px; margin-bottom: 16px; box-shadow: var(--shadow); }
  .panel-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
  .panel-title { font-family: var(--font-display); font-size: 14px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
  .panel-sub { font-size: 12px; color: var(--muted); margin-top: 1px; }
  .seg-group { display: inline-flex; background: var(--elevated); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 2px; gap: 2px; }
  .seg-btn { border: none; background: transparent; color: var(--muted); font-size: 11.5px; font-weight: 600; padding: 4px 10px; border-radius: 6px; cursor: pointer; }
  .seg-btn.active { background: var(--surface); color: var(--text); box-shadow: 0 1px 2px rgba(0,0,0,0.08); }

  /* Chart */
  .chart-wrap { position: relative; width: 100%; }
  .chart-legend { display: flex; align-items: center; gap: 14px; font-size: 11.5px; color: var(--muted); margin-bottom: 6px; }
  .legend-dot { display: inline-block; width: 8px; height: 8px; border-radius: 2px; margin-right: 5px; }
  .chart-tip { position: absolute; pointer-events: none; background: var(--surface); border: 1px solid var(--border-strong); color: var(--text); font-size: 11.5px; font-weight: 600; padding: 5px 10px; border-radius: 7px; box-shadow: var(--shadow); opacity: 0; transition: opacity 0.12s; white-space: nowrap; z-index: 15; }

  /* Insights & Priority Breakdown */
  .donut-row { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
  .insight-item { background: var(--elevated); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 10px 12px; margin-bottom: 8px; display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; }
  .insight-h { font-size: 12.5px; font-weight: 600; color: var(--text); }
  .insight-p { font-size: 11.5px; color: var(--muted); margin-top: 2px; line-height: 1.4; }

  /* Filter chips & Crisp Data Table */
  .toolbar-row { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
  .chip-bar { display: flex; gap: 6px; flex-wrap: wrap; }
  .chip { background: var(--elevated); border: 1px solid var(--border); color: var(--muted); border-radius: 999px; padding: 4px 11px; font-size: 12px; font-weight: 500; cursor: pointer; }
  .chip.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .table-wrap { width: 100%; overflow-x: auto; }
  table { width: 100%; border-collapse: collapse; text-align: left; font-size: 12.5px; min-width: 580px; }
  th { padding: 9px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); font-weight: 600; border-bottom: 1px solid var(--border); background: var(--elevated); }
  td { padding: 10px 12px; border-bottom: 1px solid var(--border); color: var(--text); vertical-align: middle; }
  tbody tr { cursor: pointer; transition: background 0.1s; }
  tbody tr:hover { background: var(--hover); }
  .pill { display: inline-flex; align-items: center; padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 600; }
  .pill-active { background: var(--accent-soft); color: var(--accent); }
  .pill-verified { background: rgba(29, 78, 216, 0.10); color: var(--accent2); }
  .pill-progress { background: rgba(217, 119, 6, 0.12); color: var(--warning); }
  .cards-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
  .rec-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 14px; cursor: pointer; transition: border-color 0.15s; }
  .rec-card:hover { border-color: var(--accent); }

  /* Progress & Settings */
  .bar-track { height: 8px; background: var(--elevated); border-radius: 999px; overflow: hidden; margin-top: 6px; margin-bottom: 14px; }
  .bar-fill { height: 100%; border-radius: 999px; }
  .toggle-row { display: flex; align-items: center; justify-content: space-between; padding: 13px 0; border-bottom: 1px solid var(--border); gap: 12px; }
  .switch { position: relative; display: inline-block; width: 42px; height: 22px; flex-shrink: 0; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; inset: 0; background: var(--border-strong); border-radius: 999px; cursor: pointer; transition: 0.2s; }
  .slider:before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: #fff; border-radius: 50%; transition: 0.2s; }
  input:checked + .slider { background: var(--accent); }
  input:checked + .slider:before { transform: translateX(20px); }

  /* Drawer & Modal */
  .backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(2px); display: none; z-index: 80; }
  .backdrop.open { display: flex; }
  .modal-box { margin: auto; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius-card); width: min(460px, 92vw); padding: 20px; box-shadow: 0 20px 45px rgba(15, 23, 42, 0.2); }
  .drawer { margin-left: auto; width: min(400px, 92vw); height: 100%; background: var(--surface); border-left: 1px solid var(--border-strong); padding: 20px; display: flex; flex-direction: column; overflow-y: auto; }
  .form-group { margin-bottom: 13px; }
  .form-lbl { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin-bottom: 5px; }
  .form-ctl { width: 100%; background: var(--elevated); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 8px 11px; font-size: 13px; outline: none; }
  .form-ctl:focus { border-color: var(--accent); background: var(--surface); }

  /* Toast */
  .toast-stack { position: fixed; bottom: 18px; right: 18px; display: flex; flex-direction: column; gap: 8px; z-index: 120; pointer-events: none; }
  .toast { background: var(--surface); border: 1px solid var(--border-strong); border-left: 3px solid var(--accent); color: var(--text); padding: 9px 14px; border-radius: var(--radius-control); font-size: 12.5px; font-weight: 500; box-shadow: var(--shadow); }

  /* Responsive */
  @media (max-width: 900px) {
    .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .bento-2 { grid-template-columns: 1fr; }
    .cards-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .search-global { width: 145px; }
  }
  @media (max-width: 700px) {
    html, body { height: auto; min-height: 100%; overflow-x: hidden; overflow-y: auto; }
    body { flex-direction: column; }
    aside, main { width: 100%; max-width: 100%; min-width: 0; border-right: none; overflow: visible; }
    aside { border-bottom: 1px solid var(--border); }
    .brand { padding: 10px 14px; }
    .aside-card, .nav-group { display: none; }
    .nav-list { flex-direction: row; flex-wrap: wrap; gap: 6px; padding: 8px 10px; overflow: visible; }
    .nav-item { padding: 6px 10px; font-size: 11.5px; }
    header.topbar { padding: 10px 12px; height: auto; min-height: 50px; flex-wrap: wrap; gap: 8px; }
    .top-actions { flex-wrap: wrap; width: 100%; justify-content: flex-start; gap: 6px; }
    .page-crumb, .search-global { display: none; }
    .view-area { padding: 14px 12px 24px; overflow: visible; }
    .kpi-grid, .cards-grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body class="__BODY_CLASS__">
  <aside>
    <div class="brand">
      <div class="brand-mark" id="brand-initials">WK</div>
      <div style="min-width:0;">
        <div class="brand-name">__SAFE_TITLE__</div>
        <div class="brand-sub">Workspace</div>
      </div>
    </div>
    <ul class="nav-list" id="nav-list">
      <li class="nav-group">Core Workspace</li>
      <li class="nav-item active" data-view="overview" onclick="switchView('overview', this)">
        <svg viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>
        Overview
      </li>
      <li class="nav-item" data-view="workspace" onclick="switchView('workspace', this)">
        <svg viewBox="0 0 24 24"><path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/></svg>
        __WORKSPACE_LABEL__
      </li>
      <li class="nav-item" data-view="analytics" onclick="switchView('analytics', this)">
        <svg viewBox="0 0 24 24"><path d="M3 3v18h18"/><path d="M7 15l4-4 4 3 5-6"/></svg>
        Analytics
      </li>
      <li class="nav-group">Governance</li>
      <li class="nav-item" data-view="settings" onclick="switchView('settings', this)">
        <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        Settings &amp; Security
      </li>
    </ul>
    <div class="aside-card">
      <div><span class="aside-dot"></span><strong style="color:var(--text);">All Systems Synced</strong></div>
      <div style="margin-top:3px;">__SAFE_TAGLINE__</div>
    </div>
  </aside>

  <main>
    <header class="topbar">
      <div class="top-left">
        <div>
          <div class="page-title" id="topbar-title">Overview</div>
          <div class="page-crumb">__SAFE_TITLE__ &middot; __STYLE_BADGE__</div>
        </div>
      </div>
      <div class="top-actions">
        <input type="text" class="search-global" id="global-search" placeholder="Search entries, owners..." oninput="handleGlobalSearch(this.value)">
        <button type="button" class="auth-chip" id="auth-chip-btn" style="display:__AUTH_BADGE_DISPLAY__;" onclick="openAuthModal()">
          <span id="auth-chip-label">Verified &middot; 2FA</span>
        </button>
        <div class="notif-wrap">
          <button type="button" class="btn" onclick="toggleNotifs()" title="Notifications">
            <svg viewBox="0 0 24 24"><path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></svg>
            <span class="notif-badge" id="notif-dot"></span>
          </button>
          <div class="notif-pop" id="notif-pop">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
              <strong style="font-size:12px;">Workspace Alerts</strong>
              <button type="button" class="btn" style="padding:3px 8px;font-size:11px;" onclick="markNotifsRead()">Clear</button>
            </div>
            <div id="notif-list"></div>
          </div>
        </div>
        <button type="button" class="btn" onclick="toggleTheme()" title="Switch Light/Dark Theme">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>
        </button>
        <button type="button" class="btn btn-primary" onclick="openCreateModal()">+ __CTA_LABEL__</button>
      </div>
    </header>

    <div class="view-area">
      <!-- VIEW 1: EXECUTIVE OVERVIEW -->
      <section id="view-overview" class="view-pane active">
        <div class="hero-strip">
          <div>
            <div class="hero-kicker">Updated Nov 2026 &middot; Live Operations</div>
            <div class="hero-h">__SAFE_TITLE__ Overview</div>
            <div class="hero-p">__SAFE_TAGLINE__</div>
          </div>
          <div style="display:flex;gap:8px;flex-wrap:wrap;">
            <button type="button" class="btn" onclick="switchView('analytics')">View Analytics</button>
            <button type="button" class="btn" onclick="switchView('workspace')">Open __WORKSPACE_LABEL__ &rarr;</button>
          </div>
        </div>

        <div class="kpi-grid" id="kpi-grid"></div>

        <div class="bento-2">
          <div class="panel" style="margin-bottom:0;">
            <div class="panel-head">
              <div>
                <div class="panel-title">__CHART_TITLE__</div>
                <div class="panel-sub">__CHART_SUBTITLE__</div>
              </div>
              <div class="seg-group" id="range-group">
                <button type="button" class="seg-btn" onclick="setRange('7d', this)">7D</button>
                <button type="button" class="seg-btn active" onclick="setRange('30d', this)">30D</button>
                <button type="button" class="seg-btn" onclick="setRange('90d', this)">90D</button>
              </div>
            </div>
            <div class="chart-legend">
              <span><span class="legend-dot" style="background:var(--accent);"></span>Primary Series</span>
              <span><span class="legend-dot" style="background:var(--accent2);"></span>Baseline Target</span>
            </div>
            <div class="chart-wrap">
              <svg id="trend-svg" viewBox="0 0 600 185" style="width:100%;height:auto;display:block;"></svg>
              <div class="chart-tip" id="chart-tip"></div>
            </div>
          </div>

          <div class="panel" style="margin-bottom:0;">
            <div class="panel-head">
              <div>
                <div class="panel-title">Priority Mix &amp; Recommendations</div>
                <div class="panel-sub">Operational share and quick optimizations</div>
              </div>
            </div>
            <div class="donut-row">
              <svg id="donut-svg" viewBox="0 0 110 110" width="90" height="90" style="flex-shrink:0;"></svg>
              <div id="donut-legend" style="font-size:12px;line-height:1.7;"></div>
            </div>
            <div id="insights-box"></div>
          </div>
        </div>

        <div class="panel" style="margin-top:16px;">
          <div class="panel-head">
            <div>
              <div class="panel-title">Recent __WORKSPACE_LABEL__</div>
              <div class="panel-sub">Click any row to inspect details, history, and status transitions</div>
            </div>
            <button type="button" class="btn" onclick="switchView('workspace')">View All &rarr;</button>
          </div>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Date</th><th>Workflow / Entry</th><th>Owner / Source</th><th>Category</th><th>Status</th><th style="text-align:right;">Metric</th></tr>
              </thead>
              <tbody id="overview-tbody"></tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- VIEW 2: OPERATIONS WORKSPACE -->
      <section id="view-workspace" class="view-pane">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">__WORKSPACE_LABEL__</div>
              <div class="panel-sub">Filter by status, toggle view mode, or create new entries</div>
            </div>
            <div style="display:flex;gap:8px;align-items:center;">
              <div class="seg-group">
                <button type="button" class="seg-btn active" onclick="setLayoutMode('table', this)">Table</button>
                <button type="button" class="seg-btn" onclick="setLayoutMode('cards', this)">Cards</button>
              </div>
              <button type="button" class="btn btn-primary" onclick="openCreateModal()">+ __CTA_LABEL__</button>
            </div>
          </div>
          <div class="toolbar-row">
            <div class="chip-bar" id="filter-chips">
              <button type="button" class="chip active" onclick="setFilter('All', this)">All</button>
              <button type="button" class="chip" onclick="setFilter('High', this)">High Priority</button>
              <button type="button" class="chip" onclick="setFilter('Active', this)">Active</button>
              <button type="button" class="chip" onclick="setFilter('Verified', this)">Verified</button>
            </div>
            <input type="text" class="search-global" id="ws-search" placeholder="Search records..." oninput="handleGlobalSearch(this.value)">
          </div>
          <div class="table-wrap" id="ws-table-wrap">
            <table>
              <thead>
                <tr><th>Date</th><th>Workflow</th><th>Owner</th><th>Priority</th><th>Status</th><th style="text-align:right;">Actions</th></tr>
              </thead>
              <tbody id="ws-tbody"></tbody>
            </table>
          </div>
          <div class="cards-grid" id="ws-cards-wrap" style="display:none;"></div>
        </div>
      </section>

      <!-- VIEW 3: ANALYTICS -->
      <section id="view-analytics" class="view-pane">
        <div class="bento-2">
          <div class="panel" style="margin-bottom:0;">
            <div class="panel-head">
              <div>
                <div class="panel-title">Category Breakdown</div>
                <div class="panel-sub">Active workflows and SLA distribution by module</div>
              </div>
              <button type="button" class="btn" onclick="showToast('Analytics report exported')">Export Summary</button>
            </div>
            <svg id="bar-svg" viewBox="0 0 540 200" style="width:100%;height:auto;display:block;"></svg>
          </div>
          <div class="panel" style="margin-bottom:0;">
            <div class="panel-head">
              <div><div class="panel-title">Service Benchmarks</div></div>
            </div>
            <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;"><span>Automation Coverage</span><strong class="num" style="color:var(--text);">96.4%</strong></div>
            <div class="bar-track"><div class="bar-fill" style="width:96.4%;background:var(--accent);"></div></div>
            <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;"><span>SLA Adherence</span><strong class="num" style="color:var(--text);">98.2%</strong></div>
            <div class="bar-track"><div class="bar-fill" style="width:98.2%;background:var(--accent2);"></div></div>
            <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;"><span>Audit Completeness</span><strong class="num" style="color:var(--text);">99.1%</strong></div>
            <div class="bar-track"><div class="bar-fill" style="width:99.1%;background:var(--success);"></div></div>
          </div>
        </div>
      </section>

      <!-- VIEW 4: SETTINGS & SECURITY -->
      <section id="view-settings" class="view-pane">
        <div class="panel">
          <div class="panel-head">
            <div>
              <div class="panel-title">Preferences &amp; Access Security</div>
              <div class="panel-sub">Appearance, alerts, and identity verification controls</div>
            </div>
            <button type="button" class="btn btn-primary" onclick="showToast('Workspace settings saved')">Save Settings</button>
          </div>
          <div class="toggle-row">
            <div>
              <div style="font-weight:600;font-size:13.5px;">Light Theme Surface</div>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Switch cleanly between crisp Daylight paper and precision Dark surface</div>
            </div>
            <label class="switch"><input type="checkbox" id="light-theme-toggle" __LIGHT_CHECKED__ onchange="setLightTheme(this.checked)"><span class="slider"></span></label>
          </div>
          <div class="toggle-row">
            <div>
              <div style="font-weight:600;font-size:13.5px;">Real-Time Auto-Sync</div>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Keep workspace metrics and ledgers updated in real time</div>
            </div>
            <label class="switch"><input type="checkbox" checked onchange="showToast('Auto-sync preference updated')"><span class="slider"></span></label>
          </div>
          <div class="toggle-row" style="border-bottom:none;">
            <div>
              <div style="font-weight:600;font-size:13.5px;">Two-Factor &amp; OTP Verification</div>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Test identity confirmation without leaving the active workspace</div>
            </div>
            <button type="button" class="btn" onclick="openAuthModal()">Verify Identity</button>
          </div>
        </div>
      </section>
    </div>
  </main>

  <!-- Create Modal -->
  <div class="backdrop" id="create-modal" onclick="if(event.target===this) closeCreateModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
        <strong style="font-size:15.5px;">New Record</strong>
        <button type="button" class="btn" onclick="closeCreateModal()">&times;</button>
      </div>
      <form onsubmit="submitNewRecord(event)">
        <div class="form-group">
          <label class="form-lbl">Title / Workflow Name</label>
          <input type="text" class="form-ctl" id="new-title" placeholder="e.g. Monthly Automated Reconciliation" required>
        </div>
        <div class="form-group">
          <label class="form-lbl">Category</label>
          <input type="text" class="form-ctl" id="new-cat" placeholder="e.g. Core Operations" required>
        </div>
        <div class="form-group">
          <label class="form-lbl">Priority</label>
          <select class="form-ctl" id="new-prio">
            <option value="High">High</option>
            <option value="Medium" selected>Medium</option>
            <option value="Low">Low</option>
          </select>
        </div>
        <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:16px;">
          <button type="button" class="btn" onclick="closeCreateModal()">Cancel</button>
          <button type="submit" class="btn btn-primary">Save Entry</button>
        </div>
      </form>
    </div>
  </div>

  <!-- Interactive OTP Modal -->
  <div class="backdrop" id="auth-modal" onclick="if(event.target===this) closeAuthModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <strong style="font-size:15.5px;">Account Verification</strong>
        <button type="button" class="btn" onclick="closeAuthModal()">&times;</button>
      </div>
      <div class="form-group">
        <label class="form-lbl">Mobile Number or Email</label>
        <input type="text" class="form-ctl" id="otp-contact" value="+91 98250 41290">
      </div>
      <div id="otp-step-2" style="display:none;">
        <div class="form-group">
          <label class="form-lbl">6-Digit OTP Code</label>
          <input type="text" class="form-ctl" id="otp-code" value="482910">
        </div>
      </div>
      <div style="display:flex;justify-content:flex-end;gap:8px;margin-top:14px;">
        <button type="button" class="btn" onclick="sendDemoOtp()">Send OTP</button>
        <button type="button" class="btn btn-primary" onclick="verifyDemoOtp()">Confirm</button>
      </div>
    </div>
  </div>

  <!-- Slide-Over Detail Inspector Drawer -->
  <div class="backdrop" id="detail-backdrop" onclick="if(event.target===this) closeDrawer()">
    <div class="drawer">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:14px;">
        <div>
          <div style="font-size:11px;color:var(--muted);font-family:monospace;" id="dr-id"></div>
          <div style="font-size:15.5px;font-weight:700;margin-top:2px;" id="dr-title"></div>
        </div>
        <button type="button" class="btn" onclick="closeDrawer()">&times;</button>
      </div>
      <div style="font-size:13px;color:var(--muted);line-height:1.6;margin-bottom:16px;" id="dr-notes"></div>
      <div class="form-group">
        <label class="form-lbl">Status Controls</label>
        <div style="display:flex;gap:8px;flex-wrap:wrap;" id="dr-actions"></div>
      </div>
    </div>
  </div>

  <div class="toast-stack" id="toast-stack"></div>

  <script>
    var DATA = __DATA_JSON__;
    var state = {
      range: '30d',
      filter: 'All',
      search: '',
      layout: 'table',
      records: DATA.records.slice(),
      selectedId: null
    };

    var SERIES = {
      '7d':  { p: [42, 58, 51, 69, 64, 84, 92], b: [38, 44, 48, 52, 56, 63, 70] },
      '30d': { p: [34, 48, 44, 62, 71, 79, 89], b: [30, 38, 42, 48, 54, 60, 68] },
      '90d': { p: [24, 39, 52, 60, 74, 83, 95], b: [22, 32, 40, 49, 58, 65, 74] }
    };
    var RANGE_LABELS = {
      '7d':  ['21 Nov', '22 Nov', '23 Nov', '24 Nov', '25 Nov', '26 Nov', '27 Nov'],
      '30d': ['Wk 1', 'Wk 2', 'Wk 3', 'Wk 4', 'Wk 5', 'Wk 6', '27 Nov'],
      '90d': ['Sep', 'Mid-Sep', 'Oct', 'Mid-Oct', 'Nov 1', 'Nov 14', '27 Nov']
    };

    function formatYTick(pct) {
      if (!DATA.yPrefix) return pct + '%';
      var val = Math.round((pct / 100) * DATA.yMax / 1000);
      return val === 0 ? (DATA.yPrefix + '0') : (DATA.yPrefix + val + 'k');
    }

    function initBrand() {
      var words = (DATA.productName || 'WK').trim().split(/\s+/);
      var initials = words.length >= 2 ? (words[0][0] + words[1][0]) : words[0].slice(0, 2);
      document.getElementById('brand-initials').textContent = initials.toUpperCase();
      var nList = document.getElementById('notif-list');
      nList.innerHTML = '';
      DATA.insights.forEach(function(item) {
        var div = document.createElement('div');
        div.className = 'notif-item';
        div.innerHTML = '<strong>' + esc(item[0]) + '</strong><div style="color:var(--muted);margin-top:2px;">' + esc(item[1]) + '</div>';
        nList.appendChild(div);
      });
      var lightChk = document.getElementById('light-theme-toggle');
      if (lightChk) lightChk.checked = !document.body.classList.contains('dark-theme');
    }

    function esc(s) {
      return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function pillClass(st) {
      if (st === 'Verified') return 'pill pill-verified';
      if (st === 'In Review' || st === 'Scheduled') return 'pill pill-progress';
      return 'pill pill-active';
    }

    function renderKPIs() {
      var vals = DATA.kpis[state.range] || DATA.kpis['30d'];
      var grid = document.getElementById('kpi-grid');
      grid.innerHTML = '';
      DATA.kpiLabels.forEach(function(lbl, idx) {
        var card = document.createElement('div');
        card.className = 'kpi-card';
        var val = (idx === 0 && DATA.domain === 'saas') ? String(state.records.length) : vals[idx];
        var sparks = [
          'M2 20 C18 17, 34 22, 52 13 C68 6, 84 11, 98 4',
          'M2 18 C22 14, 42 16, 60 10 C78 5, 88 8, 98 3',
          'M2 22 C20 20, 40 12, 62 15 C80 17, 88 7, 98 5',
          'M2 17 C20 19, 44 10, 66 8 C82 6, 90 4, 98 3'
        ];
        card.innerHTML =
          '<div class="kpi-top"><span>' + esc(lbl) + '</span></div>' +
          '<div class="kpi-val num">' + esc(val) + '</div>' +
          '<div class="kpi-foot"><span class="delta-pill">' + esc(DATA.deltas[idx]) + '</span>' +
          '<svg viewBox="0 0 100 26" width="68" height="20"><path d="' + sparks[idx % 4] + '" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linecap="round"/></svg></div>';
        grid.appendChild(card);
      });
    }

    function renderTrendChart() {
      var ser = SERIES[state.range] || SERIES['30d'];
      var pts = ser.p, base = ser.b;
      var lbls = RANGE_LABELS[state.range] || RANGE_LABELS['30d'];
      var svg = document.getElementById('trend-svg');
      var W = 600, H = 185, padL = 48, padR = 16, padT = 14, padB = 26;
      var innerW = W - padL - padR, innerH = H - padT - padB;
      var coords = pts.map(function(v, i) {
        return {
          x: Math.round(padL + (i / (pts.length - 1)) * innerW),
          y: Math.round(padT + innerH - (v / 100) * innerH),
          by: Math.round(padT + innerH - (base[i] / 100) * innerH),
          v: v,
          bv: base[i],
          l: lbls[i]
        };
      });
      var pathD = coords.map(function(c, i) {
        if (i === 0) return 'M ' + c.x + ' ' + c.y;
        var prev = coords[i - 1], cx = Math.round((prev.x + c.x) / 2);
        return 'C ' + cx + ' ' + prev.y + ', ' + cx + ' ' + c.y + ', ' + c.x + ' ' + c.y;
      }).join(' ');
      var baseD = coords.map(function(c, i) {
        if (i === 0) return 'M ' + c.x + ' ' + c.by;
        var prev = coords[i - 1], cx = Math.round((prev.x + c.x) / 2);
        return 'C ' + cx + ' ' + prev.by + ', ' + cx + ' ' + c.by + ', ' + c.x + ' ' + c.by;
      }).join(' ');
      var areaD = pathD + ' L ' + coords[coords.length - 1].x + ' ' + (H - padB) + ' L ' + coords[0].x + ' ' + (H - padB) + ' Z';
      var gridLines = [0, 25, 50, 75, 100].map(function(g) {
        var gy = Math.round(padT + innerH - (g / 100) * innerH);
        return '<line x1="' + padL + '" y1="' + gy + '" x2="' + (W - padR) + '" y2="' + gy + '" stroke="var(--border)" stroke-dasharray="' + (g === 0 ? '0' : '3 3') + '"/>' +
               '<text x="' + (padL - 8) + '" y="' + (gy + 3.5) + '" text-anchor="end" fill="var(--muted)" font-size="10">' + esc(formatYTick(g)) + '</text>';
      }).join('');
      var xLabels = coords.map(function(c) {
        return '<text x="' + c.x + '" y="' + (H - 6) + '" text-anchor="middle" fill="var(--muted)" font-size="10.5">' + esc(c.l) + '</text>';
      }).join('');
      var circles = coords.map(function(c, idx) {
        return '<circle cx="' + c.x + '" cy="' + c.y + '" r="4" fill="var(--accent)" stroke="var(--surface)" stroke-width="2" style="cursor:pointer;" onmouseenter="showChartTip(' + idx + ')" onmouseleave="hideChartTip()"/>';
      }).join('');
      svg.innerHTML =
        '<defs><linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">' +
        '<stop offset="0%" stop-color="var(--accent)" stop-opacity="0.14"/>' +
        '<stop offset="100%" stop-color="var(--accent)" stop-opacity="0.01"/>' +
        '</linearGradient></defs>' +
        gridLines +
        '<path d="' + areaD + '" fill="url(#areaGrad)"/>' +
        '<path d="' + baseD + '" fill="none" stroke="var(--accent2)" stroke-width="1.6" stroke-dasharray="4 4" opacity="0.7"/>' +
        '<path d="' + pathD + '" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round"/>' +
        circles + xLabels;
      svg._coords = coords;
    }

    function showChartTip(idx) {
      var svg = document.getElementById('trend-svg');
      var tip = document.getElementById('chart-tip');
      var c = (svg._coords || [])[idx];
      if (!c) return;
      tip.textContent = c.l + ' \u2022 ' + formatYTick(c.v) + ' (Target ' + formatYTick(c.bv) + ')';
      tip.style.left = Math.min(410, Math.max(8, (c.x / 600) * svg.clientWidth - 40)) + 'px';
      tip.style.top = Math.max(4, (c.y / 185) * svg.clientHeight - 32) + 'px';
      tip.style.opacity = '1';
    }
    function hideChartTip() { document.getElementById('chart-tip').style.opacity = '0'; }

    function renderDonutAndInsights() {
      var hi = state.records.filter(function(r) { return r.priority === 'High'; }).length;
      var med = state.records.filter(function(r) { return r.priority === 'Medium'; }).length;
      var lo = Math.max(0, state.records.length - hi - med);
      var tot = Math.max(1, state.records.length);
      var r = 40, circ = 2 * Math.PI * r;
      var hiLen = (hi / tot) * circ, medLen = (med / tot) * circ, loLen = (lo / tot) * circ;
      document.getElementById('donut-svg').innerHTML =
        '<circle cx="55" cy="55" r="' + r + '" fill="none" stroke="var(--elevated)" stroke-width="10"/>' +
        '<circle cx="55" cy="55" r="' + r + '" fill="none" stroke="var(--accent)" stroke-width="10" stroke-dasharray="' + hiLen + ' ' + circ + '" transform="rotate(-90 55 55)"/>' +
        '<circle cx="55" cy="55" r="' + r + '" fill="none" stroke="var(--accent2)" stroke-width="10" stroke-dasharray="' + medLen + ' ' + circ + '" stroke-dashoffset="-' + hiLen + '" transform="rotate(-90 55 55)"/>' +
        '<circle cx="55" cy="55" r="' + r + '" fill="none" stroke="var(--warning)" stroke-width="10" stroke-dasharray="' + loLen + ' ' + circ + '" stroke-dashoffset="-' + (hiLen + medLen) + '" transform="rotate(-90 55 55)"/>' +
        '<text x="55" y="59" text-anchor="middle" fill="var(--text)" font-size="14" font-weight="700">' + tot + '</text>';
      document.getElementById('donut-legend').innerHTML =
        '<div><span style="color:var(--accent);">&#9632;</span> High Priority: <strong>' + hi + '</strong></div>' +
        '<div><span style="color:var(--accent2);">&#9632;</span> Standard: <strong>' + med + '</strong></div>' +
        '<div><span style="color:var(--warning);">&#9632;</span> Scheduled: <strong>' + lo + '</strong></div>';

      var box = document.getElementById('insights-box');
      box.innerHTML = '';
      DATA.insights.forEach(function(ins, idx) {
        var el = document.createElement('div');
        el.className = 'insight-item';
        el.innerHTML =
          '<div><div class="insight-h">' + esc(ins[0]) + '</div><div class="insight-p">' + esc(ins[1]) + '</div></div>' +
          '<button type="button" class="btn" onclick="applyInsight(' + idx + ', this)">Apply</button>';
        box.appendChild(el);
      });
    }

    function applyInsight(idx, btn) {
      btn.textContent = 'Applied';
      btn.disabled = true;
      showToast('Applied rule: ' + DATA.insights[idx][0]);
    }

    function renderBarChart() {
      var counts = {};
      state.records.forEach(function(r) { counts[r.category] = (counts[r.category] || 0) + 1; });
      var keys = Object.keys(counts).slice(0, 5);
      var maxV = Math.max.apply(null, keys.map(function(k) { return counts[k]; }).concat([1]));
      var svg = document.getElementById('bar-svg');
      var bars = keys.map(function(k, i) {
        var bw = 62, gap = 36, x = 34 + i * (bw + gap);
        var h = Math.round((counts[k] / maxV) * 125);
        var y = 155 - h;
        var label = k.length > 12 ? k.slice(0, 11) + '..' : k;
        return '<rect x="' + x + '" y="' + y + '" width="' + bw + '" height="' + h + '" rx="6" fill="' + (i % 2 === 0 ? 'var(--accent)' : 'var(--accent2)') + '" opacity="0.88"/>' +
               '<text x="' + (x + bw / 2) + '" y="' + (y - 6) + '" text-anchor="middle" fill="var(--text)" font-size="11.5" font-weight="700">' + counts[k] + '</text>' +
               '<text x="' + (x + bw / 2) + '" y="178" text-anchor="middle" fill="var(--muted)" font-size="10.5">' + esc(label) + '</text>';
      }).join('');
      svg.innerHTML = '<line x1="20" y1="155" x2="520" y2="155" stroke="var(--border)"/>' + bars;
    }

    function filteredRecords() {
      var q = state.search.toLowerCase();
      return state.records.filter(function(r) {
        var matchFilter = state.filter === 'All' || r.priority === state.filter || r.status === state.filter;
        var matchSearch = !q || (r.title + ' ' + r.category + ' ' + r.owner + ' ' + r.id).toLowerCase().indexOf(q) !== -1;
        return matchFilter && matchSearch;
      });
    }

    function renderTables() {
      var list = filteredRecords();
      var ovBody = document.getElementById('overview-tbody');
      ovBody.innerHTML = '';
      list.slice(0, 7).forEach(function(r) {
        var tr = document.createElement('tr');
        tr.onclick = function() { openDrawer(r.id); };
        tr.innerHTML =
          '<td class="num" style="color:var(--muted);white-space:nowrap;">' + esc(r.updated) + '</td>' +
          '<td><strong>' + esc(r.title) + '</strong></td>' +
          '<td>' + esc(r.owner) + '</td>' +
          '<td>' + esc(r.category) + '</td>' +
          '<td><span class="' + pillClass(r.status) + '">' + esc(r.status) + '</span></td>' +
          '<td class="num" style="text-align:right;font-weight:600;">' + esc(r.score) + '</td>';
        ovBody.appendChild(tr);
      });

      var wsBody = document.getElementById('ws-tbody');
      wsBody.innerHTML = '';
      list.forEach(function(r) {
        var tr = document.createElement('tr');
        tr.onclick = function() { openDrawer(r.id); };
        tr.innerHTML =
          '<td class="num" style="color:var(--muted);white-space:nowrap;">' + esc(r.updated) + '</td>' +
          '<td><strong>' + esc(r.title) + '</strong></td>' +
          '<td>' + esc(r.owner) + '</td>' +
          '<td>' + esc(r.priority) + '</td>' +
          '<td><span class="' + pillClass(r.status) + '">' + esc(r.status) + '</span></td>';
        var tdAct = document.createElement('td');
        tdAct.style.textAlign = 'right';
        tdAct.onclick = function(ev) { ev.stopPropagation(); };
        var bCyc = document.createElement('button');
        bCyc.type = 'button';
        bCyc.className = 'btn';
        bCyc.style.cssText = 'padding:4px 9px;font-size:11px;margin-right:4px;';
        bCyc.textContent = 'Update';
        bCyc.onclick = function() { cycleStatus(r.id); };
        var bDel = document.createElement('button');
        bDel.type = 'button';
        bDel.className = 'btn';
        bDel.style.cssText = 'padding:4px 9px;font-size:11px;color:var(--danger);';
        bDel.textContent = 'Remove';
        bDel.onclick = function() { deleteRecord(r.id); };
        tdAct.appendChild(bCyc);
        tdAct.appendChild(bDel);
        tr.appendChild(tdAct);
        wsBody.appendChild(tr);
      });

      var wsCards = document.getElementById('ws-cards-wrap');
      wsCards.innerHTML = '';
      list.forEach(function(r) {
        var c = document.createElement('div');
        c.className = 'rec-card';
        c.onclick = function() { openDrawer(r.id); };
        c.innerHTML =
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">' +
          '<span class="num" style="font-size:11.5px;color:var(--muted);">' + esc(r.updated) + '</span>' +
          '<span class="' + pillClass(r.status) + '">' + esc(r.status) + '</span></div>' +
          '<div style="font-weight:600;font-size:13.5px;margin-bottom:4px;">' + esc(r.title) + '</div>' +
          '<div style="font-size:12px;color:var(--muted);">' + esc(r.owner) + ' &middot; ' + esc(r.category) + '</div>';
        wsCards.appendChild(c);
      });
    }

    function switchView(viewId, navEl) {
      document.querySelectorAll('.view-pane').forEach(function(v) { v.classList.remove('active'); });
      var target = document.getElementById('view-' + viewId);
      if (target) target.classList.add('active');
      document.querySelectorAll('.nav-item').forEach(function(n) {
        n.classList.toggle('active', navEl ? n === navEl : n.getAttribute('data-view') === viewId);
      });
      var titles = { overview: 'Overview', workspace: DATA.workspaceLabel, analytics: 'Analytics', settings: 'Settings & Security' };
      document.getElementById('topbar-title').textContent = titles[viewId] || 'Workspace';
    }

    function setRange(rng, btn) {
      state.range = rng;
      document.querySelectorAll('#range-group .seg-btn').forEach(function(b) { b.classList.remove('active'); });
      if (btn) btn.classList.add('active');
      renderKPIs();
      renderTrendChart();
    }

    function setFilter(f, btn) {
      state.filter = f;
      document.querySelectorAll('#filter-chips .chip').forEach(function(b) { b.classList.remove('active'); });
      if (btn) btn.classList.add('active');
      renderTables();
    }

    function setLayoutMode(mode, btn) {
      state.layout = mode;
      btn.parentElement.querySelectorAll('.seg-btn').forEach(function(b) { b.classList.remove('active'); });
      btn.classList.add('active');
      document.getElementById('ws-table-wrap').style.display = mode === 'table' ? 'block' : 'none';
      document.getElementById('ws-cards-wrap').style.display = mode === 'cards' ? 'grid' : 'none';
    }

    function handleGlobalSearch(q) {
      state.search = q || '';
      var gs = document.getElementById('global-search');
      var ws = document.getElementById('ws-search');
      if (gs && gs.value !== state.search) gs.value = state.search;
      if (ws && ws.value !== state.search) ws.value = state.search;
      renderTables();
    }

    function openCreateModal() { document.getElementById('create-modal').classList.add('open'); document.getElementById('new-title').focus(); }
    function closeCreateModal() { document.getElementById('create-modal').classList.remove('open'); }
    function submitNewRecord(e) {
      e.preventDefault();
      var title = document.getElementById('new-title').value.trim();
      var cat = document.getElementById('new-cat').value.trim();
      var prio = document.getElementById('new-prio').value;
      if (!title || !cat) return;
      var nextId = 'REC-' + (201 + state.records.length);
      state.records.unshift({
        id: nextId, title: title, category: cat, priority: prio,
        status: 'Active', owner: 'Workspace Host', updated: 'Today', score: '98.5%',
        notes: 'Newly created entry (' + title + ').'
      });
      closeCreateModal();
      document.getElementById('new-title').value = '';
      document.getElementById('new-cat').value = '';
      refreshAll();
      showToast('Added ' + title);
    }

    function cycleStatus(id) {
      var order = ['Active', 'Verified', 'In Review'];
      var rec = state.records.find(function(r) { return r.id === id; });
      if (!rec) return;
      rec.status = order[(order.indexOf(rec.status) + 1) % order.length];
      refreshAll();
      if (state.selectedId === id) openDrawer(id);
      showToast(rec.title + ' marked ' + rec.status);
    }

    function deleteRecord(id) {
      state.records = state.records.filter(function(r) { return r.id !== id; });
      if (state.selectedId === id) closeDrawer();
      refreshAll();
      showToast('Entry removed');
    }

    function openDrawer(id) {
      var rec = state.records.find(function(r) { return r.id === id; });
      if (!rec) return;
      state.selectedId = id;
      document.getElementById('dr-id').textContent = rec.updated + ' \u2022 ' + rec.category + ' \u2022 ' + rec.priority;
      document.getElementById('dr-title').textContent = rec.title;
      document.getElementById('dr-notes').textContent = rec.notes;
      var drAct = document.getElementById('dr-actions');
      drAct.innerHTML = '';
      var bAdv = document.createElement('button');
      bAdv.type = 'button';
      bAdv.className = 'btn btn-primary';
      bAdv.textContent = 'Advance Status (' + rec.status + ')';
      bAdv.onclick = function() { cycleStatus(rec.id); };
      var bRem = document.createElement('button');
      bRem.type = 'button';
      bRem.className = 'btn';
      bRem.style.color = 'var(--danger)';
      bRem.textContent = 'Remove';
      bRem.onclick = function() { deleteRecord(rec.id); };
      drAct.appendChild(bAdv);
      drAct.appendChild(bRem);
      document.getElementById('detail-backdrop').classList.add('open');
    }
    function closeDrawer() { document.getElementById('detail-backdrop').classList.remove('open'); state.selectedId = null; }

    function openAuthModal() { document.getElementById('auth-modal').classList.add('open'); }
    function closeAuthModal() { document.getElementById('auth-modal').classList.remove('open'); }
    function sendDemoOtp() {
      document.getElementById('otp-step-2').style.display = 'block';
      showToast('Verification code sent to ' + document.getElementById('otp-contact').value);
    }
    function verifyDemoOtp() {
      document.getElementById('auth-chip-label').textContent = 'Verified Account';
      closeAuthModal();
      showToast('Identity verified');
    }

    function toggleNotifs() { document.getElementById('notif-pop').classList.toggle('open'); }
    function markNotifsRead() {
      document.getElementById('notif-dot').style.display = 'none';
      document.getElementById('notif-pop').classList.remove('open');
      showToast('Notifications cleared');
    }

    function setLightTheme(isLight) {
      document.body.classList.toggle('dark-theme', !Boolean(isLight));
      var chk = document.getElementById('light-theme-toggle');
      if (chk) chk.checked = Boolean(isLight);
      renderTrendChart();
    }
    function toggleTheme() {
      var nextLight = document.body.classList.contains('dark-theme');
      setLightTheme(nextLight);
      showToast(nextLight ? 'Light theme enabled' : 'Dark theme enabled');
    }

    function showToast(msg) {
      var stack = document.getElementById('toast-stack');
      var t = document.createElement('div');
      t.className = 'toast';
      t.textContent = msg;
      stack.appendChild(t);
      setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.remove(); }, 250); }, 2600);
    }

    function refreshAll() {
      renderKPIs();
      renderTrendChart();
      renderDonutAndInsights();
      renderBarChart();
      renderTables();
    }

    initBrand();
    refreshAll();
  </script>
</body>
</html>"""

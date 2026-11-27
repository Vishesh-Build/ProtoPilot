"""
Human-Grade Consumer Website Synthesizer for ProtoPilot.

Renders a complete multi-section interactive website (Sticky Top Navbar,
Split Editorial Hero, Filterable Multi-Column Catalog Grid with SVG artwork,
Quick-View Modal, Wishlist, Slide-Over Cart/Booking Drawer with Promo Code &
Checkout -> Order Tracker, Testimonials, FAQ Accordion, and Footer) whenever
client requirements describe a consumer website, marketplace, booking portal,
or storefront rather than an internal admin dashboard.
"""

from __future__ import annotations

import html as html_lib
import json

from app.agents.design_system import DesignProfile, ThemeTokens


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


def _catalog_items(domain: str, currency: str, features: list[dict[str, str]], owners: tuple[str, ...]) -> list[dict]:
    domain_catalog = {
        "commerce": [
            ("AeroWeave Runner", "Footwear", 3499, 4.9, "Bestseller"),
            ("StudioCanvas Tote", "Accessories", 1899, 4.8, "Organic Cotton"),
            ("Minimalist Chrono Watch", "Watches", 5999, 4.9, "2-Year Warranty"),
            ("Nomad Commuter Pack", "Bags", 2799, 4.7, "Waterproof"),
            ("Thermal Craft Flask", "Lifestyle", 1299, 4.8, "24h Cold"),
            ("Merino Knit Overshirt", "Apparel", 3199, 4.9, "Limited Run"),
        ],
        "hospitality": [
            ("Oceanfront Deluxe Suite", "Stay", 6800, 4.9, "Breakfast Included"),
            ("Ayurvedic Renewal Spa", "Wellness", 2400, 4.8, "90 Min Session"),
            ("Chef Tasting Experience", "Dining", 1950, 4.9, "7-Course Menu"),
            ("Private Sunset Cabana", "Lounge", 4200, 4.7, "Priority Slot"),
            ("Weekend Retreat Pass", "Packages", 9400, 4.9, "All Access"),
            ("Airport Chauffeur Transfer", "Concierge", 1450, 4.8, "Instant Confirm"),
        ],
        "education": [
            ("Full-Stack System Design Cohort", "Engineering", 4999, 4.9, "Live Mentorship"),
            ("Product UI/UX Craft Bootcamp", "Design", 3999, 4.9, "Portfolio Ready"),
            ("Applied AI Engineering Track", "AI & Data", 5999, 4.8, "Capstone Project"),
            ("SQL & Cloud Data Modeling", "Analytics", 2499, 4.7, "Self-Paced"),
            ("Career Mock Interview Pass", "Coaching", 1499, 4.8, "4 Sessions"),
            ("Team Enterprise License", "Teams", 12999, 4.9, "10 Seats"),
        ],
        "healthcare": [
            ("Full Body Preventive Checkup", "Diagnostics", 1999, 4.9, "Home Pickup"),
            ("Dermatology Video Consult", "Specialist", 699, 4.8, "In 15 Mins"),
            ("Dental Wellness & Cleaning", "Clinic", 1299, 4.9, "Same-Day Slot"),
            ("Monthly Pharmacy Care Kit", "Pharmacy", 1499, 4.8, "Auto-Refill"),
            ("Cardiac & Lipid Profile", "Diagnostics", 999, 4.9, "NABL Lab"),
            ("Nutrition & Diabetes Plan", "Coaching", 2499, 4.7, "30-Day Follow-up"),
        ],
        "fintech": [
            ("Personal Wealth & UPI Plus", "Personal", 499, 4.9, "Zero Fee"),
            ("Smart GST & Invoice Suite", "Business", 1499, 4.9, "Auto-Filing"),
            ("Automated Tax Saver Vault", "Tax", 999, 4.8, "FY 2026-27"),
            ("Multi-Bank Treasury Pro", "Treasury", 2999, 4.9, "Real-Time Sync"),
            ("Corporate Expense Cards", "Spend", 1999, 4.7, "Instant Limits"),
            ("Advisory Portfolio Review", "Wealth", 2499, 4.9, "SEBI Registered"),
        ],
    }
    raw_items = list(domain_catalog.get(domain, domain_catalog["commerce"]))
    is_usd = currency == "$"
    items: list[dict] = []
    for idx, (title, cat, inr_price, rating, badge) in enumerate(raw_items, start=1):
        price = round(inr_price / 40) if is_usd else inr_price
        feat_note = features[(idx - 1) % len(features)]["title"] if features else title
        items.append({
            "id": f"ITM-{100 + idx}",
            "title": title,
            "category": cat,
            "price": price,
            "rating": rating,
            "reviews": 84 + idx * 31,
            "badge": badge,
            "provider": owners[(idx - 1) % len(owners)],
            "desc": f"Includes {feat_note}. Instant confirmation, transparent pricing, and real-time tracking.",
        })
    # Also surface any distinct extra captured feature directly as an interactive catalog card (max 8)
    for idx, feat in enumerate(features[:2], start=len(items) + 1):
        if len(items) >= 8:
            break
        price = 79 if is_usd else 2499
        items.append({
            "id": f"ITM-{100 + idx}",
            "title": feat["title"],
            "category": feat.get("category") or "Featured",
            "price": price,
            "rating": 4.9,
            "reviews": 112 + idx * 19,
            "badge": "Featured",
            "provider": owners[(idx - 1) % len(owners)],
            "desc": f"Priority offering tailored for {feat['title']}. Fully interactive quick-view and checkout.",
        })
    return items


def build_website_prototype_html(ds: dict, features: list[dict[str, str]]) -> str:
    profile: DesignProfile = ds["profile"]
    currency = ds["currency_symbol"]
    items = _catalog_items(ds["domain"], currency, features, ds["owners"])
    action_label = "Book Now" if ds["domain"] in ("hospitality", "healthcare") else "Add to Bag"
    hero_badge = f"2026 Collection · {ds['style_name']}"
    hero_h1 = f"{ds['product_name']}: {features[0]['title']}" if features else f"{ds['product_name']} Experience"
    hero_sub = f"{profile.tagline}. Browse curated offerings, compare specs, save favorites, and complete checkout in seconds."

    payload = {
        "domain": ds["domain"],
        "productName": ds["product_name"],
        "currency": currency,
        "locale": ds["locale"],
        "actionLabel": action_label,
        "hasAuth": ds["has_auth"],
        "items": items,
        "initialCart": [{"id": items[0]["id"], "qty": 1}],
        "orders": [
            {"id": "ORD-2026-418", "date": "27 Nov 2026", "summary": items[0]["title"], "total": items[0]["price"], "status": "Confirmed"},
            {"id": "ORD-2026-392", "date": "25 Nov 2026", "summary": items[1]["title"], "total": items[1]["price"], "status": "Delivered"},
        ],
    }

    safe_name = html_lib.escape(ds["product_name"])
    safe_tagline = html_lib.escape(profile.tagline)
    light_vars = _css_vars_block(profile.light_tokens, profile)
    dark_vars = _css_vars_block(profile.dark_tokens, profile)
    light_checked = "checked" if ds["prefer_light"] else ""
    body_cls = "" if ds["prefer_light"] else "dark-theme"
    auth_display = "inline-flex" if ds["has_auth"] else "none"
    data_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    template = _WEBSITE_HTML_TEMPLATE
    for k, v in {
        "__SAFE_TITLE__": safe_name,
        "__SAFE_TAGLINE__": safe_tagline,
        "__HERO_BADGE__": html_lib.escape(hero_badge),
        "__HERO_H1__": html_lib.escape(hero_h1),
        "__HERO_SUB__": html_lib.escape(hero_sub),
        "__ACTION_LABEL__": html_lib.escape(action_label),
        "__CURRENCY__": html_lib.escape(currency),
        "__LIGHT_VARS__": light_vars,
        "__DARK_VARS__": dark_vars,
        "__BODY_CLASS__": body_cls,
        "__LIGHT_CHECKED__": light_checked,
        "__AUTH_DISPLAY__": auth_display,
        "__DATA_JSON__": data_json,
    }.items():
        template = template.replace(k, v)
    return template


_WEBSITE_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__SAFE_TITLE__</title>
<style>
  :root {
    __LIGHT_VARS__
  }
  body.dark-theme {
    __DARK_VARS__
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { min-height: 100%; font-family: var(--font-body); }
  body { background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; transition: background 0.18s ease, color 0.18s ease; overflow-x: hidden; }
  .num { font-variant-numeric: tabular-nums; }
  .container { max-width: 1200px; margin: 0 auto; padding: 0 22px; }

  /* Sticky Website Header */
  header.nav { position: sticky; top: 0; z-index: 60; height: 64px; background: var(--surface); border-bottom: 1px solid var(--border); }
  .nav-inner { height: 100%; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
  .brand { display: flex; align-items: center; gap: 10px; font-family: var(--font-display); font-weight: 700; font-size: 16px; color: var(--text); text-decoration: none; cursor: pointer; }
  .brand-mark { width: 32px; height: 32px; border-radius: var(--radius-control); background: var(--accent); color: var(--accent-contrast); display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 800; }
  .nav-links { display: flex; align-items: center; gap: 6px; }
  .nav-link { padding: 7px 12px; border-radius: var(--radius-control); font-size: 13.5px; font-weight: 500; color: var(--muted); cursor: pointer; border: none; background: transparent; transition: background 0.12s, color 0.12s; }
  .nav-link:hover { color: var(--text); background: var(--hover); }
  .nav-link.active { color: var(--accent); background: var(--accent-soft); font-weight: 600; }
  .nav-actions { display: flex; align-items: center; gap: 8px; }
  .btn { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 7px 13px; font-size: 13px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: border-color 0.12s, background 0.12s; white-space: nowrap; }
  .btn:hover { border-color: var(--border-strong); background: var(--elevated); }
  .btn svg { width: 15px; height: 15px; stroke: currentColor; fill: none; stroke-width: 1.85; stroke-linecap: round; stroke-linejoin: round; }
  .btn-primary { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); font-weight: 600; }
  .btn-primary:hover { opacity: 0.92; background: var(--accent); border-color: var(--accent); }
  .badge-count { background: var(--accent-contrast); color: var(--accent); border-radius: 999px; padding: 1px 6px; font-size: 11px; font-weight: 700; }

  /* Split Editorial Hero */
  .hero { padding: 38px 0 32px; border-bottom: 1px solid var(--border); background: var(--surface); }
  .hero-grid { display: grid; grid-template-columns: 1.25fr 0.95fr; gap: 28px; align-items: center; }
  .hero-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-size: 11.5px; font-weight: 600; margin-bottom: 12px; }
  .hero h1 { font-family: var(--font-display); font-size: clamp(24px, 3.2vw, 38px); font-weight: 800; letter-spacing: -0.025em; line-height: 1.15; color: var(--text); margin-bottom: 12px; }
  .hero p { font-size: 15px; color: var(--muted); line-height: 1.55; margin-bottom: 20px; max-width: 560px; }
  .hero-search { display: flex; gap: 8px; background: var(--bg); border: 1px solid var(--border-strong); padding: 6px; border-radius: var(--radius-card); max-width: 540px; }
  .hero-search input { flex: 1; border: none; outline: none; background: transparent; padding: 8px 10px; font-size: 13.5px; color: var(--text); min-width: 0; }
  .trust-row { display: flex; gap: 22px; flex-wrap: wrap; margin-top: 20px; font-size: 12.5px; color: var(--muted); }
  .trust-row strong { color: var(--text); font-weight: 700; }
  .hero-card { background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 20px; box-shadow: var(--shadow); }

  /* Section & Catalog Grid */
  .section { padding: 30px 0; }
  .section-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
  .section-title { font-family: var(--font-display); font-size: 20px; font-weight: 700; color: var(--text); letter-spacing: -0.02em; }
  .section-sub { font-size: 13px; color: var(--muted); margin-top: 2px; }
  .filter-bar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 18px; }
  .chips { display: flex; gap: 7px; flex-wrap: wrap; }
  .chip { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 6px 13px; border-radius: 999px; font-size: 12.5px; font-weight: 500; cursor: pointer; }
  .chip.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .select-ctl { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 6px 11px; font-size: 12.5px; outline: none; }

  .grid-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); overflow: hidden; display: flex; flex-direction: column; box-shadow: var(--shadow); transition: border-color 0.15s, transform 0.15s; }
  .card:hover { border-color: var(--border-strong); transform: translateY(-2px); }
  .card-art { height: 148px; background: var(--elevated); border-bottom: 1px solid var(--border); position: relative; display: flex; align-items: center; justify-content: center; padding: 16px; }
  .card-badge { position: absolute; top: 10px; left: 10px; background: var(--surface); border: 1px solid var(--border); color: var(--text); font-size: 11px; font-weight: 600; padding: 3px 9px; border-radius: 999px; }
  .wish-btn { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); display: flex; align-items: center; justify-content: center; cursor: pointer; color: var(--muted); }
  .wish-btn.saved { color: var(--danger); border-color: var(--danger); }
  .card-body { padding: 16px; flex: 1; display: flex; flex-direction: column; }
  .card-cat { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent); margin-bottom: 4px; }
  .card-title { font-family: var(--font-display); font-size: 15.5px; font-weight: 700; color: var(--text); margin-bottom: 5px; }
  .card-desc { font-size: 12.5px; color: var(--muted); line-height: 1.45; flex: 1; margin-bottom: 12px; }
  .card-meta { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; font-size: 12.5px; }
  .price { font-family: var(--font-display); font-size: 17px; font-weight: 800; color: var(--text); }
  .rating { color: var(--warning); font-weight: 600; }
  .card-actions { display: flex; gap: 8px; }

  /* Pricing / Reviews / FAQ / Orders / Settings */
  .view-section { display: none; }
  .view-section.active { display: block; }
  .review-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
  .review-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 16px; }
  .faq-item { background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-control); margin-bottom: 8px; overflow: hidden; }
  .faq-q { width: 100%; text-align: left; background: transparent; border: none; padding: 13px 16px; font-size: 13.5px; font-weight: 600; color: var(--text); cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
  .faq-a { display: none; padding: 0 16px 14px; font-size: 13px; color: var(--muted); line-height: 1.5; }
  .faq-item.open .faq-a { display: block; }

  .table-wrap { width: 100%; overflow-x: auto; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-card); }
  table { width: 100%; border-collapse: collapse; text-align: left; font-size: 13px; min-width: 540px; }
  th { padding: 10px 14px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); border-bottom: 1px solid var(--border); background: var(--elevated); }
  td { padding: 12px 14px; border-bottom: 1px solid var(--border); }

  /* Footer */
  footer { border-top: 1px solid var(--border); background: var(--surface); padding: 28px 0; margin-top: 30px; font-size: 12.5px; color: var(--muted); }
  .footer-grid { display: flex; justify-content: space-between; gap: 20px; flex-wrap: wrap; align-items: center; }

  /* Modals & Cart Drawer */
  .backdrop { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(2px); display: none; z-index: 90; }
  .backdrop.open { display: flex; }
  .drawer { margin-left: auto; width: min(410px, 94vw); height: 100%; background: var(--surface); border-left: 1px solid var(--border-strong); padding: 20px; display: flex; flex-direction: column; overflow-y: auto; }
  .modal-box { margin: auto; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--radius-card); width: min(470px, 92vw); padding: 20px; box-shadow: 0 24px 48px rgba(0,0,0,0.2); }
  .cart-item { display: flex; justify-content: space-between; align-items: center; gap: 10px; padding: 12px 0; border-bottom: 1px solid var(--border); }
  .qty-btn { width: 24px; height: 24px; border-radius: 6px; border: 1px solid var(--border); background: var(--elevated); color: var(--text); cursor: pointer; font-weight: 700; }
  .form-ctl { width: 100%; background: var(--elevated); border: 1px solid var(--border); color: var(--text); border-radius: var(--radius-control); padding: 8px 11px; font-size: 13px; outline: none; }
  .toast-stack { position: fixed; bottom: 18px; right: 18px; display: flex; flex-direction: column; gap: 8px; z-index: 130; pointer-events: none; }
  .toast { background: var(--surface); border: 1px solid var(--border-strong); border-left: 3px solid var(--accent); color: var(--text); padding: 9px 14px; border-radius: var(--radius-control); font-size: 12.5px; font-weight: 500; box-shadow: var(--shadow); }

  .switch { position: relative; display: inline-block; width: 42px; height: 22px; }
  .switch input { opacity: 0; width: 0; height: 0; }
  .slider { position: absolute; inset: 0; background: var(--border-strong); border-radius: 999px; cursor: pointer; transition: 0.2s; }
  .slider:before { content: ""; position: absolute; height: 16px; width: 16px; left: 3px; bottom: 3px; background: #fff; border-radius: 50%; transition: 0.2s; }
  input:checked + .slider { background: var(--accent); }
  input:checked + .slider:before { transform: translateX(20px); }

  @media (max-width: 900px) {
    .hero-grid, .grid-cards, .review-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .hero-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 660px) {
    .nav-links { display: none; }
    .grid-cards, .review-grid { grid-template-columns: 1fr; }
    header.nav { padding: 0 4px; }
  }
</style>
</head>
<body class="__BODY_CLASS__">
  <header class="nav">
    <div class="container nav-inner">
      <div class="brand" onclick="showPage('home')">
        <div class="brand-mark" id="brand-mark">PP</div>
        <span>__SAFE_TITLE__</span>
      </div>
      <nav class="nav-links">
        <button type="button" class="nav-link active" data-page="home" onclick="showPage('home')">Explore</button>
        <button type="button" class="nav-link" data-page="orders" onclick="showPage('orders')">My Orders</button>
        <button type="button" class="nav-link" data-page="account" onclick="showPage('account')">Preferences</button>
      </nav>
      <div class="nav-actions">
        <button type="button" class="btn" id="wish-nav-btn" onclick="toggleWishlistFilter()">
          <svg viewBox="0 0 24 24"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>
          <span class="num" id="wish-count">0</span>
        </button>
        <button type="button" class="btn" style="display:__AUTH_DISPLAY__;" onclick="openAuthModal()">Sign In / OTP</button>
        <button type="button" class="btn" onclick="toggleTheme()" title="Switch Light/Dark">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/></svg>
        </button>
        <button type="button" class="btn btn-primary" onclick="openCart()">
          <svg viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          Bag <span class="badge-count num" id="cart-count">1</span>
        </button>
      </div>
    </div>
  </header>

  <main id="page-home" class="view-section active">
    <section class="hero">
      <div class="container hero-grid">
        <div>
          <div class="hero-pill">__HERO_BADGE__</div>
          <h1>__HERO_H1__</h1>
          <p>__HERO_SUB__</p>
          <div class="hero-search">
            <input type="text" id="hero-search" placeholder="Search items, categories, packages..." oninput="applySearch(this.value)">
            <button type="button" class="btn btn-primary" onclick="scrollToCatalog()">Browse All</button>
          </div>
          <div class="trust-row">
            <span><strong>4.9 / 5</strong> Customer Rating</span>
            <span><strong>14,200+</strong> Completed Orders</span>
            <span><strong>WELCOME10</strong> 10% Promo Ready</span>
          </div>
        </div>
        <div class="hero-card">
          <svg viewBox="0 0 360 210" style="width:100%;height:auto;display:block;">
            <rect x="8" y="8" width="344" height="194" rx="12" fill="var(--elevated)" stroke="var(--border)"/>
            <rect x="24" y="26" width="140" height="18" rx="6" fill="var(--accent-soft)"/>
            <text x="34" y="39" fill="var(--accent)" font-size="10.5" font-weight="700">2026 FEATURED SHOWCASE</text>
            <rect x="24" y="58" width="190" height="10" rx="5" fill="var(--text)" opacity="0.18"/>
            <rect x="24" y="76" width="145" height="8" rx="4" fill="var(--muted)" opacity="0.25"/>
            <rect x="234" y="28" width="102" height="102" rx="14" fill="var(--surface)" stroke="var(--border-strong)"/>
            <circle cx="285" cy="72" r="24" fill="var(--accent)" opacity="0.16"/>
            <path d="M273 73 l9 9 l16 -18" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
            <rect x="24" y="106" width="88" height="32" rx="8" fill="var(--accent)"/>
            <text x="68" y="126" text-anchor="middle" fill="var(--accent-contrast)" font-size="11" font-weight="700">Explore</text>
            <line x1="24" y1="158" x2="336" y2="158" stroke="var(--border)"/>
            <text x="24" y="180" fill="var(--muted)" font-size="11">Verified Quality &bull; Live Inventory &bull; Express Checkout</text>
          </svg>
        </div>
      </div>
    </section>

    <section class="section" id="catalog-section">
      <div class="container">
        <div class="section-head">
          <div>
            <div class="section-title">Featured Catalog &amp; Packages</div>
            <div class="section-sub">Filter by category, inspect full details, save to wishlist, or add directly to your bag</div>
          </div>
          <select class="select-ctl" id="sort-select" onchange="renderCatalog()">
            <option value="featured">Sort: Featured</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="rating">Top Rated</option>
          </select>
        </div>

        <div class="filter-bar">
          <div class="chips" id="cat-chips"></div>
          <button type="button" class="btn" onclick="openCart()">View Bag (<span id="bag-inline-count">1</span>)</button>
        </div>

        <div class="grid-cards" id="catalog-grid"></div>
      </div>
    </section>

    <section class="section" style="padding-top:10px;">
      <div class="container">
        <div class="section-head">
          <div>
            <div class="section-title">Verified Customer Reviews</div>
            <div class="section-sub">Real feedback from customers in 2026</div>
          </div>
        </div>
        <div class="review-grid">
          <div class="review-card">
            <div style="color:var(--warning);font-weight:700;margin-bottom:6px;">★★★★★ 5.0</div>
            <div style="font-size:13px;line-height:1.5;margin-bottom:8px;">"Clean checkout flow and transparent delivery updates — zero friction from browsing to confirmation."</div>
            <div style="font-size:12px;color:var(--muted);">Ananya Deshmukh &middot; Nov 2026</div>
          </div>
          <div class="review-card">
            <div style="color:var(--warning);font-weight:700;margin-bottom:6px;">★★★★★ 4.9</div>
            <div style="font-size:13px;line-height:1.5;margin-bottom:8px;">"Easy category filtering, quick-view specs, and instant promo calculation in the bag."</div>
            <div style="font-size:12px;color:var(--muted);">Karthik Nair &middot; Nov 2026</div>
          </div>
          <div class="review-card">
            <div style="color:var(--warning);font-weight:700;margin-bottom:6px;">★★★★★ 4.9</div>
            <div style="font-size:13px;line-height:1.5;margin-bottom:8px;">"Feels fast and straightforward on both desktop and mobile without cluttered popups."</div>
            <div style="font-size:12px;color:var(--muted);">Meera Joshi &middot; Nov 2026</div>
          </div>
        </div>
      </div>
    </section>

    <section class="section" style="padding-top:6px;">
      <div class="container">
        <div class="section-head">
          <div><div class="section-title">Frequently Asked Questions</div></div>
        </div>
        <div class="faq-item open">
          <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">How fast is fulfillment &amp; confirmation?<span>+</span></button>
          <div class="faq-a">Every order or booking receives an instant reference ID under My Orders, with real-time confirmation.</div>
        </div>
        <div class="faq-item">
          <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">Can I apply a promo code at checkout?<span>+</span></button>
          <div class="faq-a">Yes — open your Bag drawer and enter <strong>WELCOME10</strong> for an immediate 10% discount.</div>
        </div>
        <div class="faq-item">
          <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">Do you support mobile &amp; dark theme?<span>+</span></button>
          <div class="faq-a">Yes, switch themes anytime in the header or Preferences tab across desktop, tablet, and mobile screens.</div>
        </div>
      </div>
    </section>
  </main>

  <section id="page-orders" class="view-section section">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-title">My Orders &amp; Bookings</div>
          <div class="section-sub">Completed checkouts appear here immediately</div>
        </div>
        <button type="button" class="btn btn-primary" onclick="showPage('home')">Continue Browsing</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Order ID</th><th>Date</th><th>Items</th><th>Status</th><th style="text-align:right;">Total</th></tr></thead>
          <tbody id="orders-tbody"></tbody>
        </table>
      </div>
    </div>
  </section>

  <section id="page-account" class="view-section section">
    <div class="container">
      <div class="section-head">
        <div>
          <div class="section-title">Display &amp; Account Preferences</div>
          <div class="section-sub">Manage appearance and verification</div>
        </div>
      </div>
      <div class="review-card" style="max-width:620px;">
        <div style="display:flex;justify-content:space-between;align-items:center;padding-bottom:14px;border-bottom:1px solid var(--border);margin-bottom:14px;">
          <div>
            <div style="font-weight:600;">Light Theme Surface</div>
            <div style="font-size:12px;color:var(--muted);">Toggle between Daylight Editorial and Dark Mode</div>
          </div>
          <label class="switch"><input type="checkbox" id="light-theme-toggle" __LIGHT_CHECKED__ onchange="setLightTheme(this.checked)"><span class="slider"></span></label>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <div>
            <div style="font-weight:600;">Account &amp; Mobile OTP</div>
            <div style="font-size:12px;color:var(--muted);">Verify your phone number for faster express checkout</div>
          </div>
          <button type="button" class="btn" onclick="openAuthModal()">Verify OTP</button>
        </div>
      </div>
    </div>
  </section>

  <footer>
    <div class="container footer-grid">
      <div><strong>__SAFE_TITLE__</strong> &mdash; __SAFE_TAGLINE__</div>
      <div>&copy; 2026 __SAFE_TITLE__ &middot; Built for Seamless Customer Experience</div>
    </div>
  </footer>

  <!-- Quick View Modal -->
  <div class="backdrop" id="qv-modal" onclick="if(event.target===this) closeQv()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <span class="card-cat" id="qv-cat"></span>
        <button type="button" class="btn" onclick="closeQv()">&times;</button>
      </div>
      <h3 id="qv-title" style="font-family:var(--font-display);font-size:19px;margin-bottom:6px;"></h3>
      <div style="font-size:12.5px;color:var(--muted);margin-bottom:12px;" id="qv-meta"></div>
      <p style="font-size:13.5px;line-height:1.55;margin-bottom:16px;" id="qv-desc"></p>
      <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid var(--border);">
        <div class="price num" id="qv-price"></div>
        <button type="button" class="btn btn-primary" id="qv-add-btn">__ACTION_LABEL__</button>
      </div>
    </div>
  </div>

  <!-- Slide-Over Cart / Booking Drawer -->
  <div class="backdrop" id="cart-backdrop" onclick="if(event.target===this) closeCart()">
    <div class="drawer">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:10px;">
        <strong style="font-family:var(--font-display);font-size:16px;">Your Bag</strong>
        <button type="button" class="btn" onclick="closeCart()">&times;</button>
      </div>
      <div id="cart-items" style="flex:1;overflow-y:auto;"></div>
      <div style="border-top:1px solid var(--border);padding-top:14px;margin-top:10px;">
        <div style="display:flex;gap:6px;margin-bottom:12px;">
          <input type="text" class="form-ctl" id="promo-input" placeholder="Promo code (try WELCOME10)">
          <button type="button" class="btn" onclick="applyPromo()">Apply</button>
        </div>
        <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:4px;"><span>Subtotal</span><span class="num" id="cart-sub">0</span></div>
        <div style="font-size:12.5px;color:var(--success);display:flex;justify-content:space-between;margin-bottom:4px;" id="promo-row"><span>Promo (WELCOME10)</span><span class="num" id="cart-disc">0</span></div>
        <div style="font-size:15px;font-weight:700;display:flex;justify-content:space-between;margin:8px 0 14px;"><span>Total</span><span class="num" id="cart-total">0</span></div>
        <button type="button" class="btn btn-primary" style="width:100%;justify-content:center;padding:10px;" onclick="completeCheckout()">Place Order Now</button>
      </div>
    </div>
  </div>

  <!-- Auth / OTP Modal -->
  <div class="backdrop" id="auth-modal" onclick="if(event.target===this) closeAuthModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <strong>Sign In / Verify OTP</strong>
        <button type="button" class="btn" onclick="closeAuthModal()">&times;</button>
      </div>
      <input type="text" class="form-ctl" id="otp-phone" value="+91 98250 41290" style="margin-bottom:10px;">
      <input type="text" class="form-ctl" id="otp-val" value="482910" placeholder="Enter 6-digit OTP" style="margin-bottom:14px;">
      <div style="display:flex;justify-content:flex-end;gap:8px;">
        <button type="button" class="btn" onclick="showToast('OTP 482910 sent')">Send OTP</button>
        <button type="button" class="btn btn-primary" onclick="closeAuthModal();showToast('Account verified!')">Verify &amp; Continue</button>
      </div>
    </div>
  </div>

  <div class="toast-stack" id="toast-stack"></div>

  <script>
    var DATA = __DATA_JSON__;
    var state = {
      category: 'All',
      search: '',
      wishlistOnly: false,
      wishlist: {},
      cart: DATA.initialCart.slice(),
      promoApplied: false,
      orders: DATA.orders.slice()
    };

    function fmtMoney(n) {
      if (DATA.locale === 'IN') {
        return DATA.currency + Number(n || 0).toLocaleString('en-IN');
      }
      return DATA.currency + Number(n || 0).toLocaleString('en-US');
    }

    function esc(s) {
      return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function initWebsite() {
      var words = (DATA.productName || 'PP').trim().split(/\s+/);
      var init = words.length >= 2 ? (words[0][0] + words[1][0]) : words[0].slice(0, 2);
      document.getElementById('brand-mark').textContent = init.toUpperCase();

      var cats = ['All'];
      DATA.items.forEach(function(it) { if (cats.indexOf(it.category) === -1) cats.push(it.category); });
      var chipsEl = document.getElementById('cat-chips');
      chipsEl.innerHTML = cats.map(function(c, i) {
        return '<button type="button" class="chip' + (i === 0 ? ' active' : '') + '" onclick="setCategory(\'' + esc(c) + '\', this)">' + esc(c) + '</button>';
      }).join('');
      var lightChk = document.getElementById('light-theme-toggle');
      if (lightChk) lightChk.checked = !document.body.classList.contains('dark-theme');
      renderCatalog();
      renderCart();
      renderOrders();
    }

    function cardArtwork(idx) {
      var patterns = [
        '<svg viewBox="0 0 120 72" width="120" height="72"><rect x="14" y="10" width="92" height="52" rx="10" fill="var(--surface)" stroke="var(--border-strong)"/><circle cx="42" cy="36" r="14" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/><path d="M64 28h30M64 38h22" stroke="var(--muted)" stroke-width="2.5" stroke-linecap="round"/></svg>',
        '<svg viewBox="0 0 120 72" width="120" height="72"><rect x="18" y="12" width="84" height="48" rx="10" fill="var(--surface)" stroke="var(--border-strong)"/><path d="M32 46 L48 30 L62 40 L84 22" fill="none" stroke="var(--accent)" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>',
        '<svg viewBox="0 0 120 72" width="120" height="72"><circle cx="60" cy="36" r="24" fill="var(--surface)" stroke="var(--border-strong)"/><rect x="48" y="24" width="24" height="24" rx="6" fill="var(--accent-soft)" stroke="var(--accent)" stroke-width="2"/></svg>'
      ];
      return patterns[idx % patterns.length];
    }

    function renderCatalog() {
      var q = state.search.toLowerCase();
      var sortBy = document.getElementById('sort-select').value;
      var list = DATA.items.filter(function(it) {
        var mc = state.category === 'All' || it.category === state.category;
        var mq = !q || (it.title + ' ' + it.category + ' ' + it.desc).toLowerCase().indexOf(q) !== -1;
        var mw = !state.wishlistOnly || state.wishlist[it.id];
        return mc && mq && mw;
      });
      if (sortBy === 'price-asc') list.sort(function(a, b) { return a.price - b.price; });
      if (sortBy === 'rating') list.sort(function(a, b) { return b.rating - a.rating; });

      var grid = document.getElementById('catalog-grid');
      grid.innerHTML = list.map(function(it, idx) {
        var savedCls = state.wishlist[it.id] ? ' saved' : '';
        return '<article class="card">' +
          '<div class="card-art">' + cardArtwork(idx) +
            '<span class="card-badge">' + esc(it.badge) + '</span>' +
            '<button type="button" class="wish-btn' + savedCls + '" onclick="toggleWish(\'' + it.id + '\')" title="Save to Wishlist">&#9829;</button>' +
          '</div>' +
          '<div class="card-body">' +
            '<div class="card-cat">' + esc(it.category) + ' &middot; ' + esc(it.provider) + '</div>' +
            '<div class="card-title">' + esc(it.title) + '</div>' +
            '<div class="card-desc">' + esc(it.desc) + '</div>' +
            '<div class="card-meta"><span class="price num">' + esc(fmtMoney(it.price)) + '</span><span class="rating">&#9733; ' + it.rating + ' (' + it.reviews + ')</span></div>' +
            '<div class="card-actions">' +
              '<button type="button" class="btn" style="flex:1;justify-content:center;" onclick="openQv(\'' + it.id + '\')">Quick View</button>' +
              '<button type="button" class="btn btn-primary" style="flex:1;justify-content:center;" onclick="addToCart(\'' + it.id + '\')">' + esc(DATA.actionLabel) + '</button>' +
            '</div>' +
          '</div></article>';
      }).join('');
    }

    function setCategory(cat, btn) {
      state.category = cat;
      document.querySelectorAll('#cat-chips .chip').forEach(function(b) { b.classList.remove('active'); });
      if (btn) btn.classList.add('active');
      renderCatalog();
    }

    function applySearch(q) { state.search = q || ''; renderCatalog(); }
    function scrollToCatalog() { document.getElementById('catalog-section').scrollIntoView({ behavior: 'smooth' }); }

    function toggleWish(id) {
      if (state.wishlist[id]) delete state.wishlist[id];
      else state.wishlist[id] = true;
      document.getElementById('wish-count').textContent = String(Object.keys(state.wishlist).length);
      renderCatalog();
      showToast(state.wishlist[id] ? 'Saved to wishlist' : 'Removed from wishlist');
    }

    function toggleWishlistFilter() {
      state.wishlistOnly = !state.wishlistOnly;
      renderCatalog();
      showToast(state.wishlistOnly ? 'Showing saved items' : 'Showing full catalog');
    }

    function addToCart(id) {
      var found = state.cart.find(function(c) { return c.id === id; });
      if (found) found.qty += 1;
      else state.cart.push({ id: id, qty: 1 });
      renderCart();
      openCart();
      showToast('Added to bag');
    }

    function changeQty(id, delta) {
      var found = state.cart.find(function(c) { return c.id === id; });
      if (!found) return;
      found.qty += delta;
      if (found.qty <= 0) state.cart = state.cart.filter(function(c) { return c.id !== id; });
      renderCart();
    }

    function applyPromo() {
      var code = (document.getElementById('promo-input').value || '').trim().toUpperCase();
      if (code === 'WELCOME10') {
        state.promoApplied = true;
        renderCart();
        showToast('Promo WELCOME10 applied (-10%)');
      } else {
        showToast('Try promo code WELCOME10');
      }
    }

    function renderCart() {
      var count = state.cart.reduce(function(acc, c) { return acc + c.qty; }, 0);
      document.getElementById('cart-count').textContent = String(count);
      document.getElementById('bag-inline-count').textContent = String(count);
      var box = document.getElementById('cart-items');
      var sub = 0;
      if (!state.cart.length) {
        box.innerHTML = '<div style="padding:30px 0;text-align:center;color:var(--muted);">Your bag is empty — add items from the catalog.</div>';
      } else {
        box.innerHTML = state.cart.map(function(c) {
          var item = DATA.items.find(function(i) { return i.id === c.id; });
          if (!item) return '';
          sub += item.price * c.qty;
          return '<div class="cart-item"><div><div style="font-weight:600;font-size:13.5px;">' + esc(item.title) + '</div>' +
            '<div class="num" style="font-size:12px;color:var(--muted);">' + esc(fmtMoney(item.price)) + '</div></div>' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
              '<button type="button" class="qty-btn" onclick="changeQty(\'' + c.id + '\',-1)">-</button>' +
              '<span class="num" style="min-width:16px;text-align:center;">' + c.qty + '</span>' +
              '<button type="button" class="qty-btn" onclick="changeQty(\'' + c.id + '\',1)">+</button>' +
            '</div></div>';
        }).join('');
      }
      var disc = state.promoApplied ? Math.round(sub * 0.1) : 0;
      var total = Math.max(0, sub - disc);
      document.getElementById('promo-row').style.display = state.promoApplied ? 'flex' : 'none';
      document.getElementById('cart-sub').textContent = fmtMoney(sub);
      document.getElementById('cart-disc').textContent = '-' + fmtMoney(disc);
      document.getElementById('cart-total').textContent = fmtMoney(total);
    }

    function completeCheckout() {
      if (!state.cart.length) { showToast('Add an item before checkout'); return; }
      var summary = state.cart.map(function(c) {
        var it = DATA.items.find(function(i) { return i.id === c.id; });
        return it ? (it.title + ' x' + c.qty) : '';
      }).filter(Boolean).join(', ');
      var sub = state.cart.reduce(function(acc, c) {
        var it = DATA.items.find(function(i) { return i.id === c.id; });
        return acc + (it ? it.price * c.qty : 0);
      }, 0);
      var total = state.promoApplied ? Math.round(sub * 0.9) : sub;
      var newId = 'ORD-2026-' + (420 + state.orders.length);
      state.orders.unshift({ id: newId, date: '27 Nov 2026', summary: summary, total: total, status: 'Confirmed' });
      state.cart = [];
      state.promoApplied = false;
      renderCart();
      renderOrders();
      closeCart();
      showPage('orders');
      showToast('Order ' + newId + ' confirmed!');
    }

    function renderOrders() {
      document.getElementById('orders-tbody').innerHTML = state.orders.map(function(o) {
        return '<tr><td class="num" style="font-weight:700;">' + esc(o.id) + '</td><td class="num">' + esc(o.date) + '</td><td>' + esc(o.summary) + '</td><td><span style="color:var(--success);font-weight:600;">' + esc(o.status) + '</span></td><td class="num" style="text-align:right;font-weight:700;">' + esc(fmtMoney(o.total)) + '</td></tr>';
      }).join('');
    }

    function showPage(id) {
      document.querySelectorAll('.view-section').forEach(function(s) { s.classList.remove('active'); });
      var el = document.getElementById('page-' + id);
      if (el) el.classList.add('active');
      document.querySelectorAll('.nav-link').forEach(function(n) { n.classList.toggle('active', n.getAttribute('data-page') === id); });
    }

    function openQv(id) {
      var it = DATA.items.find(function(i) { return i.id === id; });
      if (!it) return;
      document.getElementById('qv-cat').textContent = it.category + ' · ' + it.badge;
      document.getElementById('qv-title').textContent = it.title;
      document.getElementById('qv-meta').textContent = it.provider + ' · ★ ' + it.rating + ' (' + it.reviews + ' reviews)';
      document.getElementById('qv-desc').textContent = it.desc;
      document.getElementById('qv-price').textContent = fmtMoney(it.price);
      document.getElementById('qv-add-btn').onclick = function() { closeQv(); addToCart(it.id); };
      document.getElementById('qv-modal').classList.add('open');
    }
    function closeQv() { document.getElementById('qv-modal').classList.remove('open'); }
    function openCart() { document.getElementById('cart-backdrop').classList.add('open'); }
    function closeCart() { document.getElementById('cart-backdrop').classList.remove('open'); }
    function openAuthModal() { document.getElementById('auth-modal').classList.add('open'); }
    function closeAuthModal() { document.getElementById('auth-modal').classList.remove('open'); }

    function setLightTheme(isLight) {
      document.body.classList.toggle('dark-theme', !Boolean(isLight));
      var chk = document.getElementById('light-theme-toggle');
      if (chk) chk.checked = Boolean(isLight);
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
      setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.remove(); }, 250); }, 2500);
    }

    initWebsite();
  </script>
</body>
</html>"""

export const SAMPLE_RESTAURANT_HTML = String.raw`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Saffron &amp; Stone — Modern Coastal Kitchen &amp; Reserve</title>
<style>
  :root {
    --bg: #FAF8F4;
    --surface: #FFFFFF;
    --elevated: #F3EFE7;
    --hover: rgba(28, 25, 23, 0.04);
    --border: #E7E0D4;
    --border-strong: #D3C8B6;
    --text: #1C1917;
    --muted: #57534E;
    --accent: #B45309;
    --accent2: #0F766E;
    --accent-contrast: #FFFFFF;
    --accent-soft: rgba(180, 83, 9, 0.09);
    --emerald-soft: rgba(15, 118, 110, 0.10);
    --success: #047857;
    --warning: #D97706;
    --danger: #DC2626;
    --shadow: 0 2px 10px rgba(28, 25, 23, 0.06);
    --font-display: "Georgia", "Palatino Linotype", "Book Antiqua", serif;
    --font-body: "Inter", "Segoe UI Variable Text", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --r-card: 12px;
    --r-ctl: 8px;
  }
  body.dark-theme {
    --bg: #110F0E;
    --surface: #1A1715;
    --elevated: #24201C;
    --hover: rgba(250, 248, 244, 0.05);
    --border: rgba(250, 248, 244, 0.10);
    --border-strong: rgba(250, 248, 244, 0.20);
    --text: #FAF8F4;
    --muted: #A8A29E;
    --accent: #F59E0B;
    --accent2: #2DD4BF;
    --accent-contrast: #1A1205;
    --accent-soft: rgba(245, 158, 11, 0.14);
    --emerald-soft: rgba(45, 212, 191, 0.14);
    --success: #34D399;
    --warning: #FBBF24;
    --danger: #F87171;
    --shadow: 0 10px 28px rgba(0, 0, 0, 0.42);
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { min-height: 100%; font-family: var(--font-body); }
  body { background: var(--bg); color: var(--text); -webkit-font-smoothing: antialiased; transition: background 0.2s, color 0.2s; overflow-x: hidden; line-height: 1.5; }
  .num { font-variant-numeric: tabular-nums; }
  .serif { font-family: var(--font-display); }
  .container { max-width: 1180px; margin: 0 auto; padding: 0 22px; }

  /* Sticky Top Navigation */
  header.site-nav { position: sticky; top: 0; z-index: 70; height: 66px; background: var(--surface); border-bottom: 1px solid var(--border); }
  .nav-wrap { height: 100%; display: flex; align-items: center; justify-content: space-between; gap: 14px; }
  .brand { display: flex; align-items: center; gap: 10px; cursor: pointer; }
  .brand-emblem { width: 34px; height: 34px; border-radius: var(--r-ctl); background: var(--accent); color: var(--accent-contrast); display: flex; align-items: center; justify-content: center; font-family: var(--font-display); font-weight: 700; font-size: 16px; }
  .brand-title { font-family: var(--font-display); font-size: 17px; font-weight: 700; letter-spacing: -0.01em; color: var(--text); }
  .brand-sub { font-size: 10.5px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.08em; }
  .nav-links { display: flex; align-items: center; gap: 4px; }
  .nav-btn { border: none; background: transparent; color: var(--muted); font-size: 13.5px; font-weight: 500; padding: 7px 12px; border-radius: var(--r-ctl); cursor: pointer; transition: all 0.14s; white-space: nowrap; }
  .nav-btn:hover { color: var(--text); background: var(--hover); }
  .nav-btn.active { color: var(--accent); background: var(--accent-soft); font-weight: 600; }
  .nav-right { display: flex; align-items: center; gap: 8px; }

  /* Controls */
  .btn { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--r-ctl); padding: 7px 13px; font-size: 13px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; transition: border-color 0.14s, background 0.14s; white-space: nowrap; }
  .btn:hover { border-color: var(--border-strong); background: var(--elevated); }
  .btn svg { width: 15px; height: 15px; stroke: currentColor; fill: none; stroke-width: 1.85; stroke-linecap: round; stroke-linejoin: round; }
  .btn-primary { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); font-weight: 600; }
  .btn-primary:hover { opacity: 0.92; background: var(--accent); border-color: var(--accent); }
  .btn-emerald { background: var(--accent2); color: #fff; border-color: var(--accent2); font-weight: 600; }
  .pill-badge { background: var(--accent-contrast); color: var(--accent); border-radius: 999px; padding: 1px 7px; font-size: 11px; font-weight: 700; }

  /* Hero */
  .hero { background: var(--surface); border-bottom: 1px solid var(--border); padding: 40px 0 36px; }
  .hero-grid { display: grid; grid-template-columns: 1.2fr 0.9fr; gap: 30px; align-items: center; }
  .kicker { display: inline-flex; align-items: center; gap: 7px; padding: 4px 12px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); font-size: 11.5px; font-weight: 600; margin-bottom: 14px; }
  .hero h1 { font-family: var(--font-display); font-size: clamp(28px, 3.6vw, 44px); line-height: 1.13; font-weight: 700; color: var(--text); margin-bottom: 14px; letter-spacing: -0.02em; }
  .hero-lead { font-size: 15px; color: var(--muted); line-height: 1.6; max-width: 550px; margin-bottom: 22px; }
  .hero-ctas { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 24px; }
  .stats-strip { display: flex; gap: 26px; flex-wrap: wrap; padding-top: 18px; border-top: 1px solid var(--border); font-size: 12.5px; color: var(--muted); }
  .stats-strip strong { display: block; font-size: 16px; color: var(--text); font-weight: 700; }

  .tasting-card { background: var(--bg); border: 1px solid var(--border); border-radius: var(--r-card); padding: 20px; box-shadow: var(--shadow); }
  .tasting-head { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 14px; }
  .course-row { display: flex; justify-content: space-between; align-items: center; padding: 9px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }
  .course-row:last-child { border-bottom: none; }

  /* Page Sections */
  .page { display: none; padding: 28px 0 42px; }
  .page.active { display: block; }
  .sec-head { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; flex-wrap: wrap; margin-bottom: 18px; }
  .sec-title { font-family: var(--font-display); font-size: 24px; font-weight: 700; letter-spacing: -0.015em; }
  .sec-sub { font-size: 13.5px; color: var(--muted); margin-top: 3px; }

  /* Quick Action Cards on Home */
  .feature-3 { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 30px; }
  .feat-box { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-card); padding: 18px; cursor: pointer; transition: border-color 0.14s, transform 0.14s; box-shadow: var(--shadow); }
  .feat-box:hover { border-color: var(--accent); transform: translateY(-2px); }
  .feat-title { font-family: var(--font-display); font-size: 16px; font-weight: 700; margin: 10px 0 4px; }
  .feat-desc { font-size: 12.5px; color: var(--muted); line-height: 1.5; }

  /* Filter Toolbar & Dish Cards */
  .toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 16px; }
  .chips { display: flex; gap: 7px; flex-wrap: wrap; }
  .chip { background: var(--surface); border: 1px solid var(--border); color: var(--muted); padding: 6px 13px; border-radius: 999px; font-size: 12.5px; font-weight: 500; cursor: pointer; }
  .chip.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .diet-chip.active { background: var(--emerald-soft); color: var(--accent2); border-color: var(--accent2); font-weight: 600; }
  .search-input { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: var(--r-ctl); padding: 7px 12px; font-size: 13px; width: 220px; outline: none; }
  .search-input:focus { border-color: var(--accent); }

  .dish-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; }
  .dish-card { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-card); overflow: hidden; display: flex; flex-direction: column; box-shadow: var(--shadow); transition: border-color 0.15s, transform 0.15s; }
  .dish-card:hover { border-color: var(--border-strong); transform: translateY(-2px); }
  .dish-art { height: 144px; background: var(--elevated); border-bottom: 1px solid var(--border); position: relative; display: flex; align-items: center; justify-content: center; padding: 12px; }
  .veg-dot { position: absolute; top: 10px; left: 10px; width: 18px; height: 18px; border-radius: 4px; background: var(--surface); border: 1.5px solid #047857; display: flex; align-items: center; justify-content: center; }
  .veg-dot span { width: 8px; height: 8px; border-radius: 50%; background: #047857; }
  .nonveg-dot { position: absolute; top: 10px; left: 10px; width: 18px; height: 18px; border-radius: 4px; background: var(--surface); border: 1.5px solid #B91C1C; display: flex; align-items: center; justify-content: center; }
  .nonveg-dot span { width: 8px; height: 8px; border-radius: 50%; background: #B91C1C; }
  .dish-tag { position: absolute; bottom: 10px; left: 10px; background: var(--surface); border: 1px solid var(--border); color: var(--text); font-size: 11px; font-weight: 600; padding: 2px 8px; border-radius: 999px; }
  .fav-btn { position: absolute; top: 10px; right: 10px; width: 30px; height: 30px; border-radius: 999px; background: var(--surface); border: 1px solid var(--border); color: var(--muted); cursor: pointer; display: flex; align-items: center; justify-content: center; font-size: 14px; }
  .fav-btn.active { color: var(--danger); border-color: var(--danger); }
  .dish-body { padding: 15px; flex: 1; display: flex; flex-direction: column; }
  .dish-meta-top { display: flex; justify-content: space-between; font-size: 11px; color: var(--accent); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
  .dish-title { font-family: var(--font-display); font-size: 16px; font-weight: 700; margin-bottom: 5px; color: var(--text); }
  .dish-desc { font-size: 12.5px; color: var(--muted); line-height: 1.45; flex: 1; margin-bottom: 12px; }
  .dish-foot { display: flex; align-items: center; justify-content: space-between; margin-bottom: 11px; }
  .dish-price { font-size: 16.5px; font-weight: 700; color: var(--text); }
  .dish-rate { font-size: 12px; font-weight: 600; color: var(--warning); }

  /* Reservation Page */
  .res-grid { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 20px; }
  .panel { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-card); padding: 20px; box-shadow: var(--shadow); }
  .zone-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; margin-bottom: 16px; }
  .zone-card { border: 1px solid var(--border); background: var(--elevated); border-radius: var(--r-ctl); padding: 12px; cursor: pointer; transition: all 0.14s; }
  .zone-card.active { border-color: var(--accent); background: var(--accent-soft); }
  .slot-grid { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
  .slot-btn { padding: 7px 13px; border-radius: var(--r-ctl); border: 1px solid var(--border); background: var(--surface); color: var(--text); font-size: 12.5px; font-weight: 500; cursor: pointer; }
  .slot-btn.active { background: var(--accent); color: var(--accent-contrast); border-color: var(--accent); font-weight: 600; }
  .form-lbl { display: block; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 5px; }
  .form-ctl { width: 100%; background: var(--elevated); border: 1px solid var(--border); color: var(--text); border-radius: var(--r-ctl); padding: 8px 11px; font-size: 13px; outline: none; margin-bottom: 13px; }
  .form-ctl:focus { border-color: var(--accent); background: var(--surface); }

  /* Chefs, Reviews, FAQ, Orders */
  .chefs-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px; margin-bottom: 24px; }
  .table-wrap { width: 100%; overflow-x: auto; background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-card); }
  table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; min-width: 560px; }
  th { padding: 10px 14px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); background: var(--elevated); border-bottom: 1px solid var(--border); }
  td { padding: 12px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
  .faq-item { background: var(--surface); border: 1px solid var(--border); border-radius: var(--r-ctl); margin-bottom: 8px; overflow: hidden; }
  .faq-q { width: 100%; padding: 13px 16px; text-align: left; border: none; background: transparent; color: var(--text); font-size: 13.5px; font-weight: 600; cursor: pointer; display: flex; justify-content: space-between; }
  .faq-a { display: none; padding: 0 16px 13px; font-size: 13px; color: var(--muted); line-height: 1.5; }
  .faq-item.open .faq-a { display: block; }

  /* Drawer & Modals */
  .backdrop { position: fixed; inset: 0; background: rgba(15, 12, 10, 0.52); backdrop-filter: blur(2px); display: none; z-index: 100; }
  .backdrop.open { display: flex; }
  .drawer { margin-left: auto; width: min(420px, 94vw); height: 100%; background: var(--surface); border-left: 1px solid var(--border-strong); padding: 20px; display: flex; flex-direction: column; overflow-y: auto; }
  .modal-box { margin: auto; background: var(--surface); border: 1px solid var(--border-strong); border-radius: var(--r-card); width: min(480px, 93vw); padding: 22px; box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28); max-height: 90vh; overflow-y: auto; }
  .bag-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; padding: 11px 0; border-bottom: 1px solid var(--border); }
  .qty-btn { width: 25px; height: 25px; border-radius: 6px; border: 1px solid var(--border); background: var(--elevated); color: var(--text); font-weight: 700; cursor: pointer; }
  .toast-stack { position: fixed; bottom: 18px; right: 18px; display: flex; flex-direction: column; gap: 8px; z-index: 150; pointer-events: none; }
  .toast { background: var(--surface); border: 1px solid var(--border-strong); border-left: 3px solid var(--accent); color: var(--text); padding: 9px 14px; border-radius: var(--r-ctl); font-size: 12.5px; font-weight: 500; box-shadow: var(--shadow); }

  footer { background: var(--surface); border-top: 1px solid var(--border); padding: 30px 0; margin-top: 12px; font-size: 12.5px; color: var(--muted); }
  .footer-row { display: grid; grid-template-columns: 1.4fr 1fr 1fr 1.2fr; gap: 20px; }
  .footer-h { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text); margin-bottom: 10px; }
  .footer-link { display: block; color: var(--muted); background: none; border: none; padding: 3px 0; cursor: pointer; font-size: 12.5px; text-align: left; }
  .footer-link:hover { color: var(--accent); }

  .mobile-nav-strip { display: none; }
  @media (max-width: 920px) {
    .hero-grid, .res-grid, .dish-grid, .feature-3, .chefs-grid, .footer-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .hero-grid, .res-grid { grid-template-columns: 1fr; }
  }
  @media (max-width: 660px) {
    .nav-links { display: none; }
    .mobile-nav-strip { display: flex !important; }
    .dish-grid, .feature-3, .chefs-grid, .footer-row, .zone-grid { grid-template-columns: 1fr; }
    .search-input { width: 100%; }
  }
</style>
</head>
<body>
  <header class="site-nav">
    <div class="container nav-wrap">
      <div class="brand" onclick="goPage('home')">
        <div class="brand-emblem">S</div>
        <div>
          <div class="brand-title">Saffron &amp; Stone</div>
          <div class="brand-sub">Bandra West &bull; Mumbai</div>
        </div>
      </div>

      <nav class="nav-links" id="top-nav">
        <button type="button" class="nav-btn active" data-page="home" onclick="goPage('home')">Home</button>
        <button type="button" class="nav-btn" data-page="menu" onclick="goPage('menu')">Order Menu</button>
        <button type="button" class="nav-btn" data-page="reserve" onclick="goPage('reserve')">Reserve Table</button>
        <button type="button" class="nav-btn" data-page="events" onclick="goPage('events')">Chefs &amp; Events</button>
        <button type="button" class="nav-btn" data-page="orders" onclick="goPage('orders')">My Orders &amp; Tables</button>
      </nav>

      <div class="nav-right">
        <button type="button" class="btn" onclick="openLoyaltyModal()" title="Loyalty &amp; OTP Sign-In">
          <span id="member-pill">VIP Club</span>
        </button>
        <button type="button" class="btn" onclick="toggleTheme()" title="Switch Light / Evening Theme">
          <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2"/></svg>
        </button>
        <button type="button" class="btn btn-primary" onclick="openBag()">
          <svg viewBox="0 0 24 24"><path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 0 1-8 0"/></svg>
          Bag <span class="pill-badge num" id="bag-badge">2</span>
        </button>
      </div>
    </div>
  </header>

  <!-- Mobile Secondary Nav -->
  <div style="background:var(--surface);border-bottom:1px solid var(--border);padding:8px 16px;gap:6px;overflow-x:auto;" class="mobile-nav-strip">
    <button type="button" class="chip active" data-mnav="home" onclick="goPage('home')">Home</button>
    <button type="button" class="chip" data-mnav="menu" onclick="goPage('menu')">Order Menu</button>
    <button type="button" class="chip" data-mnav="reserve" onclick="goPage('reserve')">Reserve Table</button>
    <button type="button" class="chip" data-mnav="events" onclick="goPage('events')">Chefs &amp; Catering</button>
    <button type="button" class="chip" data-mnav="orders" onclick="goPage('orders')">My Orders &amp; Bookings</button>
  </div>

  <!-- PAGE 1: HOME -->
  <section id="page-home" class="page active">
    <div class="hero">
      <div class="container hero-grid">
        <div>
          <div class="kicker">Open Today &middot; 12:00 PM &ndash; 11:45 PM &middot; Live Kitchen</div>
          <h1>Wood-Fired Coastal Indian Dining, Delivered or Plated Fresh.</h1>
          <p class="hero-lead">Experience heirloom spices, charcoal tandoor classics, and house-fermented sourdough kulchas crafted daily in Bandra West. Browse our full menu, customize spice levels, or reserve your evening table in seconds.</p>
          <div class="hero-ctas">
            <button type="button" class="btn btn-primary" style="padding:10px 18px;" onclick="goPage('menu')">Explore Full Menu &amp; Order &rarr;</button>
            <button type="button" class="btn btn-emerald" style="padding:10px 18px;" onclick="goPage('reserve')">Book a Table</button>
            <button type="button" class="btn" style="padding:10px 16px;" onclick="goPage('events')">Private Dining Quote</button>
          </div>
          <div class="stats-strip">
            <div><strong class="num">4.9 / 5 ★</strong>2,840+ Verified Diners</div>
            <div><strong class="num">25&ndash;35 min</strong>Hot Thermal Express</div>
            <div><strong class="num">CHEF10</strong>10% Off First Online Order</div>
          </div>
        </div>

        <div class="tasting-card">
          <div class="tasting-head">
            <div>
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.07em;color:var(--accent);">Tonight&rsquo;s 4-Course Spotlight</div>
              <div class="serif" style="font-size:19px;font-weight:700;margin-top:2px;">Winter Coastal Tasting Table</div>
            </div>
            <button type="button" class="btn btn-primary" style="padding:5px 11px;font-size:12px;" onclick="addDishById('D-106')">Add Tasting</button>
          </div>
          <div class="course-row"><span>1. Smoked Kokum Rasam Shots &amp; Khakra</span><strong class="num">Included</strong></div>
          <div class="course-row"><span>2. Malabar Tellicherry Pepper Paneer</span><strong class="num">&#8377;490</strong></div>
          <div class="course-row"><span>3. Wood-Fired Truffle Butter Kulcha + Slow Dal</span><strong class="num">&#8377;640</strong></div>
          <div class="course-row"><span>4. Roasted Hazelnut Jaggery Tres Leches</span><strong class="num">&#8377;420</strong></div>
          <div style="margin-top:14px;display:flex;justify-content:space-between;align-items:center;font-size:12px;color:var(--muted);">
            <span>Fresh sourdough batch baking now</span>
            <button type="button" class="btn" style="padding:4px 10px;font-size:12px;" onclick="goPage('menu')">Customize Dishes &rarr;</button>
          </div>
        </div>
      </div>
    </div>

    <div class="container" style="margin-top:28px;">
      <div class="feature-3">
        <div class="feat-box" onclick="goPage('menu')">
          <div style="color:var(--accent);font-weight:700;font-size:12px;">01 &bull; DELIVERY &amp; PICKUP</div>
          <div class="feat-title">Customize Every Plate</div>
          <div class="feat-desc">Filter Veg, Chef Special, or Gluten-Free plates, pick exact spice heat, add sides, and track delivery live.</div>
        </div>
        <div class="feat-box" onclick="goPage('reserve')">
          <div style="color:var(--accent2);font-weight:700;font-size:12px;">02 &bull; INSTANT RESERVATIONS</div>
          <div class="feat-title">Pick Your Seating Zone</div>
          <div class="feat-desc">Choose Chef&rsquo;s Counter, Terrace Garden, or Private Lounge with live evening time-slot availability.</div>
        </div>
        <div class="feat-box" onclick="goPage('events')">
          <div style="color:var(--warning);font-weight:700;font-size:12px;">03 &bull; EVENTS &amp; CATERING</div>
          <div class="feat-title">Plan Private Gatherings</div>
          <div class="feat-desc">Calculate transparent per-guest quotes for curated corporate dinners, anniversaries, and tasting menus.</div>
        </div>
      </div>

      <div class="sec-head">
        <div>
          <h2 class="sec-title">Guest Favourites Tonight</h2>
          <p class="sec-sub">Click any plate to customize spice &amp; add-ons, or add directly to your order bag</p>
        </div>
        <button type="button" class="btn" onclick="goPage('menu')">View All 12 Dishes &rarr;</button>
      </div>
      <div class="dish-grid" id="home-featured-grid"></div>

      <div class="sec-head" style="margin-top:34px;">
        <div>
          <h2 class="sec-title">Recent Diner Reviews</h2>
          <p class="sec-sub">Real feedback from Nov 2026 guests — add your own review live</p>
        </div>
        <button type="button" class="btn btn-primary" onclick="openReviewModal()">+ Write a Review</button>
      </div>
      <div class="chefs-grid" id="reviews-grid"></div>

      <div class="sec-head" style="margin-top:20px;">
        <div><h2 class="sec-title">Dining &amp; Delivery FAQ</h2></div>
      </div>
      <div class="faq-item open">
        <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">Do you accommodate Jain, Vegan, or nut-free allergies?<span>+</span></button>
        <div class="faq-a">Yes — click Customize on any menu item or note allergies during Table Reservation and our pass chef cooks cleanly on dedicated pans.</div>
      </div>
      <div class="faq-item">
        <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">Is valet parking available at Bandra West?<span>+</span></button>
        <div class="faq-a">Complimentary valet parking is available from 12:00 PM till midnight right outside Gate A, 16th Road.</div>
      </div>
      <div class="faq-item">
        <button type="button" class="faq-q" onclick="this.parentElement.classList.toggle('open')">What promo code gives a discount on online orders?<span>+</span></button>
        <div class="faq-a">Enter <strong>CHEF10</strong> inside the Order Bag drawer for an instant 10% savings across food and craft beverages.</div>
      </div>
    </div>
  </section>

  <!-- PAGE 2: FULL MENU -->
  <section id="page-menu" class="page">
    <div class="container">
      <div class="sec-head">
        <div>
          <h1 class="sec-title">Seasonal Kitchen &amp; Bar Menu</h1>
          <p class="sec-sub">Filter by course, dietary preference, saved favourites, or price</p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
          <input type="text" class="search-input" id="menu-search" placeholder="Search dishes, ingredients..." oninput="renderMenu()">
          <select class="search-input" style="width:auto;" id="menu-sort" onchange="renderMenu()">
            <option value="featured">Sort: Featured</option>
            <option value="price-asc">Price: Low to High</option>
            <option value="price-desc">Price: High to Low</option>
            <option value="rating">Top Rated</option>
          </select>
        </div>
      </div>

      <div class="toolbar">
        <div class="chips" id="menu-cat-chips"></div>
        <div class="chips">
          <button type="button" class="chip diet-chip active" onclick="setDiet('All', this)">All Diets</button>
          <button type="button" class="chip diet-chip" onclick="setDiet('Veg', this)">Pure Veg Only</button>
          <button type="button" class="chip diet-chip" onclick="setDiet('Chef', this)">Chef Specials</button>
          <button type="button" class="chip diet-chip" onclick="toggleFavOnly(this)">Favourites (<span id="fav-count">0</span>)</button>
        </div>
      </div>

      <div class="dish-grid" id="menu-grid"></div>
    </div>
  </section>

  <!-- PAGE 3: TABLE RESERVATION -->
  <section id="page-reserve" class="page">
    <div class="container">
      <div class="sec-head">
        <div>
          <h1 class="sec-title">Reserve Your Table</h1>
          <p class="sec-sub">Real-time zone availability for Bandra West flagship dining room</p>
        </div>
      </div>
      <div class="res-grid">
        <div class="panel">
          <label class="form-lbl">1. Select Seating Atmosphere</label>
          <div class="zone-grid" id="zone-grid">
            <div class="zone-card active" onclick="selectZone('Terrace Garden', this)">
              <strong>Terrace Garden</strong>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Open-air lanterns &amp; live breeze &bull; 4 tables left</div>
            </div>
            <div class="zone-card" onclick="selectZone('Chef Counter', this)">
              <strong>Chef&rsquo;s Wood-Fire Counter</strong>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Front-row kitchen theater &bull; 2 seats left</div>
            </div>
            <div class="zone-card" onclick="selectZone('Main Dining Room', this)">
              <strong>Main Dining Hall</strong>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Acoustic warmth, plush booths &bull; 6 tables left</div>
            </div>
            <div class="zone-card" onclick="selectZone('Private Lounge', this)">
              <strong>Private Pearl Room (6&ndash;12)</strong>
              <div style="font-size:12px;color:var(--muted);margin-top:2px;">Dedicated sommelier &bull; 1 suite left</div>
            </div>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
              <label class="form-lbl">2. Date</label>
              <select class="form-ctl" id="res-date">
                <option value="28 Nov 2026 (Tomorrow)">28 Nov 2026 (Tomorrow)</option>
                <option value="29 Nov 2026 (Sun)">29 Nov 2026 (Sunday)</option>
                <option value="30 Nov 2026 (Mon)">30 Nov 2026 (Monday)</option>
              </select>
            </div>
            <div>
              <label class="form-lbl">3. Guests</label>
              <select class="form-ctl" id="res-guests" onchange="updateResSummary()">
                <option value="2 Guests">2 Guests</option>
                <option value="4 Guests" selected>4 Guests</option>
                <option value="6 Guests">6 Guests</option>
                <option value="8 Guests">8 Guests</option>
              </select>
            </div>
          </div>

          <label class="form-lbl">4. Available Evening Slots</label>
          <div class="slot-grid" id="slot-grid">
            <button type="button" class="slot-btn" onclick="selectSlot('6:30 PM', this)">6:30 PM</button>
            <button type="button" class="slot-btn active" onclick="selectSlot('7:30 PM', this)">7:30 PM</button>
            <button type="button" class="slot-btn" onclick="selectSlot('8:15 PM', this)">8:15 PM</button>
            <button type="button" class="slot-btn" onclick="selectSlot('9:00 PM', this)">9:00 PM</button>
            <button type="button" class="slot-btn" onclick="selectSlot('9:45 PM', this)">9:45 PM</button>
          </div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">
            <div>
              <label class="form-lbl">Guest Name</label>
              <input type="text" class="form-ctl" id="res-name" value="Vishesh &amp; Friends">
            </div>
            <div>
              <label class="form-lbl">Mobile Number</label>
              <input type="text" class="form-ctl" id="res-phone" value="+91 98250 41290">
            </div>
          </div>
          <label class="form-lbl">Occasion / Dietary Note</label>
          <input type="text" class="form-ctl" id="res-note" placeholder="e.g. Anniversary dessert note or Jain mains">
          <button type="button" class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="confirmReservation()">Confirm Table Reservation</button>
        </div>

        <div class="panel" style="align-self:start;">
          <div style="font-size:11px;font-weight:700;text-transform:uppercase;color:var(--accent);letter-spacing:0.06em;margin-bottom:6px;">Live Booking Summary</div>
          <h3 class="serif" style="font-size:20px;margin-bottom:14px;">Your Evening at Saffron &amp; Stone</h3>
          <div class="course-row"><span>Zone</span><strong id="sum-zone">Terrace Garden</strong></div>
          <div class="course-row"><span>Party Size</span><strong id="sum-guests">4 Guests</strong></div>
          <div class="course-row"><span>Time Slot</span><strong id="sum-slot">7:30 PM</strong></div>
          <div class="course-row"><span>Cover Deposit</span><strong>&#8377;0 (Pay at Table)</strong></div>
          <div style="margin-top:16px;padding:12px;border-radius:var(--r-ctl);background:var(--elevated);font-size:12.5px;color:var(--muted);line-height:1.5;">
            Instant WhatsApp / SMS confirmation &bull; Free cancellation up to 2 hours prior &bull; Complimentary valet included.
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- PAGE 4: CHEFS & PRIVATE EVENTS -->
  <section id="page-events" class="page">
    <div class="container">
      <div class="sec-head">
        <div>
          <h1 class="sec-title">Meet the Culinary Team &amp; Private Dining</h1>
          <p class="sec-sub">Crafted by award-winning regional specialists — book full buyouts or curated catering</p>
        </div>
      </div>

      <div class="chefs-grid">
        <div class="panel">
          <div style="font-size:11px;font-weight:700;color:var(--accent);text-transform:uppercase;">Chef Patron</div>
          <h3 class="serif" style="font-size:18px;margin:4px 0 6px;">Chef Aarav Kulkarni</h3>
          <p style="font-size:13px;color:var(--muted);">14 years across Konkan coasts and wood-fire kitchens. Obsessed with heirloom Tellicherry peppercorns and 36-hour smoked lentils.</p>
        </div>
        <div class="panel">
          <div style="font-size:11px;font-weight:700;color:var(--accent2);text-transform:uppercase;">Head Pastry &amp; Ferments</div>
          <h3 class="serif" style="font-size:18px;margin:4px 0 6px;">Chef Meera Rao</h3>
          <p style="font-size:13px;color:var(--muted);">Crafts sourdough tandoori flatbreads, jaggery gelatos, and single-origin Coorg cacao finales baked to order.</p>
        </div>
        <div class="panel">
          <div style="font-size:11px;font-weight:700;color:var(--warning);text-transform:uppercase;">Beverage &amp; Zero-Proof Lead</div>
          <h3 class="serif" style="font-size:18px;margin:4px 0 6px;">Devika Sen</h3>
          <p style="font-size:13px;color:var(--muted);">Designs botanical infusions, Clarified Mango Highballs, and smoked kokum tonics paired to coastal spice profiles.</p>
        </div>
      </div>

      <div class="panel">
        <h3 class="serif" style="font-size:20px;margin-bottom:4px;">Instant Private Event &amp; Catering Estimator</h3>
        <p style="font-size:13px;color:var(--muted);margin-bottom:16px;">Adjust headcount and tasting tier to calculate a live estimate immediately.</p>
        <div style="display:grid;grid-template-columns:repeat(3, minmax(0, 1fr));gap:14px;">
          <div>
            <label class="form-lbl">Guest Count (<span id="evt-guest-lbl">24</span>)</label>
            <input type="range" min="10" max="120" value="24" style="width:100%;accent-color:var(--accent);margin-top:8px;" id="evt-guests" oninput="calcEventQuote()">
          </div>
          <div>
            <label class="form-lbl">Menu Package</label>
            <select class="form-ctl" id="evt-tier" onchange="calcEventQuote()">
              <option value="1450">Classic Feast (&#8377;1,450 / guest)</option>
              <option value="2200" selected>Chef&rsquo;s 5-Course Tasting (&#8377;2,200 / guest)</option>
              <option value="3100">Royal Pairing Experience (&#8377;3,100 / guest)</option>
            </select>
          </div>
          <div>
            <label class="form-lbl">Estimated Package Total</label>
            <div style="font-size:24px;font-weight:800;color:var(--accent);" class="num" id="evt-total">&#8377;52,800</div>
          </div>
        </div>
        <div style="margin-top:14px;display:flex;gap:10px;flex-wrap:wrap;align-items:center;">
          <input type="text" class="search-input" style="flex:1;min-width:220px;" id="evt-contact" placeholder="Enter name or phone for callback">
          <button type="button" class="btn btn-primary" onclick="submitEventInquiry()">Request Event Proposal</button>
        </div>
      </div>
    </div>
  </section>

  <!-- PAGE 5: MY ORDERS & BOOKINGS -->
  <section id="page-orders" class="page">
    <div class="container">
      <div class="sec-head">
        <div>
          <h1 class="sec-title">My Orders &amp; Table Reservations</h1>
          <p class="sec-sub">Track food delivery progress and manage upcoming table bookings</p>
        </div>
        <div style="display:flex;gap:8px;">
          <button type="button" class="btn" onclick="goPage('menu')">Order More Food</button>
          <button type="button" class="btn btn-primary" onclick="goPage('reserve')">+ New Table</button>
        </div>
      </div>

      <h3 class="serif" style="font-size:18px;margin-bottom:10px;">Active &amp; Recent Food Orders</h3>
      <div class="table-wrap" style="margin-bottom:24px;">
        <table>
          <thead><tr><th>Order ID</th><th>Date &amp; Mode</th><th>Dishes</th><th>Kitchen Status</th><th style="text-align:right;">Total</th></tr></thead>
          <tbody id="orders-tbody"></tbody>
        </table>
      </div>

      <h3 class="serif" style="font-size:18px;margin-bottom:10px;">Confirmed Table Reservations</h3>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Booking Ref</th><th>Date &amp; Time</th><th>Zone</th><th>Party</th><th>Status</th><th style="text-align:right;">Action</th></tr></thead>
          <tbody id="bookings-tbody"></tbody>
        </table>
      </div>
    </div>
  </section>

  <footer>
    <div class="container footer-row">
      <div>
        <div class="serif" style="font-size:17px;font-weight:700;color:var(--text);margin-bottom:6px;">Saffron &amp; Stone</div>
        <p style="line-height:1.5;">16th Road, Pali Hill, Bandra West, Mumbai 400050<br>Daily 12:00 PM &ndash; 11:45 PM &middot; +91 22 4890 3100</p>
      </div>
      <div>
        <div class="footer-h">Explore</div>
        <button type="button" class="footer-link" onclick="goPage('home')">Home Showcase</button>
        <button type="button" class="footer-link" onclick="goPage('menu')">Seasonal Menu</button>
        <button type="button" class="footer-link" onclick="goPage('reserve')">Reserve Table</button>
        <button type="button" class="footer-link" onclick="goPage('events')">Private Events</button>
      </div>
      <div>
        <div class="footer-h">Guest Services</div>
        <button type="button" class="footer-link" onclick="goPage('orders')">Track Delivery</button>
        <button type="button" class="footer-link" onclick="openLoyaltyModal()">VIP OTP Club</button>
        <button type="button" class="footer-link" onclick="toggleTheme()">Toggle Day / Evening Mode</button>
      </div>
      <div>
        <div class="footer-h">Secret Chef&rsquo;s Club</div>
        <p style="margin-bottom:8px;">Join for Friday tasting invites &amp; instant code CHEF10.</p>
        <div style="display:flex;gap:6px;">
          <input type="email" id="club-email" class="search-input" style="flex:1;width:auto;" placeholder="you@domain.com">
          <button type="button" class="btn btn-primary" onclick="joinClub()">Join</button>
        </div>
      </div>
    </div>
  </footer>

  <!-- Quick-View & Customize Dish Modal -->
  <div class="backdrop" id="dish-modal" onclick="if(event.target===this) closeDishModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">
        <span style="font-size:11px;font-weight:700;color:var(--accent);text-transform:uppercase;" id="dm-cat"></span>
        <button type="button" class="btn" onclick="closeDishModal()">&times;</button>
      </div>
      <h3 class="serif" style="font-size:21px;margin-bottom:4px;" id="dm-title"></h3>
      <div style="font-size:12.5px;color:var(--muted);margin-bottom:10px;" id="dm-meta"></div>
      <p style="font-size:13px;color:var(--muted);line-height:1.5;margin-bottom:14px;" id="dm-desc"></p>

      <label class="form-lbl">Spice Preference</label>
      <div class="chips" style="margin-bottom:14px;" id="dm-spice-row">
        <button type="button" class="chip" onclick="setSpice('Mild', this)">Mild</button>
        <button type="button" class="chip active" onclick="setSpice('Signature Medium', this)">Signature Medium</button>
        <button type="button" class="chip" onclick="setSpice('Coastal Fiery', this)">Coastal Fiery</button>
      </div>

      <label class="form-lbl">Recommended Pairings &amp; Add-ons</label>
      <div style="display:flex;flex-direction:column;gap:7px;margin-bottom:14px;font-size:13px;" id="dm-addons">
        <label style="display:flex;justify-content:space-between;cursor:pointer;"><span><input type="checkbox" value="140" data-name="Truffle Butter Naan" onchange="updateDishModalPrice()"> Truffle Butter Naan</span><span class="num">+&#8377;140</span></label>
        <label style="display:flex;justify-content:space-between;cursor:pointer;"><span><input type="checkbox" value="90" data-name="Roasted Cumin Mint Raita" onchange="updateDishModalPrice()"> Roasted Cumin Mint Raita</span><span class="num">+&#8377;90</span></label>
        <label style="display:flex;justify-content:space-between;cursor:pointer;"><span><input type="checkbox" value="60" data-name="Smoked Chili Garlic Crisp" onchange="updateDishModalPrice()"> Smoked Chili Garlic Crisp</span><span class="num">+&#8377;60</span></label>
      </div>

      <input type="text" class="form-ctl" id="dm-note" placeholder="Cooking note (e.g. less oil, no coriander)">
      <div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid var(--border);">
        <div><span style="font-size:11.5px;color:var(--muted);display:block;">Plate Total</span><strong class="num" style="font-size:19px;" id="dm-price"></strong></div>
        <button type="button" class="btn btn-primary" style="padding:10px 18px;" onclick="addCustomizedDish()">Add to Order Bag</button>
      </div>
    </div>
  </div>

  <!-- Slide-Over Order Bag & Express Checkout Drawer -->
  <div class="backdrop" id="bag-backdrop" onclick="if(event.target===this) closeBag()">
    <div class="drawer">
      <div style="display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid var(--border);padding-bottom:12px;margin-bottom:12px;">
        <strong class="serif" style="font-size:18px;">Your Order Bag</strong>
        <button type="button" class="btn" onclick="closeBag()">&times;</button>
      </div>

      <div class="chips" style="margin-bottom:12px;">
        <button type="button" class="chip active" id="mode-delivery" onclick="setOrderMode('Delivery', this)">Home Delivery</button>
        <button type="button" class="chip" id="mode-pickup" onclick="setOrderMode('Self Pickup', this)">Self Pickup (20 min)</button>
      </div>

      <div id="bag-items" style="flex:1;overflow-y:auto;"></div>

      <div style="border-top:1px solid var(--border);padding-top:12px;margin-top:10px;">
        <div style="display:flex;gap:6px;margin-bottom:10px;">
          <input type="text" class="search-input" style="flex:1;width:auto;" id="promo-box" placeholder="Promo code (CHEF10)">
          <button type="button" class="btn" onclick="applyPromo()">Apply</button>
        </div>
        <input type="text" class="form-ctl" id="checkout-addr" value="14B Pali Mala Rd, Bandra West" placeholder="Delivery address or pickup name">
        <select class="form-ctl" id="checkout-pay" style="margin-bottom:10px;">
          <option value="UPI (GPay / PhonePe)">Pay via UPI (GPay / PhonePe)</option>
          <option value="Credit / Debit Card">Credit / Debit Card</option>
          <option value="Cash on Delivery">Pay on Delivery</option>
        </select>

        <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:3px;"><span>Items Subtotal</span><span class="num" id="bag-sub">0</span></div>
        <div style="font-size:12.5px;color:var(--muted);display:flex;justify-content:space-between;margin-bottom:3px;"><span>GST (5%) &amp; Packaging</span><span class="num" id="bag-tax">0</span></div>
        <div style="font-size:12.5px;color:var(--success);display:none;justify-content:space-between;margin-bottom:3px;" id="bag-disc-row"><span>Promo Discount (CHEF10)</span><span class="num" id="bag-disc">0</span></div>
        <div style="font-size:16px;font-weight:700;display:flex;justify-content:space-between;margin:8px 0 12px;"><span>Grand Total</span><span class="num" id="bag-total">0</span></div>
        <button type="button" class="btn btn-primary" style="width:100%;justify-content:center;padding:11px;" onclick="placeOrder()">Place Order Now</button>
      </div>
    </div>
  </div>

  <!-- Review Modal -->
  <div class="backdrop" id="review-modal" onclick="if(event.target===this) closeReviewModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
        <strong class="serif" style="font-size:18px;">Share Your Experience</strong>
        <button type="button" class="btn" onclick="closeReviewModal()">&times;</button>
      </div>
      <label class="form-lbl">Your Name</label>
      <input type="text" class="form-ctl" id="rev-name" placeholder="e.g. Rohan Kapoor">
      <label class="form-lbl">Rating</label>
      <select class="form-ctl" id="rev-stars">
        <option value="5.0">5.0 ★ — Extraordinary</option>
        <option value="4.5">4.5 ★ — Great Evening</option>
        <option value="4.0">4.0 ★ — Very Good</option>
      </select>
      <label class="form-lbl">Review</label>
      <input type="text" class="form-ctl" id="rev-text" placeholder="Tell others what stood out...">
      <button type="button" class="btn btn-primary" style="width:100%;justify-content:center;" onclick="submitReview()">Publish Review</button>
    </div>
  </div>

  <!-- Loyalty OTP Modal -->
  <div class="backdrop" id="loyalty-modal" onclick="if(event.target===this) closeLoyaltyModal()">
    <div class="modal-box">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
        <strong class="serif" style="font-size:18px;">Saffron VIP Loyalty Club</strong>
        <button type="button" class="btn" onclick="closeLoyaltyModal()">&times;</button>
      </div>
      <p style="font-size:13px;color:var(--muted);margin-bottom:14px;">Verify your mobile number to unlock complimentary dessert perks &amp; priority Chef&rsquo;s Counter seating.</p>
      <label class="form-lbl">Mobile Number</label>
      <input type="text" class="form-ctl" id="vip-phone" value="+91 98250 41290">
      <label class="form-lbl">6-Digit OTP</label>
      <input type="text" class="form-ctl" id="vip-otp" value="482910">
      <div style="display:flex;justify-content:flex-end;gap:8px;">
        <button type="button" class="btn" onclick="showToast('OTP 482910 sent via SMS')">Send OTP</button>
        <button type="button" class="btn btn-primary" onclick="verifyVip()">Verify Member</button>
      </div>
    </div>
  </div>

  <div class="toast-stack" id="toast-stack"></div>

  <script>
    var DISHES = [
      { id: 'D-101', title: 'Charcoal Malai Broccoli', cat: 'Small Plates', veg: true, chef: true, price: 460, rating: 4.9, mins: '15 min', tag: 'Chef Special', desc: 'Tandoor-blistered florets glazed in saffron cashew cream, cardamom & pickled shallots.' },
      { id: 'D-102', title: 'Malabar Pepper Paneer Tikka', cat: 'Small Plates', veg: true, chef: false, price: 490, rating: 4.8, mins: '18 min', tag: 'Gluten Free', desc: 'Artisanal cottage cheese charred over tamarind embers with crushed Tellicherry pepper.' },
      { id: 'D-103', title: 'Smoked Guntur Crispy Wings', cat: 'Small Plates', veg: false, chef: true, price: 540, rating: 4.9, mins: '20 min', tag: 'Crispy Glaze', desc: 'Free-range wings tossed in burnt garlic honey glaze, curry leaves & sesame crunch.' },
      { id: 'D-104', title: 'Coastal Avocado & Papdi Chaat', cat: 'Small Plates', veg: true, chef: false, price: 420, rating: 4.8, mins: '12 min', tag: 'Crisp & Tangy', desc: 'Whipped herb yogurt, ruby pomegranate, raw mango ribbons & tamarind reduction.' },
      { id: 'D-105', title: '24-Hour Old Delhi Black Dal', cat: 'Wood-Fired Mains', veg: true, chef: true, price: 620, rating: 5.0, mins: '22 min', tag: 'House Legend', desc: 'Slow-simmered urad lentils finished overnight over glowing charcoal with cultured butter.' },
      { id: 'D-106', title: 'Saffron Coastal Curry Bowl', cat: 'Wood-Fired Mains', veg: false, chef: true, price: 780, rating: 4.9, mins: '24 min', tag: 'Bestseller', desc: 'Alleppey coconut curry simmered with kokum, stone-ground spices & red rice string hoppers.' },
      { id: 'D-107', title: 'Wild Mushroom truffle Kolhapuri', cat: 'Wood-Fired Mains', veg: true, chef: true, price: 690, rating: 4.8, mins: '20 min', tag: 'Plant Forward', desc: 'Roasted shiitake & button mushrooms folded into smoky roasted-coconut stone-ground masala.' },
      { id: 'D-108', title: 'Awadhi Dum Kathal Biryani', cat: 'Biryani & Breads', veg: true, chef: true, price: 650, rating: 4.9, mins: '25 min', tag: 'Clay-Pot Sealed', desc: 'Aged basmati steamed under saffron pastry crust with caramelized onions & rosewater mint raita.' },
      { id: 'D-109', title: 'Sourdough Garlic Truffle Kulcha', cat: 'Biryani & Breads', veg: true, chef: false, price: 240, rating: 4.9, mins: '10 min', tag: 'Fresh Dough', desc: '48-hour wild-fermented flatbread baked in clay oven with black sea salt.' },
      { id: 'D-110', title: 'Roasted Hazelnut Jaggery Tres Leches', cat: 'Craft Desserts', veg: true, chef: true, price: 420, rating: 5.0, mins: '10 min', tag: 'Table Favourite', desc: 'Cardamom sponge soaked in palm jaggery three-milk cream topped with brittle praline.' },
      { id: 'D-111', title: '70% Coorg Dark Chocolate Mousse', cat: 'Craft Desserts', veg: true, chef: false, price: 460, rating: 4.8, mins: '10 min', tag: 'Gluten Free', desc: 'Single-origin Karnataka cacao whipped mousse with spiced orange zest crumble.' },
      { id: 'D-112', title: 'Smoked Kokum Botanical Spritz', cat: 'Signature Drinks', veg: true, chef: true, price: 320, rating: 4.9, mins: '8 min', tag: 'Zero Proof', desc: 'Clarified Ratnagiri kokum shrub, charred rosemary, Gondhoraj lime & tonic.' }
    ];

    var state = {
      cat: 'All',
      diet: 'All',
      favOnly: false,
      favs: { 'D-105': true, 'D-110': true },
      bag: [
        { key: 'D-105|Signature Medium|None', id: 'D-105', title: '24-Hour Old Delhi Black Dal', note: 'Signature Medium', unitPrice: 620, qty: 1 },
        { key: 'D-109|Standard|None', id: 'D-109', title: 'Sourdough Garlic Truffle Kulcha', note: 'Charred crisp', unitPrice: 240, qty: 2 }
      ],
      orderMode: 'Delivery',
      promoApplied: false,
      orders: [
        { id: 'ORD-2026-884', meta: '27 Nov 2026 · Home Delivery', items: 'Malabar Pepper Paneer x1, Kokum Spritz x2', status: 'Chef Preparing', total: 1186 },
        { id: 'ORD-2026-841', meta: '24 Nov 2026 · Self Pickup', items: 'Awadhi Dum Biryani x2, Tres Leches x1', status: 'Delivered', total: 1806 }
      ],
      bookings: [
        { id: 'TBL-904', dt: '28 Nov 2026 · 8:15 PM', zone: 'Terrace Garden', party: '4 Guests', status: 'Confirmed' }
      ],
      reviews: [
        { name: 'Riya Malhotra', stars: '5.0 ★', text: 'The 24-hour Black Dal and Sourdough Kulcha rival London and Bombay finest dining rooms.' },
        { name: 'Siddharth Mehta', stars: '4.9 ★', text: 'Booked the Terrace Garden slot in 2 clicks — service timing and kokum spritz were spot-on.' },
        { name: 'Neha Sharma', stars: '5.0 ★', text: 'Customizing spice levels and Jain options online worked effortlessly without calling.' }
      ],
      zone: 'Terrace Garden',
      slot: '7:30 PM',
      activeModalDish: null,
      activeSpice: 'Signature Medium'
    };

    function esc(s) {
      return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function inr(n) {
      return '₹' + Number(n || 0).toLocaleString('en-IN');
    }

    function dishIllustration(d, idx) {
      var col = d.veg ? '#0F766E' : '#B45309';
      var modes = [
        '<svg viewBox="0 0 140 84" width="140" height="84"><circle cx="70" cy="42" r="32" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="2"/><circle cx="70" cy="42" r="22" fill="var(--accent-soft)" stroke="' + col + '" stroke-width="1.8" stroke-dasharray="4 3"/><circle cx="62" cy="38" r="5" fill="' + col + '" opacity="0.8"/><circle cx="77" cy="44" r="6" fill="var(--accent)" opacity="0.75"/></svg>',
        '<svg viewBox="0 0 140 84" width="140" height="84"><ellipse cx="70" cy="46" rx="42" ry="22" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="2"/><path d="M44 44 Q70 22 96 44" fill="var(--accent-soft)" stroke="' + col + '" stroke-width="2"/><circle cx="70" cy="34" r="4" fill="var(--warning)"/></svg>',
        '<svg viewBox="0 0 140 84" width="140" height="84"><rect x="34" y="16" width="72" height="52" rx="14" fill="var(--surface)" stroke="var(--border-strong)" stroke-width="2"/><path d="M48 44 Q70 28 92 44" fill="none" stroke="' + col + '" stroke-width="2.5" stroke-linecap="round"/><circle cx="56" cy="48" r="4" fill="' + col + '"/><circle cx="84" cy="48" r="4" fill="var(--accent)"/></svg>'
      ];
      return modes[idx % modes.length];
    }

    function buildDishCard(d, idx) {
      var dot = d.veg ? '<div class="veg-dot" title="Pure Veg"><span></span></div>' : '<div class="nonveg-dot" title="Coastal / Non-Veg"><span></span></div>';
      var favCls = state.favs[d.id] ? ' active' : '';
      return '<article class="dish-card">' +
        '<div class="dish-art" style="cursor:pointer;" onclick="openDishModal(\'' + d.id + '\')">' +
          dishIllustration(d, idx) + dot +
          '<span class="dish-tag">' + esc(d.tag) + '</span>' +
          '<button type="button" class="fav-btn' + favCls + '" onclick="event.stopPropagation();toggleFav(\'' + d.id + '\')" title="Save Favourite">&#9829;</button>' +
        '</div>' +
        '<div class="dish-body">' +
          '<div class="dish-meta-top"><span>' + esc(d.cat) + '</span><span>' + esc(d.mins) + '</span></div>' +
          '<div class="dish-title">' + esc(d.title) + '</div>' +
          '<div class="dish-desc">' + esc(d.desc) + '</div>' +
          '<div class="dish-foot"><span class="dish-price num">' + inr(d.price) + '</span><span class="dish-rate">&#9733; ' + d.rating + '</span></div>' +
          '<div style="display:flex;gap:8px;">' +
            '<button type="button" class="btn" style="flex:1;justify-content:center;" onclick="openDishModal(\'' + d.id + '\')">Customize</button>' +
            '<button type="button" class="btn btn-primary" style="flex:1;justify-content:center;" onclick="addDishById(\'' + d.id + '\')">+ Add</button>' +
          '</div>' +
        '</div></article>';
    }

    function initApp() {
      var cats = ['All', 'Small Plates', 'Wood-Fired Mains', 'Biryani & Breads', 'Craft Desserts', 'Signature Drinks'];
      document.getElementById('menu-cat-chips').innerHTML = cats.map(function(c, i) {
        return '<button type="button" class="chip' + (i === 0 ? ' active' : '') + '" onclick="setCat(\'' + esc(c) + '\', this)">' + esc(c) + '</button>';
      }).join('');
      document.getElementById('home-featured-grid').innerHTML = DISHES.filter(function(d) { return d.chef; }).slice(0, 6).map(buildDishCard).join('');
      renderMenu();
      renderReviews();
      renderBag();
      renderOrdersAndBookings();
      updateFavCount();
      calcEventQuote();
    }

    function renderMenu() {
      var q = (document.getElementById('menu-search').value || '').toLowerCase();
      var sort = document.getElementById('menu-sort').value;
      var list = DISHES.filter(function(d) {
        var mc = state.cat === 'All' || d.cat === state.cat;
        var md = state.diet === 'All' || (state.diet === 'Veg' && d.veg) || (state.diet === 'Chef' && d.chef);
        var mf = !state.favOnly || state.favs[d.id];
        var mq = !q || (d.title + ' ' + d.desc + ' ' + d.cat).toLowerCase().indexOf(q) !== -1;
        return mc && md && mf && mq;
      });
      if (sort === 'price-asc') list.sort(function(a, b) { return a.price - b.price; });
      if (sort === 'price-desc') list.sort(function(a, b) { return b.price - a.price; });
      if (sort === 'rating') list.sort(function(a, b) { return b.rating - a.rating; });
      var grid = document.getElementById('menu-grid');
      grid.innerHTML = list.length ? list.map(buildDishCard).join('') : '<div class="panel" style="grid-column:1/-1;text-align:center;color:var(--muted);">No dishes match that filter — clear filters to view all 12 plates.</div>';
    }

    function setCat(c, btn) {
      state.cat = c;
      document.querySelectorAll('#menu-cat-chips .chip').forEach(function(b) { b.classList.remove('active'); });
      if (btn) btn.classList.add('active');
      renderMenu();
    }

    function setDiet(d, btn) {
      state.diet = d;
      state.favOnly = false;
      document.querySelectorAll('.diet-chip').forEach(function(b) { b.classList.remove('active'); });
      if (btn) btn.classList.add('active');
      renderMenu();
    }

    function toggleFavOnly(btn) {
      state.favOnly = !state.favOnly;
      document.querySelectorAll('.diet-chip').forEach(function(b) { b.classList.remove('active'); });
      if (state.favOnly && btn) btn.classList.add('active');
      renderMenu();
    }

    function toggleFav(id) {
      if (state.favs[id]) delete state.favs[id]; else state.favs[id] = true;
      updateFavCount();
      document.getElementById('home-featured-grid').innerHTML = DISHES.filter(function(d) { return d.chef; }).slice(0, 6).map(buildDishCard).join('');
      renderMenu();
      showToast(state.favs[id] ? 'Saved to your favourites' : 'Removed from favourites');
    }

    function updateFavCount() {
      document.getElementById('fav-count').textContent = String(Object.keys(state.favs).length);
    }

    function openDishModal(id) {
      var d = DISHES.find(function(x) { return x.id === id; });
      if (!d) return;
      state.activeModalDish = d;
      state.activeSpice = 'Signature Medium';
      document.querySelectorAll('#dm-spice-row .chip').forEach(function(c, i) { c.classList.toggle('active', i === 1); });
      document.querySelectorAll('#dm-addons input').forEach(function(cb) { cb.checked = false; });
      document.getElementById('dm-note').value = '';
      document.getElementById('dm-cat').textContent = d.cat + (d.veg ? ' · Pure Veg' : ' · Coastal Kitchen');
      document.getElementById('dm-title').textContent = d.title;
      document.getElementById('dm-meta').textContent = '★ ' + d.rating + ' · Prep ' + d.mins;
      document.getElementById('dm-desc').textContent = d.desc;
      updateDishModalPrice();
      document.getElementById('dish-modal').classList.add('open');
    }
    function closeDishModal() { document.getElementById('dish-modal').classList.remove('open'); }
    function setSpice(s, btn) {
      state.activeSpice = s;
      document.querySelectorAll('#dm-spice-row .chip').forEach(function(c) { c.classList.remove('active'); });
      if (btn) btn.classList.add('active');
    }
    function updateDishModalPrice() {
      if (!state.activeModalDish) return;
      var extra = 0;
      document.querySelectorAll('#dm-addons input:checked').forEach(function(cb) { extra += Number(cb.value || 0); });
      document.getElementById('dm-price').textContent = inr(state.activeModalDish.price + extra);
    }
    function addCustomizedDish() {
      var d = state.activeModalDish;
      if (!d) return;
      var addons = [], extra = 0;
      document.querySelectorAll('#dm-addons input:checked').forEach(function(cb) {
        addons.push(cb.getAttribute('data-name'));
        extra += Number(cb.value || 0);
      });
      var custNote = (document.getElementById('dm-note').value || '').trim();
      var summary = state.activeSpice + (addons.length ? ' + ' + addons.join(', ') : '') + (custNote ? ' (' + custNote + ')' : '');
      var key = d.id + '|' + summary;
      var existing = state.bag.find(function(b) { return b.key === key; });
      if (existing) existing.qty += 1;
      else state.bag.push({ key: key, id: d.id, title: d.title, note: summary, unitPrice: d.price + extra, qty: 1 });
      closeDishModal();
      renderBag();
      openBag();
      showToast('Added customized ' + d.title);
    }

    function addDishById(id) {
      var d = DISHES.find(function(x) { return x.id === id; });
      if (!d) return;
      var key = d.id + '|Chef Standard';
      var existing = state.bag.find(function(b) { return b.key === key; });
      if (existing) existing.qty += 1;
      else state.bag.push({ key: key, id: d.id, title: d.title, note: 'Chef Standard', unitPrice: d.price, qty: 1 });
      renderBag();
      showToast(d.title + ' added to bag');
    }

    function changeQty(idx, delta) {
      if (!state.bag[idx]) return;
      state.bag[idx].qty += delta;
      if (state.bag[idx].qty <= 0) state.bag.splice(idx, 1);
      renderBag();
    }

    function setOrderMode(mode, btn) {
      state.orderMode = mode;
      document.getElementById('mode-delivery').classList.toggle('active', mode === 'Delivery');
      document.getElementById('mode-pickup').classList.toggle('active', mode === 'Self Pickup');
      renderBag();
    }

    function applyPromo() {
      var code = (document.getElementById('promo-box').value || '').trim().toUpperCase();
      if (code === 'CHEF10' || code === 'WELCOME10') {
        state.promoApplied = true;
        renderBag();
        showToast('Promo ' + code + ' applied (-10%)!');
      } else {
        showToast('Try code CHEF10 for 10% savings');
      }
    }

    function renderBag() {
      var count = state.bag.reduce(function(a, b) { return a + b.qty; }, 0);
      document.getElementById('bag-badge').textContent = String(count);
      var box = document.getElementById('bag-items');
      var sub = 0;
      if (!state.bag.length) {
        box.innerHTML = '<div style="padding:36px 0;text-align:center;color:var(--muted);">Your order bag is empty.<br><button type="button" class="btn btn-primary" style="margin-top:12px;" onclick="closeBag();goPage(\'menu\')">Browse Menu</button></div>';
      } else {
        box.innerHTML = state.bag.map(function(b, idx) {
          sub += b.unitPrice * b.qty;
          return '<div class="bag-row">' +
            '<div><div style="font-weight:600;font-size:13.5px;">' + esc(b.title) + '</div>' +
            '<div style="font-size:11.5px;color:var(--muted);">' + esc(b.note) + ' &middot; ' + inr(b.unitPrice) + '</div></div>' +
            '<div style="display:flex;align-items:center;gap:6px;">' +
              '<button type="button" class="qty-btn" onclick="changeQty(' + idx + ',-1)">-</button>' +
              '<span class="num" style="min-width:16px;text-align:center;font-weight:600;">' + b.qty + '</span>' +
              '<button type="button" class="qty-btn" onclick="changeQty(' + idx + ',1)">+</button>' +
            '</div></div>';
        }).join('');
      }
      var disc = state.promoApplied ? Math.round(sub * 0.1) : 0;
      var tax = Math.round((sub - disc) * 0.05) + (sub > 0 ? 35 : 0);
      var total = Math.max(0, sub - disc + tax);
      document.getElementById('bag-disc-row').style.display = state.promoApplied ? 'flex' : 'none';
      document.getElementById('bag-sub').textContent = inr(sub);
      document.getElementById('bag-disc').textContent = '-' + inr(disc);
      document.getElementById('bag-tax').textContent = inr(tax);
      document.getElementById('bag-total').textContent = inr(total);
    }

    function placeOrder() {
      if (!state.bag.length) { showToast('Add a dish first'); return; }
      var sub = state.bag.reduce(function(a, b) { return a + b.unitPrice * b.qty; }, 0);
      var disc = state.promoApplied ? Math.round(sub * 0.1) : 0;
      var tax = Math.round((sub - disc) * 0.05) + 35;
      var total = sub - disc + tax;
      var itemsTxt = state.bag.map(function(b) { return b.title + ' x' + b.qty; }).join(', ');
      var oid = 'ORD-2026-' + (885 + state.orders.length);
      state.orders.unshift({ id: oid, meta: 'Just now · ' + state.orderMode, items: itemsTxt, status: 'Kitchen Accepted', total: total });
      state.bag = [];
      state.promoApplied = false;
      renderBag();
      renderOrdersAndBookings();
      closeBag();
      goPage('orders');
      showToast('Order ' + oid + ' sent to Saffron & Stone kitchen!');
    }

    function selectZone(z, el) {
      state.zone = z;
      document.querySelectorAll('#zone-grid .zone-card').forEach(function(c) { c.classList.remove('active'); });
      if (el) el.classList.add('active');
      updateResSummary();
    }
    function selectSlot(s, el) {
      state.slot = s;
      document.querySelectorAll('#slot-grid .slot-btn').forEach(function(b) { b.classList.remove('active'); });
      if (el) el.classList.add('active');
      updateResSummary();
    }
    function updateResSummary() {
      document.getElementById('sum-zone').textContent = state.zone;
      document.getElementById('sum-guests').textContent = document.getElementById('res-guests').value;
      document.getElementById('sum-slot').textContent = state.slot;
    }
    function confirmReservation() {
      var bid = 'TBL-' + (905 + state.bookings.length);
      var dt = document.getElementById('res-date').value.split(' (')[0] + ' · ' + state.slot;
      var party = document.getElementById('res-guests').value;
      state.bookings.unshift({ id: bid, dt: dt, zone: state.zone, party: party, status: 'Confirmed' });
      renderOrdersAndBookings();
      goPage('orders');
      showToast('Table ' + bid + ' confirmed in ' + state.zone + '!');
    }
    function cancelBooking(id) {
      state.bookings = state.bookings.filter(function(b) { return b.id !== id; });
      renderOrdersAndBookings();
      showToast('Booking ' + id + ' cancelled');
    }

    function renderOrdersAndBookings() {
      document.getElementById('orders-tbody').innerHTML = state.orders.map(function(o) {
        return '<tr><td class="num" style="font-weight:700;">' + esc(o.id) + '</td><td>' + esc(o.meta) + '</td><td>' + esc(o.items) + '</td><td><span style="color:var(--success);font-weight:600;">' + esc(o.status) + '</span></td><td class="num" style="text-align:right;font-weight:700;">' + inr(o.total) + '</td></tr>';
      }).join('');
      document.getElementById('bookings-tbody').innerHTML = state.bookings.length ? state.bookings.map(function(b) {
        return '<tr><td class="num" style="font-weight:700;">' + esc(b.id) + '</td><td>' + esc(b.dt) + '</td><td>' + esc(b.zone) + '</td><td>' + esc(b.party) + '</td><td><span style="color:var(--success);font-weight:600;">' + esc(b.status) + '</span></td><td style="text-align:right;"><button type="button" class="btn" style="padding:4px 10px;font-size:12px;color:var(--danger);" onclick="cancelBooking(\'' + esc(b.id) + '\')">Cancel</button></td></tr>';
      }).join('') : '<tr><td colspan="6" style="text-align:center;color:var(--muted);">No upcoming reservations — book a table anytime.</td></tr>';
    }

    function renderReviews() {
      document.getElementById('reviews-grid').innerHTML = state.reviews.slice(0, 6).map(function(r) {
        return '<div class="panel"><div style="color:var(--warning);font-weight:700;font-size:12.5px;margin-bottom:6px;">' + esc(r.stars) + '</div><p style="font-size:13px;line-height:1.5;margin-bottom:10px;">&ldquo;' + esc(r.text) + '&rdquo;</p><div style="font-size:12px;color:var(--muted);font-weight:600;">' + esc(r.name) + ' &middot; Verified Diner</div></div>';
      }).join('');
    }
    function openReviewModal() { document.getElementById('review-modal').classList.add('open'); }
    function closeReviewModal() { document.getElementById('review-modal').classList.remove('open'); }
    function submitReview() {
      var name = (document.getElementById('rev-name').value || '').trim() || 'Guest Diner';
      var stars = document.getElementById('rev-stars').value + ' ★';
      var text = (document.getElementById('rev-text').value || '').trim();
      if (!text) { showToast('Please enter a short review note'); return; }
      state.reviews.unshift({ name: name, stars: stars, text: text });
      document.getElementById('rev-name').value = '';
      document.getElementById('rev-text').value = '';
      closeReviewModal();
      renderReviews();
      showToast('Thank you! Your review is now live.');
    }

    function calcEventQuote() {
      var g = Number(document.getElementById('evt-guests').value || 24);
      var rate = Number(document.getElementById('evt-tier').value || 2200);
      document.getElementById('evt-guest-lbl').textContent = String(g);
      document.getElementById('evt-total').textContent = inr(g * rate);
    }
    function submitEventInquiry() {
      var c = (document.getElementById('evt-contact').value || '').trim();
      if (!c) { showToast('Enter your name or phone for the proposal'); return; }
      document.getElementById('evt-contact').value = '';
      showToast('Private dining proposal sent for ' + document.getElementById('evt-guest-lbl').textContent + ' guests!');
    }

    function goPage(id) {
      document.querySelectorAll('.page').forEach(function(p) { p.classList.remove('active'); });
      var el = document.getElementById('page-' + id);
      if (el) el.classList.add('active');
      document.querySelectorAll('#top-nav .nav-btn').forEach(function(b) { b.classList.toggle('active', b.getAttribute('data-page') === id); });
      document.querySelectorAll('.mobile-nav-strip .chip').forEach(function(b) { b.classList.toggle('active', b.getAttribute('data-mnav') === id); });
      window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function openBag() { document.getElementById('bag-backdrop').classList.add('open'); }
    function closeBag() { document.getElementById('bag-backdrop').classList.remove('open'); }
    function openLoyaltyModal() { document.getElementById('loyalty-modal').classList.add('open'); }
    function closeLoyaltyModal() { document.getElementById('loyalty-modal').classList.remove('open'); }
    function verifyVip() {
      document.getElementById('member-pill').textContent = 'VIP Verified ✓';
      closeLoyaltyModal();
      showToast('VIP account active — complimentary welcome mocktail unlocked!');
    }
    function joinClub() {
      var em = (document.getElementById('club-email').value || '').trim();
      if (!em || em.indexOf('@') === -1) { showToast('Enter a valid email address'); return; }
      document.getElementById('club-email').value = '';
      showToast('Joined! Promo code CHEF10 is ready inside your Bag.');
    }
    function toggleTheme() {
      var isDark = document.body.classList.toggle('dark-theme');
      showToast(isDark ? 'Evening candlelit theme enabled' : 'Daylight editorial theme enabled');
    }
    function showToast(msg) {
      var stack = document.getElementById('toast-stack');
      var t = document.createElement('div');
      t.className = 'toast';
      t.textContent = msg;
      stack.appendChild(t);
      setTimeout(function() { t.style.opacity = '0'; setTimeout(function() { t.remove(); }, 260); }, 2600);
    }

    initApp();
  </script>
</body>
</html>`;

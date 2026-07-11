"""
ui_components.py
-----------------
Reusable, styled UI building blocks shared across every tab of the Edge
AI Vehicle Intelligence Platform: the dark theme CSS, metric cards,
gauges, radar charts, and health-status badges. Centralizing these here
means every tab looks consistent and we only tune the visual style once.
"""

import base64
import functools

import plotly.graph_objects as go
import streamlit as st

# ---- Color palette (premium automotive dark theme) ----
COLOR_BG = "#0e1117"
COLOR_CARD = "#171b24"
COLOR_ACCENT = "#00d4ff"
COLOR_GOOD = "#2ecc71"
COLOR_WARN = "#f39c12"
COLOR_CRITICAL = "#e74c3c"
COLOR_TEXT_MUTED = "#8b93a7"


def inject_custom_css():
    """Injects global CSS: the 'Liquid Glass'-inspired premium automotive theme — frosted glass panels, soft blur, gradients, floating shadows, and a subtle ambient background shimmer."""
    st.markdown(f"""
    <style>
        :root {{
            --radius-card: 18px;
            --radius-control: 14px;
            --radius-pill: 999px;
            --shadow-ambient: 0 8px 28px rgba(0,0,0,0.32);
            --shadow-float: 0 12px 32px rgba(0,0,0,0.4);
            --shadow-deep: 0 20px 46px rgba(0,0,0,0.5);
            --ease-premium: cubic-bezier(0.22, 1, 0.36, 1);
        }}
        /* Tabular figures everywhere a number can change, so live-updating
           stats (battery %, range, scores) never jitter in width. */
        .metric-value, .hs-val, .cvalue, .mc-sub, .issue-row, .ai-greeting-title {{
            font-variant-numeric: tabular-nums;
        }}
        .stApp, .stApp p, .stApp li {{ line-height: 1.5; }}
        .stApp h1, .stApp h2, .stApp h3 {{ letter-spacing: -0.01em; font-weight: 800; }}
        @keyframes evFadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        @keyframes ambientShimmer {{
            0%   {{ background-position: 0% 50%; }}
            50%  {{ background-position: 100% 50%; }}
            100% {{ background-position: 0% 50%; }}
        }}
        @keyframes softGlow {{
            0%, 100% {{ opacity: 0.5; }}
            50% {{ opacity: 0.9; }}
        }}
        .stApp {{
            background:
                radial-gradient(circle at top left, rgba(0,212,255,0.05) 0%, rgba(0,212,255,0) 40%),
                radial-gradient(circle at bottom right, rgba(120,80,255,0.05) 0%, rgba(120,80,255,0) 45%),
                radial-gradient(circle at top left, #131722 0%, #0a0c10 100%);
            background-size: 200% 200%, 200% 200%, 100% 100%;
            animation: ambientShimmer 22s ease-in-out infinite;
        }}
        /* ---- Liquid Glass card treatment ---- */
        .metric-card, .glass-panel, .toggle-card, .mode-card, .issue-card, .settings-card,
        .rec-card, .placeholder-card, .driver-hero, .ai-summary-box, .companion-float,
        .ai-greeting-block, .mood-indicator, .ring-card {{
            background: linear-gradient(145deg, rgba(255,255,255,0.045), rgba(255,255,255,0.015)),
                        linear-gradient(145deg, {COLOR_CARD}cc, #10131acc);
            backdrop-filter: blur(18px) saturate(140%);
            -webkit-backdrop-filter: blur(18px) saturate(140%);
            border: 1px solid rgba(255,255,255,0.09);
            border-radius: 18px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.06);
        }}
        .metric-card {{
            padding: 18px 20px;
            margin-bottom: 10px;
            animation: evFadeIn 0.45s ease both;
            transition: transform 0.18s ease, box-shadow 0.18s ease;
        }}
        .metric-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 12px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08);
        }}
        [data-testid="stVerticalBlock"] .stPlotlyChart, .element-container {{
            animation: evFadeIn 0.5s ease both;
        }}
        div[data-testid="stButton"] > button {{
            transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
            border-radius: 14px !important;
            backdrop-filter: blur(10px);
        }}
        div[data-testid="stButton"] > button:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 14px rgba(0,212,255,0.25);
        }}
        div[data-testid="stButton"] > button:active {{
            transform: translateY(0px) scale(0.98);
        }}
        /* Smooth toggles/sliders */
        div[data-testid="stToggle"] label div[data-baseweb], .stSlider, .stSelectbox {{
            transition: all 0.2s ease;
        }}
        .metric-title {{
            color: {COLOR_TEXT_MUTED};
            font-size: 0.78rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 4px;
        }}
        .metric-value {{
            font-size: 1.9rem;
            font-weight: 700;
            color: #f2f4f8;
        }}
        .metric-sub {{
            font-size: 0.8rem;
            color: {COLOR_TEXT_MUTED};
            margin-top: 2px;
        }}
        .badge {{
            display: inline-block;
            padding: 3px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 700;
            letter-spacing: 0.03em;
        }}
        .badge-good {{ background: rgba(46,204,113,0.15); color: {COLOR_GOOD}; border: 1px solid {COLOR_GOOD}; }}
        .badge-warn {{ background: rgba(243,156,18,0.15); color: {COLOR_WARN}; border: 1px solid {COLOR_WARN}; }}
        .badge-critical {{ background: rgba(231,76,60,0.15); color: {COLOR_CRITICAL}; border: 1px solid {COLOR_CRITICAL}; }}
        .ai-line {{
            border-left: 3px solid {COLOR_ACCENT};
            padding: 8px 14px;
            margin: 6px 0;
            background: rgba(0,212,255,0.05);
            backdrop-filter: blur(8px);
            border-radius: 0 12px 12px 0;
            font-size: 0.92rem;
            animation: evFadeIn 0.35s ease both;
        }}
        .alert-line {{
            border-left: 3px solid {COLOR_WARN};
            padding: 8px 14px;
            margin: 6px 0;
            background: rgba(243,156,18,0.06);
            backdrop-filter: blur(8px);
            border-radius: 0 12px 12px 0;
            font-size: 0.9rem;
            animation: evFadeIn 0.35s ease both;
        }}
        .section-header {{
            font-size: 1.05rem;
            font-weight: 800;
            letter-spacing: -0.005em;
            color: #f2f4f8;
            margin: 18px 0 10px 0;
            padding-bottom: 8px;
            position: relative;
        }}
        .section-header::after {{
            content: "";
            position: absolute; left: 0; right: 0; bottom: 0; height: 1px;
            background: linear-gradient(90deg, rgba(0,212,255,0.35), rgba(255,255,255,0.06) 55%, rgba(255,255,255,0) 100%);
        }}
        .driver-hero {{
            padding: 24px 28px;
            margin-bottom: 14px;
        }}
        .driver-hero-title {{
            font-size: 1.4rem;
            font-weight: 700;
            color: #f2f4f8;
            margin-bottom: 2px;
        }}
        .driver-hero-sub {{
            color: {COLOR_TEXT_MUTED};
            font-size: 0.95rem;
        }}
        .ai-summary-box {{
            padding: 18px 20px;
            font-size: 1.02rem;
            line-height: 1.55;
            color: #eef1f7;
            animation: evFadeIn 0.5s ease both;
        }}
        .coach-check {{
            padding: 6px 0;
            font-size: 0.98rem;
            color: {COLOR_GOOD};
        }}
        .coach-suggest {{
            padding: 6px 0 6px 0;
            font-size: 0.95rem;
            color: {COLOR_TEXT_MUTED};
        }}
        .driver-card-title {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: {COLOR_TEXT_MUTED};
            margin-bottom: 10px;
            font-weight: 700;
        }}
        .ai-greeting-block {{
            padding: 22px 26px;
            margin-bottom: 14px;
            animation: evFadeIn 0.5s ease both;
        }}
        .ai-greeting-title {{
            font-size: 1.55rem;
            font-weight: 700;
            color: #f8fafc;
            margin-bottom: 4px;
        }}
        .ai-greeting-sub {{
            font-size: 0.95rem;
            color: {COLOR_TEXT_MUTED};
        }}
        .mood-indicator {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 14px 20px;
            margin-bottom: 14px;
            animation: evFadeIn 0.55s ease both;
        }}
        .mood-emoji {{ font-size: 1.8rem; animation: softGlow 3s ease-in-out infinite; }}
        .mood-text {{ font-size: 1.05rem; font-weight: 700; color: #f2f4f8; }}
        .companion-float {{
            padding: 14px 18px;
            font-size: 0.9rem;
            color: #eef1f7;
            margin-top: 14px;
            min-height: 24px;
            transition: opacity 0.4s ease;
            animation: evFadeIn 0.6s ease both;
        }}
        .companion-float .cf-label {{
            font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.06em;
            color: {COLOR_ACCENT}; margin-bottom: 4px; font-weight: 700;
        }}
    </style>
    """, unsafe_allow_html=True)


def dynamic_theme_overlay_css(condition: str) -> str:
    """
    Returns a small CSS override that subtly tints the ambient background
    based on driving conditions (time of day / weather / charging state).
    Deliberately subtle per the design brief — a gentle color wash, not a
    dramatic re-theme.
    """
    tints = {
        "morning": "rgba(255,178,102,0.05) 0%, rgba(255,178,102,0) 45%",
        "night": "rgba(40,60,140,0.10) 0%, rgba(40,60,140,0) 50%",
        "rain": "rgba(80,150,200,0.08) 0%, rgba(80,150,200,0) 45%",
        "charging": "rgba(0,212,255,0.10) 0%, rgba(0,212,255,0) 50%",
        "day": "rgba(0,212,255,0.03) 0%, rgba(0,212,255,0) 40%",
    }
    tint = tints.get(condition, tints["day"])
    return f"""
    <style>
        .stApp {{
            background-image:
                radial-gradient(circle at 15% 10%, {tint}),
                radial-gradient(circle at top left, rgba(0,212,255,0.05) 0%, rgba(0,212,255,0) 40%),
                radial-gradient(circle at bottom right, rgba(120,80,255,0.05) 0%, rgba(120,80,255,0) 45%),
                radial-gradient(circle at top left, #131722 0%, #0a0c10 100%) !important;
        }}
    </style>
    """


def health_color(value: float, good=80, warn=60) -> str:
    """Returns a hex color based on a 0-100 health score."""
    if value >= good:
        return COLOR_GOOD
    elif value >= warn:
        return COLOR_WARN
    return COLOR_CRITICAL


def health_badge_html(label: str, value: float, good=80, warn=60) -> str:
    """Builds an HTML badge (Good / Warning / Critical) for a health score."""
    if value >= good:
        cls, text = "badge-good", "Good"
    elif value >= warn:
        cls, text = "badge-warn", "Attention"
    else:
        cls, text = "badge-critical", "Critical"
    return f'<span class="badge {cls}">{label}: {text}</span>'


def metric_card(title: str, value: str, subtitle: str = "", color: str = "#f2f4f8"):
    """Renders a styled metric card (title / big value / subtitle)."""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value" style="color:{color};">{value}</div>
        <div class="metric-sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


def gauge_chart(value: float, title: str, suffix: str = "%", good=80, warn=60, height=260) -> go.Figure:
    """Builds a Plotly gauge/indicator chart color-coded by health thresholds."""
    color = health_color(value, good, warn)
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": suffix, "font": {"size": 30}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#4b5566"},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, warn], "color": "rgba(231,76,60,0.15)"},
                {"range": [warn, good], "color": "rgba(243,156,18,0.15)"},
                {"range": [good, 100], "color": "rgba(46,204,113,0.15)"},
            ],
        },
        title={"text": title, "font": {"size": 14, "color": "#c8cede"}},
    ))
    fig.update_layout(
        height=height,
        margin=dict(l=15, r=15, t=45, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e6e9f0"},
    )
    return fig


def radar_chart(categories: list, values: list, title: str = "", height=380) -> go.Figure:
    """Builds a Plotly radar/spider chart, e.g. for the Driver Behaviour profile."""
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        line=dict(color=COLOR_ACCENT),
        fillcolor="rgba(0,212,255,0.25)",
    ))
    fig.update_layout(
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], color="#8b93a7"),
            angularaxis=dict(color="#c8cede"),
        ),
        showlegend=False,
        title={"text": title, "font": {"color": "#e6e9f0"}},
        height=height,
        margin=dict(l=40, r=40, t=50, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#e6e9f0"},
    )
    return fig


def line_trend(x, y, title, y_label="", color=COLOR_ACCENT, height=300) -> go.Figure:
    """Builds a styled Plotly line chart for historical trend sections."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=color, width=2.5),
                              fill="tozeroy", fillcolor="rgba(0,212,255,0.08)"))
    fig.update_layout(
        title={"text": title, "font": {"size": 14, "color": "#e6e9f0"}},
        height=height,
        margin=dict(l=30, r=20, t=45, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c8cede"},
        yaxis_title=y_label,
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    return fig


def vehicle_avatar_svg(status_color: str, label: str) -> str:
    """
    A simple, clean top-down vehicle illustration whose body color reflects
    overall health (green/yellow/red) — used in the Driver View. Purely
    decorative SVG; the actual "tap to see details" action is a Streamlit
    button placed right below it (SVG alone can't call back into Python).
    """
    return f"""
    <div style="display:flex;justify-content:center;padding:6px 0 2px 0;">
        <svg width="220" height="130" viewBox="0 0 220 130" xmlns="http://www.w3.org/2000/svg">
            <ellipse cx="110" cy="118" rx="80" ry="8" fill="rgba(0,0,0,0.35)"/>
            <rect x="30" y="45" width="160" height="45" rx="18" fill="{status_color}" opacity="0.9"/>
            <rect x="55" y="20" width="110" height="35" rx="14" fill="{status_color}" opacity="0.75"/>
            <rect x="65" y="26" width="40" height="22" rx="4" fill="#0e1117" opacity="0.55"/>
            <rect x="115" y="26" width="40" height="22" rx="4" fill="#0e1117" opacity="0.55"/>
            <circle cx="60" cy="92" r="14" fill="#0e1117"/>
            <circle cx="60" cy="92" r="6" fill="#4b5566"/>
            <circle cx="160" cy="92" r="14" fill="#0e1117"/>
            <circle cx="160" cy="92" r="6" fill="#4b5566"/>
            <circle cx="42" cy="60" r="4" fill="#fff8e7"/>
            <circle cx="178" cy="60" r="4" fill="#fff8e7"/>
        </svg>
    </div>
    <div style="text-align:center;color:{COLOR_TEXT_MUTED};font-size:0.85rem;margin-top:-4px;">{label}</div>
    """


@functools.lru_cache(maxsize=4)
def load_image_base64(path: str) -> str:
    """
    Reads an image file from disk and returns its base64 encoding, cached
    so the (potentially large) EV product photo is only read from disk
    once per process, not on every Streamlit rerun.
    """
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def vehicle_hero_image(image_base64: str, max_width_px: int = 460) -> str:
    """
    Renders the official EV product photo (a real PNG supplied by the
    user, never an AI-generated or hand-drawn illustration) as the
    static, non-interactive hero visual for the Driver View. Per the
    design brief: no hotspots, no click handlers, just a premium,
    responsive presentation — a floating drop-shadow underneath and a
    smooth fade-in when the Driver View opens.
    """
    return f"""
    <div class="vehicle-hero-wrap">
        <img class="vehicle-hero-img" src="data:image/png;base64,{image_base64}"
             style="max-width:{max_width_px}px;" alt="Vehicle" />
    </div>
    """


def vehicle_hero_css() -> str:
    """CSS for the vehicle_hero_image: fade-in animation + floating shadow, fully responsive."""
    return """
    <style>
        @keyframes heroFadeIn {
            from { opacity: 0; transform: translateY(14px) scale(0.98); }
            to   { opacity: 1; transform: translateY(0) scale(1); }
        }
        .vehicle-hero-wrap {
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 12px 6px 0 6px;
        }
        .vehicle-hero-img {
            width: 100%;
            height: auto;
            object-fit: contain;
            filter: drop-shadow(0 22px 18px rgba(0,0,0,0.45)) drop-shadow(0 2px 4px rgba(0,0,0,0.25));
            animation: heroFadeIn 0.9s cubic-bezier(0.22, 1, 0.36, 1) both;
        }
    </style>
    """


def premium_ev_illustration(status_color: str = COLOR_ACCENT) -> str:
    """
    A polished, static, non-interactive EV side-profile illustration for
    the Driver View hero panel. Deliberately decorative only — per the
    latest design brief this replaces the old clickable component-hotspot
    vehicle diagram. No click handlers, no hotspots, purely visual.
    """
    return f"""
    <div style="display:flex;justify-content:center;align-items:center;padding:10px 0 4px 0;">
        <svg width="100%" height="200" viewBox="0 0 480 220" xmlns="http://www.w3.org/2000/svg" style="max-width:420px;">
            <defs>
                <linearGradient id="bodyGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="{status_color}" stop-opacity="0.95"/>
                    <stop offset="100%" stop-color="{status_color}" stop-opacity="0.55"/>
                </linearGradient>
                <radialGradient id="shadowGrad" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stop-color="rgba(0,0,0,0.45)"/>
                    <stop offset="100%" stop-color="rgba(0,0,0,0)"/>
                </radialGradient>
            </defs>
            <ellipse cx="240" cy="195" rx="190" ry="14" fill="url(#shadowGrad)"/>
            <path d="M60,150 C60,110 95,95 140,90 C165,60 205,45 260,45 C320,45 365,65 390,95
                     C420,98 445,110 452,130 C456,142 452,155 438,158 L410,158
                     C405,140 388,128 370,128 C352,128 335,140 330,158 L175,158
                     C170,140 153,128 135,128 C117,128 100,140 95,158 L68,158
                     C58,156 58,152 60,150 Z" fill="url(#bodyGrad)" stroke="rgba(255,255,255,0.15)" stroke-width="1.5"/>
            <path d="M150,90 C172,66 205,55 255,55 C305,55 340,68 362,90 Z" fill="rgba(10,12,18,0.55)"/>
            <path d="M158,88 C178,70 206,62 250,62 L250,88 Z" fill="rgba(210,225,245,0.28)"/>
            <path d="M255,62 C300,63 328,73 348,88 L255,88 Z" fill="rgba(210,225,245,0.16)"/>
            <circle cx="135" cy="158" r="26" fill="#0b0d12"/>
            <circle cx="135" cy="158" r="26" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
            <circle cx="135" cy="158" r="11" fill="#3a4152"/>
            <circle cx="370" cy="158" r="26" fill="#0b0d12"/>
            <circle cx="370" cy="158" r="26" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
            <circle cx="370" cy="158" r="11" fill="#3a4152"/>
            <ellipse cx="70" cy="112" rx="7" ry="5" fill="#fff8e7" opacity="0.9"/>
            <ellipse cx="440" cy="128" rx="6" ry="9" fill="#ff5566" opacity="0.85"/>
            <rect x="205" y="100" width="60" height="4" rx="2" fill="rgba(255,255,255,0.25)"/>
        </svg>
    </div>
    """


def nav_rail_css_extra() -> str:
    """Extra CSS scoped to the Driver View left navigation rail buttons and new section cards (backgrounds are glass-ified globally in inject_custom_css; this adds layout + nav-specific styling)."""
    return f"""
    <style>
        .nav-rail div[data-testid="stButton"] > button {{
            width: 100%;
            text-align: left;
            justify-content: flex-start;
            padding: 12px 16px;
            font-size: 0.92rem;
            background: rgba(255,255,255,0.03);
            backdrop-filter: blur(14px);
            border: 1px solid rgba(255,255,255,0.07);
        }}
        .nav-rail div[data-testid="stButton"] > button[kind="primary"] {{
            background: linear-gradient(145deg, rgba(0,212,255,0.20), rgba(0,212,255,0.06));
            border: 1px solid rgba(0,212,255,0.45);
            box-shadow: 0 0 18px rgba(0,212,255,0.12);
        }}
        .hero-stat-row {{
            display:flex; gap:10px; margin: 10px 0 4px 0;
        }}
        .hero-stat {{
            flex:1; text-align:center;
            padding: 12px 6px;
            transition: transform 0.2s ease;
        }}
        .hero-stat:hover {{ transform: translateY(-2px); }}
        .hero-stat .hs-val {{ font-size: 1.25rem; font-weight: 700; color: #f2f4f8; }}
        .hero-stat .hs-label {{ font-size: 0.68rem; color: {COLOR_TEXT_MUTED}; text-transform: uppercase; letter-spacing: 0.04em; margin-top:2px; }}
        .rec-card {{
            border-left: 3px solid rgba(0,212,255,0.4);
            padding: 10px 14px;
            margin: 6px 0;
            font-size: 0.85rem;
            line-height: 1.4;
            animation: evFadeIn 0.4s ease both;
        }}
        .placeholder-card {{
            padding: 28px 24px;
            text-align: center;
            color: {COLOR_TEXT_MUTED};
        }}
        .timeline-item {{
            display:flex; gap:12px; padding: 8px 0;
            border-left: 2px solid rgba(0,212,255,0.25);
            margin-left: 6px; padding-left: 16px; position: relative;
        }}
        .timeline-item::before {{
            content:""; position:absolute; left:-6px; top:14px;
            width:10px; height:10px; border-radius:50%;
            background: {COLOR_ACCENT};
            box-shadow: 0 0 8px {COLOR_ACCENT};
        }}
        .timeline-time {{ font-size: 0.72rem; color: {COLOR_TEXT_MUTED}; min-width: 62px; }}
        .timeline-text {{ font-size: 0.88rem; }}

        .toggle-card {{
            padding: 12px 16px;
            margin-bottom: 8px;
        }}
        .toggle-card .tc-title {{ font-weight: 600; font-size: 0.9rem; color: #f2f4f8; }}
        .toggle-card .tc-sub {{ font-size: 0.75rem; color: {COLOR_TEXT_MUTED}; margin-top: 1px; }}

        .mode-card {{
            position: relative;
            border-radius: 18px;
            padding: 16px 18px;
            text-align: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }}
        .mode-card .mc-icon {{ font-size: 1.5rem; }}
        .mode-card .mc-title {{ font-weight: 700; margin-top: 4px; letter-spacing: 0.01em; }}
        .mode-card .mc-sub {{ font-size: 0.72rem; color: {COLOR_TEXT_MUTED}; margin-top: 2px; }}

        .severity-badge {{
            display:inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: 0.7rem; font-weight: 700; letter-spacing: 0.03em;
        }}
        .sev-minor {{ background: rgba(46,204,113,0.15); color: {COLOR_GOOD}; border: 1px solid {COLOR_GOOD}; }}
        .sev-moderate {{ background: rgba(243,156,18,0.15); color: {COLOR_WARN}; border: 1px solid {COLOR_WARN}; }}
        .sev-severe {{ background: rgba(231,76,60,0.15); color: {COLOR_CRITICAL}; border: 1px solid {COLOR_CRITICAL}; }}

        .issue-card {{
            padding: 16px 18px;
            margin-bottom: 12px;
        }}
        .issue-title {{ font-weight: 700; font-size: 0.98rem; color: #f2f4f8; margin-bottom: 4px; }}
        .issue-row {{ font-size: 0.85rem; color: {COLOR_TEXT_MUTED}; margin-top: 4px; }}
        .issue-row b {{ color: #dfe4ee; }}

        .settings-card {{
            padding: 14px 16px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .settings-card .sc-label {{ font-size: 0.88rem; color: #f2f4f8; }}
        .settings-card .sc-value {{ font-size: 0.82rem; color: {COLOR_ACCENT}; font-weight: 600; }}

        .ring-card {{
            text-align: center;
            padding: 14px 8px;
        }}
    </style>
    """


def _efd_icon(name: str, cx: float, cy: float, color: str, scale: float = 1.0) -> str:
    """
    Centered, single-stroke-weight icon glyphs for the Energy Flow
    diagram nodes -- one small consistent icon family (round caps/joins,
    ~1.7 stroke width) instead of emoji, so every node reads as part of
    the same visual system.
    """
    s = scale
    icons = {
        "battery": f"""
            <g transform="translate({cx},{cy}) scale({s})" stroke="{color}" stroke-width="1.7"
               fill="none" stroke-linecap="round" stroke-linejoin="round">
                <rect x="-11" y="-7" width="20" height="14" rx="2.5"/>
                <rect x="9" y="-3" width="3.5" height="6" rx="1" fill="{color}" stroke="none"/>
                <line x1="-6" y1="-3.2" x2="-6" y2="3.2"/>
                <line x1="-1.5" y1="-3.2" x2="-1.5" y2="3.2"/>
                <line x1="3" y1="-3.2" x2="3" y2="3.2"/>
            </g>""",
        "motor": f"""
            <g transform="translate({cx},{cy}) scale({s})" stroke="{color}" stroke-width="1.7"
               fill="none" stroke-linecap="round" stroke-linejoin="round">
                <circle r="6.2"/>
                <circle r="2.1" fill="{color}" stroke="none"/>
                <line x1="0" y1="-11" x2="0" y2="-7.4"/>
                <line x1="0" y1="11" x2="0" y2="7.4"/>
                <line x1="-11" y1="0" x2="-7.4" y2="0"/>
                <line x1="11" y1="0" x2="7.4" y2="0"/>
                <line x1="-7.8" y1="-7.8" x2="-5.2" y2="-5.2"/>
                <line x1="7.8" y1="-7.8" x2="5.2" y2="-5.2"/>
                <line x1="-7.8" y1="7.8" x2="-5.2" y2="5.2"/>
                <line x1="7.8" y1="7.8" x2="5.2" y2="5.2"/>
            </g>""",
        "wheel": f"""
            <g transform="translate({cx},{cy}) scale({s})" stroke="{color}" stroke-width="1.7"
               fill="none" stroke-linecap="round" stroke-linejoin="round">
                <circle r="10.5"/>
                <circle r="3.2" fill="{color}" stroke="none"/>
                <line x1="0" y1="-10.5" x2="0" y2="-4.6"/>
                <line x1="0" y1="10.5" x2="0" y2="4.6"/>
                <line x1="-10.5" y1="0" x2="-4.6" y2="0"/>
                <line x1="10.5" y1="0" x2="4.6" y2="0"/>
                <line x1="-7.4" y1="-7.4" x2="-3.3" y2="-3.3"/>
                <line x1="7.4" y1="-7.4" x2="3.3" y2="-3.3"/>
                <line x1="-7.4" y1="7.4" x2="-3.3" y2="3.3"/>
                <line x1="7.4" y1="7.4" x2="3.3" y2="3.3"/>
            </g>""",
        "regen": f"""
            <g transform="translate({cx},{cy}) scale({s})" stroke="{color}" stroke-width="1.8"
               fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path d="M -8.5,-2 A 9 9 0 1 1 -8.5,5.2"/>
                <path d="M -12.5,-5.5 L -8.5,-2 L -5,-6.6" fill="none"/>
            </g>""",
    }
    return icons[name]


def _efd_node(cx: float, cy: float, r: float, color: str, glow_id: str, icon: str, label_lines: list) -> str:
    """
    One Energy Flow node: a soft blurred glow behind, a perfect circle
    with a consistent border, a centered icon, and a centered label
    placed *below* the circle so it never overlaps the icon or any
    connecting arrow.
    """
    label_html = "".join(
        f'<tspan x="{cx}" dy="{0 if i == 0 else 13}">{line}</tspan>'
        for i, line in enumerate(label_lines)
    )
    return f"""
        <circle class="efd-glow" cx="{cx}" cy="{cy}" r="{r + 7}" fill="{color}" opacity="0.16" filter="url(#{glow_id})"/>
        <g class="efd-node">
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="url(#efdNodeFill)" stroke="{color}" stroke-width="2"/>
            <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="rgba(255,255,255,0.14)" stroke-width="1"/>
            {_efd_icon(icon, cx, cy, color)}
        </g>
        <text x="{cx}" y="{cy + r + 20}" text-anchor="middle" font-family="-apple-system,'Segoe UI',Arial,sans-serif"
              font-size="11.5" font-weight="600" letter-spacing="0.2" fill="#c7cfdd">{label_html}</text>
    """


def energy_flow_diagram() -> str:
    """
    A precisely-aligned, animated Energy Flow diagram for the Charging
    section: Battery, Motor and Wheels sit on one centered horizontal
    line with equal spacing; Regenerative Braking sits directly beneath
    the Motor. Every arrow starts/ends exactly on a node's circumference
    (computed from the node centers, not eyeballed), so nothing overlaps
    text and every arrowhead points precisely at its destination.

    Instead of a dashed-line "marching ants" effect, small glowing
    pellets travel smoothly along each path via SVG <animateMotion> -- a
    gentle, continuous motion rather than a flashy one. Forward energy
    (Battery -> Motor -> Wheels) uses the accent cyan; regenerative
    energy (Wheels -> Battery, via the Regen node) uses the "good" green,
    so the two flows stay readable at a glance. A CSS hover state (scale
    + brightness) gives every node the same gentle, premium interaction.
    """
    import math

    r = 34
    cx_battery, cx_motor, cx_wheels = 90, 280, 470
    cy_top = 46
    cy_regen = 168

    # Horizontal edge points (forward flow), computed from node radius
    # so arrows start/stop exactly on the circle boundary.
    b_right = cx_battery + r
    m_left = cx_motor - r
    m_right = cx_motor + r
    w_left = cx_wheels - r

    def edge_point(cx1, cy1, cx2, cy2, radius, from_first=True):
        dx, dy = cx2 - cx1, cy2 - cy1
        dist = math.hypot(dx, dy) or 1
        ux, uy = dx / dist, dy / dist
        if from_first:
            return cx1 + ux * radius, cy1 + uy * radius
        return cx2 - ux * radius, cy2 - uy * radius

    w_regen_start = edge_point(cx_wheels, cy_top, cx_motor, cy_regen, r, from_first=True)
    w_regen_end = edge_point(cx_wheels, cy_top, cx_motor, cy_regen, r, from_first=False)
    r_batt_start = edge_point(cx_motor, cy_regen, cx_battery, cy_top, r, from_first=True)
    r_batt_end = edge_point(cx_motor, cy_regen, cx_battery, cy_top, r, from_first=False)

    forward_path_1 = f"M{b_right},{cy_top} L{m_left},{cy_top}"
    forward_path_2 = f"M{m_right},{cy_top} L{w_left},{cy_top}"
    regen_path_1 = f"M{w_regen_start[0]:.1f},{w_regen_start[1]:.1f} L{w_regen_end[0]:.1f},{w_regen_end[1]:.1f}"
    regen_path_2 = f"M{r_batt_start[0]:.1f},{r_batt_start[1]:.1f} L{r_batt_end[0]:.1f},{r_batt_end[1]:.1f}"

    svg_markup = (
        f'<svg width="100%" height="210" viewBox="0 0 560 210" style="max-width:560px; overflow:visible;">'
        f'<defs>'
        f'<linearGradient id="efdNodeFill" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="rgba(255,255,255,0.09)"/>'
        f'<stop offset="100%" stop-color="rgba(255,255,255,0.015)"/>'
        f'</linearGradient>'
        f'<filter id="efdGlowCyan" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>'
        f'<filter id="efdGlowGreen" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="7"/></filter>'
        f'<marker id="efdArrowCyan" markerWidth="7" markerHeight="7" refX="5.5" refY="3.5" orient="auto">'
        f'<path d="M0,0 L7,3.5 L0,7 Z" fill="{COLOR_ACCENT}"/></marker>'
        f'<marker id="efdArrowGreen" markerWidth="7" markerHeight="7" refX="5.5" refY="3.5" orient="auto">'
        f'<path d="M0,0 L7,3.5 L0,7 Z" fill="{COLOR_GOOD}"/></marker>'
        f'</defs>'
        f'<path d="{forward_path_1}" stroke="rgba(0,212,255,0.18)" stroke-width="2" fill="none" marker-end="url(#efdArrowCyan)"/>'
        f'<path d="{forward_path_2}" stroke="rgba(0,212,255,0.18)" stroke-width="2" fill="none" marker-end="url(#efdArrowCyan)"/>'
        f'<path d="{regen_path_1}" stroke="rgba(46,204,113,0.18)" stroke-width="2" fill="none" marker-end="url(#efdArrowGreen)"/>'
        f'<path d="{regen_path_2}" stroke="rgba(46,204,113,0.18)" stroke-width="2" fill="none" marker-end="url(#efdArrowGreen)"/>'
        f'<circle r="3.4" fill="{COLOR_ACCENT}"><animateMotion dur="2.4s" repeatCount="indefinite" path="{forward_path_1}"/></circle>'
        f'<circle r="3.4" fill="{COLOR_ACCENT}" opacity="0.7"><animateMotion dur="2.4s" begin="1.2s" repeatCount="indefinite" path="{forward_path_1}"/></circle>'
        f'<circle r="3.4" fill="{COLOR_ACCENT}"><animateMotion dur="2.4s" begin="0.5s" repeatCount="indefinite" path="{forward_path_2}"/></circle>'
        f'<circle r="3.4" fill="{COLOR_ACCENT}" opacity="0.7"><animateMotion dur="2.4s" begin="1.7s" repeatCount="indefinite" path="{forward_path_2}"/></circle>'
        f'<circle r="3.2" fill="{COLOR_GOOD}"><animateMotion dur="2.8s" begin="0.3s" repeatCount="indefinite" path="{regen_path_1}"/></circle>'
        f'<circle r="3.2" fill="{COLOR_GOOD}"><animateMotion dur="2.8s" begin="1.6s" repeatCount="indefinite" path="{regen_path_2}"/></circle>'
        + _efd_node(cx_battery, cy_top, r, COLOR_ACCENT, "efdGlowCyan", "battery", ["Battery"])
        + _efd_node(cx_motor, cy_top, r, COLOR_ACCENT, "efdGlowCyan", "motor", ["Motor"])
        + _efd_node(cx_wheels, cy_top, r, COLOR_ACCENT, "efdGlowCyan", "wheel", ["Wheels"])
        + _efd_node(cx_motor, cy_regen, r, COLOR_GOOD, "efdGlowGreen", "regen", ["Regenerative", "Braking"])
        + '</svg>'
    )

    style_block = (
        "<style>"
        ".energy-flow-wrap { display:flex; justify-content:center; padding: 10px 0 6px 0; }"
        ".efd-node { transform-box: fill-box; transform-origin: center; "
        "transition: transform 0.25s cubic-bezier(0.22,1,0.36,1), filter 0.25s ease; }"
        ".efd-node:hover { transform: scale(1.06); filter: brightness(1.15); }"
        "</style>"
    )

    html = f'{style_block}<div class="energy-flow-wrap">{svg_markup}</div>'

    # Belt-and-suspenders: collapse to one contiguous line with no leading
    # whitespace on any line. Streamlit's st.markdown runs content through a
    # CommonMark-style parser even with unsafe_allow_html=True. A <div> is a
    # recognized HTML "block" tag whose block ends at the first *blank*
    # line inside it; anything after that point gets re-parsed as ordinary
    # markdown, where 4+ leading spaces trigger the "indented code block"
    # rule -- rendering the rest of the SVG as literal escaped text instead
    # of graphics (that was the reported bug: multi-line, indented, blank
    # -line-separated markup tripping this rule). Building/joining the
    # whole thing as one line with zero internal blank lines and zero
    # leading indentation makes that misclassification impossible,
    # regardless of which markdown parser or Streamlit version renders it.
    return " ".join(line.strip() for line in html.splitlines() if line.strip())


def bar_compare(categories: list, values: list, title: str, color=COLOR_ACCENT, height=300) -> go.Figure:
    """Simple horizontal bar chart, e.g. for road-type distribution or component costs."""
    fig = go.Figure(go.Bar(x=values, y=categories, orientation="h", marker_color=color))
    fig.update_layout(
        title={"text": title, "font": {"size": 14, "color": "#e6e9f0"}},
        height=height,
        margin=dict(l=10, r=20, t=45, b=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "#c8cede"},
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    )
    return fig

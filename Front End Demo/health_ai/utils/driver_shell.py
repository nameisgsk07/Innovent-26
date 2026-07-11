"""
driver_shell.py
----------------
The Driver View shell — redesigned around one rule: the home screen
answers exactly four questions (Is my vehicle healthy? How much battery
and range do I have? What should I know before driving? Does anything
need attention?) and nothing else. Everything more detailed lives behind
the left navigation rail.

Layout:
    Left   -> fixed vertical navigation rail (Vehicle, Charging, Drive
              Intelligence, Smart Assist, Comfort, Vehicle Care, Settings)
    Center -> whichever section is selected (Vehicle is the default "home")
    Right  -> the persistent hero panel: AI greeting, mood indicator, AI
              vehicle summary, the real vehicle photo, animated
              battery/trip/range stats, "before driving" notes, alerts
              (only if something is actually wrong), and a floating AI
              companion that rotates short insights on its own timer.

A short "AI is thinking" sequence plays whenever the state actually
changes (Refresh button or a Demo Mode tick) — not on every incidental
widget rerun — so recommendations never appear to update instantly.
Section switches show a brief branded loading beat for the same reason
Streamlit reruns would otherwise feel abrupt.
"""

import os
import time

import streamlit as st

from utils import ai_engine as ai
from utils import ui_components as ui
from utils import animated_ui as anim
from utils import driver_sections as sections

VEHICLE_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "..", "assets", "vehicle_ev.png")

NAV_ITEMS = [
    ("Vehicle", "🚘"),
    ("Charging", "⚡"),
    ("Drive Intelligence", "🧠"),
    ("Smart Assist", "🛡️"),
    ("Comfort", "❄️"),
    ("Vehicle Care", "🔧"),
    ("Settings", "⚙️"),
]

SECTION_RENDERERS = {
    "Vehicle": sections.render_vehicle_section,
    "Charging": sections.render_charging_placeholder,
    "Drive Intelligence": sections.render_drive_intelligence_placeholder,
    "Smart Assist": sections.render_smart_assist_placeholder,
    "Comfort": sections.render_comfort_placeholder,
    "Vehicle Care": sections.render_vehicle_care_placeholder,
    "Settings": sections.render_settings_placeholder,
}

LOADING_MESSAGES = {
    "Vehicle": "Preparing Vehicle Overview...",
    "Charging": "Loading Charging Intelligence...",
    "Drive Intelligence": "Loading Drive Intelligence...",
    "Smart Assist": "Preparing Smart Assist...",
    "Comfort": "Adjusting Comfort Settings...",
    "Vehicle Care": "Updating AI Insights...",
    "Settings": "Loading Settings...",
}

AI_THINKING_STEPS = [
    "Analyzing driving behaviour...",
    "Checking battery performance...",
    "Evaluating weather conditions...",
    "Generating recommendations...",
]


def _render_nav(active: str):
    st.markdown('<div class="nav-rail">', unsafe_allow_html=True)
    for name, icon in NAV_ITEMS:
        is_active = name == active
        if st.button(f"{icon}  {name}", key=f"navbtn_{name}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.driver_section = name
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _maybe_run_ai_thinking():
    """
    Plays the brief 'AI is thinking' sequence exactly once per actual
    state change (Refresh button or Demo Mode tick), never on unrelated
    widget reruns — gated by a flag app/dashboard.py sets right after
    calling sim.tick().
    """
    if st.session_state.pop("just_ticked", False):
        placeholder = st.empty()
        for step in AI_THINKING_STEPS:
            placeholder.markdown(f'<div class="companion-float"><div class="cf-label">AI</div>{step}</div>', unsafe_allow_html=True)
            time.sleep(0.22)
        placeholder.empty()

        toast_msg = ai.smart_notification(st.session_state.vehicle_state)
        st.toast(toast_msg)


def _render_hero(state: dict, score_info: dict):
    st.markdown(ui.vehicle_hero_css(), unsafe_allow_html=True)

    # ---- AI Welcome Experience ----
    greeting = ai.ai_greeting(state)
    st.markdown(f"""
    <div class="ai-greeting-block">
        <div class="ai-greeting-title">{greeting['title']}</div>
        <div class="ai-greeting-sub">{greeting['detail']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- AI Mood Indicator ----
    mood = ai.ai_mood(score_info)
    st.markdown(f"""
    <div class="mood-indicator">
        <div class="mood-emoji">{mood['emoji']}</div>
        <div class="mood-text">{mood['text']}</div>
    </div>
    """, unsafe_allow_html=True)

    # ---- AI Vehicle Summary (natural language, no raw percentages) ----
    summary_sentences = ai.vehicle_summary_sentences(state, score_info)
    st.markdown(f'<div class="ai-summary-box">🧠 {" ".join(summary_sentences)}</div>', unsafe_allow_html=True)

    # ---- Vehicle photo (static, no hotspots) ----
    try:
        img_b64 = ui.load_image_base64(VEHICLE_IMAGE_PATH)
        st.markdown(ui.vehicle_hero_image(img_b64), unsafe_allow_html=True)
    except FileNotFoundError:
        st.markdown(ui.premium_ev_illustration(ui.health_color(score_info["overall"])), unsafe_allow_html=True)

    # ---- How much battery and range do I have? (animated) ----
    trip = state.get("trip", {})
    prev_stats = st.session_state.get("_prev_hero_stats", {})
    stats = [
        {"label": "Battery", "value": round(state["battery"]["state_of_charge"]), "suffix": "%",
         "prev": prev_stats.get("battery", round(state["battery"]["state_of_charge"]))},
        {"label": "Trip Distance", "value": round(trip.get("distance_km", 0), 1), "suffix": " km",
         "prev": prev_stats.get("trip", round(trip.get("distance_km", 0), 1))},
        {"label": "Range Left", "value": ai.estimated_range_km(state), "suffix": " km",
         "prev": prev_stats.get("range", ai.estimated_range_km(state))},
    ]
    anim.animated_stat_row(stats)
    st.session_state["_prev_hero_stats"] = {
        "battery": stats[0]["value"], "trip": stats[1]["value"], "range": stats[2]["value"],
    }

    # ---- What should I know before driving? ----
    st.markdown('<div class="section-header">Before You Drive</div>', unsafe_allow_html=True)
    for note in ai.before_driving_notes(state):
        st.markdown(f'<div class="rec-card">💡 {note}</div>', unsafe_allow_html=True)

    # ---- Does anything need immediate attention? (only if real) ----
    real_alerts = [a for a in state["alerts"] if "No critical" not in a]
    if real_alerts:
        st.markdown('<div class="section-header">Needs Attention</div>', unsafe_allow_html=True)
        for a in real_alerts:
            st.markdown(f'<div class="alert-line">⚠ {a}</div>', unsafe_allow_html=True)

    # ---- Floating AI Companion ----
    anim.floating_companion(ai.companion_messages(state))


def render(state: dict, score_info: dict, demo_mode: bool):
    st.markdown(ui.nav_rail_css_extra(), unsafe_allow_html=True)
    st.markdown(ui.dynamic_theme_overlay_css(ai.current_theme_condition(state)), unsafe_allow_html=True)

    if "driver_section" not in st.session_state:
        st.session_state.driver_section = "Vehicle"

    _maybe_run_ai_thinking()

    # Brief branded loading beat on section switch (kept under a second).
    if st.session_state.get("_last_rendered_section") != st.session_state.driver_section:
        with st.spinner(LOADING_MESSAGES.get(st.session_state.driver_section, "Loading...")):
            time.sleep(0.35)
        st.session_state["_last_rendered_section"] = st.session_state.driver_section

    nav_col, content_col, hero_col = st.columns([1.0, 2.5, 1.2])

    with nav_col:
        _render_nav(st.session_state.driver_section)

    with content_col:
        renderer = SECTION_RENDERERS.get(st.session_state.driver_section, sections.render_vehicle_section)
        renderer(state, score_info)

    with hero_col:
        _render_hero(state, score_info)

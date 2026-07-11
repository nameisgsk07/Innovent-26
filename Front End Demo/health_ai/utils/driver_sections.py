"""
driver_sections.py
-------------------
Content renderers for each Driver View navigation section (see
driver_shell.py for the nav rail + hero panel that surrounds these).

Phase 1 fully implements "Vehicle" — Vehicle Health, Today's Summary,
Trip Information, Vehicle Timeline, Recent Alerts, and AI Summary — all
in plain, driver-friendly language (no engineering jargon, no raw
sensor units), reusing the existing driver-facing helpers in
utils/ai_engine.py so Insights View and Driver View stay consistent
with each other.

The remaining six sections (Charging, Drive Intelligence, Smart Assist,
Comfort, Vehicle Care, Settings) are intentionally left as clearly
labeled placeholders for now — each is a substantial feature in its own
right per the design brief, and will be built out in its own phase.
"""

import streamlit as st

from utils import ai_engine as ai
from utils import ui_components as ui
from utils import animated_ui as anim


def _placeholder(title: str, description: str, upcoming: list):
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)
    items = "".join(f"<div>• {i}</div>" for i in upcoming)
    st.markdown(f"""
    <div class="placeholder-card">
        <div style="font-size:1.4rem;">🚧</div>
        <div style="font-weight:700;color:#f2f4f8;margin:6px 0 4px 0;">{title} — coming in the next phase</div>
        <div style="font-size:0.88rem;margin-bottom:10px;">{description}</div>
        <div style="font-size:0.82rem;text-align:left;display:inline-block;">{items}</div>
    </div>
    """, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Vehicle (fully built)
# ---------------------------------------------------------------------

def render_vehicle_section(state: dict, score_info: dict):
    d = state["driver"]
    breakdown = ai.driving_score_breakdown(state)

    # ---- Vehicle Health (animated rings, not raw percentages in a table) ----
    st.markdown('<div class="section-header">Vehicle Health</div>', unsafe_allow_html=True)
    rings = [
        {"label": "Battery", "value": state["battery"]["health_percent"], "color": ui.health_color(state["battery"]["health_percent"])},
        {"label": "Motor", "value": state["motor"]["health_pct"], "color": ui.health_color(state["motor"]["health_pct"])},
        {"label": "Safety", "value": d["safety_score"], "color": ui.health_color(d["safety_score"])},
        {"label": "Comfort", "value": state["suspension"]["ride_comfort_score"], "color": ui.health_color(state["suspension"]["ride_comfort_score"])},
        {"label": "Efficiency", "value": breakdown["energy_efficiency"], "color": ui.health_color(breakdown["energy_efficiency"])},
    ]
    anim.animated_health_rings(rings)
    st.info(f"**{score_info['label']}.** " + ai.vehicle_status_message(score_info))

    # ---- Today's Summary ----
    st.markdown('<div class="section-header">Today\'s Summary</div>', unsafe_allow_html=True)
    journey = ai.todays_journey(state)
    c1, c2, c3, c4 = st.columns(4)
    with c1: ui.metric_card("Trips Today", f"{journey['trips']}")
    with c2: ui.metric_card("Distance Driven", f"{journey['distance_km']} km")
    with c3: ui.metric_card("Driving Time", f"{journey['driving_time_min']} min")
    with c4: ui.metric_card("Efficiency", f"{journey['efficiency_pct']}%", color=ui.health_color(journey["efficiency_pct"]))

    # ---- Trip Information ----
    st.markdown('<div class="section-header">Trip Information</div>', unsafe_allow_html=True)
    trip = state.get("trip", {})
    c1, c2, c3 = st.columns(3)
    with c1:
        ui.metric_card("Current Destination", trip.get("destination", "—"))
        ui.metric_card("ETA", f"{trip.get('eta_min', 0):.0f} min")
    with c2:
        ui.metric_card("Trip Distance", f"{trip.get('distance_km', 0):.1f} km")
        ui.metric_card("Driving Time", f"{trip.get('duration_min', 0):.0f} min")
    with c3:
        ui.metric_card("Current Speed", f"{trip.get('current_speed_kmh', 0):.0f} km/h")
        ui.metric_card("Avg / Peak Speed", f"{trip.get('avg_speed_kmh', 0):.0f} / {trip.get('peak_speed_kmh', 0):.0f} km/h")
    c1, c2 = st.columns(2)
    with c1: ui.metric_card("Energy Used", f"{trip.get('energy_used_kwh', 0):.2f} kWh")
    with c2: ui.metric_card("Energy Recovered", f"{trip.get('energy_recovered_kwh', 0):.2f} kWh")

    # ---- Journey Timeline (chronological narrative, updates in Demo Mode) ----
    st.markdown('<div class="section-header">Journey Timeline</div>', unsafe_allow_html=True)
    steps = ai.journey_timeline_narrative(state)
    for i, step in enumerate(steps):
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-time">Step {i + 1}</div>
            <div class="timeline-text">{step}</div>
        </div>
        """, unsafe_allow_html=True)

    # ---- Recent Alerts ----
    st.markdown('<div class="section-header">Recent Alerts</div>', unsafe_allow_html=True)
    for alert in state["alerts"]:
        st.markdown(f'<div class="alert-line">⚠ {alert}</div>', unsafe_allow_html=True)

    # ---- AI Summary ----
    st.markdown('<div class="section-header">AI Summary</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ai-summary-box">🧠 {ai.driver_ai_summary(state, score_info)}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------
# Placeholders for phases 2-7
# ---------------------------------------------------------------------

def render_charging_placeholder(state: dict, score_info: dict):
    b = state["battery"]
    trip = state.get("trip", {})

    st.markdown('<div class="section-header">Charging Overview</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: ui.metric_card("Battery Percentage", f"{round(b['state_of_charge'])}%")
    with c2: ui.metric_card("Remaining Range", f"{ai.estimated_range_km(state)} km")
    with c3: ui.metric_card("Estimated Charging Time", f"{round((100 - b['state_of_charge']) * 0.6)} min to 80%")

    st.markdown('<div class="section-header">Charge Limit</div>', unsafe_allow_html=True)
    st.slider("Daily charge limit", min_value=50, max_value=100, value=80, step=5,
              key="charge_limit_slider", help="The AI recommends 80% for daily driving to protect long-term battery health.")

    st.markdown('<div class="section-header">Charging Mode</div>', unsafe_allow_html=True)
    smart = ai.smart_charging_recommendation(state)
    mode_cols = st.columns(3)
    for col, (mode_name, info) in zip(mode_cols, ai.CHARGING_MODES.items()):
        is_selected = mode_name == smart["mode"]
        with col:
            st.markdown(f"""
            <div class="mode-card {'selected' if is_selected else ''}">
                <div class="mc-icon">{info['icon']}</div>
                <div class="mc-title">{mode_name}</div>
                <div class="mc-sub">{info['sub']} · {info['rate_kw']} kW</div>
                {'<div class="mc-sub" style="color:#00d4ff;margin-top:6px;">✓ AI Recommended</div>' if is_selected else ''}
            </div>
            """, unsafe_allow_html=True)

    st.markdown(f'<div class="ai-line">🤖 <b>AI Smart Charging:</b> {smart["reason"]}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Charging Schedule</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: ui.metric_card("Optimal Window", state["charging"]["optimal_window"])
    with c2: ui.metric_card("Recommended Range", state["charging"]["recommended_soc_pct"])
    with c3: ui.metric_card("Est. Cost Tonight", f"₹{int(state['charging']['cost_estimate_inr'])}")

    st.markdown('<div class="section-header">Charging History</div>', unsafe_allow_html=True)
    history = ai.charging_history(state)
    for h in history:
        st.markdown(f"""
        <div class="timeline-item">
            <div class="timeline-time">{h['date']}</div>
            <div class="timeline-text">{h['mode']} · {h['from_pct']}% → {h['to_pct']}% · ₹{h['cost_inr']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Battery Protection &amp; Optimization</div>', unsafe_allow_html=True)
    for tip in ai.charging_optimization_tips(state):
        st.markdown(f'<div class="ai-line">🛡️ {tip}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Energy Flow</div>', unsafe_allow_html=True)
    st.markdown(ui.energy_flow_diagram(), unsafe_allow_html=True)


def render_drive_intelligence_placeholder(state: dict, score_info: dict):
    breakdown = ai.driving_score_breakdown(state)

    st.markdown('<div class="section-header">Driving Scores</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: ui.metric_card("Driving Score", f"{breakdown['driving_score']}%", color=ui.health_color(breakdown["driving_score"]))
    with c2: ui.metric_card("Eco Score", f"{breakdown['eco_score']}%", color=ui.health_color(breakdown["eco_score"]))
    with c3: ui.metric_card("Safety Score", f"{breakdown['safety_score']}%", color=ui.health_color(breakdown["safety_score"]))

    st.markdown('<div class="section-header">Driver Behaviour</div>', unsafe_allow_html=True)
    categories = ["Acceleration", "Braking", "Cornering", "Energy Efficiency"]
    values = [breakdown["acceleration"], breakdown["braking"], breakdown["cornering"], breakdown["energy_efficiency"]]
    st.plotly_chart(ui.radar_chart(categories, values, "Driving Style"), use_container_width=True, key="driver_intel_radar")

    st.markdown('<div class="section-header">AI Driving Coach</div>', unsafe_allow_html=True)
    coach = ai.driving_coach(state)
    for p in coach["positives"]:
        st.markdown(f'<div class="ai-line">✅ {p}</div>', unsafe_allow_html=True)
    for s in coach["suggestions"]:
        st.markdown(f'<div class="alert-line">💡 {s}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-header">Driving Suggestions</div>', unsafe_allow_html=True)
    for tip in ai.driving_suggestions(state):
        st.markdown(f'<div class="ai-line">🎯 {tip}</div>', unsafe_allow_html=True)


def render_smart_assist_placeholder(state: dict, score_info: dict):
    st.markdown('<div class="section-header">Smart Assist Features</div>', unsafe_allow_html=True)
    features = ai.smart_assist_features(state)
    cols = st.columns(2)
    for i, feat in enumerate(features):
        with cols[i % 2]:
            sub_bits = []
            if feat.get("health") is not None:
                sub_bits.append(f"Health {feat['health']}%")
            if feat.get("confidence") is not None:
                sub_bits.append(f"Confidence {feat['confidence']}%")
            if feat.get("desc"):
                sub_bits.append(feat["desc"])
            st.markdown(f"""
            <div class="toggle-card">
                <div class="tc-title">{feat['name']} · <span style="color:{ui.COLOR_GOOD if feat['status']=='Active' else ui.COLOR_WARN};">{feat['status']}</span></div>
                <div class="tc-sub">{' · '.join(sub_bits)}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">Smart Lane Transition Profile</div>', unsafe_allow_html=True)
    st.select_slider("Lane change style", options=ai.LANE_CHANGE_PROFILES, value="Balanced", key="lane_change_profile")

    st.markdown('<div class="section-header">Adaptive Cruise Settings</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.slider("Adaptive Cruise Speed (km/h)", 20, 130, 80, key="cruise_speed")
    with c2:
        st.select_slider("Following Distance", options=["Close", "Medium", "Far"], value="Medium", key="following_distance")


def render_comfort_placeholder(state: dict, score_info: dict):
    rec = ai.comfort_recommendation(state)

    st.markdown('<div class="section-header">AI Climate Control</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1: ui.metric_card("Cabin Temperature Target", f"{rec['cabin_target_c']}°C")
    with c2: ui.metric_card("Climate Mode", rec["climate_mode"])
    with c3: ui.metric_card("Cabin Air Quality", rec["air_quality"])

    st.markdown('<div class="section-header">Seat &amp; Cabin Comfort</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.toggle("Ventilated Seats", value="Ventilated" in rec["seats"], key="ventilated_seats")
        st.toggle("Heated Seats", value="Heated" in rec["seats"], key="heated_seats")
        st.toggle("Steering Wheel Heating", value=rec["climate_mode"] == "Heating", key="steering_heat")
    with c2:
        st.toggle("Auto Defogging", value=True, key="auto_defog")
        st.toggle("Interior Ambient Lighting", value=True, key="ambient_lighting")
        st.select_slider("Interior Lighting Brightness", options=["Low", "Medium", "High"], value="Medium", key="lighting_brightness")

    st.markdown('<div class="section-header">AI Cabin Comfort Optimization</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="ai-line">🤖 {rec["note"]}</div>', unsafe_allow_html=True)


def render_vehicle_care_placeholder(state: dict, score_info: dict):
    st.markdown('<div class="section-header">AI Vehicle Inspection</div>', unsafe_allow_html=True)
    issues = ai.vehicle_care_diagnostics(state)

    if not issues:
        st.markdown('<div class="ai-line">✅ No issues detected. Your vehicle passed its latest AI inspection.</div>', unsafe_allow_html=True)
        return

    sev_class = {"Minor": "sev-minor", "Moderate": "sev-moderate", "Severe": "sev-severe"}
    for issue in issues:
        st.markdown(f"""
        <div class="issue-card">
            <div class="issue-title">{issue['issue']} &nbsp;
                <span class="severity-badge {sev_class[issue['severity']]}">{issue['severity']}</span>
            </div>
            <div class="issue-row"><b>Affected Component:</b> {issue['component']}</div>
            <div class="issue-row"><b>AI Diagnosis:</b> {issue['diagnosis']}</div>
            <div class="issue-row"><b>Possible Cause:</b> {issue['cause']}</div>
            <div class="issue-row"><b>Can Driver Fix It?</b> {"Yes" if issue['driver_fixable'] else "No — professional service recommended"}</div>
            <div class="issue-row"><b>Recommended Action:</b> {issue['action']}</div>
            <div class="issue-row"><b>Estimated Repair Time:</b> {issue['repair_time_min']} minutes</div>
            <div class="issue-row"><b>Estimated Repair Cost:</b> {issue['repair_cost_inr']}</div>
        </div>
        """, unsafe_allow_html=True)


def render_settings_placeholder(state: dict, score_info: dict):
    st.markdown('<div class="section-header">Driver &amp; Preferences</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        st.selectbox("Driver Profile", ["Driver 1 (Primary)", "Driver 2", "Guest"], key="driver_profile")
        st.selectbox("Theme", ["Dark (Recommended)", "Light"], key="theme_setting")
        st.selectbox("Language", ["English", "Tamil", "Hindi"], key="language_setting")
    with c2:
        st.selectbox("Units", ["Kilometers / Celsius", "Miles / Fahrenheit"], key="units_setting")
        st.toggle("Notifications", value=True, key="notifications_setting")
        st.toggle("Demo Mode", value=st.session_state.get("demo_mode", False), key="settings_demo_mode_mirror",
                   help="Use the Demo Mode toggle in the sidebar to control live simulation.", disabled=True)

    st.markdown('<div class="section-header">AI &amp; Privacy</div>', unsafe_allow_html=True)
    st.toggle("AI Personalization", value=True, key="ai_personalization")
    st.toggle("Share anonymized data to improve AI (stays local in this demo)", value=False, key="privacy_sharing")

    st.markdown('<div class="section-header">Edge AI Status</div>', unsafe_allow_html=True)
    status = ai.edge_ai_status(state)
    for label, value in status.items():
        st.markdown(f"""
        <div class="settings-card">
            <div class="sc-label">{label.replace('_', ' ').title()}</div>
            <div class="sc-value">{value}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<div class="section-header">System</div>', unsafe_allow_html=True)
    st.button("Check for System Updates", use_container_width=True, key="check_updates_btn")
    st.caption("Version 1.0.0 · Edge AI Vehicle Intelligence Platform")

"""
dashboard.py
------------
Edge AI Vehicle Intelligence Platform - a full multi-system dashboard
built on top of the original Battery Health Predictor. Everything runs
locally: the battery numbers come from the real trained Random Forest
model; every other subsystem (motor, brakes, tires, suspension, driver
behaviour, environment, traffic, ADAS, predictive maintenance, charging)
is realistic simulated data, generated in utils/vehicle_simulation.py,
since real telemetry for those systems isn't available in this project.

Run:
    streamlit run app/dashboard.py
"""

import os
import sys
import time

import pandas as pd
import streamlit as st

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
from utils import ui_components as ui
from utils import vehicle_simulation as sim
from utils import ai_engine as ai
from utils import driver_view
from utils import background_theme
from utils import liquid_glass

st.set_page_config(
    page_title="Edge AI Vehicle Intelligence Platform",
    page_icon="🚗",
    layout="wide",
)

ui.inject_custom_css()
background_theme.inject()


# ---------------------------------------------------------------------
# State bootstrap
# ---------------------------------------------------------------------

if "vehicle_state" not in st.session_state:
    with st.spinner("Initializing Edge AI Vehicle Intelligence Platform..."):
        st.session_state.vehicle_state = sim.init_vehicle_state()

if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False

if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

if "view" not in st.session_state:
    st.session_state.view = "driver"

state = st.session_state.vehicle_state


# ---------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------

st.sidebar.title("🚗 Vehicle Intelligence")
st.sidebar.caption("Edge AI · 100% local processing")

st.sidebar.markdown("---")
demo_toggle = st.sidebar.toggle("Demo Mode (live simulation)", value=st.session_state.demo_mode)
st.session_state.demo_mode = demo_toggle

if st.sidebar.button("🔄 Refresh Analysis", use_container_width=True):
    sim.tick(state)
    st.session_state.just_ticked = True
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(f"Last AI analysis: {state['last_analysis_time'].strftime('%H:%M:%S')}")
st.sidebar.caption("Vehicle: Demo EV · Model Year 2024")


# ---------------------------------------------------------------------
# Top summary bar (always visible)
# ---------------------------------------------------------------------

score_info = ai.overall_vehicle_score(state)

nav_title_col, nav_driver_col, nav_insights_col = st.columns([4, 1, 1])
with nav_title_col:
    st.markdown("## Vehicle Intelligence")
with nav_driver_col:
    if st.button("🚘 Driver View", use_container_width=True,
                 type="primary" if st.session_state.view == "driver" else "secondary"):
        st.session_state.view = "driver"
        st.rerun()
with nav_insights_col:
    if st.button("🔧 Insights View", use_container_width=True,
                 type="primary" if st.session_state.view == "insights" else "secondary"):
        st.session_state.view = "insights"
        st.rerun()

if st.session_state.view == "driver":
    driver_view.render(state, score_info)

else:
    top1, top2, top3, top4, top5 = st.columns(5)
    with top1:
        ui.metric_card("Overall Vehicle Health", f"{score_info['overall']}%", score_info["label"],
                        color=ui.health_color(score_info["overall"]))
    with top2:
        ui.metric_card("AI Confidence", f"{score_info['confidence']}%", "Model certainty")
    with top3:
        ui.metric_card("Vehicle Risk Score", f"{score_info['risk_score']}%", "Lower is better",
                        color=ui.health_color(100 - score_info["risk_score"]))
    with top4:
        ui.metric_card("Efficiency Score", f"{score_info['efficiency_score']}%", "Energy + motor efficiency")
    with top5:
        ui.metric_card("Last AI Analysis", state["last_analysis_time"].strftime("%H:%M:%S"), "Auto-updates in Demo Mode")

    st.markdown("")


    # ---------------------------------------------------------------------
    # Tabs
    # ---------------------------------------------------------------------

    tabs = st.tabs([
        "🧭 Overview & Digital Twin",
        "🔋 Battery Intelligence",
        "⚙️ Motor & Chassis",
        "🧑 Driver & Trips",
        "🌦️ Environment & Traffic",
        "🛡️ ADAS",
        "🔧 Predictive Maintenance",
        "⚡ Charging Intelligence",
        "🤖 AI Insights & Assistant",
        "📈 Historical Trends",
    ])

    # ===================== TAB 1: Overview & Digital Twin =====================
    with tabs[0]:
        st.markdown('<div class="section-header">Digital Twin - Component Health Map</div>', unsafe_allow_html=True)

        components = {
            "Battery": state["battery"]["health_percent"],
            "Motor": state["motor"]["health_pct"],
            "Brakes": 100 - state["brakes"]["pad_wear_pct"],
            "Tires": 100 - (sum(state["tires"]["wear_pct"]) / 4),
            "Suspension": state["suspension"]["shock_health_pct"],
        }

        cols = st.columns(len(components))
        for col, (name, health) in zip(cols, components.items()):
            with col:
                color = ui.health_color(health)
                st.markdown(f"""
                <div class="metric-card" style="text-align:center;">
                    <div style="font-size:2rem;">{'🟢' if health>=80 else '🟡' if health>=60 else '🔴'}</div>
                    <div class="metric-title">{name}</div>
                    <div class="metric-value" style="color:{color};">{round(health,1)}%</div>
                </div>
                """, unsafe_allow_html=True)

        selected = st.radio("Inspect a component:", list(components.keys()), horizontal=True)
        st.info(f"**{selected}** health: {round(components[selected],1)}% — "
                f"{'Healthy, no action needed.' if components[selected]>=80 else 'Monitor closely, minor degradation detected.' if components[selected]>=60 else 'Critical - schedule service soon.'}")

        st.markdown('<div class="section-header">Quick Snapshot</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.plotly_chart(ui.gauge_chart(state["battery"]["health_percent"], "Battery Health"), use_container_width=True, key="gauge_overview_battery")
        with c2:
            st.plotly_chart(ui.gauge_chart(state["motor"]["health_pct"], "Motor Health"), use_container_width=True, key="gauge_overview_motor")
        with c3:
            st.plotly_chart(ui.gauge_chart(state["driver"]["safety_score"], "Driver Safety Score"), use_container_width=True, key="gauge_overview_driver")

    # ===================== TAB 2: Battery Intelligence =====================
    with tabs[1]:
        b = state["battery"]
        st.markdown('<div class="section-header">Battery Core Metrics</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.plotly_chart(ui.gauge_chart(b["health_percent"], "Battery Health"), use_container_width=True, key="gauge_battery_tab")
        with c2:
            ui.metric_card("State of Health (SOH)", f"{b['soh']}%")
            ui.metric_card("State of Charge (SOC)", f"{b['state_of_charge']:.1f}%")
        with c3:
            ui.metric_card("State of Power (SOP)", f"{b['sop_kw']} kW")
            ui.metric_card("Remaining Cycles", f"{b['remaining_cycles']}")
        with c4:
            ui.metric_card("Internal Resistance", f"{b['internal_resistance']} mΩ")
            ui.metric_card("Battery Temperature", f"{b['temperature']:.1f} °C")

        st.markdown('<div class="section-header">Efficiency, Stress & Aging</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Charging Efficiency", f"{b['charging_efficiency']}%")
        with c2: ui.metric_card("Discharging Efficiency", f"{b['discharging_efficiency']}%")
        with c3: ui.metric_card("Fast Charge Freq.", f"{b['fast_charge_freq_per_week']}/week")
        with c4: ui.metric_card("Battery Stress Index", f"{b['stress_index']}", color=ui.health_color(100 - b["stress_index"]))

        c1, c2, c3 = st.columns(3)
        with c1: ui.metric_card("Cell Temp. Spread", f"{b['cell_temp_spread_c']} °C")
        with c2: ui.metric_card("Thermal Risk", b["thermal_risk"])
        with c3: ui.metric_card("Est. Replacement", f"~{b['replacement_eta_months']} months")

        st.markdown('<div class="section-header">Predicted Degradation Curve</div>', unsafe_allow_html=True)
        months = list(range(0, 61, 6))
        projected = [max(50, b["health_percent"] - (m * 0.35)) for m in months]
        st.plotly_chart(ui.line_trend(months, projected, "Battery Health Projection (next 5 years)", "Health %"),
                         use_container_width=True, key="chart_battery_degradation")

        st.markdown('<div class="section-header">AI Explanation</div>', unsafe_allow_html=True)
        st.markdown(ui.health_badge_html("Battery Status", b["health_percent"]), unsafe_allow_html=True)
        for f in b["factors"]:
            st.markdown(f'<div class="ai-line">⚠ {f}</div>', unsafe_allow_html=True)
        for r in b["recommendations"]:
            st.markdown(f'<div class="ai-line">💡 {r}</div>', unsafe_allow_html=True)

    # ===================== TAB 3: Motor & Chassis =====================
    with tabs[2]:
        m, br, tires, sus = state["motor"], state["brakes"], state["tires"], state["suspension"]

        st.markdown('<div class="section-header">Motor Health</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.plotly_chart(ui.gauge_chart(m["health_pct"], "Motor Health"), use_container_width=True, key="gauge_motor_tab")
        with c2:
            ui.metric_card("Motor Temperature", f"{m['temperature_c']} °C")
            ui.metric_card("Motor RPM", f"{m['rpm']}")
        with c3:
            ui.metric_card("Torque", f"{m['torque_nm']} Nm")
            ui.metric_card("Efficiency", f"{m['efficiency_pct']}%")
        with c4:
            ui.metric_card("Bearing Health", f"{m['bearing_health_pct']}%")
            ui.metric_card("Vibration", f"{m['vibration_mm_s']} mm/s")
        st.caption(f"Cooling system status: **{m['cooling_status']}** · Estimated remaining life: **{m['remaining_life_pct']}%**")
        st.info("Maintenance recommendation: " + ("Inspect motor cooling and bearings soon." if m["health_pct"] < 85 else "No action required."))

        st.markdown('<div class="section-header">Brake System Intelligence</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Pad Wear", f"{br['pad_wear_pct']}%", color=ui.health_color(100 - br["pad_wear_pct"]))
        with c2: ui.metric_card("Disc Wear", f"{br['disc_wear_pct']}%")
        with c3: ui.metric_card("Brake Temperature", f"{br['temperature_c']} °C")
        with c4: ui.metric_card("Fluid Status", f"{br['fluid_status_pct']}%")
        c1, c2, c3 = st.columns(3)
        with c1: ui.metric_card("Braking Efficiency", f"{br['efficiency_pct']}%")
        with c2: ui.metric_card("Regen Braking Efficiency", f"{br['regen_efficiency_pct']}%")
        with c3: ui.metric_card("Service Distance", f"{br['service_distance_km']} km")
        st.info("AI suggestion: " + ("Schedule brake inspection soon." if br["pad_wear_pct"] > 45 else "Brakes performing normally."))

        st.markdown('<div class="section-header">Tire Intelligence</div>', unsafe_allow_html=True)
        tire_df = pd.DataFrame({
            "Position": ["Front-Left", "Front-Right", "Rear-Left", "Rear-Right"],
            "Pressure (PSI)": tires["pressure_psi"],
            "Temperature (°C)": tires["temperature_c"],
            "Wear (%)": tires["wear_pct"],
        })
        st.dataframe(tire_df, hide_index=True, use_container_width=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui.metric_card("Alignment", tires["alignment_status"])
        with c2: ui.metric_card("Rotation Due", f"{tires['rotation_due_km']} km")
        with c3: ui.metric_card("Remaining Life", f"{tires['remaining_life_km']} km")

        st.markdown('<div class="section-header">Suspension Health</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Shock Absorber Health", f"{sus['shock_health_pct']}%")
        with c2: ui.metric_card("Vibration Score", f"{sus['vibration_score']}")
        with c3: ui.metric_card("Ride Comfort Score", f"{sus['ride_comfort_score']}%")
        with c4: ui.metric_card("Road Impact Events/wk", f"{sus['road_impact_events_week']}")

    # ===================== TAB 4: Driver & Trips =====================
    with tabs[3]:
        d, daily = state["driver"], state["daily"]
        st.markdown('<div class="section-header">AI Driver Profile</div>', unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            categories = ["Acceleration", "Braking", "Cornering", "Steering", "Speed Consistency"]
            values = [d["acceleration_aggressiveness"], d["braking_style"], d["cornering"],
                      d["steering_smoothness"], d["speed_consistency"]]
            st.plotly_chart(ui.radar_chart(categories, values, "Driving Style Profile"), use_container_width=True, key="radar_driver_style")
        with c2:
            rating = ("Aggressive Driver" if d["acceleration_aggressiveness"] > 65 else
                      "Eco Driver" if d["eco_score"] > 75 else
                      "Conservative Driver" if d["braking_style"] < 35 else "Excellent Driver")
            ui.metric_card("Overall Driving Rating", rating)
            ui.metric_card("Safety Score", f"{d['safety_score']}%")
            ui.metric_card("Eco Driving Score", f"{d['eco_score']}%")
            ui.metric_card("Driving Confidence Score", f"{d['confidence_score']}%")

        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Reaction Time", f"{d['reaction_time_ms']} ms")
        with c2: ui.metric_card("Night Driving", f"{d['night_driving_pct']}%")
        with c3: ui.metric_card("Rain Driving", f"{d['rain_driving_pct']}%")
        with c4: ui.metric_card("Speed Consistency", f"{d['speed_consistency']}%")

        st.markdown(f'<div class="ai-line">🧠 Aggressive acceleration and hard braking accelerate battery degradation and increase brake wear — this driver\'s current profile suggests '
                    f'{"above-average" if d["acceleration_aggressiveness"]>60 else "below-average"} component stress from driving style.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Daily Driving Pattern Analysis</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Most Frequent Route", daily["most_frequent_route"])
        with c2: ui.metric_card("Daily Commute", f"{daily['commute_distance_km']} km")
        with c3: ui.metric_card("Avg Driving Time", f"{daily['avg_driving_time_min']} min")
        with c4: ui.metric_card("Departure / Arrival", f"{daily['preferred_departure']} / {daily['preferred_arrival']}")

        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Weekly Distance", f"{daily['weekly_distance_km']} km")
        with c2: ui.metric_card("Monthly Distance", f"{daily['monthly_distance_km']} km")
        with c3: ui.metric_card("Avg / Peak Speed", f"{daily['avg_speed_kmh']} / {daily['peak_speed_kmh']} km/h")
        with c4: ui.metric_card("Idle Time", f"{daily['idle_time_pct']}%")

        st.plotly_chart(ui.bar_compare(["City Driving", "Highway Driving"],
                                        [daily["city_pct"], 100 - daily["city_pct"]],
                                        "Road Type Distribution"), use_container_width=True, key="bar_road_type")
        st.caption("Most visited locations: " + ", ".join(daily["most_visited"]))

    # ===================== TAB 5: Environment & Traffic =====================
    with tabs[4]:
        env, tr = state["environment"], state["traffic"]
        st.markdown('<div class="section-header">Environmental Intelligence</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            ui.metric_card("City", env["city"])
            ui.metric_card("Temperature", f"{env['temperature_c']} °C")
        with c2:
            ui.metric_card("Humidity", f"{env['humidity_pct']}%")
            ui.metric_card("Air Quality Index", f"{env['air_quality_index']}")
        with c3:
            ui.metric_card("Weather", env["weather"])
            ui.metric_card("Road Surface", env["road_surface"])
        with c4:
            ui.metric_card("Wind", f"{env['wind_kmh']} km/h")
            ui.metric_card("Elevation", f"{env['elevation_m']} m")

        impact = round((env["temperature_c"] - 25) * 0.3, 1) if env["temperature_c"] > 25 else 0
        if impact > 0:
            st.markdown(f'<div class="ai-line">🌡️ High ambient temperature reduced battery efficiency by approximately {impact}%.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="ai-line">🌡️ Ambient temperature is within the optimal range for battery efficiency.</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Traffic Intelligence</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: ui.metric_card("Traffic Density", f"{tr['density_pct']}%")
        with c2: ui.metric_card("Congestion Score", f"{tr['congestion_score']}%")
        with c3: ui.metric_card("Avg Delay", f"{tr['avg_delay_min']} min")
        with c4: ui.metric_card("Avg Stop Time", f"{tr['avg_stop_time_min']} min")

        st.caption("Frequent traffic zones: " + ", ".join(tr["frequent_zones"]))
        st.markdown(f'<div class="ai-line">🚦 Energy lost in traffic today: approximately {tr["energy_lost_pct"]}%. '
                    f'Consider an alternate route to save battery.</div>', unsafe_allow_html=True)

    # ===================== TAB 6: ADAS =====================
    with tabs[5]:
        st.markdown('<div class="section-header">Advanced Driver Assistance Systems</div>', unsafe_allow_html=True)
        adas = state["adas"]
        cols = st.columns(3)
        for i, (name, info) in enumerate(adas.items()):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">{name}</div>
                    <div class="metric-value" style="font-size:1.2rem;color:{ui.health_color(info['health'])};">{info['status']}</div>
                    <div class="metric-sub">Health: {info['health']}% · Confidence: {info['confidence']}%</div>
                </div>
                """, unsafe_allow_html=True)

    # ===================== TAB 7: Predictive Maintenance =====================
    with tabs[6]:
        st.markdown('<div class="section-header">Predictive Maintenance - All Components</div>', unsafe_allow_html=True)
        maint = state.get("maintenance", {})
        rows = []
        for name, info in maint.items():
            rows.append({
                "Component": name,
                "Health %": info["health"],
                "Failure Risk %": info["failure_risk"],
                "Remaining Life (days)": info["remaining_life_days"],
                "Service Date": info["service_date"],
                "Priority": info["priority"],
                "Cost Est. (₹)": info["cost_estimate_inr"],
                "Recommendation": info["recommendation"],
            })
        maint_df = pd.DataFrame(rows).sort_values("Failure Risk %", ascending=False)
        st.dataframe(maint_df, hide_index=True, use_container_width=True)

        high_priority = maint_df[maint_df["Priority"] == "High"]
        if not high_priority.empty:
            for _, row in high_priority.iterrows():
                st.markdown(f'<div class="alert-line">🔧 {row["Component"]}: {row["recommendation"] if "recommendation" in row else row["Recommendation"]} '
                            f'(Failure risk {row["Failure Risk %"]}%)</div>', unsafe_allow_html=True)

    # ===================== TAB 8: Charging Intelligence =====================
    with tabs[7]:
        ch = state["charging"]
        st.markdown('<div class="section-header">Charging Intelligence</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: ui.metric_card("Optimal Charging Window", ch["optimal_window"])
        with c2: ui.metric_card("Recommended SOC Range", ch["recommended_soc_pct"])
        with c3: ui.metric_card("Est. Charging Cost", f"₹{ch['cost_estimate_inr']}")

        c1, c2 = st.columns(2)
        with c1: ui.metric_card("Fast Charging Guidance", ch["fast_charge_recommendation"])
        with c2: ui.metric_card("Slow Charging Guidance", ch["slow_charge_recommendation"])

        ui.metric_card("Battery Stress from Charging", f"{ch['stress_from_charging']}%",
                        color=ui.health_color(100 - ch["stress_from_charging"]))

        st.markdown('<div class="section-header">AI Charging Suggestions</div>', unsafe_allow_html=True)
        st.markdown('<div class="ai-line">🔌 Charge between 20% and 80% for daily use to reduce long-term degradation.</div>', unsafe_allow_html=True)
        st.markdown('<div class="ai-line">🔌 Avoid charging immediately after aggressive driving sessions - let the battery cool first.</div>', unsafe_allow_html=True)

    # ===================== TAB 9: AI Insights & Assistant =====================
    with tabs[8]:
        st.markdown('<div class="section-header">AI Recommendations</div>', unsafe_allow_html=True)
        for rec in ai.generate_recommendations(state):
            st.markdown(f'<div class="ai-line">💡 {rec}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Alerts Panel</div>', unsafe_allow_html=True)
        for alert in state["alerts"]:
            st.markdown(f'<div class="alert-line">⚠ {alert}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">Explainable AI - Overall Score Breakdown</div>', unsafe_allow_html=True)
        for line in ai.explain_overall_score(state, score_info):
            st.markdown(f'<div class="ai-line">🧠 {line}</div>', unsafe_allow_html=True)

        st.markdown('<div class="section-header">AI Vehicle Assistant</div>', unsafe_allow_html=True)
        sample_qs = ["How is my vehicle?", "When should I service my brakes?",
                     "How can I increase battery life?", "Why did my efficiency decrease?"]
        qcols = st.columns(4)
        clicked_question = None
        for i, q in enumerate(sample_qs):
            if qcols[i].button(q, use_container_width=True, key=f"sample_q_{i}"):
                clicked_question = q

        user_question = st.chat_input("Ask the AI Vehicle Assistant...")
        final_question = user_question or clicked_question

        if final_question:
            answer = ai.assistant_answer(final_question, state, score_info)
            st.session_state.chat_log.append((final_question, answer))

        for q, a in reversed(st.session_state.chat_log[-6:]):
            with st.chat_message("user"):
                st.write(q)
            with st.chat_message("assistant"):
                st.write(a)

    # ===================== TAB 10: Historical Trends =====================
    with tabs[9]:
        h = state["history"]
        st.markdown('<div class="section-header">Historical Trends</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.plotly_chart(ui.line_trend(h["t"], h["battery_health"], "Battery Health vs Time", "Health %"), use_container_width=True, key="trend_battery_health")
            st.plotly_chart(ui.line_trend(h["t"], h["brake_wear"], "Brake Wear vs Time", "Wear %", color="#f39c12"), use_container_width=True, key="trend_brake_wear")
            st.plotly_chart(ui.line_trend(h["t"], h["driving_score"], "Driving Score vs Time", "Score", color="#9b59b6"), use_container_width=True, key="trend_driving_score")
            st.plotly_chart(ui.line_trend(h["t"], h["daily_distance"], "Daily Distance vs Time", "km", color="#1abc9c"), use_container_width=True, key="trend_daily_distance")
            st.plotly_chart(ui.line_trend(h["t"], h["traffic_impact"], "Traffic Energy Impact vs Time", "% energy lost", color="#e74c3c"), use_container_width=True, key="trend_traffic_impact")
        with c2:
            st.plotly_chart(ui.line_trend(h["t"], h["motor_health"], "Motor Health vs Time", "Health %", color="#00d4ff"), use_container_width=True, key="trend_motor_health")
            st.plotly_chart(ui.line_trend(h["t"], h["energy_consumption"], "Energy Consumption vs Time", "kWh/100km", color="#e67e22"), use_container_width=True, key="trend_energy_consumption")
            st.plotly_chart(ui.line_trend(h["t"], h["efficiency"], "Efficiency Trend", "%", color="#2ecc71"), use_container_width=True, key="trend_efficiency")
            st.plotly_chart(ui.line_trend(h["t"], h["temperature"], "Temperature History", "°C", color="#f1c40f"), use_container_width=True, key="trend_temperature")


# ---------------------------------------------------------------------
# Re-assert the layered road background
# -----------------------------------------------------------------------
# Driver View's shell (utils/driver_shell.py) calls
# ui.dynamic_theme_overlay_css() to apply its subtle time-of-day/weather
# tint, and that rule also sets .stApp's background with !important —
# so it would otherwise win the cascade over our first call at the top
# of this file and silently replace the road photo with the old flat
# gradient. Calling background_theme.inject() again here, last, makes
# sure the road photo (plus its overlay/vignette/tint layers) is always
# what actually renders, in both Driver View and Insights View.
# ---------------------------------------------------------------------
background_theme.inject()

# ---------------------------------------------------------------------
# Liquid Glass pointer interaction
# -----------------------------------------------------------------------
# Invisible (height=0) component — see utils/liquid_glass.py. Reaches
# into the parent page to drive the cursor-reactive internal specular
# highlight that background_theme.py's CSS reads via the --mx/--my
# custom properties. No parallax or tilt: the layout itself never
# moves. Called once, after the CSS it depends on is in place.
# ---------------------------------------------------------------------
liquid_glass.inject_pointer_interaction()


# ---------------------------------------------------------------------
# Demo mode auto-refresh loop
# -----------------------------------------------------------------------
# Both views now run on native Streamlit widgets fed by sim.tick(), so
# both need this rerun loop to keep their live values moving during Demo
# Mode. (Previously Driver View had its own independent client-side JS
# simulation in utils/vehicle_experience.py and was deliberately excluded
# here; that component has been retired in favor of the new nav-rail
# Driver View, which reads the same backend state as Insights View.)
# ---------------------------------------------------------------------

if st.session_state.demo_mode:
    with st.spinner("AI analyzing live sensor data..."):
        time.sleep(2.5)
    sim.tick(state)
    st.session_state.just_ticked = True
    st.rerun()

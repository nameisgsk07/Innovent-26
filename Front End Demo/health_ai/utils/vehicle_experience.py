"""
vehicle_experience.py
----------------------
The centerpiece of the redesigned Driver View: a single self-contained
HTML/CSS/JS component (rendered via streamlit.components.v1.html) that
implements the "premium EV infotainment" experience — an interactive
vehicle visualization, animated journey stats, a mini route map, a
rotating AI driving-companion, and an "AI analyzing..." sequence.

WHY A COMPONENT INSTEAD OF PLAIN STREAMLIT WIDGETS
Streamlit's execution model reruns the whole Python script on every
interaction, which is fine for data widgets but can't produce the fluid,
constantly-alive feel (ticking clock, moving wheels, animated counters,
a dot gliding along a route) that this brief asks for — every one of
those reruns would flicker the entire page. So this module hands the
browser one HTML/CSS/JS payload, seeded with the current backend state
as JSON, and lets it run its own animation loop and click handling
entirely inside the iframe. No Streamlit rerun is needed for any of the
animation, clicking a component hotspot, or the rotating AI messages —
only switching between Driver View and Insights View touches Streamlit
itself.

LIMITATIONS (worth being upfront about)
- This is a 2D SVG vehicle, not true 3D — matches the brief's own
  fallback ("2D is acceptable if true 3D is impractical in Streamlit").
- The live driving simulation inside Demo Mode runs independently of the
  backend `vehicle_simulation.tick()` used by Insights View, since the
  two run on different clocks (client-side JS vs. server-side Streamlit
  reruns). Both are seeded from the same underlying state so they stay
  broadly consistent, but they are not frame-synchronized.
"""

import json
from datetime import datetime

import streamlit.components.v1 as components

from utils import ai_engine as ai


def _greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    elif hour < 18:
        return "Good afternoon"
    return "Good evening"


def _build_payload(state: dict, score_info: dict) -> dict:
    driver = state["driver"]
    return {
        "greeting": _greeting(),
        "overall": score_info["overall"],
        "condition": ai.condition_word(score_info["overall"]),
        "rangeKm": ai.estimated_range_km(state),
        "soc": round(state["battery"]["state_of_charge"], 1),
        "components": ai.component_health_map(state),
        "journey": ai.todays_journey(state),
        "driver": {
            "acceleration": driver["acceleration_aggressiveness"],
            "braking": driver["braking_style"],
            "cornering": driver["cornering"],
            "steering": driver["steering_smoothness"],
            "speedConsistency": driver["speed_consistency"],
            "ecoScore": driver["eco_score"],
            "safetyScore": driver["safety_score"],
        },
        "weather": state["environment"]["weather"],
        "temperature": round(state["environment"]["temperature_c"], 1),
        "traffic": state["environment"]["traffic_level"],
        "recommendations": ai.smart_recommendations_driver(state),
        "peakSpeed": state["daily"]["peak_speed_kmh"],
        "avgSpeed": state["daily"]["avg_speed_kmh"],
    }


_HTML_TEMPLATE = r"""
<div id="evroot">
  <style>
    #evroot {
      --good: #2ecc71; --warn: #f39c12; --bad: #e74c3c; --accent: #00d4ff;
      --glass: rgba(23,27,36,0.55); --text: #f2f4f8; --muted: #93a0b8;
      font-family: -apple-system, "Segoe UI", Roboto, Arial, sans-serif;
      color: var(--text);
      position: relative;
      padding: 6px 4px 16px 4px;
    }
    #evroot * { box-sizing: border-box; }
    @keyframes fadeIn { from { opacity:0; transform: translateY(8px);} to {opacity:1; transform: translateY(0);} }
    @keyframes pulseGlow { 0%,100% { opacity:0.55; } 50% { opacity:1; } }
    @keyframes spin { from { transform: rotate(0deg);} to { transform: rotate(360deg);} }
    @keyframes dash { to { stroke-dashoffset: -40; } }
    .fadein { animation: fadeIn .5s ease both; }

    .topbar {
      display:flex; justify-content:space-between; align-items:center;
      padding: 4px 10px 14px 10px;
    }
    .greeting { font-size: 1.3rem; font-weight: 700; }
    .greeting .sub { display:block; font-size:0.82rem; color: var(--muted); font-weight: 400; margin-top:2px;}
    .status-icons { display:flex; gap:16px; align-items:center; font-size:0.85rem; color: var(--muted);}
    .status-icons span.live-dot { color: var(--good); animation: pulseGlow 2s infinite; }

    .companion-bar {
      background: var(--glass); backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
      padding: 12px 18px; margin: 6px 10px 18px 10px;
      font-size: 0.98rem; min-height: 26px;
      transition: opacity .4s ease;
    }

    .stage {
      position: relative;
      display:flex; justify-content:center; align-items:center;
      padding: 10px 0 6px 0;
      min-height: 300px;
    }
    .ring {
      position:absolute; width: 320px; height: 320px; border-radius: 50%;
      background: radial-gradient(circle, rgba(0,212,255,0.08) 0%, rgba(0,212,255,0) 70%);
    }
    .hotspot {
      position:absolute; width: 20px; height: 20px; border-radius: 50%;
      border: 2px solid rgba(255,255,255,0.6); cursor: pointer;
      box-shadow: 0 0 12px currentColor; transition: transform .2s ease;
      animation: pulseGlow 2.4s infinite;
    }
    .hotspot:hover { transform: scale(1.35); }
    .hotspot.selected { transform: scale(1.5); border-color: #fff; }
    .hotspot-label {
      position:absolute; font-size: 0.68rem; color: var(--muted);
      white-space:nowrap; transform: translate(-50%, 4px);
    }

    #wheelFL, #wheelFR, #wheelRL, #wheelRR { transform-origin: center; animation: spin 1.4s linear infinite; animation-play-state: paused; }
    .headlight { animation: pulseGlow 3s infinite; }
    .brakeflash { opacity: 0; transition: opacity .15s ease; }
    .charge-pulse { opacity: 0; }
    .powerflow { stroke-dasharray: 6 6; animation: dash 1s linear infinite; opacity:0; }

    .detail-panel {
      background: var(--glass); backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,0.1); border-radius: 18px;
      padding: 16px 20px; margin: 4px 10px 18px 10px;
      display:none;
    }
    .detail-title { font-size: 1.05rem; font-weight: 700; margin-bottom:2px; }
    .detail-status { font-size: 0.85rem; margin-bottom: 10px; }
    .spark { display:flex; align-items:flex-end; gap:3px; height: 30px; margin: 8px 0; }
    .spark div { width: 8px; border-radius: 2px 2px 0 0; background: var(--accent); opacity: 0.8; }
    .detail-row { font-size: 0.88rem; color: var(--muted); margin-top: 4px; }

    .journey-grid {
      display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
      margin: 6px 10px 18px 10px;
    }
    @media (max-width: 700px) { .journey-grid { grid-template-columns: repeat(2, 1fr); } }
    .jcard {
      background: var(--glass); backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
      padding: 12px 14px; text-align:center;
    }
    .jcard .jlabel { font-size: 0.68rem; text-transform: uppercase; letter-spacing:.05em; color: var(--muted); }
    .jcard .jvalue { font-size: 1.3rem; font-weight: 700; margin-top: 4px; }

    .route-wrap {
      background: var(--glass); backdrop-filter: blur(14px);
      border: 1px solid rgba(255,255,255,0.08); border-radius: 18px;
      padding: 14px 18px; margin: 4px 10px 18px 10px;
    }
    .route-head { display:flex; justify-content:space-between; font-size: 0.85rem; color: var(--muted); margin-bottom: 6px;}
    .analyzing {
      text-align:center; font-size: 0.85rem; color: var(--accent);
      min-height: 20px; margin: 2px 10px 4px 10px; transition: opacity .3s ease;
    }
  </style>

  <div class="topbar fadein">
    <div class="greeting">__GREETING__, driver.
      <span class="sub">Vehicle condition: __CONDITION__ · __SOC__% charged · __RANGE__ km range</span>
    </div>
    <div class="status-icons">
      <span id="clock">--:--</span>
      <span id="weatherIcon">☁️ __WEATHER__ · __TEMP__°C</span>
      <span class="live-dot">●</span> <span>Edge AI Live</span>
    </div>
  </div>

  <div class="companion-bar fadein" id="companionBar">Welcome back. Your vehicle is ready.</div>

  <div class="analyzing" id="analyzingLine"></div>

  <div class="stage fadein">
    <div class="ring"></div>
    <svg viewBox="0 0 400 220" width="100%" height="260" style="max-width:460px;">
      <ellipse cx="200" cy="205" rx="150" ry="10" fill="rgba(0,0,0,0.35)"/>
      <!-- body -->
      <rect x="60" y="90" width="280" height="70" rx="26" fill="#232a38" stroke="rgba(255,255,255,0.08)"/>
      <rect x="110" y="55" width="180" height="50" rx="20" fill="#2b3344" stroke="rgba(255,255,255,0.1)"/>
      <rect x="125" y="62" width="65" height="30" rx="6" fill="#0e1117" opacity="0.6"/>
      <rect x="210" y="62" width="65" height="30" rx="6" fill="#0e1117" opacity="0.6"/>
      <!-- headlights / brakelights -->
      <circle class="headlight" cx="66" cy="105" r="6" fill="#fff8e0"/>
      <circle class="headlight" cx="66" cy="145" r="6" fill="#fff8e0"/>
      <circle id="brakeL" class="brakeflash" cx="334" cy="105" r="6" fill="#ff3b3b"/>
      <circle id="brakeR" class="brakeflash" cx="334" cy="145" r="6" fill="#ff3b3b"/>
      <!-- charging glow -->
      <circle id="chargeGlow" class="charge-pulse" cx="340" cy="125" r="16" fill="#00d4ff"/>
      <!-- power flow lines -->
      <path id="powerflow1" class="powerflow" d="M100,125 L300,125" stroke="#00d4ff" stroke-width="2" fill="none"/>
      <!-- wheels -->
      <g id="wheelFL" transform-origin="105 165"><circle cx="105" cy="165" r="18" fill="#111520"/><circle cx="105" cy="165" r="7" fill="#4b5566"/><line x1="105" y1="150" x2="105" y2="180" stroke="#4b5566" stroke-width="2"/><line x1="90" y1="165" x2="120" y2="165" stroke="#4b5566" stroke-width="2"/></g>
      <g id="wheelRL" transform-origin="295 165"><circle cx="295" cy="165" r="18" fill="#111520"/><circle cx="295" cy="165" r="7" fill="#4b5566"/><line x1="295" y1="150" x2="295" y2="180" stroke="#4b5566" stroke-width="2"/><line x1="280" y1="165" x2="310" y2="165" stroke="#4b5566" stroke-width="2"/></g>
    </svg>

    __HOTSPOTS__
  </div>

  <div class="detail-panel" id="detailPanel">
    <div class="detail-title" id="detailTitle"></div>
    <div class="detail-status" id="detailStatus"></div>
    <div class="spark" id="detailSpark"></div>
    <div class="detail-row" id="detailRec"></div>
    <div class="detail-row" id="detailService"></div>
  </div>

  <div class="journey-grid fadein" id="journeyGrid"></div>

  <div class="route-wrap fadein">
    <div class="route-head"><span id="routeLeg">Home → Office</span><span id="routeEta">ETA --</span></div>
    <svg viewBox="0 0 400 60" width="100%" height="60">
      <path id="routePath" d="M20,40 L100,20 L180,40 L260,20 L340,40" stroke="rgba(255,255,255,0.15)" stroke-width="3" fill="none"/>
      <circle id="routeDot" r="6" fill="var(--accent, #00d4ff)"/>
      <circle cx="20" cy="40" r="4" fill="#8b93a7"/><circle cx="100" cy="20" r="4" fill="#8b93a7"/>
      <circle cx="180" cy="40" r="4" fill="#8b93a7"/><circle cx="260" cy="20" r="4" fill="#8b93a7"/>
      <circle cx="340" cy="40" r="4" fill="#8b93a7"/>
    </svg>
  </div>
</div>

<script>
(function() {
  const DATA = __DATA_JSON__;
  const DEMO = __DEMO_MODE__;
  const root = document.getElementById('evroot');

  function healthColor(h) { return h >= 80 ? 'var(--good)' : h >= 60 ? 'var(--warn)' : 'var(--bad)'; }

  // ---- Hotspot click handling ----
  const panel = document.getElementById('detailPanel');
  document.querySelectorAll('.hotspot').forEach(function(el) {
    el.addEventListener('click', function() {
      document.querySelectorAll('.hotspot').forEach(function(h){h.classList.remove('selected');});
      el.classList.add('selected');
      const name = el.getAttribute('data-name');
      const info = DATA.components[name];
      if (!info) return;
      document.getElementById('detailTitle').textContent = name;
      document.getElementById('detailStatus').innerHTML =
        '<span style="color:' + healthColor(info.health) + '">' + info.status + ' · ' + info.health + '%</span>';
      const spark = document.getElementById('detailSpark');
      spark.innerHTML = '';
      const maxV = Math.max.apply(null, info.history.concat([1]));
      info.history.forEach(function(v){
        const bar = document.createElement('div');
        bar.style.height = Math.max(4, (v / maxV) * 28) + 'px';
        spark.appendChild(bar);
      });
      document.getElementById('detailRec').textContent = '💡 ' + info.recommendation;
      document.getElementById('detailService').textContent = '🔧 Next service: ' + info.service;
      panel.style.display = 'block';
      panel.classList.remove('fadein'); void panel.offsetWidth; panel.classList.add('fadein');
    });
  });

  // ---- Journey grid (animated counters) ----
  const jGrid = document.getElementById('journeyGrid');
  const journeyFields = [
    ['trip_distance', 'Trip Distance', 'km'],
    ['total_distance', 'Total Today', 'km'],
    ['trip_duration', 'Trip Duration', 'min'],
    ['avg_speed', 'Avg Speed', 'km/h'],
    ['current_speed', 'Current Speed', 'km/h'],
    ['peak_speed', 'Peak Speed', 'km/h'],
    ['energy_used', 'Energy Used', 'kWh'],
    ['energy_recovered', 'Energy Recovered', 'kWh'],
    ['avg_efficiency', 'Avg Efficiency', '%'],
    ['regen_energy', 'Regen Energy', 'kWh'],
    ['idle_time', 'Idle Time', 'min'],
    ['eta_range', 'Range Remaining', 'km'],
  ];
  const sim = {
    trip_distance: 0,
    total_distance: DATA.journey.distance_km,
    trip_duration: 0,
    avg_speed: DATA.avgSpeed,
    current_speed: DATA.avgSpeed * 0.6,
    peak_speed: DATA.peakSpeed,
    energy_used: DATA.journey.energy_used_kwh,
    energy_recovered: DATA.journey.energy_used_kwh * 0.12,
    avg_efficiency: DATA.journey.efficiency_pct,
    regen_energy: DATA.journey.energy_used_kwh * 0.12,
    idle_time: 0,
    eta_range: DATA.rangeKm,
  };

  journeyFields.forEach(function(f) {
    const card = document.createElement('div');
    card.className = 'jcard';
    card.innerHTML = '<div class="jlabel">' + f[1] + '</div><div class="jvalue" id="j_' + f[0] + '">' +
      sim[f[0]].toFixed(1) + ' <span style="font-size:0.7rem;color:var(--muted)">' + f[2] + '</span></div>';
    jGrid.appendChild(card);
  });

  function renderJourney() {
    journeyFields.forEach(function(f) {
      const el = document.getElementById('j_' + f[0]);
      if (el) el.innerHTML = sim[f[0]].toFixed(1) + ' <span style="font-size:0.7rem;color:var(--muted)">' + f[2] + '</span>';
    });
  }
  renderJourney();

  // ---- Route mini-map ----
  const legs = ['Home → Office', 'Office → Lunch', 'Lunch → Office', 'Office → Shopping Mall', 'Mall → Charging Station', 'Charging Station → Home'];
  const routePoints = [[20,40],[100,20],[180,40],[260,20],[340,40]];
  let legIndex = 0, legProgress = 0;
  const dot = document.getElementById('routeDot');
  const legLabel = document.getElementById('routeLeg');
  const etaLabel = document.getElementById('routeEta');

  function lerp(a,b,t){ return a + (b-a)*t; }
  function renderRoute() {
    const segCount = routePoints.length - 1;
    const segFloat = legProgress * segCount;
    const seg = Math.min(Math.floor(segFloat), segCount - 1);
    const t = segFloat - seg;
    const p0 = routePoints[seg], p1 = routePoints[seg+1];
    dot.setAttribute('cx', lerp(p0[0], p1[0], t));
    dot.setAttribute('cy', lerp(p0[1], p1[1], t));
    legLabel.textContent = legs[legIndex % legs.length];
    const remainMin = Math.max(1, Math.round((1 - legProgress) * 18));
    etaLabel.textContent = 'ETA ' + remainMin + ' min · ' + DATA.traffic + ' traffic';
  }
  renderRoute();

  // ---- Weather / traffic driven modifiers ----
  const weatherCycle = ['Sunny', 'Rain', 'Cloudy', 'Hot', 'Cold'];
  const trafficCycle = ['Free', 'Moderate', 'Heavy'];
  let weather = DATA.weather, traffic = DATA.traffic;
  const weatherIcons = {Sunny:'☀️', Rain:'🌧️', Cloudy:'☁️', Hot:'🔥', Cold:'❄️'};

  function weatherPenalty() {
    return {Sunny:0, Cloudy:2, Rain:6, Hot:8, Cold:10}[weather] || 0;
  }
  function trafficTargetSpeed() {
    return {Free:[55,75], Moderate:[28,45], Heavy:[8,22]}[traffic] || [30,45];
  }
  function trafficEnergyPenalty() {
    return {Free:0, Moderate:5, Heavy:12}[traffic] || 0;
  }

  // ---- Driving behaviour (smooth vs aggressive phase) ----
  let smoothPhase = true;
  let tickCount = 0;
  let chargingLeg = false;
  let brakeFlashUntil = 0;

  function tick() {
    tickCount++;
    if (tickCount % 6 === 0) smoothPhase = Math.random() > 0.35;
    if (tickCount % 9 === 0) weather = weatherCycle[Math.floor(Math.random()*weatherCycle.length)];
    if (tickCount % 7 === 0) traffic = trafficCycle[Math.floor(Math.random()*trafficCycle.length)];

    document.getElementById('weatherIcon').textContent =
      (weatherIcons[weather]||'☁️') + ' ' + weather + ' · ' + DATA.temperature + '°C';

    const [lo, hi] = trafficTargetSpeed();
    const targetSpeed = lo + Math.random() * (hi - lo);
    const prevSpeed = sim.current_speed;
    sim.current_speed = sim.current_speed + (targetSpeed - sim.current_speed) * 0.35;
    sim.peak_speed = Math.max(sim.peak_speed, sim.current_speed);

    if (sim.current_speed < prevSpeed - 4) {
      brakeFlashUntil = Date.now() + 400;
    }

    const distanceInc = (sim.current_speed / 3600) * 2.2; // ~2.2s tick, km per tick
    if (sim.current_speed < 3) {
      sim.idle_time += 2.2/60;
    } else {
      sim.trip_distance += distanceInc;
      sim.total_distance += distanceInc;
    }
    sim.trip_duration += 2.2/60;
    sim.avg_speed = sim.total_distance > 0 ? (sim.total_distance / Math.max(sim.trip_duration/60, 0.01)) : sim.avg_speed;

    const basePenalty = weatherPenalty() + trafficEnergyPenalty() + (smoothPhase ? 0 : 10);
    const energyPerKm = 0.16 + basePenalty * 0.003;
    const energyInc = distanceInc * energyPerKm;
    sim.energy_used += energyInc;

    const regenFactor = smoothPhase ? 0.22 : 0.08;
    const regenInc = energyInc * regenFactor;
    sim.energy_recovered += regenInc;
    sim.regen_energy = sim.energy_recovered;

    sim.avg_efficiency = Math.max(40, Math.min(99, 100 - basePenalty - (smoothPhase ? -5 : 5)));
    sim.eta_range = Math.max(0, sim.eta_range - (energyInc - regenInc) * 5.2);

    legProgress += 0.012;
    if (legProgress >= 1) {
      legProgress = 0;
      legIndex++;
      chargingLeg = legs[legIndex % legs.length].indexOf('Charging Station') === 0;
    }
    renderRoute();
    renderJourney();

    // wheel spin speed tied to current speed
    const spinDuration = Math.max(0.25, 1.6 - (sim.current_speed/60));
    ['wheelFL','wheelRL'].forEach(function(id){
      const el = document.getElementById(id);
      el.style.animationPlayState = sim.current_speed > 2 ? 'running' : 'paused';
      el.style.animationDuration = spinDuration + 's';
    });

    // brake light flash
    const brakeOn = Date.now() < brakeFlashUntil;
    document.getElementById('brakeL').style.opacity = brakeOn ? 1 : 0;
    document.getElementById('brakeR').style.opacity = brakeOn ? 1 : 0;

    // charging glow + power flow when at a charging leg
    const chargeEl = document.getElementById('chargeGlow');
    const flowEl = document.getElementById('powerflow1');
    if (chargingLeg) {
      chargeEl.style.opacity = 0.9; chargeEl.style.animation = 'pulseGlow 1.2s infinite';
      flowEl.style.opacity = 0.8;
    } else {
      chargeEl.style.opacity = 0; flowEl.style.opacity = 0;
    }
  }

  if (DEMO) {
    setInterval(tick, 2200);
  }

  // ---- Live clock (always ticking, demo or not) ----
  function updateClock() {
    const now = new Date();
    document.getElementById('clock').textContent =
      now.toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  }
  updateClock();
  setInterval(updateClock, 1000);

  // ---- AI Analyzing sequence + rotating companion messages ----
  const analyzingPhrases = [
    'AI analyzing driving behaviour...',
    'Checking battery performance...',
    'Analyzing environmental conditions...',
  ];
  const companionMessages = [DATA.greeting + ', driver.'].concat(
    DATA.recommendations.map(function(r){ return '💡 ' + r; })
  ).concat([
    'Traffic is ' + DATA.traffic.toLowerCase() + ' today.',
    'Battery temperature is being monitored continuously.',
    'Your eco driving score is ' + DATA.driver.ecoScore + '%.',
  ]);

  const analyzingEl = document.getElementById('analyzingLine');
  const companionEl = document.getElementById('companionBar');
  let msgIndex = 0;

  function runAnalyzingCycle() {
    let i = 0;
    analyzingEl.style.opacity = 1;
    const iv = setInterval(function() {
      analyzingEl.textContent = analyzingPhrases[i];
      i++;
      if (i >= analyzingPhrases.length) {
        clearInterval(iv);
        setTimeout(function() {
          analyzingEl.style.opacity = 0;
          msgIndex = (msgIndex + 1) % companionMessages.length;
          companionEl.style.opacity = 0;
          setTimeout(function() {
            companionEl.textContent = companionMessages[msgIndex];
            companionEl.style.opacity = 1;
          }, 350);
        }, 900);
      }
    }, 1000);
  }

  companionEl.textContent = companionMessages[0];
  setTimeout(runAnalyzingCycle, 2500);
  setInterval(runAnalyzingCycle, 11000);
})();
</script>
"""


def _build_hotspots(components_map: dict) -> str:
    """Positions one clickable hotspot per component around the vehicle SVG stage."""
    # (name, left%, top%)
    layout = [
        ("Battery", 50, 78),
        ("Motor", 18, 55),
        ("Brakes", 30, 70),
        ("Tires", 74, 70),
        ("Suspension", 84, 55),
        ("Charging Port", 88, 40),
        ("Lights", 12, 38),
        ("ADAS", 50, 18),
        ("Doors", 62, 55),
    ]
    parts = []
    for name, left, top in layout:
        info = components_map.get(name, {"health": 90})
        color = "#2ecc71" if info["health"] >= 80 else "#f39c12" if info["health"] >= 60 else "#e74c3c"
        parts.append(
            f'<div class="hotspot" data-name="{name}" '
            f'style="left:{left}%; top:{top}%; background:{color}; color:{color};"></div>'
            f'<div class="hotspot-label" style="left:{left}%; top:{top}%;">{name}</div>'
        )
    return "\n".join(parts)


def render(state: dict, score_info: dict, demo_mode: bool, height: int = 980):
    """Renders the full interactive vehicle experience component into the page."""
    payload = _build_payload(state, score_info)
    html = (
        _HTML_TEMPLATE
        .replace("__DATA_JSON__", json.dumps(payload))
        .replace("__DEMO_MODE__", "true" if demo_mode else "false")
        .replace("__GREETING__", payload["greeting"])
        .replace("__CONDITION__", payload["condition"])
        .replace("__SOC__", str(payload["soc"]))
        .replace("__RANGE__", str(payload["rangeKm"]))
        .replace("__WEATHER__", payload["weather"])
        .replace("__TEMP__", str(payload["temperature"]))
        .replace("__HOTSPOTS__", _build_hotspots(payload["components"]))
    )
    components.html(html, height=height, scrolling=False)

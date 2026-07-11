"""
animated_ui.py
---------------
A small set of self-contained HTML/CSS/JS widgets (rendered via
streamlit.components.v1.html) for the handful of places in Driver View
that need genuine motion — animated count-up numbers, animated circular
health rings, and a floating AI companion that rotates messages on its
own timer. Everything else in the app is plain Streamlit + CSS, which
handles fades/hovers/transitions fine; these three specifically need a
few lines of JavaScript because Streamlit's rerun-the-whole-script model
can't animate a value changing from A to B on its own.

Kept deliberately small and dependency-free (no charting library inside
the iframe) so they stay fast even when Demo Mode re-mounts them every
couple of seconds.

Styled to match utils/background_theme.py's Liquid Glass material
(convex-shadow language, no shimmer) — see that file's HONEST LIMITS
note for why these particular widgets can't show the live blurred
background or join the cursor-tracking effects the rest of the app's
glass cards get (they render inside their own iframe, a separate
rendering context from the main page).
"""

import json

import streamlit.components.v1 as components


def animated_stat_row(stats: list, height: int = 110):
    """
    Renders a row of glass-card stats (e.g. Battery / Trip Distance /
    Remaining Range) where the number animates from its previous value to
    its current one on every mount, instead of jumping instantly.

    stats: list of dicts, each {"label": str, "value": float, "suffix": str, "prev": float}
    """
    payload = json.dumps(stats)
    html = f"""
    <div id="statrow" style="display:flex; gap:10px; font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;">
    </div>
    <style>
        html, body {{ background: transparent !important; margin: 0; }}
        .astat {{
            position: relative; overflow: hidden;
            flex:1; text-align:center; padding: 14px 6px;
            background: linear-gradient(180deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.015) 45%, rgba(0,0,0,0.04) 100%),
                        linear-gradient(145deg, rgba(23,27,36,0.55), rgba(16,19,26,0.5));
            backdrop-filter: blur(16px) saturate(140%);
            border: 1px solid rgba(255,255,255,0.12);
            border-radius: 18px;
            /* Same convex-glass shadow language as background_theme.py's
               cards (bright top inset, dark bottom inset, cool side
               highlight) so this iframe-rendered widget still reads as
               part of the same material even though — per that file's
               HONEST LIMITS note — it can't see or blur the page behind
               it, and can't join the cursor-tracking effects either. */
            box-shadow:
                0 8px 22px rgba(0,0,0,0.3),
                inset 0 1px 0 rgba(255,255,255,0.16),
                inset 0 -10px 16px -6px rgba(0,0,0,0.18),
                inset 8px 0 14px -12px rgba(255,255,255,0.10),
                inset -8px 0 14px -12px rgba(120,170,255,0.08);
            transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.25s ease, border-color 0.25s ease;
        }}
        .astat:hover {{
            transform: translateY(-3px);
            border-color: rgba(255,255,255,0.22);
            box-shadow:
                0 12px 28px rgba(0,0,0,0.36),
                inset 0 1px 0 rgba(255,255,255,0.22),
                inset 0 -12px 18px -6px rgba(0,0,0,0.2),
                inset 8px 0 14px -12px rgba(255,255,255,0.14),
                inset -8px 0 14px -12px rgba(120,170,255,0.12);
        }}
        .astat .av {{ font-size: 1.3rem; font-weight: 700; color: #f2f4f8; font-variant-numeric: tabular-nums; }}
        .astat .al {{ font-size: 0.68rem; color: #93a0b8; text-transform: uppercase; letter-spacing: 0.04em; margin-top: 3px; }}
    </style>
    <script>
        const stats = {payload};
        const row = document.getElementById('statrow');
        stats.forEach(function(s, idx) {{
            const card = document.createElement('div');
            card.className = 'astat';
            card.innerHTML = '<div class="av" id="av' + idx + '">' + s.prev + s.suffix + '</div><div class="al">' + s.label + '</div>';
            row.appendChild(card);
        }});

        function animateValue(el, start, end, suffix, duration) {{
            const startTime = performance.now();
            const decimals = (String(end).split('.')[1] || '').length;
            function step(now) {{
                const progress = Math.min((now - startTime) / duration, 1);
                const eased = 1 - Math.pow(1 - progress, 3);
                const current = start + (end - start) * eased;
                el.textContent = current.toFixed(decimals) + suffix;
                if (progress < 1) requestAnimationFrame(step);
            }}
            requestAnimationFrame(step);
        }}

        stats.forEach(function(s, idx) {{
            const el = document.getElementById('av' + idx);
            animateValue(el, s.prev, s.value, s.suffix, 800);
        }});
    </script>
    """
    components.html(html, height=height, scrolling=False)


def animated_health_rings(rings: list, height: int = 220):
    """
    Renders a row of animated circular progress rings (Battery, Motor,
    Safety, Comfort, Efficiency) that sweep in from 0 to their target
    value whenever the component mounts.

    rings: list of dicts {"label": str, "value": float, "color": str}
    """
    payload = json.dumps(rings)
    html = f"""
    <div id="ringrow" style="display:flex; gap:14px; justify-content:center; flex-wrap:wrap; font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;"></div>
    <style>
        .ringcard {{ text-align:center; width: 96px; }}
        .ringlabel {{ font-size: 0.72rem; color: #93a0b8; margin-top: 6px; text-transform: uppercase; letter-spacing: 0.03em; }}
        .ringval {{ font-size: 1.0rem; font-weight: 700; fill: #f2f4f8; font-variant-numeric: tabular-nums; }}
    </style>
    <script>
        const rings = {payload};
        const wrap = document.getElementById('ringrow');
        const R = 34, C = 2 * Math.PI * 34;

        rings.forEach(function(r, idx) {{
            const div = document.createElement('div');
            div.className = 'ringcard';
            const svgId = 'ring' + idx;
            div.innerHTML = `
                <svg width="88" height="88" viewBox="0 0 88 88">
                    <circle cx="44" cy="44" r="${{R}}" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="7"/>
                    <circle id="${{svgId}}" cx="44" cy="44" r="${{R}}" fill="none" stroke="${{r.color}}" stroke-width="7"
                            stroke-linecap="round" stroke-dasharray="${{C}}" stroke-dashoffset="${{C}}"
                            transform="rotate(-90 44 44)" style="transition: stroke-dashoffset 1.1s cubic-bezier(0.22,1,0.36,1);"/>
                    <text x="44" y="49" text-anchor="middle" class="ringval">${{Math.round(r.value)}}%</text>
                </svg>
                <div class="ringlabel">${{r.label}}</div>
            `;
            wrap.appendChild(div);
        }});

        // Trigger the sweep-in on next frame so the transition applies.
        requestAnimationFrame(function() {{
            requestAnimationFrame(function() {{
                rings.forEach(function(r, idx) {{
                    const el = document.getElementById('ring' + idx);
                    const offset = C - (Math.max(0, Math.min(100, r.value)) / 100) * C;
                    el.setAttribute('stroke-dashoffset', offset);
                }});
            }});
        }});
    </script>
    """
    components.html(html, height=height, scrolling=False)


def floating_companion(messages: list, height: int = 90):
    """
    A small "AI companion" card that rotates through short insight
    messages on its own timer (independent of Streamlit reruns), fading
    between them. Not a chatbot — purely a rotating status display.
    """
    payload = json.dumps(messages)
    html = f"""
    <div id="companion" style="
        font-family:-apple-system,'Segoe UI',Roboto,Arial,sans-serif;
        background: linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.01) 100%),
                    linear-gradient(145deg, rgba(0,212,255,0.08), rgba(0,212,255,0.015));
        backdrop-filter: blur(18px) saturate(150%);
        border: 1px solid rgba(0,212,255,0.22);
        border-radius: 18px;
        padding: 14px 18px;
        color: #eef1f7;
        font-size: 0.88rem;
        min-height: 20px;
        box-shadow: 0 8px 22px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.12), 0 0 24px rgba(0,212,255,0.08);
        transition: opacity 0.5s ease;
    ">
        <style> html, body {{ background: transparent !important; margin: 0; }} </style>
        <div style="font-size:0.66rem; text-transform:uppercase; letter-spacing:0.06em; color:#00d4ff; font-weight:700; margin-bottom:5px;">
            🤖 AI Companion
        </div>
        <div id="companionText"></div>
    </div>
    <script>
        const msgs = {payload};
        let i = 0;
        const el = document.getElementById('companionText');
        const box = document.getElementById('companion');
        function show(idx) {{
            box.style.opacity = 0;
            setTimeout(function() {{
                el.textContent = msgs[idx];
                box.style.opacity = 1;
            }}, 300);
        }}
        if (msgs.length > 0) {{
            el.textContent = msgs[0];
            setInterval(function() {{
                i = (i + 1) % msgs.length;
                show(i);
            }}, 4200);
        }}
    </script>
    """
    components.html(html, height=height, scrolling=False)

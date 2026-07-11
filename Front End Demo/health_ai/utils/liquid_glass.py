"""
liquid_glass.py
-----------------
The pointer-interaction half of the "Liquid Glass" material system (see
utils/background_theme.py for the CSS half, which defines what these
effects *look like* once the custom properties below are set).

WHY THIS NEEDS TO EXIST
Streamlit's own Python script only reruns on user actions (button
clicks, slider drags, Demo Mode's timer) — it has no way to react to
raw mouse movement between reruns. The moving specular reflection the
design brief asks for depends on live cursor position, so it has to be
plain client-side JavaScript, sitting alongside Streamlit rather than
going through it.

HOW IT REACHES THE MAIN PAGE
`streamlit.components.v1.html` renders into its own sandboxed iframe, so
a script here can't listen for events directly on the main app page.
Since the iframe is same-origin, it can reach across to
`window.parent.document` and attach its listeners there instead — a
well-established pattern for exactly this "inject some page-wide
behaviour" case. This component renders at height=0 and is otherwise
completely invisible; it exists purely to run its <script> tag.

WHAT THE SCRIPT ACTUALLY DOES
One delegated `pointermove` listener, throttled to at most once per
animation frame (via requestAnimationFrame — never runs on every raw
mouse-move event, so it stays cheap even on a busy demo laptop):

  Finds whichever glass element the cursor is currently over via event
  delegation (`e.target.closest(SELECTOR)`), and writes that one
  element's own --mx / --my (cursor position inside the card, as a %).
  background_theme.py reads these two variables to move the *internal*
  specular highlight (a ::after radial-gradient "reflection") so it
  tracks the cursor — like a flashlight sweeping across glass. Nothing
  here toggles a CSS class or tracks "is this the hovered card" state in
  JS — the browser's own :hover pseudo-class in background_theme.py is
  what actually turns --mx/--my into a visible highlight, so there's no
  enter/leave bookkeeping to keep in sync, and it can't drift out of
  sync with the DOM even when Streamlit's Demo Mode reruns replace that
  DOM every couple of seconds — `closest()` is re-evaluated fresh on
  every event, never cached against a stale node.

  REMOVED: this module previously also wrote whole-dashboard parallax
  (--parallax-x/--parallax-y, applied as a page-wide `transform` on the
  background and every card) and per-card tilt-toward-cursor
  (--tilt-x/--tilt-y, applied as `rotateX`/`rotateY`). Both made the
  entire UI — background, glass cards, text, icons, charts — visibly
  shift or wobble with every mouse movement. Both have been deleted
  from this script and from the CSS that read them, so the layout is
  now perfectly stationary; only the internal reflection still reacts
  to the cursor.

PERFORMANCE
  - Only one listener, attached once, delegated — not one listener per
    card (which would also need re-attaching after every Streamlit
    rerun tears down and rebuilds the DOM).
  - `{{ passive: true }}` tells the browser this listener never calls
    preventDefault(), so it can't block scrolling/rendering.
  - Actual DOM writes (`style.setProperty`) happen at most once per
    animation frame no matter how fast the mouse moves, via the
    pending-event + requestAnimationFrame pattern below.
  - The CSS side only moves a gradient's center point on the hovered
    element's own ::after layer — no transform, no layout-triggering
    properties, so there's no forced reflow per frame and nothing else
    on the page moves.

HONEST LIMITS
  - This cross-frame `window.parent` trick only works because the
    Streamlit app and this component are same-origin (the normal case
    for claude.ai / local / most self-hosted deployments). If a
    deployment ever embeds the app cross-origin, the try/except below
    means the effect quietly does nothing rather than throwing — the
    rest of the app is completely unaffected either way.
  - `animated_ui.py`'s iframes (animated_stat_row, floating_companion)
    are themselves separate rendering contexts and can't be reached by
    — or reach out to — this script; they keep their own static styling
    instead (see that file's docstring).
"""

import streamlit.components.v1 as components

# Kept as one shared constant so this stays in sync with the selector
# list background_theme.py styles — if a new glass card class is added
# there, add it here too so it picks up the cursor-tracking behaviour.
GLASS_SELECTOR = (
    ".metric-card, .glass-panel, .issue-card, .rec-card, .placeholder-card, "
    ".ai-summary-box, .companion-float, .ai-greeting-block, .mood-indicator, "
    ".ring-card, .toggle-card, .settings-card, .mode-card"
)


def inject_pointer_interaction():
    """
    Call once per page render, any time after background_theme.inject().
    Renders an invisible (height=0) component; produces no visible
    output of its own.
    """
    html = f"""
    <script>
    (function() {{
        try {{
            const doc = window.parent.document;
            const root = doc.documentElement;
            const SELECTOR = {GLASS_SELECTOR!r};

            let pendingEvent = null;
            let ticking = false;

            function applyFrame() {{
                const e = pendingEvent;
                ticking = false;
                if (!e) return;

                // ---- per-card specular highlight only ----
                // No page-wide parallax and no cursor-based tilt here
                // anymore — both caused the whole UI to shift/wobble.
                // This just moves the internal reflection's center point
                // on whichever glass element the cursor is over.
                const el = e.target && e.target.closest ? e.target.closest(SELECTOR) : null;
                if (el) {{
                    const rect = el.getBoundingClientRect();
                    if (rect.width > 0 && rect.height > 0) {{
                        const mx = ((e.clientX - rect.left) / rect.width) * 100;
                        const my = ((e.clientY - rect.top) / rect.height) * 100;
                        el.style.setProperty('--mx', mx.toFixed(1) + '%');
                        el.style.setProperty('--my', my.toFixed(1) + '%');
                    }}
                }}
            }}

            doc.addEventListener('pointermove', function(e) {{
                pendingEvent = e;
                if (!ticking) {{
                    ticking = true;
                    window.parent.requestAnimationFrame(applyFrame);
                }}
            }}, {{ passive: true }});
        }} catch (err) {{
            // Cross-origin embedding or another context where reaching
            // window.parent isn't available. The rest of the app (all
            // static CSS, including the base glass look) is completely
            // unaffected — this only skips the cursor-driven extras.
        }}
    }})();
    </script>
    """
    components.html(html, height=0, scrolling=False)

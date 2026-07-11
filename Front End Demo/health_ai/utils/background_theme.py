"""
background_theme.py
---------------------
Turns the app's flat dark theme into a layered, "automotive OS" backdrop:
the user's road photo as an immersive, always-visible background, with a
true Liquid Glass material (Apple-style curved, physical glass — not
classic web "glassmorphism") layered on top of every existing card
class. This is additive CSS only — it doesn't touch ui_components.py,
driver_shell.py, driver_sections.py, or animated_ui.py; it just injects
one more <style> block, after theirs, so its rules win the cascade for
the properties it redeclares (background, backdrop-filter, shadows,
borders, transform) while everything else (padding, layout, existing
fade-in animations) keeps working exactly as before.

The cursor-reactive half of this system (the pointermove listener that
drives the moving internal specular highlight) lives in
utils/liquid_glass.py — this file only defines what those CSS custom
properties (--mx, --my) *do* once they're set; that module is what sets
them. Earlier versions also had whole-dashboard parallax and per-card
tilt-toward-cursor; both caused the whole UI to wobble with the mouse
and have been removed from both files — the layout is now completely
stationary, and only the internal reflection tracks the cursor.

THE FIVE BACKGROUND LAYERS (back to front)
  1. The road photo itself (resized + a very slight pre-blur baked in
     once with Pillow, so Layer 3's "subtle blur" is real and doesn't
     depend on flaky cross-browser CSS filter-on-background tricks).
  2. A dark gradient overlay for text readability (stronger toward the
     bottom of the screen, where most of the UI's text-heavy content
     sits).
  3. (baked into layer 1 — see above.)
  4. A soft vignette toward the screen edges.
  5. A slow, faint color-wash gradient in the app's existing accent
     colors, so the road scene still feels like part of this product
     rather than a generic wallpaper.
All five are plain `background-image` layers on `.stApp` — no
pseudo-elements, so there's no risk of them being clipped or painted in
the wrong order relative to Streamlit's own DOM.

LIQUID GLASS — NOT GLASSMORPHISM
The earlier version of this file gave every card a flat translucent
fill plus a diagonal light streak that swept across it forever (classic
"shimmer" glassmorphism). That shimmer has been removed completely and
replaced with a system built to look like real curved glass instead of
a tinted rectangle:
  - Convex shading + a faint cool/warm edge split, fixed per card
    (::before) — simulates a physical light source and thick edges.
  - A cursor-tracking specular highlight (::after) that only appears on
    hover and fades naturally — replaces the old shimmer.
  - Layered shadows (contact + ambient + floating + a faint colored
    glow) instead of one flat drop-shadow.
  - A hover state that lifts the card by a small, fixed amount
    (translateY only — no tilt, no parallax, no rotation) rather than
    just scaling it, so the card's position and orientation never
    change; only its apparent height off the page does.
See the "LIQUID GLASS material system" comment block below for the full
per-layer breakdown, and utils/liquid_glass.py for how the underlying
CSS custom properties get their values from the cursor.

DYNAMIC / "SPATIAL" BLUR
CSS `filter` can't selectively blur one layer of a multi-layer
background while leaving the rest (and all the text) sharp. What *does*
work, natively and per element, is `backdrop-filter` on each floating
card — it blurs whatever is directly behind that specific card in real
time. So: the base photo carries only a gentle, uniform blur (Layer 1),
and each card's own `backdrop-filter` is what makes the area *behind
that card* noticeably blurrier than open background — exactly the
"areas behind floating cards should appear more blurred than empty
background areas" requirement, and it updates live if the card moves or
its content changes, at zero extra cost. The faint radial highlight
baked into each card's own background (rather than varying the blur
radius itself, which backdrop-filter can't do spatially) is what gives
the "denser edges, slightly clearer center" thick-glass impression.

ADAPTIVE GLASS COLOR
Pillow samples the resized photo's average brightness once (cached for
the process). Cards then tint very slightly toward white (if the photo
is dark) or slightly darker (if the photo is bright) via one extra CSS
custom property, `--adaptive-tint`, rather than hardcoded values — a
practical proxy for "the glass reacts to what's behind it" given that
true per-pixel, per-card sampling would need a canvas/JS pipeline far
beyond what a Streamlit CSS injection can do.

ELEVATION SYSTEM
Per the brief, transparency/blur/brightness now differ by role instead
of being identical everywhere:
    Level 2  Navigation (nav rail)      -> darker, least transparent
    Level 3  Information cards          -> large cards, moderate
    Level 3s Small widgets              -> hero stats, more transparent
    Level 5  Notifications (ai-line /
             alert-line / rec-card)     -> brighter glass
    Level 6  Floating AI companion      -> highest transparency

HONEST LIMITS
- True per-pixel optical refraction (the background image actually
  bending around the cursor) needs a shader/canvas or WebGL pipeline.
  This uses backdrop-filter (blur/saturate/contrast, nudged slightly on
  hover) plus gradient-based highlights instead — a common, cheap,
  GPU-accelerated approximation of "glass bends light," not a literal
  displacement map. See utils/liquid_glass.py for more on this tradeoff.
- `animated_ui.py`'s widgets (animated_stat_row, floating_companion)
  render inside `streamlit.components.v1.html` iframes. Iframes are a
  separate rendering context, so `backdrop-filter` inside them cannot
  see or blur the parent page's background — this is a browser
  limitation, not a config issue. Those widgets are still restyled here
  to the same glass palette (their own solid-ish translucent background
  plus a transparent iframe canvas), so they look consistent, but they
  won't show a live blurred road photo through them the way ordinary
  markdown cards do, and they don't participate in the cursor-tracking
  effects for the same reason (a separate iframe can't see the parent
  page's mouse position without the same cross-frame trick
  utils/liquid_glass.py uses for its own, invisible, zero-height frame).
- "Adaptive per-card" color is a single whole-image brightness average,
  not per-region sampling, for the reason above.
"""

import base64
import functools
import io
import os

import streamlit as st

try:
    from PIL import Image, ImageFilter
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

DEFAULT_BACKGROUND_PATH = os.path.join(
    os.path.dirname(__file__), "..", "assets", "backgrounds", "road_hero.jpg"
)


@functools.lru_cache(maxsize=2)
def _prepare_background(path: str, max_width: int = 1600, blur_radius: float = 2.2):
    """
    Loads the background photo once per process: downsizes it (a
    5000px+ photo re-embedded as base64 on every rerun would be slow and
    heavy), applies a gentle Gaussian blur for Layer 3, and measures
    average brightness for the adaptive glass tint. Returns
    (base64_jpeg_str, brightness_0_to_1). Falls back to a plain dark
    gradient (no photo) if Pillow isn't installed or the file is
    missing — the app still runs, just without the road backdrop.
    """
    if not _PIL_OK or not os.path.exists(path):
        return None, 0.35

    with Image.open(path) as img:
        img = img.convert("RGB")
        if img.width > max_width:
            ratio = max_width / img.width
            img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)

        brightness = sum(img.convert("L").resize((48, 48)).getdata()) / (48 * 48) / 255.0

        blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
        buf = io.BytesIO()
        blurred.save(buf, format="JPEG", quality=80)
        b64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    return b64, round(brightness, 3)


def inject(image_path: str = DEFAULT_BACKGROUND_PATH):
    """
    Call once per page render, after ui.inject_custom_css(). Injects the
    layered background + the Liquid Glass upgrades over every existing
    card class. Safe to call even if the image is missing — degrades to
    the existing dark gradient theme.
    """
    b64, brightness = _prepare_background(image_path)

    # Adaptive tint: darker photo -> brighten glass slightly; brighter photo -> darken it slightly.
    if brightness < 0.45:
        tint_rgb, tint_alpha = "255,255,255", round(0.025 + (0.45 - brightness) * 0.09, 3)
    else:
        tint_rgb, tint_alpha = "0,0,0", round(0.02 + (brightness - 0.45) * 0.10, 3)

    if b64:
        bg_layers = f"""
            background-image:
                linear-gradient(180deg, rgba(6,8,13,0.38) 0%, rgba(6,8,13,0.58) 55%, rgba(4,6,10,0.82) 100%),
                radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(0,0,0,0.55) 100%),
                radial-gradient(circle at 0% 50%, rgba(0,212,255,0.08) 0%, rgba(0,212,255,0) 45%),
                radial-gradient(circle at 100% 50%, rgba(120,80,255,0.07) 0%, rgba(120,80,255,0) 50%),
                url("data:image/jpeg;base64,{b64}") !important;
            background-size: cover, cover, 200% 200%, 200% 200%, cover !important;
            background-position: center, center, 0% 50%, 100% 50%, center !important;
            background-attachment: fixed, fixed, fixed, fixed, fixed !important;
            background-repeat: no-repeat !important;
        """
    else:
        # Graceful fallback: no photo available, keep a premium dark gradient.
        bg_layers = """
            background-image:
                radial-gradient(circle at top left, rgba(0,212,255,0.06) 0%, rgba(0,212,255,0) 40%),
                radial-gradient(circle at bottom right, rgba(120,80,255,0.06) 0%, rgba(120,80,255,0) 45%),
                radial-gradient(circle at top left, #131722 0%, #0a0c10 100%) !important;
            background-size: 200% 200%, 200% 200%, 100% 100% !important;
        """

    st.markdown(f"""
    <style>
        :root {{
            --adaptive-tint-rgb: {tint_rgb};
            --adaptive-tint-alpha: {tint_alpha};
        }}

        @keyframes dialogFadeScale {{
            from {{ opacity: 0; transform: translateY(10px) scale(0.985); }}
            to   {{ opacity: 1; transform: translateY(0) scale(1); }}
        }}

        /* ---- Layer 1/2/3/4/5: the immersive road background ----
           !important, and this module is re-invoked at the very end of
           dashboard.py's render, specifically because
           ui.dynamic_theme_overlay_css() (called inside driver_shell,
           after this module's first call) also sets .stApp's
           background-image with !important for its subtle time-of-day
           tint. Without both of these, that later rule would silently
           replace the road photo with the old flat gradient. */
        .stApp {{
            {bg_layers}
            /* The background is intentionally completely static: no
               drift animation, no parallax transform, no perspective.
               Only the blur baked into the photo (Layer 1) and the
               dark gradient/vignette overlays above move nowhere,
               ever, regardless of cursor position. */
        }}

        /* ============================================================
           LIQUID GLASS material system
           --------------------------------------------------------------
           Replaces the old flat frosted-glass-plus-shimmer treatment.
           Every card is built from three cooperating layers:
             1. the element itself   -> backdrop blur/saturate/contrast
                                        (the "frosted" glass body)
             2. ::before              -> a fixed, per-card light source:
                                        convex shading (brighter top-left,
                                        darker lower-right) plus a faint
                                        cool/warm edge split for a subtle
                                        chromatic-separation feel
             3. ::after                -> the dynamic specular highlight —
                                        a soft light circle that tracks the
                                        cursor via the --mx/--my custom
                                        properties utils/liquid_glass.py's
                                        pointermove listener writes onto
                                        the hovered element. Fully driven
                                        by the browser's own :hover state,
                                        so there's no JS class-toggling
                                        to keep in sync with the DOM.
           Convex "thick glass" edges come from a stack of inset shadows
           (bright top inset, dark bottom inset, cool/warm side insets)
           rather than a uniform border — no flat white border anywhere.
           Hover only adds a small, fixed translateY lift — no tilt, no
           parallax, no rotation — so the card's position and
           orientation stay perfectly stable while it's lit.
           ============================================================ */

        .metric-card, .glass-panel, .issue-card,
        .rec-card, .placeholder-card, .ai-summary-box, .companion-float,
        .ai-greeting-block, .mood-indicator, .ring-card, .toggle-card, .settings-card, .mode-card {{
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(140% 120% at var(--mx, 28%) var(--my, 18%), rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.02) 35%, rgba(255,255,255,0) 60%),
                linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.015) 40%, rgba(0,0,0,0.04) 100%),
                linear-gradient(145deg, rgba(var(--adaptive-tint-rgb), var(--adaptive-tint-alpha)), rgba(var(--adaptive-tint-rgb), 0)),
                linear-gradient(145deg, rgba(23,27,36,0.46), rgba(16,19,26,0.40));
            /* "layered blur": edges read denser/blurrier, the radial
               highlight above gives the center a very slightly clearer
               feel without literally varying the blur radius spatially
               (backdrop-filter can't do that yet) — see liquid_glass.py
               docstring for the honest limits on this approximation. */
            backdrop-filter: blur(20px) saturate(150%) contrast(1.02);
            -webkit-backdrop-filter: blur(20px) saturate(150%) contrast(1.02);
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow:
                0 1px 1px rgba(0,0,0,0.20),
                0 8px 18px rgba(0,0,0,0.24),
                0 24px 44px rgba(0,0,0,0.30),
                0 0 24px rgba(0,212,255,0.05),
                inset 0 1px 0 rgba(255,255,255,0.22),
                inset 0 -16px 24px -8px rgba(0,0,0,0.22),
                inset 11px 0 20px -15px rgba(255,255,255,0.10),
                inset -11px 0 20px -15px rgba(120,170,255,0.08);
            transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1),
                        box-shadow 0.35s ease,
                        backdrop-filter 0.35s ease,
                        border-color 0.3s ease,
                        background 0.2s ease;
            animation: evFadeIn 0.45s ease both;
        }}

        /* Layer 2: the fixed, non-cursor-driven convex/edge lighting. */
        .metric-card::before, .rec-card::before, .ai-summary-box::before, .companion-float::before,
        .ai-greeting-block::before, .mood-indicator::before, .ring-card::before, .issue-card::before,
        .toggle-card::before, .settings-card::before, .mode-card::before {{
            content: "";
            position: absolute; inset: 0;
            border-radius: inherit;
            pointer-events: none;
            background:
                linear-gradient(115deg, rgba(255,255,255,0.16) 0%, rgba(255,255,255,0) 24%),
                linear-gradient(295deg, rgba(130,190,255,0.07) 0%, rgba(130,190,255,0) 28%),
                linear-gradient(65deg, rgba(255,190,150,0.04) 0%, rgba(255,190,150,0) 22%);
            mix-blend-mode: screen;
        }}

        /* Layer 3: the cursor-reactive specular reflection — replaces
           the old shimmer sheen entirely. Only visible on :hover, so it
           fades in/out naturally instead of looping forever. */
        .metric-card::after, .rec-card::after, .ai-summary-box::after, .companion-float::after,
        .ai-greeting-block::after, .mood-indicator::after, .ring-card::after, .issue-card::after,
        .toggle-card::after, .settings-card::after, .mode-card::after {{
            content: "";
            position: absolute; inset: 0;
            border-radius: inherit;
            pointer-events: none;
            background: radial-gradient(240px circle at var(--mx, 50%) var(--my, 35%),
                        rgba(255,255,255,0.32), rgba(255,255,255,0.06) 35%, rgba(255,255,255,0) 62%);
            opacity: 0;
            transition: opacity 0.4s ease;
        }}
        .metric-card:hover::after, .rec-card:hover::after, .ai-summary-box:hover::after, .companion-float:hover::after,
        .ai-greeting-block:hover::after, .mood-indicator:hover::after, .ring-card:hover::after, .issue-card:hover::after,
        .toggle-card:hover::after, .settings-card:hover::after, .mode-card:hover::after {{
            opacity: 1;
        }}

        .metric-card:hover, .rec-card:hover, .issue-card:hover, .ring-card:hover,
        .toggle-card:hover, .settings-card:hover, .ai-summary-box:hover, .mode-card:hover {{
            backdrop-filter: blur(28px) saturate(168%) contrast(1.06) brightness(1.05);
            -webkit-backdrop-filter: blur(28px) saturate(168%) contrast(1.06) brightness(1.05);
            border-color: rgba(255,255,255,0.30);
            box-shadow:
                0 2px 2px rgba(0,0,0,0.24),
                0 14px 24px rgba(0,0,0,0.30),
                0 32px 58px rgba(0,0,0,0.38),
                0 0 36px rgba(0,212,255,0.15),
                inset 0 1px 0 rgba(255,255,255,0.32),
                inset 0 -18px 28px -8px rgba(0,0,0,0.26),
                inset 11px 0 22px -15px rgba(255,255,255,0.17),
                inset -11px 0 22px -15px rgba(120,170,255,0.13);
            /* "Lifting a glass panel": a small, stable elevation only —
               no tilt, no parallax, no rotation. The card's position
               and orientation never change; only its height off the
               page does, by a few px. */
            transform: translateY(-3px);
        }}
        .metric-card:active, .rec-card:active, .mode-card:active, .toggle-card:active, .settings-card:active {{
            transform: translateY(-1px) scale(0.99);
            transition: transform 0.08s ease;
        }}
        .mode-card.selected {{
            border-color: rgba(0,212,255,0.5);
            box-shadow:
                0 16px 34px rgba(0,0,0,0.4),
                inset 0 1px 0 rgba(255,255,255,0.14),
                0 0 26px rgba(0,212,255,0.16);
        }}


        /* ---- Elevation: dialogs / expanders / popovers - highest blur of all ---- */
        [data-testid="stExpander"] details,
        [data-testid="stExpander"] summary,
        [data-testid="stDialog"] > div,
        [data-testid="stPopover"] > div {{
            background:
                linear-gradient(180deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.02) 45%, rgba(0,0,0,0.05) 100%),
                linear-gradient(145deg, rgba(23,27,36,0.72), rgba(12,14,20,0.68)) !important;
            backdrop-filter: blur(34px) saturate(150%) !important;
            -webkit-backdrop-filter: blur(34px) saturate(150%) !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            border-radius: 18px !important;
            box-shadow:
                0 20px 46px rgba(0,0,0,0.5),
                inset 0 1px 0 rgba(255,255,255,0.14) !important;
            animation: dialogFadeScale 0.3s cubic-bezier(0.22,1,0.36,1) both;
        }}

        /* ---- Elevation: large hero/summary cards - least transparent of the "content" tier ---- */
        .ai-greeting-block, .ai-summary-box, .mood-indicator {{
            background:
                linear-gradient(180deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.015) 45%, rgba(0,0,0,0.04) 100%),
                linear-gradient(145deg, rgba(var(--adaptive-tint-rgb), var(--adaptive-tint-alpha)), rgba(var(--adaptive-tint-rgb), 0)),
                linear-gradient(145deg, rgba(23,27,36,0.55), rgba(16,19,26,0.50));
            box-shadow:
                0 10px 30px rgba(0,0,0,0.38),
                inset 0 1px 0 rgba(255,255,255,0.10),
                0 0 26px rgba(0,212,255,0.06);
            animation-delay: 0s;
        }}

        /* ---- Elevation: notifications (recommendations / ai-line / alert-line) - brighter glass ---- */
        .rec-card, .ai-line {{
            background:
                linear-gradient(180deg, rgba(255,255,255,0.10) 0%, rgba(255,255,255,0.02) 100%),
                linear-gradient(145deg, rgba(0,212,255,0.10), rgba(0,212,255,0.02));
            backdrop-filter: blur(14px) saturate(140%);
            -webkit-backdrop-filter: blur(14px) saturate(140%);
            animation-delay: 1.2s;
        }}
        .alert-line {{
            background:
                linear-gradient(180deg, rgba(255,255,255,0.09) 0%, rgba(255,255,255,0.02) 100%),
                linear-gradient(145deg, rgba(243,156,18,0.10), rgba(243,156,18,0.02));
            backdrop-filter: blur(14px) saturate(140%);
            -webkit-backdrop-filter: blur(14px) saturate(140%);
        }}

        /* ---- Elevation: floating AI companion - highest transparency of all ---- */
        .companion-float {{
            background:
                linear-gradient(180deg, rgba(255,255,255,0.08) 0%, rgba(255,255,255,0.01) 100%),
                linear-gradient(145deg, rgba(0,212,255,0.08), rgba(0,212,255,0.015));
            backdrop-filter: blur(24px) saturate(150%);
            -webkit-backdrop-filter: blur(24px) saturate(150%);
            border: 1px solid rgba(0,212,255,0.22);
            box-shadow:
                0 10px 30px rgba(0,0,0,0.35),
                inset 0 1px 0 rgba(255,255,255,0.14),
                0 0 30px rgba(0,212,255,0.10);
            animation-delay: 2s;
        }}

        /* ---- Elevation: navigation rail - darker, least transparent (grounds the layout) ---- */
        .nav-rail div[data-testid="stButton"] > button {{
            background: linear-gradient(145deg, rgba(8,10,14,0.62), rgba(6,8,12,0.55));
            backdrop-filter: blur(22px) saturate(130%);
            -webkit-backdrop-filter: blur(22px) saturate(130%);
            transition: transform 0.25s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.2s ease, background 0.2s ease;
        }}
        .nav-rail div[data-testid="stButton"] > button:hover {{
            background: linear-gradient(145deg, rgba(12,14,20,0.68), rgba(8,10,16,0.6));
            transform: translateX(2px);
        }}
        .nav-rail div[data-testid="stButton"] > button[kind="primary"] {{
            background: linear-gradient(145deg, rgba(0,212,255,0.24), rgba(0,212,255,0.08));
            box-shadow: 0 0 22px rgba(0,212,255,0.16);
        }}

        /* ---- Elevation: small widgets (hero stats) - more transparent ---- */
        .hero-stat {{
            background: linear-gradient(145deg, rgba(255,255,255,0.05), rgba(255,255,255,0.01));
            backdrop-filter: blur(12px) saturate(130%);
            -webkit-backdrop-filter: blur(12px) saturate(130%);
        }}

        /* ---- Typography polish: soft white, muted secondary text (never pure black) ---- */
        .stApp, .stApp p, .stApp span, .stApp label {{
            color: #eef1f7;
        }}
    </style>
    """, unsafe_allow_html=True)

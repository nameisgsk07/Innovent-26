"""
driver_view.py
---------------
The Driver View entry point. As of this revision, Driver View has been
rebuilt around a Tesla-style layout: a fixed left navigation rail with
seven major sections, a static (non-interactive) EV hero illustration on
the right with live battery/trip/range values and rotating AI
Recommendation cards, and section content in the middle. See
utils/driver_shell.py for the shell and utils/driver_sections.py for
each section's content.

This replaces the previous design, which rendered a single hand-drawn
SVG vehicle with clickable component hotspots (utils/vehicle_experience.py).
That file is left in the repo, unused, in case its animation techniques
are useful again later, but per the latest design brief the vehicle
visualization is now a plain static image with no hotspots.
"""

import streamlit as st

from utils import driver_shell


def render(state: dict, score_info: dict):
    driver_shell.render(state, score_info, demo_mode=st.session_state.get("demo_mode", False))

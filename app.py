"""
Globe Quiz — click-the-country geography game.

How it works
------------
- A world GeoJSON (country polygons + ISO-3 ids) is loaded once, cached,
  and flattened into a compact {id, name, rings} structure per country.
- The globe itself is a small custom Streamlit component (see
  frontend/index.html): plain SVG with a hand-rolled orthographic
  projection in vanilla JS. Dragging rotates the globe; clicking fires a
  native browser click on whichever country's <path> element is under
  the cursor, which is what gives us exact, reliable point-in-border hit
  testing without depending on any third-party chart library's click
  events (which turned out not to fire reliably for geo/globe charts).
- A country name is shown in a box; each click is compared against the
  target country's ISO-3 id and scored.

Run with:
    pip install -r requirements.txt
    streamlit run app.py
"""

import os
import random

import requests
import streamlit as st
import streamlit.components.v1 as components

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

GEOJSON_URL = (
    "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
)

LAND_COLOR = "#3a7d44"
OCEAN_COLOR = "#1b4f72"
HIGHLIGHT_COLOR = "#f4d35e"

st.set_page_config(page_title="Globe Quiz", page_icon="🌍", layout="wide")

_component_func = components.declare_component(
    "globe_quiz_map",
    path=os.path.join(os.path.dirname(__file__), "frontend"),
)


def globe_map(countries, highlight_id=None, height=600, key=None):
    return _component_func(
        countries=countries,
        land_color=LAND_COLOR,
        ocean_color=OCEAN_COLOR,
        highlight_color=HIGHLIGHT_COLOR,
        highlight_id=highlight_id,
        height=height,
        key=key,
        default=None,
    )


# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------


@st.cache_data(show_spinner="Loading world map...")
def load_geojson():
    resp = requests.get(GEOJSON_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _flatten_rings(geometry):
    """Return a flat list of rings (each a list of [lon, lat]) for a
    Polygon or MultiPolygon geometry. Holes are just additional rings —
    the frontend draws with an even-odd fill rule, so holes and separate
    landmasses both come out correct without special-casing."""
    gtype = geometry.get("type")
    coords = geometry.get("coordinates") or []
    rings = []
    if gtype == "Polygon":
        rings.extend(coords)
    elif gtype == "MultiPolygon":
        for poly in coords:
            rings.extend(poly)
    return rings


@st.cache_data(show_spinner=False)
def build_countries(_geojson):
    """Compact per-country data for the frontend, plus the quiz-eligible
    subset (countries with a real ISO-3 code)."""
    compact = []
    quiz_pool = []
    seen = set()
    for feature in _geojson["features"]:
        cid = feature.get("id")
        name = feature.get("properties", {}).get("name")
        geometry = feature.get("geometry")
        if not cid or not name or not geometry or cid in seen:
            continue
        rings = _flatten_rings(geometry)
        if not rings:
            continue
        # round coordinates - ~1km precision is plenty for a globe this
        # size and keeps the payload sent to the browser much smaller
        rounded = [[[round(lon, 2), round(lat, 2)] for lon, lat in ring] for ring in rings]
        compact.append({"id": cid, "name": name, "rings": rounded})
        seen.add(cid)
        if cid != "-99" and len(cid) == 3:
            quiz_pool.append({"id": cid, "name": name})
    return compact, quiz_pool


geojson_data = load_geojson()
all_countries, quiz_countries = build_countries(geojson_data)
id_to_name = {c["id"]: c["name"] for c in quiz_countries}

# --------------------------------------------------------------------------
# Session state / game logic
# --------------------------------------------------------------------------


def new_pool():
    pool = quiz_countries.copy()
    random.shuffle(pool)
    return pool


def pick_next_target():
    if not st.session_state.pool:
        st.session_state.pool = new_pool()
        if (
            len(st.session_state.pool) > 1
            and st.session_state.pool[-1]["id"] == st.session_state.get("target", {}).get("id")
        ):
            st.session_state.pool.insert(0, st.session_state.pool.pop())
    st.session_state.target = st.session_state.pool.pop()
    st.session_state.highlight_id = None


def init_game():
    st.session_state.score = 0
    st.session_state.attempts = 0
    st.session_state.streak = 0
    st.session_state.best_streak = 0
    st.session_state.pool = new_pool()
    st.session_state.message = None
    st.session_state.message_type = None
    st.session_state.highlight_id = None
    st.session_state.last_nonce = None
    pick_next_target()


if "target" not in st.session_state:
    init_game()


def process_click(location_id):
    st.session_state.attempts += 1
    target_id = st.session_state.target["id"]
    target_name = st.session_state.target["name"]

    if location_id is None:
        st.session_state.message = "🌊 That's open ocean — click on land!"
        st.session_state.message_type = "info"
        st.session_state.streak = 0
    elif location_id == target_id:
        st.session_state.score += 1
        st.session_state.streak += 1
        st.session_state.best_streak = max(st.session_state.best_streak, st.session_state.streak)
        st.session_state.message = f"✅ Correct! That's {target_name}."
        st.session_state.message_type = "success"
        st.session_state.highlight_id = target_id
        pick_next_target()
    else:
        clicked_name = id_to_name.get(location_id, "somewhere unmarked")
        st.session_state.message = f"❌ Nope, that's {clicked_name}. Keep looking for {target_name}!"
        st.session_state.message_type = "error"
        st.session_state.streak = 0


def skip_target():
    st.session_state.message = f"⏭️ Skipped. That was {st.session_state.target['name']}."
    st.session_state.message_type = "info"
    st.session_state.streak = 0
    pick_next_target()


# --------------------------------------------------------------------------
# UI
# --------------------------------------------------------------------------

with st.sidebar:
    st.title("🌍 Globe Quiz")
    st.write(
        "A country name appears — find it on the globe and click inside its "
        "borders. Drag the globe to rotate it."
    )
    st.divider()
    st.metric("Score", st.session_state.score)
    st.metric("Attempts", st.session_state.attempts)
    accuracy = (
        f"{100 * st.session_state.score / st.session_state.attempts:.0f}%"
        if st.session_state.attempts
        else "—"
    )
    st.metric("Accuracy", accuracy)
    st.metric("Current streak", st.session_state.streak)
    st.metric("Best streak", st.session_state.best_streak)
    st.divider()
    if st.button("🔄 Restart game", use_container_width=True):
        init_game()
        st.rerun()

st.markdown(
    f"""
    <div style="
        background:{OCEAN_COLOR};
        color:white;
        padding:18px 24px;
        border-radius:14px;
        text-align:center;
        font-size:26px;
        font-weight:700;
        letter-spacing:0.5px;
        margin-bottom:14px;
    ">
        Find: {st.session_state.target['name']}
    </div>
    """,
    unsafe_allow_html=True,
)

col_map, col_side = st.columns([4, 1])

with col_side:
    st.button("⏭️ Skip", on_click=skip_target, use_container_width=True)

with col_map:
    result = globe_map(
        all_countries,
        highlight_id=st.session_state.highlight_id,
        height=600,
        key="globe",
    )

if result and result.get("nonce") != st.session_state.last_nonce:
    st.session_state.last_nonce = result.get("nonce")
    process_click(result.get("id"))
    st.rerun()

if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "error":
        st.error(st.session_state.message)
    else:
        st.info(st.session_state.message)

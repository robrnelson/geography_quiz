"""
Globe Quiz — click-the-country geography game.

How it works
------------
- A world GeoJSON (country polygons + ISO-3 ids) is loaded once and cached.
- The globe is drawn as a Plotly Choropleth on an orthographic projection,
  every country painted the same "land" color and every ocean pixel the
  same "ocean" color, with no borders/labels drawn — just a plain globe
  you can drag to rotate, exactly like a blue-marble Earth.
- A country name is shown in a box. You click anywhere on the globe;
  Plotly's choropleth click event tells us the ISO-3 id of whatever
  country polygon was actually clicked (this is what gives us free,
  exact point-in-country-border hit testing — no manual polygon math
  needed). We compare that id to the target and score accordingly.

Run with:
    pip install -r requirements.txt
    streamlit run app.py
"""

import random

import plotly.graph_objects as go
import requests
import streamlit as st
from streamlit_plotly_events import plotly_events

# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

GEOJSON_URL = (
    "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json"
)

LAND_COLOR = "#3a7d44"      # muted green landmass
OCEAN_COLOR = "#1b4f72"     # deep blue ocean
SPACE_COLOR = "#03050c"     # background behind the globe
FLASH_CORRECT = "#f4d35e"   # gold highlight flash on a correct click
HIGHLIGHT_COLOR = FLASH_CORRECT

st.set_page_config(page_title="Globe Quiz", page_icon="🌍", layout="wide")

# --------------------------------------------------------------------------
# Data loading
# --------------------------------------------------------------------------


@st.cache_data(show_spinner="Loading world map...")
def load_geojson():
    resp = requests.get(GEOJSON_URL, timeout=20)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(show_spinner=False)
def build_country_list(_geojson):
    """Return list of {id, name} for countries with a usable ISO-3 id."""
    countries = []
    seen_ids = set()
    for feature in _geojson["features"]:
        cid = feature.get("id")
        name = feature.get("properties", {}).get("name")
        if not cid or not name:
            continue
        if cid in ("-99",) or len(cid) != 3:
            continue
        if cid in seen_ids:
            continue
        seen_ids.add(cid)
        countries.append({"id": cid, "name": name})
    return countries


geojson_data = load_geojson()
all_countries = build_country_list(geojson_data)
id_to_name = {c["id"]: c["name"] for c in all_countries}
all_ids = [c["id"] for c in all_countries]

# --------------------------------------------------------------------------
# Session state / game logic
# --------------------------------------------------------------------------


def new_pool():
    pool = all_countries.copy()
    random.shuffle(pool)
    return pool


def pick_next_target():
    if not st.session_state.pool:
        st.session_state.pool = new_pool()
        # avoid immediately repeating the just-finished target if possible
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
    st.session_state.render_id = 0
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

    # remount the plotly-events component so it forgets this click and
    # doesn't hand it back to us again on the next unrelated rerun
    st.session_state.render_id += 1


def skip_target():
    st.session_state.message = f"⏭️ Skipped. That was {st.session_state.target['name']}."
    st.session_state.message_type = "info"
    st.session_state.streak = 0
    pick_next_target()
    st.session_state.render_id += 1


# --------------------------------------------------------------------------
# Figure
# --------------------------------------------------------------------------


def build_figure():
    z = [1] * len(all_ids)
    colors = [LAND_COLOR] * len(all_ids)
    if st.session_state.highlight_id in all_ids:
        colors[all_ids.index(st.session_state.highlight_id)] = FLASH_CORRECT

    # a discrete colorscale built from the per-country color list via z-index trick
    n = len(all_ids)
    if n > 1:
        colorscale = [[i / (n - 1), colors[i]] for i in range(n)]
    else:
        colorscale = [[0, colors[0]], [1, colors[0]]]
    z = list(range(n))

    fig = go.Figure(
        go.Choropleth(
            geojson=geojson_data,
            locations=all_ids,
            z=z,
            featureidkey="id",
            colorscale=colorscale,
            showscale=False,
            marker_line_width=0.4,
            marker_line_color=LAND_COLOR,
            hoverinfo="skip",
        )
    )

    fig.update_geos(
        projection_type="orthographic",
        showland=False,
        showocean=True,
        oceancolor=OCEAN_COLOR,
        showcountries=False,
        showcoastlines=False,
        showframe=False,
        bgcolor=SPACE_COLOR,
    )

    fig.update_layout(
        paper_bgcolor=SPACE_COLOR,
        plot_bgcolor=SPACE_COLOR,
        margin=dict(l=0, r=0, t=0, b=0),
        height=650,
    )
    return fig


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
    fig = build_figure()
    clicked_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=650,
        override_width="100%",
        key=f"globe_{st.session_state.render_id}",
    )

if clicked_points:
    location_id = clicked_points[0].get("location")
    process_click(location_id)
    st.rerun()

if st.session_state.message:
    if st.session_state.message_type == "success":
        st.success(st.session_state.message)
    elif st.session_state.message_type == "error":
        st.error(st.session_state.message)
    else:
        st.info(st.session_state.message)
